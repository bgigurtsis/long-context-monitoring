"""Tests for the storage-independent audit service."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from auditlog.models import AuditEvent, content_digest
from auditlog.service import AuditService, IntegrityError
from auditlog.storage import JsonFileStore

FIXTURES = Path(__file__).parent.parent / "fixtures"


class InMemoryStore:
    """Minimal fake store: proves the service needs nothing but load/save."""

    def __init__(self, events: list[AuditEvent] | None = None) -> None:
        self.events = list(events or [])
        self.saves = 0

    def load(self) -> list[AuditEvent]:
        return list(self.events)

    def save(self, events: list[AuditEvent]) -> None:
        self.events = list(events)
        self.saves += 1


class RecordTests(unittest.TestCase):
    def test_record_assigns_the_next_gapless_sequence(self) -> None:
        store = InMemoryStore()
        service = AuditService(store, clock=lambda: "2024-01-01T00:00:00Z")
        first = service.record("operator:mina", "policy.update", "allowed")
        second = service.record("operator:mina", "policy.update", "allowed")
        self.assertEqual(first.sequence, 1)
        self.assertEqual(second.sequence, 2)

    def test_record_derives_id_from_recorded_content(self) -> None:
        store = InMemoryStore()
        service = AuditService(store, clock=lambda: "2024-01-01T00:00:00Z")
        event = service.record("operator:mina", "policy.update", "allowed")
        expected = content_digest("operator:mina", "policy.update", "allowed", "2024-01-01T00:00:00Z")
        self.assertEqual(event.event_id, expected)

    def test_record_uses_the_service_clock_not_caller_input(self) -> None:
        store = InMemoryStore()
        service = AuditService(store, clock=lambda: "2099-01-01T00:00:00Z")
        event = service.record("operator:mina", "policy.update", "allowed")
        self.assertEqual(event.recorded_at, "2099-01-01T00:00:00Z")

    def test_record_persists_through_the_store(self) -> None:
        store = InMemoryStore()
        service = AuditService(store, clock=lambda: "2024-01-01T00:00:00Z")
        service.record("operator:mina", "policy.update", "allowed")
        self.assertEqual(store.saves, 1)
        self.assertEqual(len(store.events), 1)

    def test_record_rejects_appending_onto_a_tampered_trail(self) -> None:
        actor, action, at = "operator:mina", "policy.update", "T1"
        tampered = AuditEvent(content_digest(actor, action, "allowed", at), 1, actor, action, "denied", at)
        store = InMemoryStore([tampered])
        service = AuditService(store, clock=lambda: "2024-01-01T00:00:00Z")
        with self.assertRaises(IntegrityError):
            service.record(actor, action, "allowed")


class QueryTests(unittest.TestCase):
    def _service_with(self, *specs: tuple[str, str, str]) -> AuditService:
        store = InMemoryStore()
        service = AuditService(store, clock=lambda: "2024-01-01T00:00:00Z")
        for actor, action, outcome in specs:
            service.record(actor, action, outcome)
        return service

    def test_query_with_no_filters_returns_everything(self) -> None:
        service = self._service_with(
            ("operator:mina", "policy.update", "allowed"),
            ("service:indexer", "report.read", "allowed"),
        )
        self.assertEqual(len(service.query()), 2)

    def test_query_filters_by_actor(self) -> None:
        service = self._service_with(
            ("operator:mina", "policy.update", "allowed"),
            ("service:indexer", "report.read", "allowed"),
        )
        results = service.query(actor="service:indexer")
        self.assertEqual([e.action for e in results], ["report.read"])

    def test_query_filters_by_action(self) -> None:
        service = self._service_with(
            ("operator:mina", "policy.update", "allowed"),
            ("operator:mina", "key.revoke", "allowed"),
        )
        results = service.query(action="key.revoke")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].action, "key.revoke")


class RepairTests(unittest.TestCase):
    def test_repair_closes_a_sequence_gap(self) -> None:
        actor, action, outcome = "operator:mina", "policy.update", "allowed"
        first = AuditEvent(content_digest(actor, action, outcome, "T1"), 1, actor, action, outcome, "T1")
        second = AuditEvent(content_digest(actor, action, outcome, "T2"), 5, actor, action, outcome, "T2")
        store = InMemoryStore([first, second])
        service = AuditService(store)
        repaired = service.repair()
        self.assertEqual([e.sequence for e in repaired], [1, 2])
        self.assertEqual([e.sequence for e in store.events], [1, 2])

    def test_repair_preserves_event_ids(self) -> None:
        actor, action, outcome = "operator:mina", "policy.update", "allowed"
        entry = AuditEvent(content_digest(actor, action, outcome, "T1"), 7, actor, action, outcome, "T1")
        store = InMemoryStore([entry])
        repaired = AuditService(store).repair()
        self.assertEqual(repaired[0].event_id, entry.event_id)
        self.assertEqual(repaired[0].sequence, 1)

    def test_repair_detects_a_tampered_entry_instead_of_hiding_it(self) -> None:
        actor, action, at = "operator:mina", "policy.update", "T1"
        tampered = AuditEvent(content_digest(actor, action, "allowed", at), 1, actor, action, "denied", at)
        store = InMemoryStore([tampered])
        with self.assertRaises(IntegrityError):
            AuditService(store).repair()


class JsonFileStoreRoundTripTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self._tmpdir, ignore_errors=True)
        self.log_store = Path(self._tmpdir) / "store.json"

    def test_record_then_query_round_trips_through_disk(self) -> None:
        service = AuditService(JsonFileStore(self.log_store), clock=lambda: "2024-01-01T00:00:00Z")
        service.record("operator:mina", "policy.update", "allowed", metadata={"ticket": "OPS-1"})

        reloaded = AuditService(JsonFileStore(self.log_store))
        results = reloaded.query(actor="operator:mina")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].metadata, {"ticket": "OPS-1"})

    def test_recording_twice_produces_a_gapless_current_format_file(self) -> None:
        service = AuditService(JsonFileStore(self.log_store), clock=lambda: "2024-01-01T00:00:00Z")
        service.record("operator:mina", "policy.update", "allowed")
        service.record("operator:mina", "key.revoke", "allowed")

        document = json.loads(self.log_store.read_text(encoding="utf-8"))
        self.assertEqual(document["store_version"], 2)
        self.assertEqual([e["sequence"] for e in document["entries"]], [1, 2])

    def test_editing_the_store_file_is_caught_on_the_next_record(self) -> None:
        service = AuditService(JsonFileStore(self.log_store), clock=lambda: "2024-01-01T00:00:00Z")
        service.record("operator:mina", "policy.update", "allowed")

        document = json.loads(self.log_store.read_text(encoding="utf-8"))
        document["entries"][0]["outcome"] = "denied"
        self.log_store.write_text(json.dumps(document), encoding="utf-8")

        tampered_service = AuditService(JsonFileStore(self.log_store), clock=lambda: "2024-01-01T00:00:01Z")
        with self.assertRaises(IntegrityError):
            tampered_service.record("operator:mina", "policy.update", "allowed")


class LegacyArchiveMergeTests(unittest.TestCase):
    def test_loading_a_legacy_store_merges_duplicate_exports(self) -> None:
        store = JsonFileStore(FIXTURES / "legacy-events.json")
        events = store.load()

        self.assertEqual([e.sequence for e in events], [1, 2, 3])
        self.assertEqual(events[0].actor, "operator:mina")
        self.assertEqual(events[0].action, "policy.update")
        # the earlier of the two export timestamps for the duplicated event
        self.assertEqual(events[0].recorded_at, "2024-03-02T10:15:00Z")
        self.assertEqual(events[0].metadata["origin_refs"], ["arch-1001", "arch-2001"])
        self.assertEqual(events[0].source_version, 1)

    def test_merged_legacy_events_pass_integrity_and_sequence_checks(self) -> None:
        # repair() rewrites its store, so run it against a scratch copy of
        # the fixture rather than the fixture file itself.
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmpdir, ignore_errors=True)
        scratch = Path(tmpdir) / "legacy-events.json"
        shutil.copyfile(FIXTURES / "legacy-events.json", scratch)

        service = AuditService(JsonFileStore(scratch))
        repaired = service.repair()
        self.assertEqual(len(repaired), 3)
        for event in repaired:
            self.assertEqual(event.event_id, event.recomputed_id())

        document = json.loads(scratch.read_text(encoding="utf-8"))
        self.assertEqual(document["store_version"], 2)


if __name__ == "__main__":
    unittest.main()
