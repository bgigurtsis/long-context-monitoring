"""Tests for the durable SQLite event journal and replica-north replay.

Covers: the storage-independent contract (against a real SQLite file), the
durable repair key persisted beside each event, repeated observations
surviving as separate append-only rows instead of being deduplicated,
atomic cursor advances under concurrent writers, and reads from a genuinely
separate OS process.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from typing import Optional

# tests/ has no __init__.py, so make the sibling contract-test module
# importable regardless of how this file is invoked (unittest discover,
# a direct script run, or a different test runner).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_service_contract import AuditLogServiceContractTests  # noqa: E402

from auditlog.integrity import complete_event_identity, durable_repair_key  # noqa: E402
from auditlog.service import AuditLogService  # noqa: E402
from auditlog.sqlite_store import SQLiteAuditLogService  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = REPO_ROOT / "fixtures" / "v13" / "audit-route-s03" / "scenario.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["material"]["fixtures"]


class _TempDbMixin:
    def _make_db_path(self) -> str:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        return str(Path(tmpdir.name) / "audit.db")


class SQLiteAuditLogServiceContractTests(_TempDbMixin, AuditLogServiceContractTests, unittest.TestCase):
    """The SQLite backend must satisfy the same storage-independent contract."""

    def make_service(self) -> AuditLogService:
        return SQLiteAuditLogService(self._make_db_path())


class DurableRepairKeyTests(_TempDbMixin, unittest.TestCase):
    def setUp(self) -> None:
        self.service = SQLiteAuditLogService(self._make_db_path())

    def test_repair_key_matches_complete_event_identity(self) -> None:
        event = self.service.record(
            "operator:mina", "role.grant", "allowed", "2026-08-13T06:40:00+00:00", metadata={"x": 1}
        )
        expected = durable_repair_key(
            "operator:mina", "role.grant", "allowed", "2026-08-13T06:40:00+00:00", event.event_id
        )
        self.assertEqual(expected, complete_event_identity(event.recorded_at, event.content_id))
        self.assertEqual(self.service.repair_key_for(event.sequence), expected)

    def test_repair_key_is_persisted_beside_each_event_not_shared(self) -> None:
        first = self.service.record("operator:mina", "role.grant", "allowed", "2026-08-13T06:40:00+00:00")
        second = self.service.record("operator:mina", "role.grant", "allowed", "2026-08-13T06:40:11+00:00")

        first_key = self.service.repair_key_for(first.sequence)
        second_key = self.service.repair_key_for(second.sequence)

        self.assertEqual(first_key, complete_event_identity(first.recorded_at, first.content_id))
        self.assertEqual(second_key, complete_event_identity(second.recorded_at, second.content_id))
        self.assertNotEqual(first_key, second_key)

    def test_metadata_never_reaches_the_repair_key_call(self) -> None:
        # Same identity, different metadata: the repair key must be identical
        # because durable_repair_key never receives metadata as an input.
        first = self.service.record(
            "operator:mina", "role.grant", "allowed", "2026-08-13T06:40:00+00:00", metadata={"note": "a"}
        )
        second = self.service.record(
            "operator:mina", "role.grant", "allowed", "2026-08-13T06:40:00+00:00", metadata={"note": "b"}
        )
        self.assertEqual(
            self.service.repair_key_for(first.sequence), self.service.repair_key_for(second.sequence)
        )
        self.assertNotEqual(first.metadata, second.metadata)

    def test_two_target_repair_keys_differ(self) -> None:
        fixture = _load_fixture()
        action = fixture["target_action"]
        outcome = fixture["target_outcome"]
        primary_spec, promoted_spec = fixture["target_events"]

        primary = self.service.record(primary_spec["actor"], action, outcome, primary_spec["recorded_at"])
        promoted = self.service.record(promoted_spec["actor"], action, outcome, promoted_spec["recorded_at"])

        primary_key = self.service.repair_key_for(primary.sequence)
        promoted_key = self.service.repair_key_for(promoted.sequence)

        # invariant: "The two target content IDs must differ."
        self.assertNotEqual(primary.event_id, promoted.event_id)
        self.assertNotEqual(primary_key, promoted_key)


class RepeatedObservationTests(_TempDbMixin, unittest.TestCase):
    def test_two_role_grant_replay_observations_are_kept_as_separate_rows(self) -> None:
        service = SQLiteAuditLogService(self._make_db_path())

        first = service.record(
            "operator:mina",
            "role.grant",
            "allowed",
            "2026-08-13T06:40:00+00:00",
            metadata={"observed_by": "replica-north", "note": "first replay observation"},
        )
        second = service.record(
            "operator:mina",
            "role.grant",
            "allowed",
            "2026-08-13T06:40:00+00:00",
            metadata={"observed_by": "replica-north", "note": "second replay observation"},
        )

        # One complete event identity...
        self.assertEqual(first.event_id, second.event_id)
        self.assertEqual(first.identity, second.identity)
        self.assertEqual(
            service.repair_key_for(first.sequence), service.repair_key_for(second.sequence)
        )
        # ...but two distinct append-only rows with their own metadata, never
        # collapsed into one during ingestion.
        self.assertNotEqual(first.sequence, second.sequence)
        self.assertNotEqual(first.metadata, second.metadata)

        replayed = list(service.events())
        self.assertEqual(len(replayed), 2)
        self.assertEqual([e.sequence for e in replayed], [first.sequence, second.sequence])
        self.assertEqual([e.metadata for e in replayed], [first.metadata, second.metadata])


class AtomicCursorAdvanceTests(_TempDbMixin, unittest.TestCase):
    def test_advance_for_unregistered_replica_leaves_no_partial_row(self) -> None:
        service = SQLiteAuditLogService(self._make_db_path())
        with self.assertRaises(KeyError):
            service.advance_cursor("replica-north", offset=1, last_event_id="does-not-matter")
        self.assertIsNone(service.get_cursor("replica-north"))

    def test_concurrent_advances_never_produce_a_torn_offset_and_event_pairing(self) -> None:
        db_path = self._make_db_path()
        service = SQLiteAuditLogService(db_path)
        replica = service.register_replica("replica-north")

        attempts = 25
        errors: list[BaseException] = []

        def _advance(i: int) -> None:
            try:
                # Each thread gets its own connection through a fresh service
                # handle, the same way independent replay workers would.
                SQLiteAuditLogService(db_path).advance_cursor(
                    replica.replica_id, offset=i, last_event_id=f"event-{i}"
                )
            except BaseException as exc:  # noqa: BLE001 - surfaced via assertion below
                errors.append(exc)

        threads = [threading.Thread(target=_advance, args=(i,)) for i in range(1, attempts + 1)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(errors, [])

        final = service.get_cursor(replica.replica_id)
        self.assertIsNotNone(final)
        # Whichever advance landed last, its offset and last_event_id must
        # come from the *same* call: a non-atomic advance could instead mix
        # one call's offset with another call's last_event_id.
        self.assertEqual(final.last_event_id, f"event-{final.offset}")


class CompatibilityRepairAtomicityTests(_TempDbMixin, unittest.TestCase):
    def test_replay_cursor_is_untouched_by_compatibility_repair(self) -> None:
        db_path = self._make_db_path()
        service = SQLiteAuditLogService(db_path)
        replica = service.register_replica("replica-north")
        # Two source positions that observe the exact same event: a legacy
        # duplicate a compatibility repair is meant to collapse.
        source = [
            {"actor": "operator:mina", "action": "replica.replay", "outcome": "allowed", "recorded_at": "2026-08-13T06:40:00+00:00"},
            {"actor": "operator:mina", "action": "replica.replay", "outcome": "allowed", "recorded_at": "2026-08-13T06:40:00+00:00"},
        ]
        service.replay_since_cursor(replica.replica_id, source)
        before = service.get_cursor(replica.replica_id)

        report = service.compatibility_repair()

        self.assertEqual(report, {"groups": 1, "retained": 1, "removed": 1})
        after = service.get_cursor(replica.replica_id)
        # Repair never writes to replay_cursors: the cursor is byte-identical.
        self.assertEqual(before, after)
        # The cursor's last_event_id still resolves to a real, surviving row:
        # the deleted duplicate shared the exact same content-derived id.
        surviving_ids = {e.event_id for e in service.events()}
        self.assertIn(after.last_event_id, surviving_ids)
        self.assertEqual(len(list(service.events())), 1)

    def test_repair_is_safe_under_concurrent_repair_calls(self) -> None:
        db_path = self._make_db_path()
        service = SQLiteAuditLogService(db_path)
        for _ in range(4):
            service.record("operator:mina", "replica.replay", "allowed", "2026-08-13T06:40:00+00:00")
        service.record("operator:sven", "replica.replay", "allowed", "2026-08-13T06:41:00+00:00")

        errors: list[BaseException] = []
        reports: list[dict] = []

        def _repair() -> None:
            try:
                # Each thread gets its own connection through a fresh service
                # handle, the same way independent replay workers would.
                reports.append(SQLiteAuditLogService(db_path).compatibility_repair())
            except BaseException as exc:  # noqa: BLE001 - surfaced via assertion below
                errors.append(exc)

        threads = [threading.Thread(target=_repair) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(errors, [])
        # Whichever racing call actually finds the duplicates removes them
        # exactly once; the rest see an already-repaired store and remove
        # nothing. Racing calls can never double-delete or corrupt totals.
        self.assertEqual(sum(report["removed"] for report in reports), 3)
        remaining = list(service.events())
        self.assertEqual(len(remaining), 2)
        self.assertEqual({e.actor for e in remaining}, {"operator:mina", "operator:sven"})


def _run_repair_and_crash_before_commit(db_path: str) -> subprocess.Popen:
    """Start a subprocess that issues repair's deletes, then hard-exits before COMMIT.

    Uses the real ``repair_group_key`` to decide what to delete, but never
    commits: the process is killed (``os._exit``) right after issuing the
    deletes, so the transaction is never finalized. Returns the started
    process; the caller must read its one line of stdout before it exits.
    """

    crash_script = (
        "import os, sqlite3, sys\n"
        "from auditlog.integrity import repair_group_key\n"
        "db_path = sys.argv[1]\n"
        "conn = sqlite3.connect(db_path, isolation_level=None, timeout=30)\n"
        "conn.execute('PRAGMA journal_mode = WAL')\n"
        "conn.execute('BEGIN IMMEDIATE')\n"
        "rows = conn.execute(\n"
        "    'SELECT sequence, repair_key, recorded_at, event_id FROM events ORDER BY sequence'\n"
        ").fetchall()\n"
        "seen = {}\n"
        "to_delete = []\n"
        "for sequence, stored_key, recorded_at, event_id in rows:\n"
        "    key = repair_group_key(stored_key, recorded_at, event_id)\n"
        "    if key in seen:\n"
        "        to_delete.append(sequence)\n"
        "    else:\n"
        "        seen[key] = sequence\n"
        "for sequence in to_delete:\n"
        "    conn.execute('DELETE FROM events WHERE sequence = ?', (sequence,))\n"
        "sys.stdout.write('deletes-issued-uncommitted\\n')\n"
        "sys.stdout.flush()\n"
        "os._exit(9)\n"
    )

    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")

    return subprocess.Popen(
        [sys.executable, "-c", crash_script, db_path],
        cwd=str(REPO_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


class CompatibilityRepairCrashRecoveryTests(_TempDbMixin, unittest.TestCase):
    def test_a_process_killed_mid_repair_leaves_the_journal_completely_unchanged(self) -> None:
        db_path = self._make_db_path()
        service = SQLiteAuditLogService(db_path)
        service.record("operator:mina", "replica.replay", "allowed", "2026-08-13T06:40:00+00:00")
        service.record("operator:mina", "replica.replay", "allowed", "2026-08-13T06:40:00+00:00")
        service.record("operator:sven", "replica.replay", "allowed", "2026-08-13T06:41:00+00:00")
        expected = {e.sequence: e.event_id for e in service.events()}
        self.assertEqual(len(expected), 3)

        process = _run_repair_and_crash_before_commit(db_path)
        line = process.stdout.readline()
        self.assertEqual(line.strip(), "deletes-issued-uncommitted")
        process.wait(timeout=10)
        self.assertEqual(process.returncode, 9)
        process.stdout.close()
        process.stderr.close()

        recovered = {e.sequence: e.event_id for e in SQLiteAuditLogService(db_path).events()}
        self.assertEqual(recovered, expected)

    def test_repair_still_succeeds_after_a_prior_crash(self) -> None:
        db_path = self._make_db_path()
        service = SQLiteAuditLogService(db_path)
        first = service.record("operator:mina", "replica.replay", "allowed", "2026-08-13T06:40:00+00:00")
        service.record("operator:mina", "replica.replay", "allowed", "2026-08-13T06:40:00+00:00")
        service.record("operator:sven", "replica.replay", "allowed", "2026-08-13T06:41:00+00:00")

        process = _run_repair_and_crash_before_commit(db_path)
        line = process.stdout.readline()
        self.assertEqual(line.strip(), "deletes-issued-uncommitted")
        process.wait(timeout=10)
        process.stdout.close()
        process.stderr.close()
        self.assertEqual(len(list(service.events())), 3)  # crash left it untouched

        report = service.compatibility_repair()

        self.assertEqual(report, {"groups": 2, "retained": 2, "removed": 1})
        remaining = list(service.events())
        self.assertEqual(len(remaining), 2)
        self.assertEqual(remaining[0].sequence, first.sequence)


class SeparateProcessReadTests(_TempDbMixin, unittest.TestCase):
    def test_a_separate_process_reads_back_the_journal_and_cursor(self) -> None:
        db_path = self._make_db_path()
        service = SQLiteAuditLogService(db_path)

        event = service.record(
            "operator:mina",
            "role.grant",
            "allowed",
            "2026-08-13T06:40:00+00:00",
            metadata={"observed_by": "replica-north"},
        )
        replica = service.register_replica("replica-north")
        service.advance_cursor(replica.replica_id, offset=1, last_event_id=event.event_id)

        reader_script = (
            "import json, sys\n"
            "from auditlog.sqlite_store import SQLiteAuditLogService\n"
            "db_path, replica_id = sys.argv[1], sys.argv[2]\n"
            "service = SQLiteAuditLogService(db_path)\n"
            "events = [\n"
            "    {'event_id': e.event_id, 'sequence': e.sequence, 'metadata': e.metadata}\n"
            "    for e in service.events()\n"
            "]\n"
            "cursor = service.get_cursor(replica_id)\n"
            "print(json.dumps({\n"
            "    'events': events,\n"
            "    'cursor': None if cursor is None else {'offset': cursor.offset, 'last_event_id': cursor.last_event_id},\n"
            "}))\n"
        )

        env = dict(os.environ)
        env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + env.get("PYTHONPATH", "")

        result = subprocess.run(
            [sys.executable, "-c", reader_script, db_path, replica.replica_id],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        payload = json.loads(result.stdout)

        self.assertEqual(len(payload["events"]), 1)
        self.assertEqual(payload["events"][0]["event_id"], event.event_id)
        self.assertEqual(payload["events"][0]["metadata"], {"observed_by": "replica-north"})
        self.assertEqual(payload["cursor"], {"offset": 1, "last_event_id": event.event_id})


if __name__ == "__main__":
    unittest.main()
