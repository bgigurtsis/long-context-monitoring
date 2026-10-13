"""SQLite log-store tests: the same contract, plus real durability.

``SqliteLogStore`` is exercised first through the same storage-independent
contract as the JSON stores (protocol compliance, gapless sequence,
idempotent record, tamper detection, repair), then through two genuinely
separate OS processes to prove a record is durably visible to a query that
never shared memory with the process that wrote it.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from auditlog.service import (
    IntegrityError,
    LogStore,
    RepairReport,
    SqliteLogStore,
    open_store,
    query_events,
    record_event,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


class SqliteStoreTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.store_path = Path(self._tmp.name) / "store.db"


class SqliteStoreContractTests(SqliteStoreTestCase):
    def test_open_store_defaults_a_new_path_to_sqlite(self) -> None:
        store = open_store(self.store_path)
        self.assertIsInstance(store, SqliteLogStore)
        self.assertIsInstance(store, LogStore)
        self.assertFalse(store.read_only)

    def test_open_store_recognizes_an_existing_sqlite_file_by_content(self) -> None:
        SqliteLogStore(self.store_path).load()  # creates the file with the schema
        self.assertIsInstance(open_store(self.store_path), SqliteLogStore)

    def test_record_and_query_round_trip(self) -> None:
        store = SqliteLogStore(self.store_path)
        record_event(
            store, actor="mina", action="policy.update", outcome="allowed", recorded_at="T1", metadata={}
        )
        record_event(
            store, actor="sven", action="key.revoke", outcome="allowed", recorded_at="T2", metadata={}
        )
        self.assertEqual(len(query_events(store)), 2)
        self.assertEqual(len(query_events(store, actor="mina")), 1)

    def test_recording_identical_content_twice_collapses_to_one_event(self) -> None:
        store = SqliteLogStore(self.store_path)
        first = record_event(
            store, actor="a", action="act", outcome="allowed", recorded_at="T1", metadata={}
        )
        second = record_event(
            store, actor="a", action="act", outcome="allowed", recorded_at="T1", metadata={}
        )
        self.assertEqual(first.event_id, second.event_id)
        self.assertEqual(len(store.load()), 1)

    def test_tampered_content_is_detected_on_load(self) -> None:
        store = SqliteLogStore(self.store_path)
        record_event(store, actor="a", action="act", outcome="allowed", recorded_at="T1", metadata={})

        connection = sqlite3.connect(self.store_path)
        with connection:
            connection.execute("UPDATE entries SET outcome = 'denied' WHERE sequence = 1")
        connection.close()

        with self.assertRaises(IntegrityError):
            store.load()

    def test_repair_resequences_without_changing_identity(self) -> None:
        store = SqliteLogStore(self.store_path)
        first = record_event(
            store, actor="a", action="act", outcome="allowed", recorded_at="T1", metadata={}
        )
        second = record_event(
            store, actor="b", action="act", outcome="allowed", recorded_at="T2", metadata={}
        )

        connection = sqlite3.connect(self.store_path)
        with connection:
            connection.execute("UPDATE entries SET sequence = 5 WHERE sequence = 2")
        connection.close()

        report = store.repair()
        self.assertIsInstance(report, RepairReport)
        self.assertTrue(report.resequenced)
        self.assertFalse(report.migrated_from_archive)

        events = store.load()
        self.assertEqual([e.sequence for e in events], [1, 2])
        self.assertEqual({e.event_id for e in events}, {first.event_id, second.event_id})


class SeparateProcessDurabilityTests(SqliteStoreTestCase):
    """`record` and `query` each run as their own OS process, sharing only the file."""

    def _run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "auditlog.cli", *args],
            capture_output=True,
            text=True,
            check=True,
            cwd=str(REPO_ROOT),
        )

    def test_a_record_from_one_process_is_durably_visible_to_a_query_from_another(self) -> None:
        self._run_cli(
            "record",
            "operator:mina",
            "policy.update",
            "allowed",
            "--log-store",
            str(self.store_path),
        )
        result = self._run_cli("query", "--actor", "operator:mina", "--log-store", str(self.store_path))

        lines = [line for line in result.stdout.splitlines() if line.strip()]
        self.assertEqual(len(lines), 1)
        recorded = json.loads(lines[0])
        self.assertEqual(recorded["actor"], "operator:mina")
        self.assertEqual(recorded["action"], "policy.update")
        self.assertEqual(recorded["sequence"], 1)

    def test_two_separate_record_processes_both_land_in_the_same_durable_store(self) -> None:
        self._run_cli(
            "record", "operator:mina", "policy.update", "allowed", "--log-store", str(self.store_path)
        )
        self._run_cli(
            "record", "operator:sven", "key.revoke", "allowed", "--log-store", str(self.store_path)
        )
        result = self._run_cli("query", "--log-store", str(self.store_path))

        lines = [line for line in result.stdout.splitlines() if line.strip()]
        self.assertEqual(len(lines), 2)
        self.assertEqual([json.loads(line)["sequence"] for line in lines], [1, 2])


if __name__ == "__main__":
    unittest.main()
