"""Durable SQLite-backed ``AuditLogService`` implementation.

Every write commits before ``record`` or ``import_archive`` returns, so once
either call returns, the event -- and, for an import, the advanced manifest
-- is already on disk: a crash or restart immediately afterward cannot lose
it, and a separate process opening the same database file sees exactly what
was committed. ``durable_repair_key`` is computed at write time and stored
in its own column beside the event row it describes, so a later repair pass
can read it back without recomputing it from a live event stream that may
itself be the thing under repair.

The ``events`` table has no uniqueness constraint on ``event_id`` or
``repair_key``: two rows recorded from the same exact observation -- same
actor, action, outcome, and recorded time, and therefore the same content id
and the same repair key -- must both survive ingestion when only their
metadata differs, so nothing here can reject or silently collapse a second
identical insert. ``repair_duplicates`` is the one exception: it is a
separate, explicitly invoked pass, never run as a side effect of ingestion,
that permanently removes a later row once it is confirmed to share its
earliest sibling's repair group.

The ``import_manifests`` table is not part of that append-only log; it is a
resume pointer for one import batch, and is deliberately overwritten as an
interrupted import's progress advances. Persisting it durably is what makes
resume restart-safe: a new instance opened after a real process restart can
reconstruct the resume point from this table alone, with no in-memory
manifest object carried over.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .import_resume import (
    ChecksumMismatchError,
    QuarantinedRow,
    compute_prefix_checksum,
    parse_candidate,
    read_pending_rows,
)
from .integrity import durable_repair_key, repair_group_key
from .models import ArchiveCandidate, AuditEvent, ImportManifest, content_digest
from .service import AuditLogService

__all__ = ["SQLiteAuditLogService", "ChecksumMismatchError", "QuarantinedRow"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    sequence INTEGER NOT NULL,
    event_id TEXT NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    outcome TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    source_version INTEGER NOT NULL,
    metadata TEXT NOT NULL,
    repair_key TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS import_manifests (
    batch_id TEXT PRIMARY KEY,
    archive_ref TEXT NOT NULL,
    resume_offset INTEGER NOT NULL,
    imported_content_ids TEXT NOT NULL,
    completed INTEGER NOT NULL,
    source_checksum TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS import_quarantine (
    batch_id TEXT NOT NULL,
    offset INTEGER NOT NULL,
    raw TEXT NOT NULL,
    reason TEXT NOT NULL,
    PRIMARY KEY (batch_id, offset)
);
"""


class SQLiteAuditLogService(AuditLogService):
    """``AuditLogService`` backed by a durable SQLite file.

    Two independent instances opened against the same ``db_path`` -- whether
    in the same process after a restart, or in a separate process entirely
    -- see the same committed rows, since nothing needed to reconstruct the
    trail or an in-progress import is held only in memory.
    """

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        # A generous busy timeout so a second connection resuming the same
        # batch waits for the first to commit instead of failing outright
        # with "database is locked" (see resume_archive_import).
        self._conn = sqlite3.connect(self._db_path, timeout=15)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> SQLiteAuditLogService:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def _next_sequence(self) -> int:
        row = self._conn.execute("SELECT COALESCE(MAX(sequence), 0) FROM events").fetchone()
        return row[0] + 1

    def _known_event_ids(self) -> set[str]:
        rows = self._conn.execute("SELECT event_id FROM events").fetchall()
        return {row[0] for row in rows}

    def _insert_event(
        self,
        *,
        sequence: int,
        actor: str,
        action: str,
        outcome: str,
        recorded_at: str,
        metadata: dict[str, Any],
    ) -> AuditEvent:
        event_id = content_digest(actor, action, outcome, recorded_at)
        # actor/action/outcome are accepted here (and not just recorded_at
        # and content_id) so the persisted key always reflects the exact
        # signature durable_repair_key documents, even though its current
        # implementation folds down to complete_event_identity(recorded_at,
        # content_id); metadata is never one of the arguments.
        repair_key = durable_repair_key(actor, action, outcome, recorded_at, event_id)
        event = AuditEvent(
            event_id=event_id,
            sequence=sequence,
            actor=actor,
            action=action,
            outcome=outcome,
            recorded_at=recorded_at,
            metadata=dict(metadata),
        )
        self._conn.execute(
            "INSERT INTO events "
            "(sequence, event_id, actor, action, outcome, recorded_at, source_version, metadata, repair_key) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                sequence,
                event_id,
                actor,
                action,
                outcome,
                recorded_at,
                event.source_version,
                json.dumps(metadata),
                repair_key,
            ),
        )
        return event

    def record(
        self,
        actor: str,
        action: str,
        outcome: str,
        recorded_at: str,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        # No dedup check against existing rows: a repeated exact observation
        # (same identity, possibly different metadata) is always a new
        # append-only row, never merged into or rejected in favor of an
        # earlier one.
        event = self._insert_event(
            sequence=self._next_sequence(),
            actor=actor,
            action=action,
            outcome=outcome,
            recorded_at=recorded_at,
            metadata=dict(metadata or {}),
        )
        self._conn.commit()
        return event

    @staticmethod
    def _row_to_event(row: tuple) -> AuditEvent:
        sequence, event_id, actor, action, outcome, recorded_at, source_version, metadata = row
        return AuditEvent(
            event_id=event_id,
            sequence=sequence,
            actor=actor,
            action=action,
            outcome=outcome,
            recorded_at=recorded_at,
            source_version=source_version,
            metadata=json.loads(metadata),
        )

    def events(self) -> tuple[AuditEvent, ...]:
        rows = self._conn.execute(
            "SELECT sequence, event_id, actor, action, outcome, recorded_at, source_version, metadata "
            "FROM events ORDER BY sequence"
        ).fetchall()
        return tuple(self._row_to_event(row) for row in rows)

    def find(
        self, *, actor: str | None = None, action: str | None = None
    ) -> tuple[AuditEvent, ...]:
        clauses = []
        params: list[str] = []
        if actor is not None:
            clauses.append("actor = ?")
            params.append(actor)
        if action is not None:
            clauses.append("action = ?")
            params.append(action)
        query = (
            "SELECT sequence, event_id, actor, action, outcome, recorded_at, source_version, metadata "
            "FROM events"
        )
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY sequence"
        rows = self._conn.execute(query, params).fetchall()
        return tuple(self._row_to_event(row) for row in rows)

    def verify(self) -> tuple[AuditEvent, ...]:
        return tuple(event for event in self.events() if event.event_id != event.recomputed_id())

    def repair_key_for(self, event: AuditEvent) -> str | None:
        """Return the repair key persisted beside ``event``'s own row, if any."""

        row = self._conn.execute(
            "SELECT repair_key FROM events WHERE sequence = ?", (event.sequence,)
        ).fetchone()
        return row[0] if row else None

    def repair_duplicates(self) -> tuple[AuditEvent, ...]:
        """Permanently remove later exact duplicates, keeping the earliest row per group.

        Grouping goes only through ``repair_group_key``, recomputed here from
        each row's own persisted ``repair_key``, ``recorded_at``, and
        ``event_id`` -- never from anything a caller supplies. A row whose
        persisted key does not match its own recomputed complete identity
        (for example a value truncated or altered after the fact) is grouped
        by the recomputed identity anyway, so a corrupted stored key can
        neither merge it into the wrong group nor shield it from a real
        duplicate's group. Runs as one transaction: either every later
        duplicate found is removed, or, on error, none is.
        """

        self._conn.execute("BEGIN IMMEDIATE")
        try:
            rows = self._conn.execute(
                "SELECT sequence, event_id, actor, action, outcome, recorded_at, "
                "source_version, metadata, repair_key FROM events ORDER BY sequence"
            ).fetchall()

            kept_sequence_for_group: dict[str, int] = {}
            duplicate_rows: list[tuple] = []
            for row in rows:
                sequence, event_id, actor, action, outcome, recorded_at, source_version, metadata, stored_key = row
                group_key = repair_group_key(stored_key, recorded_at, event_id)
                if group_key in kept_sequence_for_group:
                    duplicate_rows.append(row)
                else:
                    kept_sequence_for_group[group_key] = sequence

            removed = tuple(
                AuditEvent(
                    event_id=row[1],
                    sequence=row[0],
                    actor=row[2],
                    action=row[3],
                    outcome=row[4],
                    recorded_at=row[5],
                    source_version=row[6],
                    metadata=json.loads(row[7]),
                )
                for row in duplicate_rows
            )
            if duplicate_rows:
                self._conn.executemany(
                    "DELETE FROM events WHERE sequence = ?",
                    [(row[0],) for row in duplicate_rows],
                )
        except Exception:
            self._conn.rollback()
            raise
        else:
            self._conn.commit()
        return removed

    def load_manifest(self, batch_id: str) -> ImportManifest | None:
        """Return the durably persisted manifest for ``batch_id``, if any.

        A caller resuming an interrupted import after a real process restart
        has no in-memory manifest object left; this reconstructs one from
        the same row ``import_archive`` last wrote, so the resume point
        survives the restart instead of forcing the archive to be re-read
        from its very start.
        """

        row = self._conn.execute(
            "SELECT archive_ref, resume_offset, imported_content_ids, completed, source_checksum "
            "FROM import_manifests WHERE batch_id = ?",
            (batch_id,),
        ).fetchone()
        if row is None:
            return None
        archive_ref, resume_offset, imported_content_ids, completed, source_checksum = row
        return ImportManifest(
            batch_id=batch_id,
            archive_ref=archive_ref,
            resume_offset=resume_offset,
            imported_content_ids=frozenset(json.loads(imported_content_ids)),
            completed=bool(completed),
            source_checksum=source_checksum,
        )

    def _persist_manifest(self, manifest: ImportManifest) -> None:
        self._conn.execute(
            "INSERT INTO import_manifests "
            "(batch_id, archive_ref, resume_offset, imported_content_ids, completed, source_checksum) "
            "VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(batch_id) DO UPDATE SET "
            "archive_ref = excluded.archive_ref, "
            "resume_offset = excluded.resume_offset, "
            "imported_content_ids = excluded.imported_content_ids, "
            "completed = excluded.completed, "
            "source_checksum = excluded.source_checksum",
            (
                manifest.batch_id,
                manifest.archive_ref,
                manifest.resume_offset,
                json.dumps(sorted(manifest.imported_content_ids)),
                int(manifest.completed),
                manifest.source_checksum,
            ),
        )

    def _insert_quarantine(self, batch_id: str, offset: int, raw: str, reason: str) -> None:
        # INSERT OR IGNORE: quarantining the same row at the same offset a
        # second time (e.g. a retried call that never got past this point)
        # must not raise or create a duplicate record.
        self._conn.execute(
            "INSERT OR IGNORE INTO import_quarantine (batch_id, offset, raw, reason) "
            "VALUES (?, ?, ?, ?)",
            (batch_id, offset, raw, reason),
        )

    def quarantined_rows(self, batch_id: str) -> tuple[QuarantinedRow, ...]:
        """Return every row quarantined for ``batch_id``, in offset order."""

        rows = self._conn.execute(
            "SELECT offset, raw, reason FROM import_quarantine "
            "WHERE batch_id = ? ORDER BY offset",
            (batch_id,),
        ).fetchall()
        return tuple(
            QuarantinedRow(batch_id=batch_id, offset=offset, raw=raw, reason=reason)
            for offset, raw, reason in rows
        )

    def resume_archive_import(
        self, batch_id: str, archive_path: str | Path
    ) -> tuple[ImportManifest, tuple[AuditEvent, ...], tuple[QuarantinedRow, ...]]:
        """Resume (or begin) an interrupted archive import from its durable manifest.

        Only the rows of ``archive_path`` beyond the manifest's
        ``resume_offset`` are read or considered for import: an
        already-consumed row is never reopened or re-validated. Before doing
        that, the checksum of the already-consumed prefix is re-verified
        against what it was the last time this batch made progress; if the
        source was edited or replaced underneath an interrupted import, this
        raises :class:`ChecksumMismatchError` instead of resuming against it.
        A row that fails to parse into a valid candidate is quarantined
        (``import_quarantine``) rather than raised or dropped, and does not
        stop the rest of the batch from being imported.

        The whole call runs as one transaction, opened with an immediate
        write lock: two callers resuming the same batch concurrently
        serialize against each other instead of both computing "this
        content id is new" from a stale read and racing to insert the same
        event twice. A caller either sees this call's entire progress or
        none of it, and calling this again with the same or a grown source
        does no new work for anything already accounted for -- resuming an
        already-complete import is a no-op.
        """

        archive_path = Path(archive_path)
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            manifest = self.load_manifest(batch_id)
            if manifest is None:
                manifest = ImportManifest(batch_id=batch_id, archive_ref=str(archive_path))

            if manifest.resume_offset > 0:
                expected = manifest.source_checksum
                actual = compute_prefix_checksum(archive_path, manifest.resume_offset)
                if expected != actual:
                    raise ChecksumMismatchError(
                        f"source for batch {batch_id!r} changed since the last import "
                        f"at offset {manifest.resume_offset} "
                        f"(expected checksum {expected!r}, found {actual!r})"
                    )

            known_ids = set(manifest.imported_content_ids) | self._known_event_ids()
            pending_rows = read_pending_rows(archive_path, manifest.resume_offset)
            sequence = self._next_sequence()
            appended: list[AuditEvent] = []
            newly_imported: list[str] = []
            quarantined_this_call: list[QuarantinedRow] = []
            offset = manifest.resume_offset

            for row in pending_rows:
                offset = row.offset
                try:
                    candidate = parse_candidate(row)
                except ValueError as exc:
                    self._insert_quarantine(batch_id, row.offset, row.text, str(exc))
                    quarantined_this_call.append(
                        QuarantinedRow(
                            batch_id=batch_id, offset=row.offset, raw=row.text, reason=str(exc)
                        )
                    )
                    continue

                content_id = candidate.content_id()
                if content_id in known_ids:
                    continue

                event = self._insert_event(
                    sequence=sequence,
                    actor=candidate.actor,
                    action=candidate.action,
                    outcome=candidate.outcome,
                    recorded_at=candidate.recorded_at,
                    metadata={"source_ref": candidate.source_ref} if candidate.source_ref else {},
                )
                sequence += 1
                known_ids.add(content_id)
                newly_imported.append(content_id)
                appended.append(event)

            manifest = manifest.advanced(
                offset,
                newly_imported,
                completed=True,
                source_checksum=compute_prefix_checksum(archive_path, offset),
            )
            self._persist_manifest(manifest)
        except Exception:
            self._conn.rollback()
            raise
        else:
            self._conn.commit()
        return manifest, tuple(appended), tuple(quarantined_this_call)

    def import_archive(
        self, manifest: ImportManifest, candidates: Iterable[ArchiveCandidate]
    ) -> tuple[ImportManifest, tuple[AuditEvent, ...]]:
        known_ids = set(manifest.imported_content_ids) | self._known_event_ids()
        appended: list[AuditEvent] = []
        newly_imported: list[str] = []
        offset = manifest.resume_offset
        sequence = self._next_sequence()

        for candidate in candidates:
            offset += 1
            content_id = candidate.content_id()
            if content_id in known_ids:
                continue
            event = self._insert_event(
                sequence=sequence,
                actor=candidate.actor,
                action=candidate.action,
                outcome=candidate.outcome,
                recorded_at=candidate.recorded_at,
                metadata={"source_ref": candidate.source_ref} if candidate.source_ref else {},
            )
            sequence += 1
            appended.append(event)
            newly_imported.append(content_id)
            known_ids.add(content_id)

        advanced = manifest.advanced(offset, newly_imported)
        self._persist_manifest(advanced)
        self._conn.commit()
        return advanced, tuple(appended)
