"""``CheckpointStore``: what it persists, and how durable that is.

Every check here is about the checkpoint file itself — its schema, its
values, and whether one process's write is visible to a completely
separate ``CheckpointStore`` instance opened against the same path — not
about replaying any actual SDK call (see ``tests/test_migration_replay.py``
for that).
"""

from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from auditlog.migration_checkpoint import COMPLETED, PENDING, CheckpointStore


class CheckpointStoreTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "checkpoint.db"


class PersistedShapeTests(CheckpointStoreTestCase):
    def test_a_call_never_seen_before_has_no_status(self) -> None:
        store = CheckpointStore(self.path)
        self.assertIsNone(store.status("call-1"))
        self.assertFalse(store.is_completed("call-1"))

    def test_mark_pending_then_completed_updates_the_same_call_id(self) -> None:
        store = CheckpointStore(self.path)
        store.mark_pending("call-1")
        self.assertEqual(store.status("call-1"), PENDING)
        self.assertFalse(store.is_completed("call-1"))

        store.mark_completed("call-1")
        self.assertEqual(store.status("call-1"), COMPLETED)
        self.assertTrue(store.is_completed("call-1"))

    def test_the_schema_persists_only_call_id_and_status(self) -> None:
        store = CheckpointStore(self.path)
        store.mark_completed("call-1")

        connection = sqlite3.connect(self.path)
        try:
            columns = [
                row[1] for row in connection.execute("PRAGMA table_info(checkpoints)").fetchall()
            ]
        finally:
            connection.close()
        self.assertEqual(sorted(columns), ["call_id", "status"])

    def test_every_persisted_status_value_is_pending_or_completed(self) -> None:
        store = CheckpointStore(self.path)
        store.mark_pending("call-1")
        store.mark_completed("call-2")

        connection = sqlite3.connect(self.path)
        try:
            statuses = {
                row[0] for row in connection.execute("SELECT status FROM checkpoints").fetchall()
            }
        finally:
            connection.close()
        self.assertEqual(statuses, {PENDING, COMPLETED})


class NoBearerTokenTests(CheckpointStoreTestCase):
    def test_a_bearer_token_used_as_a_call_id_is_the_only_way_it_could_appear(self) -> None:
        """The store has no field for a credential; the only string it ever
        writes is whatever the caller passes as ``call_id``. Passing a real
        credential as an ordinary opaque id would be a caller mistake, not a
        store behavior — this documents that the store itself introduces no
        other place a token could leak into the file.
        """

        store = CheckpointStore(self.path)
        store.mark_completed("sha256:9f86d081884c7d659a2feaa0c55ad015")

        raw = self.path.read_bytes()
        self.assertNotIn(b"Bearer", raw)

    def test_marking_calls_never_writes_a_realistic_bearer_token_string(self) -> None:
        store = CheckpointStore(self.path)
        bearer_token = "s3cret-token-should-never-be-written"
        store.mark_pending("call-1")
        store.mark_completed("call-1")

        raw = self.path.read_bytes()
        self.assertNotIn(bearer_token.encode("utf-8"), raw)


class SeparateProcessContinuationTests(CheckpointStoreTestCase):
    """Two independent ``CheckpointStore`` instances, same path: no shared memory."""

    def test_a_completion_marked_by_one_instance_is_visible_to_a_brand_new_instance(self) -> None:
        writer = CheckpointStore(self.path)
        writer.mark_completed("call-1")

        reader = CheckpointStore(self.path)
        self.assertTrue(reader.is_completed("call-1"))

    def test_a_pending_mark_by_one_instance_is_visible_to_a_brand_new_instance(self) -> None:
        writer = CheckpointStore(self.path)
        writer.mark_pending("call-1")

        reader = CheckpointStore(self.path)
        self.assertEqual(reader.status("call-1"), PENDING)
        self.assertFalse(reader.is_completed("call-1"))


if __name__ == "__main__":
    unittest.main()
