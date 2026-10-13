"""Tests for the storage-independent AuditLogService."""

from __future__ import annotations

import unittest

from auditlog.models import content_digest
from auditlog.service import AuditLogService, IntegrityError, SequenceError


class InMemoryStore:
    """A minimal EventStore with no relation to JSON files or disk at all.

    Exercising the service against this instead of JsonFileEventStore is
    the check that the service is genuinely storage-independent.
    """

    def __init__(self, entries=None) -> None:
        self.entries = list(entries or [])

    def read_all(self):
        return list(self.entries)

    def append(self, entry):
        self.entries.append(entry)


class RecordTests(unittest.TestCase):
    def test_record_assigns_a_gapless_sequence(self) -> None:
        service = AuditLogService(InMemoryStore())
        first = service.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        second = service.record("operator:mina", "policy.update", "denied", recorded_at="T2")
        self.assertEqual((first.sequence, second.sequence), (1, 2))

    def test_recorded_event_id_matches_its_own_content(self) -> None:
        service = AuditLogService(InMemoryStore())
        event = service.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        self.assertEqual(event.event_id, event.recomputed_id())

    def test_metadata_does_not_affect_the_event_id(self) -> None:
        service = AuditLogService(InMemoryStore())
        without = service.record("a", "b", "c", recorded_at="T1")
        service2 = AuditLogService(InMemoryStore())
        with_metadata = service2.record("a", "b", "c", metadata={"note": "x"}, recorded_at="T1")
        self.assertEqual(without.event_id, with_metadata.event_id)


class QueryTests(unittest.TestCase):
    def test_query_filters_by_actor_and_action(self) -> None:
        service = AuditLogService(InMemoryStore())
        service.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        service.record("service:indexer", "report.read", "allowed", recorded_at="T2")
        service.record("operator:mina", "key.revoke", "allowed", recorded_at="T3")

        by_actor = service.query(actor="operator:mina")
        self.assertEqual({e.action for e in by_actor}, {"policy.update", "key.revoke"})

        by_action = service.query(action="report.read")
        self.assertEqual([e.actor for e in by_action], ["service:indexer"])

    def test_query_results_are_sequence_ordered(self) -> None:
        service = AuditLogService(InMemoryStore())
        service.record("a", "x", "allowed", recorded_at="T1")
        service.record("a", "y", "allowed", recorded_at="T2")
        sequences = [e.sequence for e in service.query(actor="a")]
        self.assertEqual(sequences, sorted(sequences))


class VerifyTests(unittest.TestCase):
    def test_verify_passes_an_intact_trail(self) -> None:
        service = AuditLogService(InMemoryStore())
        service.record("a", "x", "allowed", recorded_at="T1")
        service.record("a", "y", "allowed", recorded_at="T2")
        self.assertEqual(len(service.verify()), 2)

    def test_verify_detects_a_sequence_gap(self) -> None:
        store = InMemoryStore(
            [
                {"event_id": content_digest("a", "x", "allowed", "T1"), "sequence": 1,
                 "actor": "a", "action": "x", "outcome": "allowed", "recorded_at": "T1",
                 "source_version": 2, "metadata": {}},
                {"event_id": content_digest("a", "y", "allowed", "T2"), "sequence": 3,
                 "actor": "a", "action": "y", "outcome": "allowed", "recorded_at": "T2",
                 "source_version": 2, "metadata": {}},
            ]
        )
        service = AuditLogService(store)
        with self.assertRaises(SequenceError):
            service.verify()

    def test_verify_detects_a_tampered_entry(self) -> None:
        service = AuditLogService(InMemoryStore())
        service.record("a", "x", "allowed", recorded_at="T1")
        # Simulate an edit made directly to storage rather than through record().
        service.store.entries[0]["outcome"] = "denied"
        with self.assertRaises(IntegrityError):
            service.verify()


if __name__ == "__main__":
    unittest.main()
