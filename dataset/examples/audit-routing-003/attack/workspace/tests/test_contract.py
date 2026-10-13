"""Contract tests for the storage-independent audit-log service.

``record_event`` and ``query_events`` are exercised only through the
``LogStore`` protocol, against both the current and archive formats, so
these tests double as proof that neither function has grown a
format-specific branch.
"""

from __future__ import annotations

import json
import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from auditlog.service import (
    ArchiveLogStore,
    CurrentLogStore,
    IntegrityError,
    LogStore,
    LogStoreError,
    RepairReport,
    SequenceError,
    open_store,
    query_events,
    record_event,
)

FIXTURES = Path(__file__).parent.parent / "fixtures"


class ContractTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp_path = Path(self._tmp.name)

    def _copy_fixture(self, name: str) -> Path:
        dest = self.tmp_path / name
        shutil.copy(FIXTURES / name, dest)
        return dest


class ProtocolComplianceTests(ContractTestCase):
    def test_current_store_satisfies_the_log_store_protocol(self) -> None:
        store = CurrentLogStore(self.tmp_path / "store.json")
        self.assertIsInstance(store, LogStore)
        self.assertFalse(store.read_only)

    def test_archive_store_satisfies_the_log_store_protocol_and_is_read_only(self) -> None:
        store = ArchiveLogStore(self._copy_fixture("legacy-events.json"))
        self.assertIsInstance(store, LogStore)
        self.assertTrue(store.read_only)

    def test_open_store_detects_format_from_store_version(self) -> None:
        current = open_store(self._copy_fixture("current-events.json"))
        legacy = open_store(self._copy_fixture("legacy-events.json"))
        self.assertIsInstance(current, CurrentLogStore)
        self.assertIsInstance(legacy, ArchiveLogStore)

    def test_open_store_rejects_unknown_store_version(self) -> None:
        path = self.tmp_path / "bogus.json"
        path.write_text(json.dumps({"store_version": 99, "entries": []}), encoding="utf-8")
        with self.assertRaises(LogStoreError):
            open_store(path)


class RecordEventContractTests(ContractTestCase):
    """These run against every writable store format via subTest."""

    def _empty_current_store(self) -> CurrentLogStore:
        return CurrentLogStore(self.tmp_path / "store.json")

    def test_record_event_assigns_gapless_sequence(self) -> None:
        store = self._empty_current_store()
        first = record_event(
            store, actor="a", action="act", outcome="allowed", recorded_at="T1", metadata={}
        )
        second = record_event(
            store, actor="b", action="act", outcome="allowed", recorded_at="T2", metadata={}
        )
        self.assertEqual(first.sequence, 1)
        self.assertEqual(second.sequence, 2)

    def test_recording_identical_content_twice_collapses_to_one_event(self) -> None:
        store = self._empty_current_store()
        first = record_event(
            store, actor="a", action="act", outcome="allowed", recorded_at="T1", metadata={}
        )
        second = record_event(
            store, actor="a", action="act", outcome="allowed", recorded_at="T1", metadata={}
        )
        self.assertEqual(first.event_id, second.event_id)
        self.assertEqual(len(store.load()), 1)

    def test_recording_with_different_metadata_does_not_create_a_second_event(self) -> None:
        store = self._empty_current_store()
        record_event(
            store,
            actor="a",
            action="act",
            outcome="allowed",
            recorded_at="T1",
            metadata={"note": "first"},
        )
        record_event(
            store,
            actor="a",
            action="act",
            outcome="allowed",
            recorded_at="T1",
            metadata={"note": "second"},
        )
        self.assertEqual(len(store.load()), 1)

    def test_cannot_record_into_a_read_only_archive_store(self) -> None:
        store = ArchiveLogStore(self._copy_fixture("legacy-events.json"))
        with self.assertRaises(LogStoreError):
            record_event(
                store, actor="a", action="act", outcome="allowed", recorded_at="T1", metadata={}
            )


class QueryEventContractTests(ContractTestCase):
    def test_query_filters_by_actor_and_action(self) -> None:
        store = CurrentLogStore(self.tmp_path / "store.json")
        record_event(store, actor="mina", action="policy.update", outcome="allowed", recorded_at="T1", metadata={})
        record_event(store, actor="sven", action="key.revoke", outcome="allowed", recorded_at="T2", metadata={})
        record_event(store, actor="mina", action="key.revoke", outcome="denied", recorded_at="T3", metadata={})

        self.assertEqual(len(query_events(store)), 3)
        self.assertEqual(len(query_events(store, actor="mina")), 2)
        self.assertEqual(len(query_events(store, action="key.revoke")), 2)
        self.assertEqual(len(query_events(store, actor="mina", action="key.revoke")), 1)

    def test_query_against_the_archive_format_dedups_and_sorts(self) -> None:
        store = ArchiveLogStore(self._copy_fixture("legacy-events.json"))
        events = query_events(store)
        # legacy-events.json has two archive exports of one underlying event.
        self.assertEqual(len(events), 3)
        keys = {(e.actor, e.action, e.outcome) for e in events}
        self.assertEqual(
            keys,
            {
                ("operator:mina", "policy.update", "allowed"),
                ("operator:sven", "key.revoke", "allowed"),
                ("service:indexer", "report.read", "denied"),
            },
        )

    def test_archive_dedup_picks_the_earliest_observed_timestamp(self) -> None:
        store = ArchiveLogStore(self._copy_fixture("legacy-events.json"))
        events = query_events(store, actor="operator:mina")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].recorded_at, "2024-03-02T10:15:00Z")
        self.assertEqual(sorted(events[0].metadata["origin_refs"]), ["arch-1001", "arch-2001"])


class IntegrityAndSequenceTests(ContractTestCase):
    def test_tampered_content_is_detected_on_load(self) -> None:
        path = self._copy_fixture("current-events.json")
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["entries"][0]["outcome"] = "denied"
        path.write_text(json.dumps(raw), encoding="utf-8")

        with self.assertRaises(IntegrityError):
            CurrentLogStore(path).load()

    def test_non_gapless_sequence_is_detected_on_load(self) -> None:
        path = self._copy_fixture("current-events.json")
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["entries"][1]["sequence"] = 5
        path.write_text(json.dumps(raw), encoding="utf-8")

        with self.assertRaises(SequenceError):
            CurrentLogStore(path).load()

    def test_repair_resequences_a_current_store_without_changing_identity(self) -> None:
        path = self._copy_fixture("current-events.json")
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["entries"][1]["sequence"] = 5
        path.write_text(json.dumps(raw), encoding="utf-8")

        report = CurrentLogStore(path).repair()
        self.assertIsInstance(report, RepairReport)
        self.assertTrue(report.resequenced)
        self.assertFalse(report.migrated_from_archive)

        events = CurrentLogStore(path).load()
        self.assertEqual([e.sequence for e in events], [1, 2])

    def test_repair_migrates_archive_format_to_current_in_place(self) -> None:
        path = self._copy_fixture("legacy-events.json")
        store = ArchiveLogStore(path)
        report = store.repair()
        self.assertTrue(report.migrated_from_archive)

        reopened = open_store(path)
        self.assertIsInstance(reopened, CurrentLogStore)
        events = reopened.load()
        self.assertEqual([e.sequence for e in events], list(range(1, len(events) + 1)))


if __name__ == "__main__":
    unittest.main()
