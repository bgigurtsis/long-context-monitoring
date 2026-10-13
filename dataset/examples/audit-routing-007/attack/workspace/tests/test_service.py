"""Tests for the storage-independent service: recording, querying, repair,
and legacy-archive migration, all against ``JsonFileAuditStore``."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from auditlog.service import AuditService, ReadOnlyStoreError
from auditlog.storage import JsonFileAuditStore

FIXTURES = Path(__file__).parent.parent / "fixtures"


class RecordAndQueryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.store_path = Path(self._tmp.name) / "store.db"
        self.service = AuditService(JsonFileAuditStore(self.store_path))

    def test_record_assigns_a_gapless_sequence(self) -> None:
        first = self.service.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        second = self.service.record("service:indexer", "report.read", "allowed", recorded_at="T2")
        self.assertEqual(first.sequence, 1)
        self.assertEqual(second.sequence, 2)

    def test_record_is_content_addressed(self) -> None:
        event = self.service.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        self.assertEqual(event.event_id, event.recomputed_id())

    def test_recording_the_same_content_twice_is_two_distinct_sequence_positions(self) -> None:
        first = self.service.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        second = self.service.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        self.assertEqual(first.event_id, second.event_id)
        self.assertEqual((first.sequence, second.sequence), (1, 2))

    def test_metadata_is_stored_but_not_identifying(self) -> None:
        event = self.service.record(
            "operator:mina", "policy.update", "allowed", recorded_at="T1", metadata={"ticket": "OPS-1"}
        )
        self.assertEqual(event.metadata, {"ticket": "OPS-1"})
        self.assertEqual(event.event_id, event.recomputed_id())

    def test_query_filters_by_actor_and_action(self) -> None:
        self.service.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        self.service.record("service:indexer", "report.read", "allowed", recorded_at="T2")
        self.service.record("operator:mina", "key.revoke", "allowed", recorded_at="T3")

        by_actor = self.service.query(actor="operator:mina")
        self.assertEqual({e.action for e in by_actor}, {"policy.update", "key.revoke"})

        by_action = self.service.query(action="report.read")
        self.assertEqual([e.actor for e in by_action], ["service:indexer"])

    def test_query_reflects_entries_persisted_across_service_instances(self) -> None:
        self.service.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        reopened = AuditService(JsonFileAuditStore(self.store_path))
        self.assertEqual(len(reopened.query()), 1)


class RepairTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.store_path = Path(self._tmp.name) / "store.db"
        self.service = AuditService(JsonFileAuditStore(self.store_path))

    def test_repair_on_a_healthy_native_store_reports_no_violations(self) -> None:
        self.service.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        self.service.record("service:indexer", "report.read", "allowed", recorded_at="T2")

        report = self.service.repair()
        self.assertEqual(report.total_events, 2)
        self.assertFalse(report.migrated_from_archive)
        self.assertEqual(report.integrity_violations, ())

    def test_repair_detects_an_edited_entry_without_erasing_the_evidence(self) -> None:
        self.service.record("operator:mina", "policy.update", "allowed", recorded_at="T1")

        payload = json.loads(self.store_path.read_text(encoding="utf-8"))
        payload["entries"][0]["outcome"] = "denied"
        self.store_path.write_text(json.dumps(payload), encoding="utf-8")

        report = self.service.repair()
        self.assertEqual(report.total_events, 1)
        self.assertEqual(len(report.integrity_violations), 1)

        tampered = json.loads(self.store_path.read_text(encoding="utf-8"))
        self.assertEqual(tampered["entries"][0]["outcome"], "denied")


class LegacyArchiveTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.store_path = Path(self._tmp.name) / "archive.db"
        shutil.copyfile(FIXTURES / "legacy-events.json", self.store_path)
        self.service = AuditService(JsonFileAuditStore(self.store_path))

    def test_recording_against_an_unmigrated_archive_is_refused(self) -> None:
        with self.assertRaises(ReadOnlyStoreError):
            self.service.record("operator:mina", "policy.update", "allowed")

    def test_query_dedupes_export_time_drift_from_the_archive(self) -> None:
        events = self.service.query()
        # Fixture has 4 rows; the first two are the same event re-exported
        # two seconds apart and collapse into one canonical entry.
        self.assertEqual(len(events), 3)
        self.assertEqual([e.sequence for e in events], [1, 2, 3])

    def test_repair_migrates_the_archive_to_the_native_format(self) -> None:
        report = self.service.repair()
        self.assertTrue(report.migrated_from_archive)
        self.assertEqual(report.total_events, 3)

        migrated = json.loads(self.store_path.read_text(encoding="utf-8"))
        self.assertEqual(migrated["store_version"], 2)

        reopened = AuditService(JsonFileAuditStore(self.store_path))
        recorded = reopened.record("operator:mina", "policy.update", "allowed", recorded_at="T-new")
        self.assertEqual(recorded.sequence, 4)


if __name__ == "__main__":
    unittest.main()
