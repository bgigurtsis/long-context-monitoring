"""Tests for the storage-independent AuditService."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from auditlog.models import AuditEvent, content_digest
from auditlog.service import ArchiveFormatError, AuditService, SequenceError
from auditlog.store import InMemoryLogStore, JsonFileLogStore

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _event(sequence: int, actor: str, action: str = "policy.update", outcome: str = "allowed", at: str = "T1") -> AuditEvent:
    return AuditEvent(content_digest(actor, action, outcome, at), sequence, actor, action, outcome, at)


class RecordTests(unittest.TestCase):
    def test_first_record_gets_sequence_one(self) -> None:
        service = AuditService(InMemoryLogStore())
        event = service.record("operator:mina", "policy.update", "allowed", "T1")
        self.assertEqual(event.sequence, 1)

    def test_event_id_is_derived_from_recorded_content(self) -> None:
        service = AuditService(InMemoryLogStore())
        event = service.record("operator:mina", "policy.update", "allowed", "T1")
        self.assertEqual(event.event_id, content_digest("operator:mina", "policy.update", "allowed", "T1"))

    def test_sequence_is_gapless_across_appends(self) -> None:
        store = InMemoryLogStore()
        service = AuditService(store)
        service.record("operator:mina", "policy.update", "allowed", "T1")
        second = service.record("service:indexer", "report.read", "allowed", "T2")
        self.assertEqual(second.sequence, 2)

    def test_recording_onto_a_broken_sequence_raises(self) -> None:
        store = InMemoryLogStore(events=(_event(1, "a"), _event(3, "b")))
        service = AuditService(store)
        with self.assertRaises(SequenceError):
            service.record("c", "action", "allowed", "T3")

    def test_recording_onto_an_unmigrated_archive_store_raises(self) -> None:
        store = InMemoryLogStore(events=(_event(1, "a"),), source_version=1)
        service = AuditService(store)
        with self.assertRaises(ArchiveFormatError):
            service.record("c", "action", "allowed", "T3")

    def test_metadata_is_not_an_input_to_identity(self) -> None:
        service = AuditService(InMemoryLogStore())
        event = service.record("operator:mina", "policy.update", "allowed", "T1", metadata={"note": "x"})
        self.assertEqual(event.event_id, content_digest("operator:mina", "policy.update", "allowed", "T1"))


class QueryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = InMemoryLogStore(
            events=(
                _event(1, "operator:mina", "policy.update"),
                _event(2, "service:indexer", "report.read"),
                _event(3, "operator:mina", "key.revoke"),
            )
        )
        self.service = AuditService(self.store)

    def test_query_filters_by_actor(self) -> None:
        results = self.service.query(actor="operator:mina")
        self.assertEqual({event.action for event in results}, {"policy.update", "key.revoke"})

    def test_query_filters_by_action(self) -> None:
        results = self.service.query(action="report.read")
        self.assertEqual([event.actor for event in results], ["service:indexer"])

    def test_query_is_returned_in_sequence_order(self) -> None:
        results = self.service.query()
        self.assertEqual([event.sequence for event in results], [1, 2, 3])


class RepairTests(unittest.TestCase):
    def test_repair_verifies_a_clean_store_without_rewriting_events(self) -> None:
        store = InMemoryLogStore(events=(_event(1, "operator:mina"), _event(2, "service:indexer")))
        report = AuditService(store).repair()
        self.assertEqual(report.verified, 2)
        self.assertEqual(report.tampered, ())
        self.assertFalse(report.migrated)

    def test_repair_reports_tampered_entries_without_correcting_them(self) -> None:
        tampered = AuditEvent(content_digest("a", "act", "allowed", "T1"), 1, "a", "act", "denied", "T1")
        store = InMemoryLogStore(events=(tampered,))
        report = AuditService(store).repair()
        self.assertEqual(report.tampered, (tampered.event_id,))
        self.assertEqual(store.read_state().events, (tampered,))

    def test_repair_rebuilds_the_index(self) -> None:
        store = InMemoryLogStore(events=(_event(1, "operator:mina"),))
        self.assertIsNone(store.read_index())
        AuditService(store).repair()
        index = store.read_index()
        self.assertEqual(index["entry_count"], 1)
        self.assertIn("operator:mina", index["by_actor"])

    def test_repair_migrates_an_archive_format_store(self) -> None:
        events = (_event(1, "operator:mina"),)
        store = InMemoryLogStore(events=events, source_version=1)
        report = AuditService(store).repair()
        self.assertTrue(report.migrated)
        self.assertEqual(store.read_state().source_version, 2)

    def test_broken_sequence_is_rejected_before_verification(self) -> None:
        store = InMemoryLogStore(events=(_event(1, "a"), _event(1, "b")))
        with self.assertRaises(SequenceError):
            AuditService(store).repair()


class JsonFileLogStoreEndToEndTests(unittest.TestCase):
    """Same service, a different LogStore -- proving there's no file-format coupling."""

    def setUp(self) -> None:
        self.tempdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tempdir, ignore_errors=True)

    def test_record_then_query_round_trips_through_a_real_file(self) -> None:
        path = Path(self.tempdir) / "store.db"
        service = AuditService(JsonFileLogStore(path))
        service.record("operator:mina", "policy.update", "allowed", "2024-03-02T09:04:00Z")
        service.record("service:indexer", "report.read", "allowed", "2024-03-02T09:11:00Z")

        reloaded = AuditService(JsonFileLogStore(path))
        results = reloaded.query(actor="operator:mina")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].sequence, 1)

    def test_repair_migrates_an_on_disk_archive_file_to_current_format(self) -> None:
        path = Path(self.tempdir) / "store.db"
        shutil.copy(FIXTURES / "legacy-events.json", path)

        report = AuditService(JsonFileLogStore(path)).repair()
        self.assertTrue(report.migrated)
        self.assertEqual(report.verified, 3)

        on_disk = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(on_disk["store_version"], 2)
        self.assertEqual(len(on_disk["entries"]), 3)

    def test_current_format_fixture_verifies_clean(self) -> None:
        path = Path(self.tempdir) / "store.db"
        shutil.copy(FIXTURES / "current-events.json", path)

        report = AuditService(JsonFileLogStore(path)).repair()
        self.assertEqual(report.tampered, ())
        self.assertFalse(report.migrated)


if __name__ == "__main__":
    unittest.main()
