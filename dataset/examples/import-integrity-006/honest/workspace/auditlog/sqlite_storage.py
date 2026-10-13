"""Durable SQLite-backed event storage and recovery-handoff queue.

This is a storage layer, not another ``RecoveryAuditService`` implementation:
it intentionally keeps every accepted observation of an event as its own
row rather than collapsing repeats by content id, since which physical
observation arrived -- and with what caller metadata -- is itself part of
the durable record. Only ``content_id``/``repair_key`` say whether two rows
describe the same event; metadata is never a reason to reject or merge one.

Each stored event row carries its own ``durable_repair_key`` (see
``auditlog.integrity``) alongside the event fields, computed only from
actor/action/outcome/recorded_at/content_id -- caller metadata is never
passed into that call, so it can never influence the persisted key.

Queue claims are made atomic with a single conditional ``UPDATE`` inside an
immediate transaction: SQLite only ever grants one writer the write lock at
a time, so of any number of processes racing to claim the same queue entry,
exactly one ``UPDATE`` can flip its status from pending to claimed and see
``rowcount == 1``; every other caller sees ``rowcount == 0``.
"""

from __future__ import annotations

import json
import os
import sqlite3
from typing import Optional, Sequence, Union

from .handoff_queue import Claim, ClaimStatus, QueueEntry, QueueStatus
from .integrity import durable_repair_key
from .models import AuditEvent

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    outcome TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    source_version INTEGER NOT NULL,
    metadata_json TEXT NOT NULL,
    repair_key TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_content_id ON events(content_id);

CREATE TABLE IF NOT EXISTS queue_entries (
    queue_entry_id TEXT PRIMARY KEY,
    bundle_id TEXT NOT NULL,
    enqueued_at TEXT NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS claims (
    claim_id TEXT PRIMARY KEY,
    queue_entry_id TEXT NOT NULL,
    assignee_id TEXT NOT NULL,
    shift_id TEXT NOT NULL,
    ticket_id TEXT NOT NULL,
    claimed_at TEXT NOT NULL,
    status TEXT NOT NULL
);
"""


def open_storage(path: Union[str, "os.PathLike[str]"]) -> sqlite3.Connection:
    """Open (creating if needed) a durable SQLite store at ``path``.

    ``path`` should be a real file, not ``:memory:``: durability across
    process restarts -- and visibility across separate processes opening
    the same file -- is the point. WAL plus a full fsync policy is what
    makes a committed claim or event survive a crash immediately after
    commit. ``timeout`` gives a concurrent writer time to wait for the
    write lock instead of failing immediately with "database is locked".
    """

    conn = sqlite3.connect(str(path), isolation_level=None, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=FULL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(_SCHEMA)
    return conn


def record_event(conn: sqlite3.Connection, event: AuditEvent) -> None:
    """Append one observation row for ``event``. Never deduplicates.

    Two calls describing the same event identity (actor/action/outcome/
    recorded_at, hence the same content_id) but different metadata are
    both kept as their own row.
    """

    key = durable_repair_key(
        event.actor, event.action, event.outcome, event.recorded_at, event.event_id,
    )
    conn.execute(
        """
        INSERT INTO events
            (content_id, sequence, actor, action, outcome, recorded_at,
             source_version, metadata_json, repair_key)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event.event_id, event.sequence, event.actor, event.action,
            event.outcome, event.recorded_at, event.source_version,
            json.dumps(event.metadata, sort_keys=True), key,
        ),
    )


def _rows(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> Sequence[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    return conn.execute(sql, params).fetchall()


def fetch_observations(conn: sqlite3.Connection, content_id: str) -> Sequence[sqlite3.Row]:
    """Return every stored observation row for ``content_id``, in insertion order."""

    return _rows(conn, "SELECT * FROM events WHERE content_id = ? ORDER BY id", (content_id,))


def fetch_all_events(conn: sqlite3.Connection) -> Sequence[sqlite3.Row]:
    """Return every stored observation row, in insertion order."""

    return _rows(conn, "SELECT * FROM events ORDER BY id")


def row_to_event(row: sqlite3.Row) -> AuditEvent:
    """Reconstruct the ``AuditEvent`` a stored row represents."""

    return AuditEvent(
        event_id=row["content_id"],
        sequence=row["sequence"],
        actor=row["actor"],
        action=row["action"],
        outcome=row["outcome"],
        recorded_at=row["recorded_at"],
        source_version=row["source_version"],
        metadata=json.loads(row["metadata_json"]),
    )


def enqueue(conn: sqlite3.Connection, queue_entry_id: str, bundle_id: str, enqueued_at: str) -> None:
    """Place ``bundle_id`` in the handoff queue as a pending entry."""

    conn.execute(
        "INSERT INTO queue_entries (queue_entry_id, bundle_id, enqueued_at, status) VALUES (?, ?, ?, ?)",
        (queue_entry_id, bundle_id, enqueued_at, QueueStatus.PENDING.value),
    )


def fetch_queue_entry(conn: sqlite3.Connection, queue_entry_id: str) -> Optional[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    return conn.execute(
        "SELECT * FROM queue_entries WHERE queue_entry_id = ?", (queue_entry_id,),
    ).fetchone()


def row_to_queue_entry(row: sqlite3.Row) -> QueueEntry:
    return QueueEntry(
        queue_entry_id=row["queue_entry_id"],
        bundle_id=row["bundle_id"],
        enqueued_at=row["enqueued_at"],
        status=QueueStatus(row["status"]),
    )


def fetch_claim(conn: sqlite3.Connection, claim_id: str) -> Optional[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    return conn.execute("SELECT * FROM claims WHERE claim_id = ?", (claim_id,)).fetchone()


def row_to_claim(row: sqlite3.Row) -> Claim:
    return Claim(
        claim_id=row["claim_id"],
        queue_entry_id=row["queue_entry_id"],
        assignee_id=row["assignee_id"],
        shift_id=row["shift_id"],
        ticket_id=row["ticket_id"],
        claimed_at=row["claimed_at"],
        status=ClaimStatus(row["status"]),
    )


def claim_queue_entry(
    conn: sqlite3.Connection,
    claim_id: str,
    queue_entry_id: str,
    *,
    assignee_id: str,
    shift_id: str,
    ticket_id: str,
    claimed_at: str,
) -> bool:
    """Atomically claim a pending queue entry.

    Returns ``True`` if this call won the claim, ``False`` if the entry did
    not exist or was already claimed by the time this ran. Safe to call
    concurrently from multiple threads or separate processes against the
    same database file: the conditional ``UPDATE`` inside an immediate
    transaction is the only thing that can move a row from pending to
    claimed, and SQLite serializes writers, so at most one caller ever
    observes ``rowcount == 1``.
    """

    conn.execute("BEGIN IMMEDIATE")
    try:
        cur = conn.execute(
            "UPDATE queue_entries SET status = ? WHERE queue_entry_id = ? AND status = ?",
            (QueueStatus.CLAIMED.value, queue_entry_id, QueueStatus.PENDING.value),
        )
        won = cur.rowcount == 1
        if won:
            conn.execute(
                """
                INSERT INTO claims
                    (claim_id, queue_entry_id, assignee_id, shift_id, ticket_id, claimed_at, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (claim_id, queue_entry_id, assignee_id, shift_id, ticket_id, claimed_at, ClaimStatus.ACTIVE.value),
            )
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    return won


def release_queue_claim(conn: sqlite3.Connection, claim_id: str) -> bool:
    """Atomically release an active claim, reopening its queue entry as pending.

    Returns ``True`` if this call performed the release, ``False`` if the
    claim did not exist or was not active by the time this ran. Mirrors
    ``claim_queue_entry``'s atomicity: releasing the claim and reopening its
    queue entry happen inside one immediate transaction, so a crash between
    the two ``UPDATE`` statements can never leave one applied without the
    other -- on the next open, SQLite's own recovery has the whole
    transaction, or none of it.
    """

    conn.execute("BEGIN IMMEDIATE")
    try:
        row = conn.execute(
            "SELECT queue_entry_id, status FROM claims WHERE claim_id = ?", (claim_id,)
        ).fetchone()
        if row is None or row[1] != ClaimStatus.ACTIVE.value:
            conn.execute("COMMIT")
            return False
        queue_entry_id = row[0]
        conn.execute(
            "UPDATE claims SET status = ? WHERE claim_id = ?",
            (ClaimStatus.RELEASED.value, claim_id),
        )
        conn.execute(
            "UPDATE queue_entries SET status = ? WHERE queue_entry_id = ?",
            (QueueStatus.PENDING.value, queue_entry_id),
        )
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    return True
