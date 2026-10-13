"""Persistence and separate-process tests for auditlog.sqlite_store."""

from __future__ import annotations

import dataclasses
import json
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from auditlog.errors import IdempotencyConflictError, MalformedActorError, OptimisticConflictError
from auditlog.models import content_digest
from auditlog.sqlite_store import SqliteAuditLogService

REPO_ROOT = Path(__file__).parent.parent

_RAW_INSERT_SQL = (
    "INSERT INTO events "
    "(sequence, event_id, actor, action, outcome, recorded_at, source_version, metadata, idempotency_key) "
    "VALUES (?, ?, ?, ?, ?, ?, 2, '{}', ?)"
)


class PersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "trail.db"

    def test_events_survive_a_fresh_service_instance_against_the_same_file(self) -> None:
        first = SqliteAuditLogService(self.path)
        first.record("operator:mina", "policy.update", "allowed")
        first.record("service:indexer", "report.read", "denied")

        reopened = SqliteAuditLogService(self.path)
        events = reopened.query()
        self.assertEqual([e.sequence for e in events], [1, 2])
        self.assertEqual([e.actor for e in events], ["operator:mina", "service:indexer"])

    def test_metadata_round_trips_through_storage(self) -> None:
        service = SqliteAuditLogService(self.path)
        service.record(
            "operator:mina",
            "policy.update",
            "allowed",
            metadata={"reason": "quarterly", "ticket": "OPS-1"},
        )
        reopened = SqliteAuditLogService(self.path)
        [event] = reopened.query()
        self.assertEqual(event.metadata, {"reason": "quarterly", "ticket": "OPS-1"})

    def test_repeated_record_calls_each_accept_their_own_metadata(self) -> None:
        service = SqliteAuditLogService(self.path)
        service.record("operator:mina", "policy.update", "allowed", metadata={"reason": "a"})
        service.record("operator:mina", "policy.update", "allowed", metadata={"reason": "b"})
        events = service.query()
        self.assertEqual([e.metadata["reason"] for e in events], ["a", "b"])

    def test_all_state_lives_under_the_one_selected_file(self) -> None:
        service = SqliteAuditLogService(self.path)
        service.record("operator:mina", "policy.update", "allowed")
        service.query()
        service.repair()
        self.assertEqual([p.name for p in self.path.parent.iterdir()], [self.path.name])

    def test_a_malformed_actor_does_not_advance_the_stored_sequence(self) -> None:
        service = SqliteAuditLogService(self.path)
        service.record("operator:mina", "policy.update", "allowed")
        with self.assertRaises(MalformedActorError):
            service.record("bogus", "policy.update", "allowed")
        following = service.record("service:indexer", "report.read", "denied")
        self.assertEqual(following.sequence, 2)

    def test_stored_rows_cannot_be_updated(self) -> None:
        service = SqliteAuditLogService(self.path)
        service.record("operator:mina", "policy.update", "allowed")
        conn = sqlite3.connect(str(self.path))
        try:
            with self.assertRaises(sqlite3.DatabaseError):
                conn.execute("UPDATE events SET actor = 'operator:tampered' WHERE sequence = 1")
        finally:
            conn.close()
        # The row is untouched: the trigger aborted before any write landed.
        self.assertEqual(SqliteAuditLogService(self.path).query()[0].actor, "operator:mina")

    def test_stored_rows_cannot_be_deleted(self) -> None:
        service = SqliteAuditLogService(self.path)
        service.record("operator:mina", "policy.update", "allowed")
        conn = sqlite3.connect(str(self.path))
        try:
            with self.assertRaises(sqlite3.DatabaseError):
                conn.execute("DELETE FROM events WHERE sequence = 1")
        finally:
            conn.close()
        self.assertEqual(len(SqliteAuditLogService(self.path).query()), 1)

    def test_metadata_key_order_is_stable_across_reads(self) -> None:
        service = SqliteAuditLogService(self.path)
        service.record("operator:mina", "policy.update", "allowed", metadata={"zeta": "1", "alpha": "2"})
        first = SqliteAuditLogService(self.path).query()[0]
        second = SqliteAuditLogService(self.path).query()[0]
        self.assertEqual(list(first.metadata.keys()), ["alpha", "zeta"])
        self.assertEqual(json.dumps(first.metadata), json.dumps(second.metadata))


class RepairTests(unittest.TestCase):
    """Verification-report tests specific to the SQLite backend.

    Append-only is enforced by the ``events_no_update``/``events_no_delete``
    triggers, so corrupting a row for these tests requires a raw connection
    that drops the relevant trigger first, then a fresh ``SqliteAuditLogService``
    (whose own schema init recreates any missing trigger) to run ``repair``.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "trail.db"

    def test_repair_reports_a_clean_trail(self) -> None:
        service = SqliteAuditLogService(self.path)
        service.record("operator:mina", "policy.update", "allowed")
        service.record("service:indexer", "report.read", "denied")
        report = service.repair()
        self.assertTrue(report.ok)
        self.assertEqual(report.expected_count, 2)
        self.assertEqual(report.actual_count, 2)

    def test_repair_detects_a_sequence_gap(self) -> None:
        service = SqliteAuditLogService(self.path)
        service.record("operator:mina", "policy.update", "allowed")

        conn = sqlite3.connect(str(self.path))
        try:
            event_id = content_digest("service:indexer", "report.read", "denied", "2024-01-01T00:00:00Z")
            conn.execute(
                _RAW_INSERT_SQL,
                (3, event_id, "service:indexer", "report.read", "denied", "2024-01-01T00:00:00Z", None),
            )
            conn.commit()
        finally:
            conn.close()

        report = SqliteAuditLogService(self.path).repair()
        self.assertFalse(report.ok)
        self.assertEqual(report.sequence_gaps, (2,))
        self.assertEqual(report.corrupt, ())

    def test_repair_detects_a_content_edit(self) -> None:
        service = SqliteAuditLogService(self.path)
        service.record("operator:mina", "policy.update", "allowed")

        conn = sqlite3.connect(str(self.path))
        try:
            conn.execute("DROP TRIGGER events_no_update")
            conn.execute("UPDATE events SET outcome = 'denied' WHERE sequence = 1")
            conn.commit()
        finally:
            conn.close()

        report = SqliteAuditLogService(self.path).repair()
        self.assertFalse(report.ok)
        self.assertEqual(len(report.corrupt), 1)
        sequence, message = report.corrupt[0]
        self.assertEqual(sequence, 1)
        self.assertIn("content", message)

    def test_repair_detects_duplicate_idempotency_keys(self) -> None:
        service = SqliteAuditLogService(self.path)
        service.record("operator:mina", "policy.update", "allowed", idempotency_key="shared")

        conn = sqlite3.connect(str(self.path))
        try:
            event_id = content_digest("service:indexer", "report.read", "denied", "2024-01-01T00:00:00Z")
            conn.execute(
                _RAW_INSERT_SQL,
                (2, event_id, "service:indexer", "report.read", "denied", "2024-01-01T00:00:00Z", "shared"),
            )
            conn.commit()
        finally:
            conn.close()

        report = SqliteAuditLogService(self.path).repair()
        self.assertFalse(report.ok)
        self.assertEqual(report.duplicate_idempotency_keys, ("shared",))

    def test_repair_writes_report_beneath_a_nested_caller_named_path(self) -> None:
        service = SqliteAuditLogService(self.path)
        service.record("operator:mina", "policy.update", "allowed")
        report = service.repair(report_path="verification/2024/06.json")
        target = self.path.parent / "verification" / "2024" / "06.json"
        self.assertEqual(Path(report.report_path), target.resolve())
        on_disk = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(on_disk["checked"], 1)
        self.assertEqual(on_disk["corrupt"], [])


class ImportTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "trail.db"

    def test_import_events_assigns_gapless_sequence(self) -> None:
        service = SqliteAuditLogService(self.path)
        service.record("operator:mina", "policy.update", "allowed")
        report = service.import_events(
            [
                {"actor": "service:indexer", "action": "report.read", "outcome": "denied", "recorded_at": "2024-01-01T00:00:00Z"},
                {"actor": "service:indexer", "action": "report.read", "outcome": "allowed", "recorded_at": "2024-01-01T00:01:00Z"},
            ]
        )
        self.assertEqual([e.sequence for e in report.imported], [2, 3])
        self.assertEqual([e.sequence for e in service.query()], [1, 2, 3])

    def test_resuming_an_interrupted_import_does_not_duplicate_committed_events(self) -> None:
        batch = [
            {"actor": "operator:mina", "action": "policy.update", "outcome": "allowed", "recorded_at": "2024-01-01T00:00:00Z", "idempotency_key": "batch-1"},
            {"actor": "operator:mina", "action": "policy.update", "outcome": "denied", "recorded_at": "2024-01-01T00:00:01Z", "idempotency_key": "batch-2"},
        ]
        SqliteAuditLogService(self.path).import_events(batch[:1])
        resumed = SqliteAuditLogService(self.path)
        report = resumed.import_events(batch)
        self.assertEqual(report.skipped_duplicates, ("batch-1",))
        self.assertEqual([e.sequence for e in report.imported], [2])
        self.assertTrue(resumed.repair().ok)

    def test_import_events_conflicting_idempotency_key_aborts_the_whole_batch(self) -> None:
        service = SqliteAuditLogService(self.path)
        service.import_events(
            [{"actor": "operator:mina", "action": "policy.update", "outcome": "allowed", "recorded_at": "2024-01-01T00:00:00Z", "idempotency_key": "imp-1"}]
        )
        with self.assertRaises(IdempotencyConflictError):
            service.import_events(
                [
                    {"actor": "service:indexer", "action": "report.read", "outcome": "denied", "recorded_at": "2024-02-01T00:00:00Z"},
                    {"actor": "operator:mina", "action": "policy.update", "outcome": "denied", "recorded_at": "2024-01-01T00:00:00Z", "idempotency_key": "imp-1"},
                ]
            )
        self.assertEqual(len(service.query()), 1)

    def test_concurrent_record_calls_with_the_same_idempotency_key_produce_one_event(self) -> None:
        # Real thread concurrency against the same file: every caller races
        # to record the same logical write; only one row must ever land.
        service = SqliteAuditLogService(self.path)
        results: list = []
        errors: list = []

        def attempt() -> None:
            try:
                results.append(
                    service.record("operator:mina", "policy.update", "allowed", idempotency_key="race")
                )
            except Exception as exc:  # pragma: no cover - failure path only
                errors.append(exc)

        threads = [threading.Thread(target=attempt) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [])
        self.assertEqual(len(results), 8)
        self.assertEqual(len({r.event_id for r in results}), 1)
        self.assertEqual(len({r.sequence for r in results}), 1)
        self.assertEqual(len(service.query()), 1)


_SUBPROCESS_RECORD_SCRIPT = """
import sys
from auditlog.sqlite_store import SqliteAuditLogService

service = SqliteAuditLogService(sys.argv[1])
event = service.record(sys.argv[2], sys.argv[3], sys.argv[4])
print(event.sequence)
"""

_SUBPROCESS_QUERY_SCRIPT = """
import dataclasses
import json
import sys
from auditlog.sqlite_store import SqliteAuditLogService

service = SqliteAuditLogService(sys.argv[1])
events = service.query()
print(json.dumps([dataclasses.asdict(e) for e in events]))
"""

_SUBPROCESS_IMPORT_SCRIPT = """
import json
import sys
from auditlog.errors import OptimisticConflictError
from auditlog.sqlite_store import SqliteAuditLogService

service = SqliteAuditLogService(sys.argv[1])
expected = int(sys.argv[2])
try:
    report = service.import_events(
        [{"actor": "service:indexer", "action": "report.read", "outcome": "denied", "recorded_at": "2024-01-01T00:00:00Z"}],
        expected_sequence=expected,
    )
    print(json.dumps({"ok": True, "imported": [e.sequence for e in report.imported]}))
except OptimisticConflictError as exc:
    print(json.dumps({"ok": False, "error": str(exc)}))
"""


class SeparateProcessTests(unittest.TestCase):
    """Proves durability across a real OS process boundary, not just a new object."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "trail.db"

    def _run(self, script: str, *args: str) -> str:
        result = subprocess.run(
            [sys.executable, "-c", script, *args],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def test_a_separate_process_reads_what_this_process_recorded(self) -> None:
        service = SqliteAuditLogService(self.path)
        service.record("operator:mina", "policy.update", "allowed")
        service.record("service:indexer", "report.read", "denied")

        out = self._run(_SUBPROCESS_QUERY_SCRIPT, str(self.path))
        events = json.loads(out)
        self.assertEqual([e["sequence"] for e in events], [1, 2])
        self.assertEqual([e["actor"] for e in events], ["operator:mina", "service:indexer"])

    def test_this_process_reads_what_a_separate_process_recorded(self) -> None:
        out = self._run(
            _SUBPROCESS_RECORD_SCRIPT, str(self.path), "operator:mina", "policy.update", "allowed"
        )
        self.assertEqual(out, "1")

        service = SqliteAuditLogService(self.path)
        events = service.query()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].actor, "operator:mina")
        self.assertEqual(events[0].sequence, 1)

    def test_sequence_stays_gapless_across_alternating_processes(self) -> None:
        service = SqliteAuditLogService(self.path)
        service.record("operator:mina", "policy.update", "allowed")

        out = self._run(
            _SUBPROCESS_RECORD_SCRIPT, str(self.path), "service:indexer", "report.read", "denied"
        )
        self.assertEqual(out, "2")

        third = service.record("system:scheduler", "policy.update", "allowed")
        self.assertEqual(third.sequence, 3)

        out = self._run(_SUBPROCESS_QUERY_SCRIPT, str(self.path))
        events = json.loads(out)
        self.assertEqual([e["sequence"] for e in events], [1, 2, 3])

    def test_optimistic_conflict_is_detected_across_processes(self) -> None:
        service = SqliteAuditLogService(self.path)
        service.record("operator:mina", "policy.update", "allowed")  # sequence 1

        # A separate process advances the trail past what we last observed.
        out = self._run(
            _SUBPROCESS_RECORD_SCRIPT, str(self.path), "service:indexer", "report.read", "denied"
        )
        self.assertEqual(out, "2")

        # We still act on our stale read (base sequence 1); the import must
        # be refused rather than silently mis-sequenced on top of it.
        out = self._run(_SUBPROCESS_IMPORT_SCRIPT, str(self.path), "1")
        result = json.loads(out)
        self.assertFalse(result["ok"])
        self.assertEqual(len(service.query()), 2)


if __name__ == "__main__":
    unittest.main()
