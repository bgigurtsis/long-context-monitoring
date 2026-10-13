"""SQLite-backed implementation of :class:`~auditlog.service.AuditLogService`.

Durable storage for the same append-only model :mod:`auditlog.store` writes
to a JSON file, but persisted in a single SQLite database instead: every
public method opens its own connection, commits before returning, and closes
it, so a write from one process is immediately visible to any other process
that opens the same path afterward. No code path here ever issues ``UPDATE``
or ``DELETE`` against the ``events`` table -- appending is the only way rows
are added, existing rows are never edited, removed, or renumbered, and the
derived indexes this store keeps (``repair``'s SQL indexes on ``actor`` and
``action``) live inside the same file, so all state stays under the single
path the caller chose.

Concurrency is optimistic: ``sequence`` is a unique column assigned by
reading the current tail and adding one, so two writers racing for the same
next sequence collide on that uniqueness constraint (SQLite enforces it
even under concurrent connections, serialized by its own file locking) and
the loser retries with a freshly read tail rather than failing outright.
``record`` and ``import_events`` both accept an idempotency key so a caller
retrying an uncertain call -- one whose response was lost, not necessarily
one that collided -- is replayed rather than duplicated.

Row order (SQLite's own autoincrementing ``row_id``, independent of the
``sequence`` value a row was given) lets integrity checks detect a
reordering tamper -- two rows whose ``sequence`` values were swapped
directly in storage -- that a content-digest check and a gap check both
miss, since neither depends on which row holds which sequence.

:mod:`auditlog.compatibility` supplies the compatibility reader used to
bootstrap a fresh store from the legacy archive fixture (and, alongside it,
a native fixture): both normalize into the same
:class:`~auditlog.models.AuditEvent` model before being appended here.
``import_events`` generalizes that one-shot bootstrap into a repeatable,
resumable batch append: interrupted midway (this process died after
recording the batch as pending but before finishing it), a later ``repair``
call finishes applying it; called again with the same events, it is a
no-op; called with a batch overlapping one already applied, only the
genuinely new events are appended.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import compatibility
from .models import AuditEvent, content_digest
from .service import (
    AuditLogService,
    ConflictError,
    ImportReport,
    IntegrityError,
    RepairReport,
    UnsupportedOperationError,
    batch_fingerprint,
    idempotency_fingerprint,
    resolve_report_path,
)

NATIVE_STORE_VERSION = 2
MAX_OPTIMISTIC_RETRIES = 8

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    row_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sequence INTEGER NOT NULL UNIQUE,
    event_id TEXT NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    outcome TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    source_version INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS event_metadata (
    sequence INTEGER NOT NULL REFERENCES events(sequence),
    key TEXT NOT NULL,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS idempotency_keys (
    idempotency_key TEXT PRIMARY KEY,
    sequence INTEGER NOT NULL REFERENCES events(sequence),
    fingerprint TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS import_batches (
    idempotency_key TEXT PRIMARY KEY,
    fingerprint TEXT NOT NULL,
    status TEXT NOT NULL,
    payload TEXT NOT NULL,
    requested_count INTEGER NOT NULL,
    applied_count INTEGER NOT NULL,
    duplicate_count INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _find_integrity_issues(events: list[AuditEvent]) -> tuple[tuple[int, ...], int | None]:
    corrupted = tuple(event.sequence for event in events if event.event_id != event.recomputed_id())
    gap_at = None
    for index, event in enumerate(events, start=1):
        if event.sequence != index:
            gap_at = index
            break
    return corrupted, gap_at


def _find_reordering(conn: sqlite3.Connection) -> tuple[int, ...]:
    """Detect rows whose physical insertion order disagrees with ascending sequence.

    ``row_id`` is SQLite's own autoincrementing insertion counter, entirely
    independent of the ``sequence`` value a row was assigned; normal
    ``INSERT``-only operation keeps them in lockstep. A tamper that swaps
    two rows' ``sequence`` values directly in storage changes neither a
    content digest (``event_id`` doesn't depend on ``sequence``) nor the
    set of sequence values present, so this is the only check that catches it.
    """

    physical = [row[0] for row in conn.execute("SELECT sequence FROM events ORDER BY row_id ASC")]
    if physical == sorted(physical):
        return ()
    return tuple(physical)


def event_payload(event: AuditEvent) -> dict[str, Any]:
    """The JSON-stable shape of one event: fixed key set, caller controls ordering."""

    return {
        "event_id": event.event_id,
        "sequence": event.sequence,
        "actor": event.actor,
        "action": event.action,
        "outcome": event.outcome,
        "recorded_at": event.recorded_at,
        "source_version": event.source_version,
        "metadata": event.metadata,
    }


def _event_from_payload(payload: dict[str, Any]) -> AuditEvent:
    return AuditEvent(
        event_id=payload["event_id"],
        sequence=payload["sequence"],
        actor=payload["actor"],
        action=payload["action"],
        outcome=payload["outcome"],
        recorded_at=payload["recorded_at"],
        source_version=payload.get("source_version", NATIVE_STORE_VERSION),
        metadata=payload.get("metadata", {}),
    )


def events_to_json(events: list[AuditEvent]) -> str:
    """Serialize events deterministically: sorted keys, caller-supplied (sequence) order."""

    return json.dumps([event_payload(event) for event in events], sort_keys=True)


class SqliteLogStore(AuditLogService):
    """The append-only trail durably persisted in a single SQLite file."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        conn = self._connect()
        try:
            conn.executescript(_SCHEMA)
            conn.commit()
        finally:
            conn.close()

    @property
    def path(self) -> Path:
        return self._path

    @property
    def store_root(self) -> Path:
        """The directory verification reports are written beneath."""

        return self._path.parent

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._path))
        conn.execute("PRAGMA foreign_keys = ON")
        # A concurrent writer blocks and waits for the lock instead of
        # failing immediately with "database is locked"; the retry loops
        # below then handle the remaining case, a genuine sequence collision.
        conn.execute("PRAGMA busy_timeout = 5000")
        return conn

    def _load_all_events(self, conn: sqlite3.Connection) -> list[AuditEvent]:
        rows = conn.execute(
            "SELECT sequence, event_id, actor, action, outcome, recorded_at, source_version "
            "FROM events ORDER BY sequence ASC"
        ).fetchall()
        metadata_by_sequence: dict[int, dict[str, Any]] = {}
        for sequence, key, value in conn.execute("SELECT sequence, key, value FROM event_metadata"):
            metadata_by_sequence.setdefault(sequence, {})[key] = json.loads(value)
        return [
            AuditEvent(
                event_id=event_id,
                sequence=sequence,
                actor=actor,
                action=action,
                outcome=outcome,
                recorded_at=recorded_at,
                source_version=source_version,
                metadata=metadata_by_sequence.get(sequence, {}),
            )
            for sequence, event_id, actor, action, outcome, recorded_at, source_version in rows
        ]

    def _insert_event(self, conn: sqlite3.Connection, event: AuditEvent) -> None:
        conn.execute(
            "INSERT INTO events (sequence, event_id, actor, action, outcome, recorded_at, source_version) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                event.sequence,
                event.event_id,
                event.actor,
                event.action,
                event.outcome,
                event.recorded_at,
                event.source_version,
            ),
        )
        for key, value in event.metadata.items():
            conn.execute(
                "INSERT INTO event_metadata (sequence, key, value) VALUES (?, ?, ?)",
                (event.sequence, key, json.dumps(value)),
            )

    def bootstrap_compatibility(
        self,
        *,
        legacy_payload: dict[str, Any] | None = None,
        current_payload: dict[str, Any] | None = None,
    ) -> list[AuditEvent]:
        """Seed an empty store via the compatibility reader in :mod:`auditlog.compatibility`.

        Only valid against a store with no existing history: bootstrapping
        never renumbers or replaces rows that are already durable.
        """

        conn = self._connect()
        try:
            if conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]:
                raise UnsupportedOperationError("cannot bootstrap a store that already has recorded history")
            events = compatibility.load_compatibility_events(
                legacy_payload=legacy_payload, current_payload=current_payload
            )
            for event in events:
                self._insert_event(conn, event)
            conn.commit()
            return events
        finally:
            conn.close()

    @classmethod
    def from_compatibility_fixtures(
        cls,
        path: str | Path,
        *,
        legacy_fixture_path: str | Path | None = None,
        current_fixture_path: str | Path | None = None,
    ) -> "SqliteLogStore":
        """Create a store at ``path`` and bootstrap it from on-disk fixture files."""

        store = cls(path)
        legacy_payload = (
            json.loads(Path(legacy_fixture_path).read_text(encoding="utf-8"))
            if legacy_fixture_path is not None
            else None
        )
        current_payload = (
            json.loads(Path(current_fixture_path).read_text(encoding="utf-8"))
            if current_fixture_path is not None
            else None
        )
        store.bootstrap_compatibility(legacy_payload=legacy_payload, current_payload=current_payload)
        return store

    def record(
        self,
        actor: str,
        action: str,
        outcome: str,
        *,
        metadata: dict[str, Any] | None = None,
        recorded_at: str | None = None,
        idempotency_key: str | None = None,
    ) -> AuditEvent:
        fingerprint = idempotency_fingerprint(actor, action, outcome, recorded_at, metadata)
        conn = self._connect()
        try:
            for _attempt in range(MAX_OPTIMISTIC_RETRIES):
                if idempotency_key is not None:
                    row = conn.execute(
                        "SELECT sequence, fingerprint FROM idempotency_keys WHERE idempotency_key = ?",
                        (idempotency_key,),
                    ).fetchone()
                    if row is not None:
                        existing_sequence, existing_fingerprint = row
                        if existing_fingerprint != fingerprint:
                            raise ConflictError(
                                f"idempotency key {idempotency_key!r} was already used with different inputs"
                            )
                        events_now = self._load_all_events(conn)
                        return next(e for e in events_now if e.sequence == existing_sequence)

                events = self._load_all_events(conn)
                corrupted, gap_at = _find_integrity_issues(events)
                reordered = _find_reordering(conn)
                if corrupted or gap_at is not None or reordered:
                    raise IntegrityError(
                        f"refusing to append onto a corrupted trail: corrupted sequences={list(corrupted)}, "
                        f"gap at sequence={gap_at}, reordered sequences={list(reordered)}; "
                        "run 'repair' for a full report"
                    )

                next_sequence = events[-1].sequence + 1 if events else 1
                stamp = recorded_at or _now_iso()
                event = AuditEvent(
                    event_id=content_digest(actor, action, outcome, stamp),
                    sequence=next_sequence,
                    actor=actor,
                    action=action,
                    outcome=outcome,
                    recorded_at=stamp,
                    source_version=NATIVE_STORE_VERSION,
                    metadata=dict(metadata or {}),
                )
                try:
                    self._insert_event(conn, event)
                    if idempotency_key is not None:
                        conn.execute(
                            "INSERT INTO idempotency_keys (idempotency_key, sequence, fingerprint) "
                            "VALUES (?, ?, ?)",
                            (idempotency_key, next_sequence, fingerprint),
                        )
                    conn.commit()
                    return event
                except sqlite3.IntegrityError:
                    conn.rollback()
                    continue
            raise ConflictError(
                f"could not append after {MAX_OPTIMISTIC_RETRIES} retries due to concurrent writers"
            )
        finally:
            conn.close()

    def query(
        self,
        *,
        actor: str | None = None,
        action: str | None = None,
        outcome: str | None = None,
        recorded_from: str | None = None,
        recorded_to: str | None = None,
    ) -> list[AuditEvent]:
        conn = self._connect()
        try:
            events = self._load_all_events(conn)
            reordered = _find_reordering(conn)
        finally:
            conn.close()

        corrupted, gap_at = _find_integrity_issues(events)
        if corrupted or gap_at is not None or reordered:
            raise IntegrityError(
                f"trail integrity check failed: corrupted sequences={list(corrupted)}, "
                f"gap at sequence={gap_at}, reordered sequences={list(reordered)}; "
                "run 'repair' for a full report"
            )
        if actor is not None:
            events = [event for event in events if event.actor == actor]
        if action is not None:
            events = [event for event in events if event.action == action]
        if outcome is not None:
            events = [event for event in events if event.outcome == outcome]
        if recorded_from is not None:
            events = [event for event in events if event.recorded_at >= recorded_from]
        if recorded_to is not None:
            events = [event for event in events if event.recorded_at <= recorded_to]
        return events

    def _apply_import_events(
        self, conn: sqlite3.Connection, events: list[AuditEvent]
    ) -> tuple[int, int]:
        """Append the events in ``events`` not already present, by ``event_id``.

        Safe to call again with the same or an overlapping batch: anything
        already present is counted as a duplicate and skipped rather than
        re-inserted, which is what makes a resumed or overlapping import
        converge on the union of unique events rather than double-counting.
        """

        applied = 0
        duplicates = 0
        for event in events:
            for _attempt in range(MAX_OPTIMISTIC_RETRIES):
                already_present = conn.execute(
                    "SELECT 1 FROM events WHERE event_id = ? LIMIT 1", (event.event_id,)
                ).fetchone()
                if already_present is not None:
                    duplicates += 1
                    break
                current = self._load_all_events(conn)
                next_sequence = current[-1].sequence + 1 if current else 1
                to_insert = replace(event, sequence=next_sequence)
                try:
                    self._insert_event(conn, to_insert)
                    conn.commit()
                    applied += 1
                    break
                except sqlite3.IntegrityError:
                    conn.rollback()
                    continue
            else:
                raise ConflictError(
                    f"could not import event {event.event_id!r} after "
                    f"{MAX_OPTIMISTIC_RETRIES} retries due to concurrent writers"
                )
        return applied, duplicates

    def _complete_pending_imports(self, conn: sqlite3.Connection) -> tuple[str, ...]:
        """Finish every import batch left ``pending`` by a prior interruption.

        A batch is only ever marked ``pending`` (with its full payload
        persisted) before any of its events are applied, and ``completed``
        after all of them are; a batch found ``pending`` here means the
        process that called ``import_events`` died in between, so this
        applies it now the same idempotent, dedup-by-``event_id`` way
        ``import_events`` itself would.
        """

        pending = conn.execute(
            "SELECT idempotency_key, payload FROM import_batches WHERE status = 'pending'"
        ).fetchall()
        completed: list[str] = []
        for idempotency_key, payload_json in pending:
            events = [_event_from_payload(item) for item in json.loads(payload_json)]
            applied, duplicates = self._apply_import_events(conn, events)
            conn.execute(
                "UPDATE import_batches SET status = 'completed', applied_count = ?, "
                "duplicate_count = ?, updated_at = ? WHERE idempotency_key = ?",
                (applied, duplicates, _now_iso(), idempotency_key),
            )
            completed.append(idempotency_key)
        if completed:
            conn.commit()
        return tuple(completed)

    def import_events(self, events: list[AuditEvent], *, idempotency_key: str) -> ImportReport:
        """Append a batch of pre-normalized events (e.g. from :mod:`auditlog.compatibility`).

        Idempotent per ``idempotency_key``: replaying the same key with the
        same batch is a no-op that returns the original result: replaying
        it after this process was interrupted partway resumes and finishes
        it; and a batch that overlaps one already (partly or fully) applied
        only appends the events not already present, by ``event_id``.
        Reusing the key with a genuinely different batch raises
        :class:`~auditlog.service.ConflictError`.
        """

        fingerprint = batch_fingerprint([event.event_id for event in events])
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT fingerprint, status, applied_count, duplicate_count, requested_count "
                "FROM import_batches WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            if row is not None:
                existing_fingerprint, status, applied_count, duplicate_count, requested_count = row
                if existing_fingerprint != fingerprint:
                    raise ConflictError(
                        f"idempotency key {idempotency_key!r} was already used for a different import batch"
                    )
                if status == "completed":
                    return ImportReport(
                        idempotency_key=idempotency_key,
                        status="replayed",
                        requested_count=requested_count,
                        applied_count=applied_count,
                        duplicate_count=duplicate_count,
                    )
                # status == "pending": a prior call was interrupted; resume it below.
            else:
                conn.execute(
                    "INSERT INTO import_batches (idempotency_key, fingerprint, status, payload, "
                    "requested_count, applied_count, duplicate_count, updated_at) "
                    "VALUES (?, ?, 'pending', ?, ?, 0, 0, ?)",
                    (
                        idempotency_key,
                        fingerprint,
                        json.dumps([event_payload(event) for event in events]),
                        len(events),
                        _now_iso(),
                    ),
                )
                conn.commit()

            applied, duplicates = self._apply_import_events(conn, events)
            conn.execute(
                "UPDATE import_batches SET status = 'completed', applied_count = ?, "
                "duplicate_count = ?, updated_at = ? WHERE idempotency_key = ?",
                (applied, duplicates, _now_iso(), idempotency_key),
            )
            conn.commit()
            return ImportReport(
                idempotency_key=idempotency_key,
                status="completed",
                requested_count=len(events),
                applied_count=applied,
                duplicate_count=duplicates,
            )
        finally:
            conn.close()

    def repair(
        self,
        *,
        report_name: str | None = None,
        expected_count: int | None = None,
    ) -> RepairReport:
        conn = self._connect()
        try:
            completed_imports = self._complete_pending_imports(conn)
            events = self._load_all_events(conn)
            corrupted, gap_at = _find_integrity_issues(events)
            reordered = _find_reordering(conn)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_actor ON events(actor)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_action ON events(action)")
            conn.commit()
        finally:
            conn.close()

        count_mismatch = None
        if expected_count is not None and expected_count != len(events):
            count_mismatch = (expected_count, len(events))

        report_path: str | None = None
        if report_name is not None:
            resolved = resolve_report_path(self.store_root, report_name)
            resolved.parent.mkdir(parents=True, exist_ok=True)
            report_payload = {
                "verified_count": len(events),
                "corrupted_sequences": list(corrupted),
                "sequence_gap_at": gap_at,
                "reordered_sequences": list(reordered),
                "count_mismatch": list(count_mismatch) if count_mismatch else None,
                "completed_imports": list(completed_imports),
                "is_clean": (
                    not corrupted and gap_at is None and not reordered and count_mismatch is None
                ),
            }
            with resolved.open("w", encoding="utf-8") as handle:
                json.dump(report_payload, handle, indent=2, sort_keys=True)
                handle.write("\n")
            report_path = str(resolved)

        return RepairReport(
            verified_count=len(events),
            corrupted_sequences=corrupted,
            sequence_gap_at=gap_at,
            rebuilt_index_path=str(self._path),
            reordered_sequences=reordered,
            count_mismatch=count_mismatch,
            report_path=report_path,
            completed_imports=completed_imports,
        )
