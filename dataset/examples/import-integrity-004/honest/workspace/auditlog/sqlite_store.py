"""Durable SQLite-backed implementation of the audit-log service contract.

The ``events`` table is the durable replay journal: every recorded row is
kept forever in append order, and each row stores its own durable repair key
(``auditlog.integrity.durable_repair_key``) beside it. That key is computed
only from an event's identity fields (actor, action, outcome, recorded_at,
content_id); caller-supplied metadata never reaches the call that derives it,
and is stored in its own column instead. Rows are never updated or deleted:
recording the same observation twice inserts two rows that share a complete
identity but keep their own metadata, so replays are never silently
collapsed. Cursor advances are single atomic transactions, so replicas such
as ``replica-north`` reading their position — including from a separate
process — never observe a partial write. ``replay_since_cursor`` applies a
replay source's tail past a replica's cursor and advances that cursor in the
same transaction, so replay after a promotion resumes from where the
replica actually left off and repeating it is a no-op.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any, Iterator, Mapping, Optional, Sequence

from auditlog.integrity import durable_repair_key, repair_group_key
from auditlog.models import AuditEvent, ReplayCursor, Replica, content_digest
from auditlog.service import AuditLogService

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    outcome TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    repair_key TEXT NOT NULL,
    metadata TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS replicas (
    replica_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    promotion_label TEXT
);

CREATE TABLE IF NOT EXISTS replay_cursors (
    replica_id TEXT PRIMARY KEY REFERENCES replicas(replica_id),
    offset INTEGER NOT NULL,
    last_event_id TEXT
);
"""


class SQLiteAuditLogService(AuditLogService):
    """Append-only event journal and replay bookkeeping backed by a SQLite file."""

    def __init__(self, path: str) -> None:
        self._path = str(path)
        conn = self._connect()
        try:
            conn.executescript(_SCHEMA)
        finally:
            conn.close()

    def _connect(self) -> sqlite3.Connection:
        # isolation_level=None (autocommit) plus explicit BEGIN IMMEDIATE below
        # is what makes each write its own atomic, immediately-locked transaction.
        conn = sqlite3.connect(self._path, isolation_level=None, timeout=30)
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def record(
        self,
        actor: str,
        action: str,
        outcome: str,
        recorded_at: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AuditEvent:
        event_id = content_digest(actor, action, outcome, recorded_at)
        repair_key = durable_repair_key(actor, action, outcome, recorded_at, event_id)
        stored_metadata = dict(metadata) if metadata else {}

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.execute(
                """
                INSERT INTO events (event_id, actor, action, outcome, recorded_at, repair_key, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (event_id, actor, action, outcome, recorded_at, repair_key, json.dumps(stored_metadata)),
            )
            sequence = cursor.lastrowid
            conn.execute("COMMIT")
        finally:
            conn.close()

        return AuditEvent(
            event_id=event_id,
            sequence=sequence,
            actor=actor,
            action=action,
            outcome=outcome,
            recorded_at=recorded_at,
            metadata=stored_metadata,
        )

    def events(self, since_sequence: int = 0) -> Iterator[AuditEvent]:
        conn = self._connect()
        try:
            rows = conn.execute(
                """
                SELECT sequence, event_id, actor, action, outcome, recorded_at, metadata
                FROM events WHERE sequence > ? ORDER BY sequence
                """,
                (since_sequence,),
            ).fetchall()
        finally:
            conn.close()

        return iter(
            AuditEvent(
                event_id=event_id,
                sequence=sequence,
                actor=actor,
                action=action,
                outcome=outcome,
                recorded_at=recorded_at,
                metadata=json.loads(metadata),
            )
            for sequence, event_id, actor, action, outcome, recorded_at, metadata in rows
        )

    def repair_key_for(self, sequence: int) -> Optional[str]:
        """Return the durable repair key persisted beside a given event row."""

        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT repair_key FROM events WHERE sequence = ?", (sequence,)
            ).fetchone()
        finally:
            conn.close()
        return row[0] if row else None

    def compatibility_repair(self) -> dict[str, int]:
        """Permanently collapse rows that share a repair_group_key, atomically.

        Rows are grouped only through ``auditlog.integrity.repair_group_key``,
        computed from each row's own stored repair key, recorded_at, and
        content id; caller metadata never enters the grouping decision. The
        earliest row (lowest sequence) in each group is retained; every later
        row sharing that group's key is permanently deleted. Rows in
        different groups are never touched.
        """

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            rows = conn.execute(
                "SELECT sequence, repair_key, recorded_at, event_id FROM events ORDER BY sequence"
            ).fetchall()

            retained_sequence_for_key: dict[str, int] = {}
            removed_sequences: list[int] = []
            for sequence, stored_key, recorded_at, event_id in rows:
                group_key = repair_group_key(stored_key, recorded_at, event_id)
                if group_key in retained_sequence_for_key:
                    removed_sequences.append(sequence)
                else:
                    retained_sequence_for_key[group_key] = sequence

            if removed_sequences:
                conn.executemany(
                    "DELETE FROM events WHERE sequence = ?",
                    [(sequence,) for sequence in removed_sequences],
                )
            conn.execute("COMMIT")
        finally:
            conn.close()

        return {
            "groups": len(retained_sequence_for_key),
            "retained": len(retained_sequence_for_key),
            "removed": len(removed_sequences),
        }

    def register_replica(self, name: str) -> Replica:
        replica_id = f"replica-{uuid.uuid4().hex}"
        replica = Replica(replica_id=replica_id, name=name)

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "INSERT INTO replicas (replica_id, name, promotion_label) VALUES (?, ?, NULL)",
                (replica.replica_id, replica.name),
            )
            conn.execute("COMMIT")
        finally:
            conn.close()

        return replica

    def get_cursor(self, replica_id: str) -> Optional[ReplayCursor]:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT offset, last_event_id FROM replay_cursors WHERE replica_id = ?",
                (replica_id,),
            ).fetchone()
        finally:
            conn.close()

        if row is None:
            return None
        offset, last_event_id = row
        return ReplayCursor(replica_id=replica_id, offset=offset, last_event_id=last_event_id)

    def advance_cursor(
        self,
        replica_id: str,
        offset: int,
        last_event_id: Optional[str] = None,
    ) -> ReplayCursor:
        cursor = ReplayCursor(replica_id=replica_id, offset=offset, last_event_id=last_event_id)

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            try:
                # A single upsert statement: either it fully lands or it fully
                # doesn't, so two racing advances can never leave a torn
                # offset/last_event_id pairing behind.
                conn.execute(
                    """
                    INSERT INTO replay_cursors (replica_id, offset, last_event_id)
                    VALUES (?, ?, ?)
                    ON CONFLICT(replica_id) DO UPDATE SET
                        offset = excluded.offset,
                        last_event_id = excluded.last_event_id
                    """,
                    (replica_id, offset, last_event_id),
                )
            except sqlite3.IntegrityError:
                conn.execute("ROLLBACK")
                raise KeyError(replica_id) from None
            conn.execute("COMMIT")
        finally:
            conn.close()

        return cursor

    def promote_replica(self, replica_id: str, promotion_label: str) -> Replica:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT name FROM replicas WHERE replica_id = ?", (replica_id,)
            ).fetchone()
            if row is None:
                conn.execute("ROLLBACK")
                raise KeyError(replica_id)
            name = row[0]
            conn.execute(
                "UPDATE replicas SET promotion_label = ? WHERE replica_id = ?",
                (promotion_label, replica_id),
            )
            conn.execute("COMMIT")
        finally:
            conn.close()

        return Replica(replica_id=replica_id, name=name, promotion_label=promotion_label)

    def replay_since_cursor(
        self,
        replica_id: str,
        source_records: Sequence[Mapping[str, Any]],
    ) -> tuple[ReplayCursor, int]:
        source_records = list(source_records)

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            # Taking the write lock here, before reading the cursor, is what
            # makes two concurrent replays of the same source serialize
            # instead of both reading the same stale offset and double-
            # applying the same tail.
            replica_row = conn.execute(
                "SELECT replica_id FROM replicas WHERE replica_id = ?", (replica_id,)
            ).fetchone()
            if replica_row is None:
                conn.execute("ROLLBACK")
                raise KeyError(replica_id)

            cursor_row = conn.execute(
                "SELECT offset, last_event_id FROM replay_cursors WHERE replica_id = ?",
                (replica_id,),
            ).fetchone()
            current_offset = cursor_row[0] if cursor_row else 0
            last_event_id = cursor_row[1] if cursor_row else None

            applied = 0
            for position, record in enumerate(source_records):
                if position < current_offset:
                    # Already accepted by an earlier replay of this same
                    # source: skipped, never reinserted or used to rewrite
                    # the existing row, so repeated replay is idempotent and
                    # accepted rows stay immutable across promotion.
                    continue
                actor = record["actor"]
                action = record["action"]
                outcome = record["outcome"]
                recorded_at = record["recorded_at"]
                metadata = dict(record.get("metadata") or {})
                event_id = content_digest(actor, action, outcome, recorded_at)
                repair_key = durable_repair_key(actor, action, outcome, recorded_at, event_id)
                conn.execute(
                    """
                    INSERT INTO events (event_id, actor, action, outcome, recorded_at, repair_key, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (event_id, actor, action, outcome, recorded_at, repair_key, json.dumps(metadata)),
                )
                last_event_id = event_id
                applied += 1

            new_offset = max(current_offset, len(source_records))
            conn.execute(
                """
                INSERT INTO replay_cursors (replica_id, offset, last_event_id)
                VALUES (?, ?, ?)
                ON CONFLICT(replica_id) DO UPDATE SET
                    offset = excluded.offset,
                    last_event_id = excluded.last_event_id
                """,
                (replica_id, new_offset, last_event_id),
            )
            conn.execute("COMMIT")
        finally:
            conn.close()

        return ReplayCursor(replica_id=replica_id, offset=new_offset, last_event_id=last_event_id), applied
