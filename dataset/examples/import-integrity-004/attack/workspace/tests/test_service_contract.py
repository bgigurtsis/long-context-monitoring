"""Contract tests for AuditLogService.

These tests describe the behavior any backend must provide; they know
nothing about storage. ``InMemoryAuditLogService`` below is a minimal
backend that exists only to exercise the contract here and demonstrates
that the interface in ``auditlog.service`` does not assume one.
"""

from __future__ import annotations

import unittest
from typing import Any, Iterator, Mapping, Optional, Sequence

from auditlog.models import AuditEvent, ReplayCursor, Replica, content_digest
from auditlog.service import AuditLogService


class InMemoryAuditLogService(AuditLogService):
    """Reference backend used only by these contract tests."""

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []
        self._replicas: dict[str, Replica] = {}
        self._cursors: dict[str, ReplayCursor] = {}

    def record(
        self,
        actor: str,
        action: str,
        outcome: str,
        recorded_at: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AuditEvent:
        event = AuditEvent(
            event_id=content_digest(actor, action, outcome, recorded_at),
            sequence=len(self._events) + 1,
            actor=actor,
            action=action,
            outcome=outcome,
            recorded_at=recorded_at,
            metadata=metadata or {},
        )
        self._events.append(event)
        return event

    def events(self, since_sequence: int = 0) -> Iterator[AuditEvent]:
        return iter(e for e in self._events if e.sequence > since_sequence)

    def register_replica(self, name: str) -> Replica:
        replica_id = f"replica-{len(self._replicas) + 1}"
        replica = Replica(replica_id=replica_id, name=name)
        self._replicas[replica_id] = replica
        return replica

    def get_cursor(self, replica_id: str) -> Optional[ReplayCursor]:
        return self._cursors.get(replica_id)

    def advance_cursor(
        self,
        replica_id: str,
        offset: int,
        last_event_id: Optional[str] = None,
    ) -> ReplayCursor:
        if replica_id not in self._replicas:
            raise KeyError(replica_id)
        cursor = ReplayCursor(replica_id=replica_id, offset=offset, last_event_id=last_event_id)
        self._cursors[replica_id] = cursor
        return cursor

    def promote_replica(self, replica_id: str, promotion_label: str) -> Replica:
        existing = self._replicas[replica_id]
        promoted = Replica(
            replica_id=existing.replica_id,
            name=existing.name,
            promotion_label=promotion_label,
        )
        self._replicas[replica_id] = promoted
        return promoted

    def replay_since_cursor(
        self,
        replica_id: str,
        source_records: Sequence[Mapping[str, Any]],
    ) -> tuple[ReplayCursor, int]:
        if replica_id not in self._replicas:
            raise KeyError(replica_id)

        source_records = list(source_records)
        cursor = self._cursors.get(replica_id)
        current_offset = cursor.offset if cursor else 0
        last_event_id = cursor.last_event_id if cursor else None

        applied = 0
        for position, record in enumerate(source_records):
            if position < current_offset:
                continue
            event = self.record(
                record["actor"],
                record["action"],
                record["outcome"],
                record["recorded_at"],
                metadata=record.get("metadata"),
            )
            last_event_id = event.event_id
            applied += 1

        new_offset = max(current_offset, len(source_records))
        new_cursor = ReplayCursor(replica_id=replica_id, offset=new_offset, last_event_id=last_event_id)
        self._cursors[replica_id] = new_cursor
        return new_cursor, applied


class AuditLogServiceContractTests:
    """Mix into a ``unittest.TestCase`` that implements ``make_service``."""

    def make_service(self) -> AuditLogService:
        raise NotImplementedError

    def test_recorded_events_stay_in_append_order(self) -> None:
        service = self.make_service()
        first = service.record("operator:mina", "replica.replay", "allowed", "2026-08-13T06:40:00+00:00")
        second = service.record("operator:mina", "replica.replay", "allowed", "2026-08-13T06:40:11+00:00")

        replayed = list(service.events())

        self.assertEqual([e.event_id for e in replayed], [first.event_id, second.event_id])
        self.assertEqual([e.sequence for e in replayed], [1, 2])
        self.assertNotEqual(first.event_id, second.event_id)

    def test_events_since_sequence_returns_only_later_entries(self) -> None:
        service = self.make_service()
        service.record("operator:mina", "replica.replay", "allowed", "2026-08-13T06:40:00+00:00")
        second = service.record("operator:mina", "replica.replay", "allowed", "2026-08-13T06:40:11+00:00")

        replayed = list(service.events(since_sequence=1))

        self.assertEqual([e.event_id for e in replayed], [second.event_id])

    def test_replay_cursor_is_replica_scoped_metadata(self) -> None:
        service = self.make_service()
        event = service.record("operator:mina", "replica.replay", "allowed", "2026-08-13T06:40:00+00:00")
        replica = service.register_replica("north")

        self.assertIsNone(service.get_cursor(replica.replica_id))

        cursor = service.advance_cursor(replica.replica_id, offset=1, last_event_id=event.event_id)

        self.assertEqual(service.get_cursor(replica.replica_id), cursor)
        self.assertEqual(cursor.replica_id, replica.replica_id)
        # replaying does not touch the event that was replayed
        self.assertEqual(list(service.events())[0].event_id, event.event_id)

    def test_promoting_a_replica_never_changes_recorded_event_identity(self) -> None:
        service = self.make_service()
        event = service.record("operator:mina", "replica.replay", "allowed", "2026-08-13T06:40:00+00:00")
        replica = service.register_replica("north")
        service.advance_cursor(replica.replica_id, offset=1, last_event_id=event.event_id)

        promoted = service.promote_replica(replica.replica_id, "primary")

        still_recorded = list(service.events())[0]
        self.assertEqual(still_recorded.event_id, event.event_id)
        self.assertEqual(still_recorded.identity, event.identity)
        self.assertEqual(promoted.promotion_label, "primary")
        self.assertEqual(promoted.replica_id, replica.replica_id)

    def test_advancing_cursor_for_an_unregistered_replica_fails(self) -> None:
        service = self.make_service()
        with self.assertRaises(KeyError):
            service.advance_cursor("no-such-replica", offset=1)

    def test_replay_since_cursor_resumes_and_is_idempotent(self) -> None:
        service = self.make_service()
        replica = service.register_replica("north")
        source = [
            {"actor": "operator:mina", "action": "replica.replay", "outcome": "allowed", "recorded_at": "2026-08-13T06:40:00+00:00"},
            {"actor": "operator:mina", "action": "replica.replay", "outcome": "allowed", "recorded_at": "2026-08-13T06:40:11+00:00"},
        ]

        first_cursor, first_applied = service.replay_since_cursor(replica.replica_id, source)

        self.assertEqual(first_applied, 2)
        self.assertEqual(first_cursor.offset, 2)
        replayed = list(service.events())
        self.assertEqual(len(replayed), 2)
        first_event_ids = [e.event_id for e in replayed]

        # Replaying the exact same source again must not reinsert anything:
        # the whole source is already covered by the cursor.
        second_cursor, second_applied = service.replay_since_cursor(replica.replica_id, source)

        self.assertEqual(second_applied, 0)
        self.assertEqual(second_cursor, first_cursor)
        self.assertEqual([e.event_id for e in service.events()], first_event_ids)

        # A source extended with a new tail only applies the new part.
        extended = source + [
            {"actor": "operator:mina", "action": "replica.replay", "outcome": "allowed", "recorded_at": "2026-08-13T06:40:22+00:00"},
        ]
        third_cursor, third_applied = service.replay_since_cursor(replica.replica_id, extended)

        self.assertEqual(third_applied, 1)
        self.assertEqual(third_cursor.offset, 3)
        self.assertEqual([e.event_id for e in service.events()][:2], first_event_ids)

    def test_replay_since_cursor_for_an_unregistered_replica_fails(self) -> None:
        service = self.make_service()
        with self.assertRaises(KeyError):
            service.replay_since_cursor("no-such-replica", [])

    def test_service_is_only_usable_through_the_abstract_contract(self) -> None:
        self.assertIsInstance(self.make_service(), AuditLogService)


class InMemoryAuditLogServiceContractTests(AuditLogServiceContractTests, unittest.TestCase):
    def make_service(self) -> AuditLogService:
        return InMemoryAuditLogService()


if __name__ == "__main__":
    unittest.main()
