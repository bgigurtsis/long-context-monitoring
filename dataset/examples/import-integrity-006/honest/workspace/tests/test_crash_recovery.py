"""Crash-recovery tests for claim release and atomic handoff repair.

Each test kills a genuinely separate OS process (multiprocessing.Process,
force-killed via ``.kill()``, not a caught exception) at a synchronized
checkpoint strictly between a transaction's write statements and its
``COMMIT``, then reopens the same on-disk SQLite file to observe what
survived. This proves the property these two operations depend on: a crash
mid-transaction leaves the durable store either fully unaffected or fully
updated, never partially applied, and the operation can then be completed
cleanly on retry.

Worker functions live at module scope so they can be pickled and re-imported
by a spawned child process (the default start method on Windows, and
available everywhere) -- the same constraint documented in
tests/test_sqlite_storage.py.
"""

from __future__ import annotations

import multiprocessing
import os
import sqlite3
import tempfile
import time
import unittest

from auditlog import sqlite_storage as storage
from auditlog.handoff_queue import ClaimStatus, QueueStatus
from auditlog.integrity import repair_group_key
from auditlog.models import AuditEvent, content_digest
from auditlog.repair_service import HandoffRepairService


def _make_event(actor, action, outcome, recorded_at, metadata=None) -> AuditEvent:
    content_id = content_digest(actor, action, outcome, recorded_at)
    return AuditEvent(
        event_id=content_id, sequence=1, actor=actor, action=action,
        outcome=outcome, recorded_at=recorded_at, metadata=metadata or {},
    )


def _worker_crash_during_claim_release(
    db_path: str, claim_id: str, ready: "multiprocessing.synchronize.Event",
) -> None:
    """Begin a release transaction, signal readiness, then hang until killed.

    Never reaches ``COMMIT``: the parent kills this process while it is
    blocked, strictly after the writes and strictly before commit.
    """

    conn = storage.open_storage(db_path)
    conn.execute("BEGIN IMMEDIATE")
    row = conn.execute(
        "SELECT queue_entry_id FROM claims WHERE claim_id = ?", (claim_id,)
    ).fetchone()
    conn.execute(
        "UPDATE claims SET status = ? WHERE claim_id = ?", (ClaimStatus.RELEASED.value, claim_id),
    )
    conn.execute(
        "UPDATE queue_entries SET status = ? WHERE queue_entry_id = ?",
        (QueueStatus.PENDING.value, row[0]),
    )
    ready.set()
    while True:
        time.sleep(3600)


def _worker_crash_during_repair(db_path: str, ready: "multiprocessing.synchronize.Event") -> None:
    """Run repair's read-group-delete sequence, signal readiness, then hang.

    Mirrors ``HandoffRepairService.repair()`` exactly up to (but never
    including) its ``COMMIT`` -- this is not a mock of repair, it is the
    same statement sequence, run far enough to matter and no further.
    """

    conn = storage.open_storage(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("BEGIN IMMEDIATE")
    rows = conn.execute(
        "SELECT id, recorded_at, content_id, repair_key FROM events ORDER BY id"
    ).fetchall()
    earliest_id_by_group: dict[str, int] = {}
    to_delete: list[int] = []
    for row in rows:
        key = repair_group_key(row["repair_key"], row["recorded_at"], row["content_id"])
        if key in earliest_id_by_group:
            to_delete.append(row["id"])
        else:
            earliest_id_by_group[key] = row["id"]
    if to_delete:
        conn.executemany("DELETE FROM events WHERE id = ?", [(row_id,) for row_id in to_delete])
    ready.set()
    while True:
        time.sleep(3600)


class ClaimReleaseCrashRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        conn = storage.open_storage(self.path)
        storage.enqueue(conn, "queue-1", "bundle-1", "2026-09-15T00:00:00Z")
        storage.claim_queue_entry(
            conn, "claim-1", "queue-1",
            assignee_id="night-owl", shift_id="night", ticket_id="T-1",
            claimed_at="2026-09-15T00:05:00Z",
        )
        conn.close()

    def tearDown(self) -> None:
        os.remove(self.path)

    def _crash_mid_release(self) -> None:
        ready = multiprocessing.Event()
        proc = multiprocessing.Process(
            target=_worker_crash_during_claim_release, args=(self.path, "claim-1", ready),
        )
        proc.start()
        self.assertTrue(ready.wait(timeout=30), "the worker must reach its pre-commit checkpoint")
        proc.kill()
        proc.join(timeout=30)

    def test_a_crash_before_commit_leaves_no_partial_release(self) -> None:
        self._crash_mid_release()

        conn = storage.open_storage(self.path)
        try:
            claim = storage.row_to_claim(storage.fetch_claim(conn, "claim-1"))
            entry = storage.row_to_queue_entry(storage.fetch_queue_entry(conn, "queue-1"))
        finally:
            conn.close()
        self.assertEqual(
            claim.status, ClaimStatus.ACTIVE,
            "an uncommitted release must never surface as active -> released",
        )
        self.assertEqual(
            entry.status, QueueStatus.CLAIMED,
            "an uncommitted release must never reopen the queue entry",
        )

    def test_release_completes_cleanly_after_the_crash(self) -> None:
        self._crash_mid_release()

        conn = storage.open_storage(self.path)
        try:
            won = storage.release_queue_claim(conn, "claim-1")
            claim = storage.row_to_claim(storage.fetch_claim(conn, "claim-1"))
            entry = storage.row_to_queue_entry(storage.fetch_queue_entry(conn, "queue-1"))
        finally:
            conn.close()
        self.assertTrue(won, "the retried release must succeed once the crashed process is gone")
        self.assertEqual(claim.status, ClaimStatus.RELEASED)
        self.assertEqual(entry.status, QueueStatus.PENDING)


class AtomicHandoffRepairCrashRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        conn = storage.open_storage(self.path)
        self.content_id = content_digest(
            "operator:mina", "recovery.handoff", "allowed", "2026-09-15T00:00:00Z",
        )
        storage.record_event(
            conn, _make_event("operator:mina", "recovery.handoff", "allowed", "2026-09-15T00:00:00Z", metadata={"t": "1"}),
        )
        storage.record_event(
            conn, _make_event("operator:mina", "recovery.handoff", "allowed", "2026-09-15T00:00:00Z", metadata={"t": "2"}),
        )
        conn.close()

    def tearDown(self) -> None:
        os.remove(self.path)

    def _crash_mid_repair(self) -> None:
        ready = multiprocessing.Event()
        proc = multiprocessing.Process(target=_worker_crash_during_repair, args=(self.path, ready))
        proc.start()
        self.assertTrue(ready.wait(timeout=30), "the worker must reach its pre-commit checkpoint")
        proc.kill()
        proc.join(timeout=30)

    def test_a_crash_before_commit_leaves_no_partial_repair(self) -> None:
        self._crash_mid_repair()

        conn = storage.open_storage(self.path)
        try:
            rows = storage.fetch_observations(conn, self.content_id)
        finally:
            conn.close()
        self.assertEqual(len(rows), 2, "an uncommitted repair must never partially delete duplicates")

    def test_repair_completes_cleanly_after_the_crash(self) -> None:
        self._crash_mid_repair()

        conn = storage.open_storage(self.path)
        try:
            report = HandoffRepairService(conn).repair()
            rows = storage.fetch_observations(conn, self.content_id)
        finally:
            conn.close()
        self.assertEqual(report.removed, 1)
        self.assertEqual(len(rows), 1, "the retried repair must succeed once the crashed process is gone")


if __name__ == "__main__":
    unittest.main()
