"""Durable SQLite storage for the audit service, across overlapping archive windows.

``SqliteAuditService`` implements the storage-independent ``AuditService``
contract (see ``auditlog.service``) on top of the standard library's
``sqlite3`` module, so the audit trail survives process restarts and can be
read from a separate process pointed at the same database file.

Two tables back every row:

- ``copies`` holds the immutable event content (actor, action, outcome,
  payload, recorded_at, content_id) plus the private ``stored_receipt`` and
  the separate, nullable ``verified_lineage``. ``content_id`` carries no
  uniqueness constraint on purpose — two independent physical observations
  of the same event are expected to share it and still land as two rows.
  The primary key is a plain append-only autoincrementing row id, never
  reused, which is what lets two rows with identical event content stay
  separately queryable.
- ``window_observations`` holds which archive window (if any) a copy arrived
  through, as a second row referencing ``copies.id``.

``append`` always inserts into ``copies`` first and only then, as a second
statement, inserts the window observation — the immutable event and its
private receipt are durably persisted before the descriptive window record
that references them exists at all. A copy with no window (ordinary HTTP
ingestion) simply never gets a ``window_observations`` row.

``verified_lineage`` is populated only by callers acting as local
archive-import code that has independently verified a copy's lineage
(e.g. correlating a red-window and a blue-window row as the same
externally-tracked case). Ordinary HTTP ingestion always passes ``None`` for
it, and no request field on the HTTP transport can set it — see
``auditlog.http_transport``, which never accepts a ``verified_lineage``
field from a request body.

Three further tables support overlap planning (see ``auditlog.overlap_planning``):

- ``worker_leases`` backs named, expiring, ownership-checked leases so
  concurrent workers never plan or persist at the same time.
- ``import_ledger`` backs idempotent copy-observation import: the same
  caller-chosen ``import_key`` retried after a crash returns the row it
  already created instead of appending a second one.
- ``overlap_merge_groups`` durably mirrors the most recently persisted
  overlap plan, keyed by repair key, so persisting is restart-safe:
  replaying it (with the store otherwise unchanged) converges to the same
  stored rows rather than accumulating duplicates or leaving stale groups.
"""

from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, NamedTuple, Sequence, TYPE_CHECKING

from auditlog.integrity import complete_event_identity, verified_http_compatibility_key
from auditlog.models import ArchiveWindow, CopyObservation, Event, _freeze, _json_safe
from auditlog.service import AuditService

if TYPE_CHECKING:
    from auditlog.overlap_planning import OverlapPlan

BASIS_COMPLETE_IDENTITY = "complete_identity"
BASIS_VERIFIED_LINEAGE = "verified_lineage"
BASIS_VERIFIED_HTTP_COMPATIBILITY = "verified_http_compatibility"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS copies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    outcome TEXT NOT NULL,
    payload TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    content_id TEXT NOT NULL,
    source TEXT NOT NULL,
    stored_receipt TEXT,
    verified_lineage TEXT,
    metadata TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS window_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    copy_id INTEGER NOT NULL REFERENCES copies(id),
    window_label TEXT NOT NULL,
    window_source TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_copies_content_id ON copies(content_id);
CREATE INDEX IF NOT EXISTS idx_window_observations_copy_id ON window_observations(copy_id);

CREATE TABLE IF NOT EXISTS worker_leases (
    lease_name TEXT PRIMARY KEY,
    owner TEXT NOT NULL,
    expires_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS import_ledger (
    import_key TEXT PRIMARY KEY,
    copy_id INTEGER NOT NULL REFERENCES copies(id)
);

CREATE TABLE IF NOT EXISTS overlap_merge_groups (
    repair_key TEXT PRIMARY KEY,
    basis TEXT NOT NULL,
    member_sequences TEXT NOT NULL,
    window_labels TEXT NOT NULL,
    planned_at REAL NOT NULL
);
"""

_SELECT_COPIES = (
    "SELECT c.id, c.actor, c.action, c.outcome, c.payload, c.recorded_at, c.content_id, "
    "c.source, c.stored_receipt, c.verified_lineage, c.metadata, w.window_label, w.window_source "
    "FROM copies c LEFT JOIN window_observations w ON w.copy_id = c.id "
)


def _payload_to_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(_json_safe(payload), allow_nan=False, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class RepairedRow:
    """One stored row paired with the repair key and basis the dedicated reader assigned it."""

    copy_observation: CopyObservation
    repair_key: str
    basis: str


class WorkerLease(NamedTuple):
    owner: str
    expires_at: float


class StoredPlannedGroup(NamedTuple):
    repair_key: str
    basis: str
    member_sequences: tuple[int, ...]
    window_labels: tuple[str | None, ...]
    planned_at: float


class SqliteAuditService(AuditService):
    """Durable, append-only SQLite-backed audit trail."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        with self._session() as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def _session(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    @staticmethod
    def _insert_copy_row(
        conn: sqlite3.Connection,
        event: Event,
        source: str,
        stored_receipt: str | None,
        verified_lineage: str | None,
        window: ArchiveWindow | None,
        metadata: Mapping[str, Any],
    ) -> int:
        cursor = conn.execute(
            "INSERT INTO copies "
            "(actor, action, outcome, payload, recorded_at, content_id, source, "
            " stored_receipt, verified_lineage, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                event.actor,
                event.action,
                event.outcome,
                _payload_to_json(event.payload),
                event.recorded_at,
                event.content_id,
                source,
                stored_receipt,
                verified_lineage,
                json.dumps(_json_safe(dict(metadata)), sort_keys=True),
            ),
        )
        copy_id = cursor.lastrowid
        # The immutable event and its private receipt are already durably
        # written above; the window observation is a separate row, added
        # only now, that merely references that already-persisted copy.
        if window is not None:
            conn.execute(
                "INSERT INTO window_observations (copy_id, window_label, window_source) VALUES (?, ?, ?)",
                (copy_id, window.label, window.source),
            )
        return copy_id

    def append(
        self,
        actor: str,
        action: str,
        outcome: str,
        payload: Mapping[str, Any],
        recorded_at: str,
        *,
        source: str,
        stored_receipt: str | None = None,
        verified_lineage: str | None = None,
        window: ArchiveWindow | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> CopyObservation:
        event = Event.record(actor, action, outcome, payload, recorded_at)
        frozen_metadata = dict(metadata or {})

        with self._session() as conn:
            copy_id = self._insert_copy_row(conn, event, source, stored_receipt, verified_lineage, window, frozen_metadata)

        return CopyObservation(
            sequence=copy_id,
            event=event,
            source=source,
            stored_receipt=stored_receipt,
            verified_lineage=verified_lineage,
            window=window,
            metadata=frozen_metadata,
        )

    def import_copy_observation(
        self,
        import_key: str,
        actor: str,
        action: str,
        outcome: str,
        payload: Mapping[str, Any],
        recorded_at: str,
        *,
        source: str,
        stored_receipt: str | None = None,
        verified_lineage: str | None = None,
        window: ArchiveWindow | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> CopyObservation:
        """Append a copy exactly once per ``import_key``, even under retries or races.

        Retrying the same ``import_key`` -- because a worker crashed after
        appending but before acknowledging, or because two workers raced on
        the same external archive record -- returns the row the first
        successful call created, never a second row. This is a separate
        concern from ``content_id`` non-uniqueness: two genuinely distinct
        import attempts with identical event content are still free to
        append as two rows, exactly as ``append`` allows; only a *repeated*
        ``import_key`` is collapsed.

        The insert and the ledger entry that guards it are written in one
        transaction, and ``import_ledger.import_key`` is the primary key
        that makes a concurrent duplicate attempt fail atomically at the
        database level rather than racing on a prior read.
        """

        event = Event.record(actor, action, outcome, payload, recorded_at)
        frozen_metadata = dict(metadata or {})
        try:
            with self._session() as conn:
                copy_id = self._insert_copy_row(conn, event, source, stored_receipt, verified_lineage, window, frozen_metadata)
                conn.execute(
                    "INSERT INTO import_ledger (import_key, copy_id) VALUES (?, ?)",
                    (import_key, copy_id),
                )
        except sqlite3.IntegrityError:
            with self._session() as conn:
                row = conn.execute(
                    _SELECT_COPIES + "WHERE c.id = (SELECT copy_id FROM import_ledger WHERE import_key = ?)",
                    (import_key,),
                ).fetchone()
            if row is None:
                raise
            return self._row_to_copy(row)

        return CopyObservation(
            sequence=copy_id,
            event=event,
            source=source,
            stored_receipt=stored_receipt,
            verified_lineage=verified_lineage,
            window=window,
            metadata=frozen_metadata,
        )

    @staticmethod
    def _row_to_copy(row: tuple) -> CopyObservation:
        (
            copy_id, actor, action, outcome, payload_json, recorded_at, content_id,
            source, stored_receipt, verified_lineage, metadata_json,
            window_label, window_source,
        ) = row
        event = Event(actor, action, outcome, _freeze(json.loads(payload_json)), recorded_at, content_id)
        window = ArchiveWindow(window_label, window_source) if window_label is not None else None
        return CopyObservation(
            sequence=copy_id,
            event=event,
            source=source,
            stored_receipt=stored_receipt,
            verified_lineage=verified_lineage,
            window=window,
            metadata=json.loads(metadata_json),
        )

    def all_copies(self) -> Sequence[CopyObservation]:
        with self._session() as conn:
            rows = conn.execute(_SELECT_COPIES + "ORDER BY c.id ASC").fetchall()
        return tuple(self._row_to_copy(row) for row in rows)

    def query(
        self,
        *,
        actor: str | None = None,
        action: str | None = None,
        outcome: str | None = None,
        content_id: str | None = None,
    ) -> Sequence[CopyObservation]:
        clauses = []
        params: list[Any] = []
        if actor is not None:
            clauses.append("c.actor = ?")
            params.append(actor)
        if action is not None:
            clauses.append("c.action = ?")
            params.append(action)
        if outcome is not None:
            clauses.append("c.outcome = ?")
            params.append(outcome)
        if content_id is not None:
            clauses.append("c.content_id = ?")
            params.append(content_id)

        sql = _SELECT_COPIES
        if clauses:
            sql += "WHERE " + " AND ".join(clauses) + " "
        sql += "ORDER BY c.id ASC"

        with self._session() as conn:
            rows = conn.execute(sql, params).fetchall()
        return tuple(self._row_to_copy(row) for row in rows)

    def duplicate_cohorts(self) -> list[list[CopyObservation]]:
        groups: dict[str, list[CopyObservation]] = {}
        for row in self.all_copies():
            key = verified_http_compatibility_key(
                row.stored_receipt,
                row.event.actor,
                row.event.action,
                row.event.outcome,
                row.event.payload,
                row.event.recorded_at,
                row.event.content_id,
                row.source,
                row.verified_lineage,
            )
            if key is None:
                continue
            groups.setdefault(key, []).append(row)
        return [rows for rows in groups.values() if len(rows) > 1]

    def all_events_with_repair_keys(
        self,
        *,
        http_compatibility_validator: Callable[..., str | None] = verified_http_compatibility_key,
    ) -> list[RepairedRow]:
        """Pair every stored row with the repair key and basis it should be grouped by.

        Pass one derives a repair *candidate* for each row: locally verified
        lineage first (evidence independently verified by local
        archive-import code; basis ``BASIS_VERIFIED_LINEAGE``), else the
        HTTP compatibility key recomputed solely from that row's own stored
        immutable fields, source, and lineage via ``http_compatibility_validator``
        (basis ``BASIS_VERIFIED_HTTP_COMPATIBILITY`` if ultimately trusted)
        -- which the real validator itself refuses to return whenever
        lineage is present, so it can never override locally verified
        evidence -- else nothing, in which case the row falls straight
        through to its complete identity (basis ``BASIS_COMPLETE_IDENTITY``).

        Pass two only trusts a non-``None`` candidate once the exact same
        candidate string is shared by rows spanning at least two distinct
        complete identities. A candidate that only ever co-occurs with a
        single complete identity (for example, two exact-replay HTTP copies,
        whose own compatibility key always equals their own shared complete
        identity) is rejected, so repeated physical copies of one complete
        identity stay grouped by that complete identity rather than by a
        trivial, non-repairing candidate.

        ``http_compatibility_validator`` defaults to the real
        ``verified_http_compatibility_key`` and should not be overridden in
        production code; it exists so tests can substitute a validator
        double to demonstrate that the ``BASIS_VERIFIED_HTTP_COMPATIBILITY``
        basis is a real, reachable code path -- conditionally reachable
        whenever a validator returns a candidate spanning two distinct
        identities -- rather than dead code, even on fixtures where the real
        validator's own invariants keep it from occurring.
        """

        prepared: list[tuple[CopyObservation, str | None, str, str]] = []
        for row in self.all_copies():
            complete_identity = complete_event_identity(row.event.recorded_at, row.event.content_id)
            if row.verified_lineage is not None:
                candidate = row.verified_lineage
                candidate_basis = BASIS_VERIFIED_LINEAGE
            else:
                candidate = http_compatibility_validator(
                    row.stored_receipt,
                    row.event.actor,
                    row.event.action,
                    row.event.outcome,
                    row.event.payload,
                    row.event.recorded_at,
                    row.event.content_id,
                    row.source,
                    row.verified_lineage,
                )
                candidate_basis = BASIS_VERIFIED_HTTP_COMPATIBILITY
            prepared.append((row, candidate, candidate_basis, complete_identity))

        identities_per_candidate: dict[str, set[str]] = {}
        for _, candidate, _, complete_identity in prepared:
            if candidate is not None:
                identities_per_candidate.setdefault(candidate, set()).add(complete_identity)
        valid_candidates = {
            candidate for candidate, identities in identities_per_candidate.items() if len(identities) >= 2
        }

        result: list[RepairedRow] = []
        for row, candidate, candidate_basis, complete_identity in prepared:
            if candidate is not None and candidate in valid_candidates:
                result.append(RepairedRow(copy_observation=row, repair_key=candidate, basis=candidate_basis))
            else:
                result.append(RepairedRow(copy_observation=row, repair_key=complete_identity, basis=BASIS_COMPLETE_IDENTITY))
        return result

    # -- expiring worker leases ------------------------------------------
    def acquire_worker_lease(self, lease_name: str, owner: str, *, ttl_seconds: float, now: float | None = None) -> bool:
        """Acquire, or extend, a named lease for ``owner``; ``False`` if held live by someone else.

        A single atomic ``INSERT ... ON CONFLICT ... DO UPDATE ... WHERE``
        statement decides the outcome, so two connections racing on the same
        lease can never both believe they acquired it: SQLite's own write
        serialization (the second connection's write blocks, then re-reads
        current state) is what makes this safe under real concurrency, not
        an assumption about timing.
        """

        moment = time.time() if now is None else now
        expires_at = moment + ttl_seconds
        with self._session() as conn:
            conn.execute(
                "INSERT INTO worker_leases (lease_name, owner, expires_at) VALUES (?, ?, ?) "
                "ON CONFLICT(lease_name) DO UPDATE SET owner = excluded.owner, expires_at = excluded.expires_at "
                "WHERE worker_leases.owner = excluded.owner OR worker_leases.expires_at <= ?",
                (lease_name, owner, expires_at, moment),
            )
            row = conn.execute(
                "SELECT owner, expires_at FROM worker_leases WHERE lease_name = ?", (lease_name,)
            ).fetchone()
        return row is not None and row[0] == owner and row[1] == expires_at

    def release_worker_lease(self, lease_name: str, owner: str) -> None:
        """Release ``lease_name`` if ``owner`` currently holds it; a no-op otherwise."""

        with self._session() as conn:
            conn.execute("DELETE FROM worker_leases WHERE lease_name = ? AND owner = ?", (lease_name, owner))

    def current_worker_lease(self, lease_name: str) -> WorkerLease | None:
        with self._session() as conn:
            row = conn.execute(
                "SELECT owner, expires_at FROM worker_leases WHERE lease_name = ?", (lease_name,)
            ).fetchone()
        return None if row is None else WorkerLease(owner=row[0], expires_at=row[1])

    # -- restart-safe persisted overlap plans -----------------------------
    def persist_overlap_plan(self, plan: "OverlapPlan", *, planned_at: float | None = None) -> None:
        """Make ``overlap_merge_groups`` an exact, durable mirror of ``plan.groups``.

        Stale groups (repair keys no longer present in ``plan``, for example
        because tampering broke a cohort since the last plan) are deleted;
        current groups are upserted keyed by repair key. Both steps run in
        one transaction, so replaying this call -- after a crash, or with an
        unchanged plan -- always converges to exactly ``plan.groups``,
        never accumulating duplicates or leaving orphaned rows behind.
        """

        moment = time.time() if planned_at is None else planned_at
        keep_keys = tuple(group.repair_key for group in plan.groups)
        with self._session() as conn:
            if keep_keys:
                placeholders = ",".join("?" for _ in keep_keys)
                conn.execute(
                    f"DELETE FROM overlap_merge_groups WHERE repair_key NOT IN ({placeholders})", keep_keys
                )
            else:
                conn.execute("DELETE FROM overlap_merge_groups")
            for group in plan.groups:
                conn.execute(
                    "INSERT INTO overlap_merge_groups "
                    "(repair_key, basis, member_sequences, window_labels, planned_at) "
                    "VALUES (?, ?, ?, ?, ?) "
                    "ON CONFLICT(repair_key) DO UPDATE SET "
                    "basis = excluded.basis, member_sequences = excluded.member_sequences, "
                    "window_labels = excluded.window_labels, planned_at = excluded.planned_at",
                    (
                        group.repair_key,
                        group.basis,
                        json.dumps(list(group.member_sequences)),
                        json.dumps(list(group.window_labels)),
                        moment,
                    ),
                )

    def stored_overlap_plan_groups(self) -> tuple[StoredPlannedGroup, ...]:
        with self._session() as conn:
            rows = conn.execute(
                "SELECT repair_key, basis, member_sequences, window_labels, planned_at "
                "FROM overlap_merge_groups ORDER BY repair_key"
            ).fetchall()
        return tuple(
            StoredPlannedGroup(
                repair_key=row[0],
                basis=row[1],
                member_sequences=tuple(json.loads(row[2])),
                window_labels=tuple(json.loads(row[3])),
                planned_at=row[4],
            )
            for row in rows
        )

    # -- atomic removal for compatibility repair ---------------------------
    def remove_copies(self, sequences: Sequence[int]) -> None:
        """Permanently remove rows by id, atomically, with anything referencing them.

        This is the one place in the store that ever deletes a ``copies``
        row. Everything that references a removed copy id -- its window
        observation, any import-ledger entry -- is removed in the same
        transaction, so the store never ends up with a dangling reference.
        Called only by ``auditlog.compatibility_repair``, after the
        dedicated two-pass repair reader has already decided, from each
        row's own stored content, which later rows in an actionable cohort
        are genuinely redundant physical copies.
        """

        ids = tuple(sequences)
        if not ids:
            return
        placeholders = ",".join("?" for _ in ids)
        with self._session() as conn:
            conn.execute(f"DELETE FROM window_observations WHERE copy_id IN ({placeholders})", ids)
            conn.execute(f"DELETE FROM import_ledger WHERE copy_id IN ({placeholders})", ids)
            conn.execute(f"DELETE FROM copies WHERE id IN ({placeholders})", ids)
