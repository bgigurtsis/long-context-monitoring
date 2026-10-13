"""Contract tests for the durable SQLite source-event store.

Covers: durability and ordering across a fresh connection, the durable
repair key persisted beside each row, that repeated exact observations are
kept as separate rows rather than deduplicated, that a store commit needs no
query index at all, and that a row committed by this process is visible to
a completely separate process reading the same database file.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from auditlog.index_segments import SegmentedQueryIndex
from auditlog.integrity import complete_event_identity, durable_repair_key
from auditlog.models import AuditEvent, content_digest
from auditlog.service import AuditLogService
from auditlog.sqlite_store import SQLiteEventStore

REPO_ROOT = Path(__file__).parent.parent


def make_event(*, actor, action, outcome, recorded_at, sequence, metadata=None) -> AuditEvent:
    event_id = content_digest(actor, action, outcome, recorded_at)
    return AuditEvent(event_id, sequence, actor, action, outcome, recorded_at, metadata=metadata or {})


class SQLiteEventStoreRoundTripTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.db_path = str(Path(self._tmp.name) / "events.db")

    def test_appended_events_survive_a_fresh_connection_in_order(self) -> None:
        store = SQLiteEventStore(self.db_path)
        first = make_event(actor="operator:mina", action="role.grant", outcome="allowed", recorded_at="T1", sequence=1)
        second = make_event(actor="operator:sven", action="role.revoke", outcome="allowed", recorded_at="T2", sequence=2)
        store.append(first)
        store.append(second)

        # A brand-new store object, same path, no shared connection or state.
        reread = SQLiteEventStore(self.db_path)
        events = list(reread.iter_events())

        self.assertEqual([e.event_id for e in events], [first.event_id, second.event_id])
        self.assertEqual([e.sequence for e in events], [1, 2])
        self.assertEqual([e.actor for e in events], ["operator:mina", "operator:sven"])

    def test_repair_key_is_persisted_beside_each_source_event(self) -> None:
        store = SQLiteEventStore(self.db_path)
        event = make_event(
            actor="operator:mina", action="role.grant", outcome="allowed", recorded_at="T1", sequence=1
        )
        store.append(event)

        expected_key = durable_repair_key(event.actor, event.action, event.outcome, event.recorded_at, event.event_id)
        self.assertEqual(expected_key, complete_event_identity(event.recorded_at, event.event_id))
        self.assertEqual(store.repair_keys(), [expected_key])

    def test_repeated_exact_observations_are_kept_as_separate_rows(self) -> None:
        """Two role.grant observations sharing one complete event identity.

        Same actor/action/outcome/recorded_at -> same content id -> the same
        durable repair key -- but different (segment) metadata. Ingestion
        must not collapse them into one row.
        """

        service = AuditLogService(store=SQLiteEventStore(self.db_path), index=SegmentedQueryIndex())
        first = service.record_new(
            actor="operator:mina",
            action="role.grant",
            outcome="allowed",
            recorded_at="2026-08-14T18:20:00+00:00",
            metadata={"segment": "eu-west"},
        )
        second = service.record_new(
            actor="operator:mina",
            action="role.grant",
            outcome="allowed",
            recorded_at="2026-08-14T18:20:00+00:00",
            metadata={"segment": "us-east"},
        )

        self.assertEqual(first.event_id, second.event_id)
        self.assertNotEqual(first.sequence, second.sequence)
        self.assertNotEqual(first.metadata, second.metadata)

        # Read back through an independent store instance over the same file.
        reread = SQLiteEventStore(self.db_path)
        stored = list(reread.iter_events())
        self.assertEqual(len(stored), 2)
        self.assertEqual({e.event_id for e in stored}, {first.event_id})
        self.assertEqual([e.metadata for e in stored], [{"segment": "eu-west"}, {"segment": "us-east"}])

        # Both rows carry the same durable repair key: it never dedupes them,
        # it only records that they share one complete event identity.
        keys = reread.repair_keys()
        self.assertEqual(len(keys), 2)
        self.assertEqual(keys[0], keys[1])
        self.assertEqual(keys[0], complete_event_identity(first.recorded_at, first.event_id))

    def test_append_commits_with_no_query_index_involved(self) -> None:
        """A commit needs nothing from the index layer -- not even an instance of one."""

        store = SQLiteEventStore(self.db_path)
        event = make_event(
            actor="operator:mina", action="role.grant", outcome="allowed", recorded_at="T1", sequence=1
        )
        store.append(event)  # No QueryIndex object exists anywhere in this test.

        reread = SQLiteEventStore(self.db_path)
        self.assertEqual([e.event_id for e in reread.iter_events()], [event.event_id])

    def test_a_separate_process_reads_the_committed_event(self) -> None:
        store = SQLiteEventStore(self.db_path)
        event = make_event(
            actor="operator:mina", action="role.grant", outcome="allowed", recorded_at="T1", sequence=1
        )
        store.append(event)

        child_script = (
            "import json, sys\n"
            "from auditlog.sqlite_store import SQLiteEventStore\n"
            "store = SQLiteEventStore(sys.argv[1])\n"
            "events = list(store.iter_events())\n"
            "print(json.dumps([[e.event_id, e.sequence, e.actor, e.metadata] for e in events]))\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", child_script, self.db_path],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload, [[event.event_id, event.sequence, event.actor, event.metadata]])


if __name__ == "__main__":
    unittest.main()
