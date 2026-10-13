"""Tests for auditlog.sqlite_storage: durable event storage and the
recovery-handoff queue built on it.

Covers: the repair key persisted beside each stored event, repeated
observations kept as separate append-only rows instead of being
deduplicated, that two distinct events get two distinct repair keys, and
that a queue claim is atomic and that event/queue state is visible
correctly when proven from separate OS processes rather than threads.
"""

from __future__ import annotations

import multiprocessing
import os
import tempfile
import unittest

from auditlog.integrity import complete_event_identity, durable_repair_key
from auditlog.models import AuditEvent, content_digest
from auditlog import sqlite_storage as storage


def _make_event(actor, action, outcome, recorded_at, sequence=1, metadata=None):
    content_id = content_digest(actor, action, outcome, recorded_at)
    return AuditEvent(
        event_id=content_id, sequence=sequence, actor=actor, action=action,
        outcome=outcome, recorded_at=recorded_at, metadata=metadata or {},
    )


class RecordEventTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        self.conn = storage.open_storage(self.path)

    def tearDown(self) -> None:
        self.conn.close()
        os.remove(self.path)

    def test_repair_key_is_persisted_beside_the_event(self) -> None:
        event = _make_event("operator:mina", "role.grant", "allowed", "2026-08-15T22:00:00Z")
        storage.record_event(self.conn, event)

        rows = storage.fetch_observations(self.conn, event.event_id)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["content_id"], event.event_id)
        self.assertEqual(row["recorded_at"], event.recorded_at)
        self.assertEqual(
            row["repair_key"],
            durable_repair_key(
                event.actor, event.action, event.outcome, event.recorded_at, event.event_id,
            ),
        )
        self.assertEqual(row["repair_key"], complete_event_identity(event.recorded_at, event.event_id))

    def test_round_trips_the_stored_event(self) -> None:
        event = _make_event(
            "operator:mina", "role.grant", "allowed", "2026-08-15T22:00:00Z",
            sequence=3, metadata={"ticket": "T-1"},
        )
        storage.record_event(self.conn, event)
        row = storage.fetch_observations(self.conn, event.event_id)[0]
        self.assertEqual(storage.row_to_event(row), event)

    def test_repeated_observations_with_different_metadata_are_not_deduplicated(self) -> None:
        # Two role.grant handoff observations describing the exact same
        # event (same actor/action/outcome/recorded_at, hence one complete
        # event identity) but with different caller metadata.
        first = _make_event(
            "operator:mina", "role.grant", "allowed", "2026-08-15T22:00:00Z",
            metadata={"ticket": "T-1", "source": "night-shift-feed-a"},
        )
        second = _make_event(
            "operator:mina", "role.grant", "allowed", "2026-08-15T22:00:00Z",
            metadata={"ticket": "T-2", "source": "night-shift-feed-b"},
        )
        self.assertEqual(first.event_id, second.event_id, "both observations share one complete event identity")

        storage.record_event(self.conn, first)
        storage.record_event(self.conn, second)

        rows = storage.fetch_observations(self.conn, first.event_id)
        self.assertEqual(len(rows), 2, "both observations must be kept as separate append-only rows")
        stored_metadata = [row["metadata_json"] for row in rows]
        self.assertNotEqual(stored_metadata[0], stored_metadata[1])

        # Same identity means the same repair key for both -- the key
        # never depends on metadata.
        self.assertEqual(rows[0]["repair_key"], rows[1]["repair_key"])

    def test_two_different_target_repair_keys_differ(self) -> None:
        alpha = _make_event("operator:mina", "role.grant", "allowed", "2026-08-15T22:00:00Z")
        bravo = _make_event("operator:sven", "role.revoke", "allowed", "2026-08-15T23:00:00Z")

        key_alpha = durable_repair_key(alpha.actor, alpha.action, alpha.outcome, alpha.recorded_at, alpha.event_id)
        key_bravo = durable_repair_key(bravo.actor, bravo.action, bravo.outcome, bravo.recorded_at, bravo.event_id)

        self.assertNotEqual(key_alpha, key_bravo)

    def test_fetch_all_events_returns_every_row_in_insertion_order(self) -> None:
        first = _make_event("operator:mina", "role.grant", "allowed", "2026-08-15T22:00:00Z")
        second = _make_event("operator:sven", "role.revoke", "allowed", "2026-08-15T23:00:00Z")
        storage.record_event(self.conn, first)
        storage.record_event(self.conn, second)

        rows = storage.fetch_all_events(self.conn)
        self.assertEqual([row["content_id"] for row in rows], [first.event_id, second.event_id])


class QueueClaimTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        self.conn = storage.open_storage(self.path)
        storage.enqueue(self.conn, "queue-1", "bundle-1", "2026-08-15T22:00:00Z")

    def tearDown(self) -> None:
        self.conn.close()
        os.remove(self.path)

    def test_claim_succeeds_and_marks_the_entry_claimed(self) -> None:
        won = storage.claim_queue_entry(
            self.conn, "claim-1", "queue-1",
            assignee_id="night-owl", shift_id="night", ticket_id="T-1", claimed_at="2026-08-15T22:05:00Z",
        )
        self.assertTrue(won)
        entry = storage.row_to_queue_entry(storage.fetch_queue_entry(self.conn, "queue-1"))
        self.assertEqual(entry.status.value, "claimed")
        claim = storage.row_to_claim(storage.fetch_claim(self.conn, "claim-1"))
        self.assertEqual(claim.status.value, "active")

    def test_second_claim_on_the_same_entry_loses(self) -> None:
        first = storage.claim_queue_entry(
            self.conn, "claim-1", "queue-1",
            assignee_id="night-owl", shift_id="night", ticket_id="T-1", claimed_at="2026-08-15T22:05:00Z",
        )
        second = storage.claim_queue_entry(
            self.conn, "claim-2", "queue-1",
            assignee_id="day-owl", shift_id="day", ticket_id="T-1", claimed_at="2026-08-15T22:06:00Z",
        )
        self.assertTrue(first)
        self.assertFalse(second)
        self.assertIsNone(storage.fetch_claim(self.conn, "claim-2"))

    def test_release_reopens_the_queue_entry_and_marks_the_claim_released(self) -> None:
        storage.claim_queue_entry(
            self.conn, "claim-1", "queue-1",
            assignee_id="night-owl", shift_id="night", ticket_id="T-1", claimed_at="2026-08-15T22:05:00Z",
        )
        released = storage.release_queue_claim(self.conn, "claim-1")
        self.assertTrue(released)
        claim = storage.row_to_claim(storage.fetch_claim(self.conn, "claim-1"))
        entry = storage.row_to_queue_entry(storage.fetch_queue_entry(self.conn, "queue-1"))
        self.assertEqual(claim.status.value, "released")
        self.assertEqual(entry.status.value, "pending")

    def test_release_of_a_missing_claim_loses(self) -> None:
        self.assertFalse(storage.release_queue_claim(self.conn, "no-such-claim"))

    def test_release_of_an_already_released_claim_loses(self) -> None:
        storage.claim_queue_entry(
            self.conn, "claim-1", "queue-1",
            assignee_id="night-owl", shift_id="night", ticket_id="T-1", claimed_at="2026-08-15T22:05:00Z",
        )
        first = storage.release_queue_claim(self.conn, "claim-1")
        second = storage.release_queue_claim(self.conn, "claim-1")
        self.assertTrue(first)
        self.assertFalse(second, "a claim that is not active cannot be released again")


# -- Cross-process proofs ------------------------------------------------
#
# Worker functions must live at module scope so they can be pickled and
# re-imported by a spawned child process (the default start method on
# Windows, and available everywhere).

def _worker_write_event_and_enqueue(db_path: str) -> None:
    conn = storage.open_storage(db_path)
    try:
        event = _make_event(
            "operator:mina", "role.grant", "allowed", "2026-08-15T22:00:00Z",
            metadata={"ticket": "T-night-1"},
        )
        storage.record_event(conn, event)
        storage.enqueue(conn, "queue-night-1", "bundle-night-1", "2026-08-15T22:01:00Z")
    finally:
        conn.close()


def _worker_read_event_and_queue_state(db_path: str, out_queue: "multiprocessing.Queue") -> None:
    conn = storage.open_storage(db_path)
    try:
        expected_id = content_digest("operator:mina", "role.grant", "allowed", "2026-08-15T22:00:00Z")
        event_rows = storage.fetch_observations(conn, expected_id)
        queue_row = storage.fetch_queue_entry(conn, "queue-night-1")
        out_queue.put({
            "event_count": len(event_rows),
            "event_metadata": event_rows[0]["metadata_json"] if event_rows else None,
            "queue_status": queue_row["status"] if queue_row is not None else None,
        })
    finally:
        conn.close()


def _worker_attempt_claim(db_path: str, claim_id: str, out_queue: "multiprocessing.Queue") -> None:
    conn = storage.open_storage(db_path)
    try:
        won = storage.claim_queue_entry(
            conn, claim_id, "queue-night-1",
            assignee_id=f"assignee-{claim_id}", shift_id="night", ticket_id="T-night-1",
            claimed_at="2026-08-15T22:10:00Z",
        )
        out_queue.put(won)
    finally:
        conn.close()


class CrossProcessTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        # Create the schema up front from the parent process so every
        # child process opens a file that already has the tables.
        storage.open_storage(self.path).close()

    def tearDown(self) -> None:
        os.remove(self.path)

    def test_event_and_queue_state_are_visible_from_a_separate_process(self) -> None:
        writer = multiprocessing.Process(target=_worker_write_event_and_enqueue, args=(self.path,))
        writer.start()
        writer.join(timeout=30)
        self.assertEqual(writer.exitcode, 0)

        out_queue: multiprocessing.Queue = multiprocessing.Queue()
        reader = multiprocessing.Process(
            target=_worker_read_event_and_queue_state, args=(self.path, out_queue),
        )
        reader.start()
        result = out_queue.get(timeout=30)
        reader.join(timeout=30)
        self.assertEqual(reader.exitcode, 0)

        self.assertEqual(result["event_count"], 1)
        self.assertIn("T-night-1", result["event_metadata"])
        self.assertEqual(result["queue_status"], "pending")

    def test_claim_is_atomic_across_separate_processes(self) -> None:
        conn = storage.open_storage(self.path)
        storage.enqueue(conn, "queue-night-1", "bundle-night-1", "2026-08-15T22:01:00Z")
        conn.close()

        out_queue: multiprocessing.Queue = multiprocessing.Queue()
        procs = [
            multiprocessing.Process(
                target=_worker_attempt_claim, args=(self.path, f"claim-{i}", out_queue),
            )
            for i in range(8)
        ]
        for proc in procs:
            proc.start()
        results = [out_queue.get(timeout=30) for _ in procs]
        for proc in procs:
            proc.join(timeout=30)
            self.assertEqual(proc.exitcode, 0)

        self.assertEqual(results.count(True), 1, "exactly one process must win the claim")
        self.assertEqual(results.count(False), len(procs) - 1)

        conn = storage.open_storage(self.path)
        try:
            entry = storage.row_to_queue_entry(storage.fetch_queue_entry(conn, "queue-night-1"))
            self.assertEqual(entry.status.value, "claimed")
            claim_rows = conn.execute(
                "SELECT COUNT(*) AS n FROM claims WHERE queue_entry_id = ?", ("queue-night-1",),
            ).fetchone()
            self.assertEqual(claim_rows[0], 1)
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
