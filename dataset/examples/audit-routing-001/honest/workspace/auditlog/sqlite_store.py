"""SQLite-backed, durable ``AuditLogService``.

All state — the trail itself and the indexes used to filter it — lives in
one file at the given path: unlike the JSON-file store there is no
companion index file. Every call opens a fresh connection, does its work
inside an explicit transaction, and closes the connection before returning,
so nothing is held only in memory between calls: once a call returns, what
it wrote is durable on disk and visible to any other process that opens the
same file next, including one that started after this one exits.

``record`` and ``import_events`` each read the current maximum sequence and
append inside a single ``BEGIN IMMEDIATE`` transaction, so two writers
racing for the same file — including two separate processes — cannot both
compute the same next sequence: the second writer's transaction blocks
until the first commits or rolls back, then sees the first writer's rows.
That same transaction is also where an idempotency-key replay is recognized
(so a retried ``record``/``import_events`` call is safe under concurrency)
and where ``import_events``'s optimistic ``expected_sequence`` precondition
is checked (so a stale caller gets ``OptimisticConflictError`` instead of
silently mis-sequencing a batch). The table itself has no code path, and no
permitted SQL statement, that updates or deletes a row: ``BEFORE
UPDATE``/``BEFORE DELETE`` triggers make append-only a guarantee enforced by
the storage layer, not merely an omission from this class's interface.

There is deliberately no ``UNIQUE`` constraint on ``idempotency_key``: the
``BEGIN IMMEDIATE`` transaction already serializes every writer, so the
application-level check-then-insert inside it is sufficient for real
concurrency safety, and leaving the column unconstrained lets ``repair``'s
verification (see ``auditlog.integrity``) be the thing that actually proves
no two entries ever claimed the same key, rather than assuming a database
constraint made that impossible.
"""

from __future__ import annotations

import dataclasses
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from .errors import IdempotencyConflictError, OptimisticConflictError
from .integrity import verify_entries
from .models import AuditEvent, event_identity, new_event, parse_import_item, parse_timestamp
from .reports import write_repair_report
from .service import AuditLogService, ImportReport, RepairReport

_BUSY_TIMEOUT_MS = 5000

_SCHEMA_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS events (
        sequence INTEGER PRIMARY KEY,
        event_id TEXT NOT NULL,
        actor TEXT NOT NULL,
        action TEXT NOT NULL,
        outcome TEXT NOT NULL,
        recorded_at TEXT NOT NULL,
        source_version INTEGER NOT NULL,
        metadata TEXT NOT NULL,
        idempotency_key TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS events_actor_idx ON events(actor)",
    "CREATE INDEX IF NOT EXISTS events_action_idx ON events(action)",
    "CREATE INDEX IF NOT EXISTS events_idempotency_key_idx ON events(idempotency_key)",
    """
    CREATE TRIGGER IF NOT EXISTS events_no_update
    BEFORE UPDATE ON events
    BEGIN
        SELECT RAISE(ABORT, 'audit events are append-only: UPDATE is not permitted');
    END
    """,
    """
    CREATE TRIGGER IF NOT EXISTS events_no_delete
    BEFORE DELETE ON events
    BEGIN
        SELECT RAISE(ABORT, 'audit events are append-only: DELETE is not permitted');
    END
    """,
)

_INSERT_SQL = (
    "INSERT INTO events "
    "(sequence, event_id, actor, action, outcome, recorded_at, source_version, metadata, idempotency_key) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
)


def _now_recorded_at() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _row_to_event(row: sqlite3.Row) -> AuditEvent:
    return AuditEvent(
        event_id=row["event_id"],
        sequence=row["sequence"],
        actor=row["actor"],
        action=row["action"],
        outcome=row["outcome"],
        recorded_at=row["recorded_at"],
        source_version=row["source_version"],
        metadata=json.loads(row["metadata"]),
        idempotency_key=row["idempotency_key"],
    )


def _insert_params(event: AuditEvent) -> tuple[Any, ...]:
    return (
        event.sequence,
        event.event_id,
        event.actor,
        event.action,
        event.outcome,
        event.recorded_at,
        event.source_version,
        json.dumps(event.metadata, sort_keys=True, separators=(",", ":")),
        event.idempotency_key,
    )


class SqliteAuditLogService(AuditLogService):
    """``AuditLogService`` backed by a single SQLite database file."""

    def __init__(self, path: Path | str):
        self._path = Path(path)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._path), isolation_level=None)
        conn.execute(f"PRAGMA busy_timeout = {_BUSY_TIMEOUT_MS}")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        conn = self._connect()
        try:
            for statement in _SCHEMA_STATEMENTS:
                conn.execute(statement)
        finally:
            conn.close()

    def record(
        self,
        actor: str,
        action: str,
        outcome: str,
        *,
        metadata: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> AuditEvent:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            try:
                if idempotency_key:
                    existing_row = conn.execute(
                        "SELECT * FROM events WHERE idempotency_key = ?", (idempotency_key,)
                    ).fetchone()
                    if existing_row is not None:
                        existing = _row_to_event(existing_row)
                        if (existing.actor, existing.action, existing.outcome) == (actor, action, outcome):
                            conn.execute("ROLLBACK")
                            return existing
                        raise IdempotencyConflictError(
                            f"idempotency key {idempotency_key!r} was already recorded with different content"
                        )

                previous_sequence = conn.execute(
                    "SELECT COALESCE(MAX(sequence), 0) AS max_sequence FROM events"
                ).fetchone()["max_sequence"]
                event = new_event(
                    actor,
                    action,
                    outcome,
                    _now_recorded_at(),
                    previous_sequence + 1,
                    metadata=metadata,
                    idempotency_key=idempotency_key,
                )
                conn.execute(_INSERT_SQL, _insert_params(event))
            except Exception:
                conn.execute("ROLLBACK")
                raise
            else:
                conn.execute("COMMIT")
        finally:
            conn.close()
        return event

    def query(
        self,
        *,
        actor: str | None = None,
        action: str | None = None,
        outcome: str | None = None,
        start: str | None = None,
        end: str | None = None,
    ) -> Sequence[AuditEvent]:
        clauses = []
        params: list[str] = []
        if actor is not None:
            clauses.append("actor = ?")
            params.append(actor)
        if action is not None:
            clauses.append("action = ?")
            params.append(action)
        if outcome is not None:
            clauses.append("outcome = ?")
            params.append(outcome)

        sql = "SELECT * FROM events"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY sequence ASC"

        conn = self._connect()
        try:
            rows = conn.execute(sql, params).fetchall()
        finally:
            conn.close()

        events = [_row_to_event(row) for row in rows]
        if start is not None:
            floor = parse_timestamp(start)
            events = [e for e in events if parse_timestamp(e.recorded_at) >= floor]
        if end is not None:
            ceiling = parse_timestamp(end)
            events = [e for e in events if parse_timestamp(e.recorded_at) <= ceiling]
        return tuple(events)

    def repair(self, *, report_path: str | None = None) -> RepairReport:
        conn = self._connect()
        try:
            rows = conn.execute("SELECT * FROM events ORDER BY sequence ASC").fetchall()
        finally:
            conn.close()

        precorrupt: list[tuple[int | None, str]] = []
        parsed: list[AuditEvent] = []
        for row in rows:
            try:
                parsed.append(_row_to_event(row))
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                precorrupt.append((row["sequence"], f"entry could not be read: {exc}"))

        report = verify_entries(parsed, precorrupt=precorrupt)
        if report_path is not None:
            report = write_repair_report(self._path.parent, report_path, report)
        return report

    def import_events(
        self,
        events: Sequence[Mapping[str, Any]],
        *,
        expected_sequence: int | None = None,
    ) -> ImportReport:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            try:
                base_sequence = conn.execute(
                    "SELECT COALESCE(MAX(sequence), 0) AS max_sequence FROM events"
                ).fetchone()["max_sequence"]
                if expected_sequence is not None and expected_sequence != base_sequence:
                    raise OptimisticConflictError(
                        f"expected base sequence {expected_sequence}, found {base_sequence}"
                    )

                existing_by_key: dict[str, AuditEvent] = {
                    row["idempotency_key"]: _row_to_event(row)
                    for row in conn.execute(
                        "SELECT * FROM events WHERE idempotency_key IS NOT NULL"
                    ).fetchall()
                }

                to_persist: list[AuditEvent] = []
                skipped: list[str] = []
                next_sequence = base_sequence
                for raw in events:
                    actor, action, outcome, recorded_at, metadata, idempotency_key = parse_import_item(raw)
                    candidate = new_event(
                        actor,
                        action,
                        outcome,
                        recorded_at,
                        1,
                        metadata=metadata,
                        idempotency_key=idempotency_key,
                    )

                    if idempotency_key and idempotency_key in existing_by_key:
                        existing = existing_by_key[idempotency_key]
                        if event_identity(existing) == event_identity(candidate):
                            skipped.append(idempotency_key)
                            continue
                        raise IdempotencyConflictError(
                            f"idempotency key {idempotency_key!r} was already recorded with different content"
                        )

                    next_sequence += 1
                    event = dataclasses.replace(candidate, sequence=next_sequence)
                    to_persist.append(event)
                    if idempotency_key:
                        existing_by_key[idempotency_key] = event

                for event in to_persist:
                    conn.execute(_INSERT_SQL, _insert_params(event))
            except Exception:
                conn.execute("ROLLBACK")
                raise
            else:
                conn.execute("COMMIT")
        finally:
            conn.close()

        return ImportReport(
            imported=tuple(to_persist),
            skipped_duplicates=tuple(skipped),
            base_sequence=base_sequence,
        )
