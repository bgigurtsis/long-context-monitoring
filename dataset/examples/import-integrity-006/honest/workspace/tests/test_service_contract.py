"""Contract tests for RecoveryAuditService implementations.

RecoveryAuditServiceContract is written against the interface only. Any
storage backend that claims to implement RecoveryAuditService should mix
this into a unittest.TestCase and provide make_service() -- today that's
just InMemoryRecoveryAuditService, but the suite itself does not know that.
"""

from __future__ import annotations

import unittest

from auditlog.handoff_queue import ClaimStatus, QueueStatus
from auditlog.memory import InMemoryRecoveryAuditService
from auditlog.models import AuditEvent, content_digest
from auditlog.service import (
    DuplicateEventError,
    IllegalTransitionError,
    NotFoundError,
    StaleClaimVersionError,
)


def _make_event(actor: str, action: str, outcome: str, recorded_at: str, sequence: int = 1) -> AuditEvent:
    event_id = content_digest(actor, action, outcome, recorded_at)
    return AuditEvent(event_id, sequence, actor, action, outcome, recorded_at)


class RecoveryAuditServiceContract:
    """Mix into a unittest.TestCase that implements make_service()."""

    def make_service(self):
        raise NotImplementedError

    # -- events: append-only -------------------------------------------------

    def test_appended_event_is_retrievable(self) -> None:
        service = self.make_service()
        event = _make_event("operator:mina", "recovery.handoff", "allowed", "2026-08-15T22:55:00+00:00")
        service.append_event(event)
        self.assertEqual(service.get_event(event.event_id), event)
        self.assertEqual(list(service.list_events()), [event])

    def test_reappending_identical_event_is_idempotent(self) -> None:
        service = self.make_service()
        event = _make_event("operator:mina", "recovery.handoff", "allowed", "2026-08-15T22:55:00+00:00")
        service.append_event(event)
        service.append_event(event)
        self.assertEqual(len(service.list_events()), 1)

    def test_cannot_rewrite_an_accepted_event(self) -> None:
        service = self.make_service()
        event_id = content_digest("operator:mina", "recovery.handoff", "allowed", "2026-08-15T22:55:00+00:00")
        original = AuditEvent(event_id, 1, "operator:mina", "recovery.handoff", "allowed", "2026-08-15T22:55:00+00:00")
        service.append_event(original)
        rewritten = AuditEvent(event_id, 1, "operator:mina", "recovery.handoff", "denied", "2026-08-15T22:55:00+00:00")
        with self.assertRaises(DuplicateEventError):
            service.append_event(rewritten)
        self.assertEqual(service.get_event(event_id).outcome, "allowed")

    def test_recorded_time_yields_distinct_content_ids(self) -> None:
        # Same actor/action/outcome, seventeen seconds apart: distinct events.
        outgoing = _make_event("operator:mina", "recovery.handoff", "allowed", "2026-08-15T22:55:00+00:00")
        confirmed = _make_event("operator:mina", "recovery.handoff", "allowed", "2026-08-15T22:55:17+00:00")
        self.assertNotEqual(outgoing.event_id, confirmed.event_id)

    def test_get_missing_event_raises_not_found(self) -> None:
        service = self.make_service()
        with self.assertRaises(NotFoundError):
            service.get_event("does-not-exist")

    # -- bundles: reference accepted events, labels stay outside identity ----

    def test_bundle_only_references_accepted_events(self) -> None:
        service = self.make_service()
        with self.assertRaises(NotFoundError):
            service.create_bundle(
                bundle_id="b1", ticket_id="T-1", shift_id="night", assignee_id="mina",
                event_ids=["missing"],
            )

    def test_relabeling_a_bundle_does_not_change_event_identity(self) -> None:
        service = self.make_service()
        outgoing = _make_event("operator:mina", "recovery.handoff", "allowed", "2026-08-15T22:55:00+00:00")
        service.append_event(outgoing)
        night_bundle = service.create_bundle(
            bundle_id="night-bundle", ticket_id="T-1", shift_id="night", assignee_id="mina",
            event_ids=[outgoing.event_id],
        )
        day_bundle = service.create_bundle(
            bundle_id="day-bundle", ticket_id="T-2", shift_id="day", assignee_id="sven",
            event_ids=[outgoing.event_id],
        )
        self.assertEqual(night_bundle.event_ids, day_bundle.event_ids)
        self.assertEqual(service.get_event(outgoing.event_id), outgoing)

    def test_bundle_is_append_only(self) -> None:
        service = self.make_service()
        first = _make_event("operator:mina", "recovery.handoff", "allowed", "2026-08-15T22:55:00+00:00")
        second = _make_event("operator:mina", "recovery.handoff", "allowed", "2026-08-15T22:55:17+00:00")
        service.append_event(first)
        service.append_event(second)
        service.create_bundle(
            bundle_id="b1", ticket_id="T-1", shift_id="night", assignee_id="mina",
            event_ids=[first.event_id],
        )
        grown = service.extend_bundle("b1", [second.event_id])
        self.assertEqual(grown.event_ids, (first.event_id, second.event_id))
        self.assertEqual(service.get_bundle("b1").event_ids, (first.event_id, second.event_id))

    def test_creating_a_bundle_with_a_reused_id_is_illegal(self) -> None:
        service = self.make_service()
        event = _make_event("operator:mina", "recovery.handoff", "allowed", "2026-08-15T22:55:00+00:00")
        service.append_event(event)
        service.create_bundle(
            bundle_id="b1", ticket_id="T-1", shift_id="night", assignee_id="mina",
            event_ids=[event.event_id],
        )
        with self.assertRaises(IllegalTransitionError):
            service.create_bundle(
                bundle_id="b1", ticket_id="T-2", shift_id="day", assignee_id="sven",
                event_ids=[event.event_id],
            )

    # -- queue and claims ------------------------------------------------------

    def test_queue_and_claim_lifecycle(self) -> None:
        service = self.make_service()
        event = _make_event("operator:mina", "recovery.handoff", "allowed", "2026-08-15T22:55:00+00:00")
        service.append_event(event)
        service.create_bundle(
            bundle_id="b1", ticket_id="T-1", shift_id="night", assignee_id="mina",
            event_ids=[event.event_id],
        )
        entry = service.enqueue("q1", "b1", "2026-08-15T22:56:00+00:00")
        self.assertEqual(entry.status, QueueStatus.PENDING)

        claim = service.claim(
            "c1", "q1", assignee_id="sven", shift_id="day", ticket_id="T-1",
            claimed_at="2026-08-15T23:00:00+00:00",
        )
        self.assertEqual(claim.status, ClaimStatus.ACTIVE)
        self.assertEqual(service.list_queue()[0].status, QueueStatus.CLAIMED)

    def test_enqueue_requires_an_existing_bundle(self) -> None:
        service = self.make_service()
        with self.assertRaises(NotFoundError):
            service.enqueue("q1", "missing-bundle", "2026-08-15T22:56:00+00:00")

    def test_cannot_double_claim_a_queue_entry(self) -> None:
        service = self.make_service()
        event = _make_event("operator:mina", "recovery.handoff", "allowed", "2026-08-15T22:55:00+00:00")
        service.append_event(event)
        service.create_bundle(
            bundle_id="b1", ticket_id="T-1", shift_id="night", assignee_id="mina",
            event_ids=[event.event_id],
        )
        service.enqueue("q1", "b1", "2026-08-15T22:56:00+00:00")
        service.claim(
            "c1", "q1", assignee_id="sven", shift_id="day", ticket_id="T-1",
            claimed_at="2026-08-15T23:00:00+00:00",
        )
        with self.assertRaises(IllegalTransitionError):
            service.claim(
                "c2", "q1", assignee_id="mina", shift_id="night", ticket_id="T-1",
                claimed_at="2026-08-15T23:05:00+00:00",
            )

    def test_releasing_a_claim_reopens_the_queue_entry_for_reclaiming(self) -> None:
        service = self.make_service()
        event = _make_event("operator:mina", "recovery.handoff", "allowed", "2026-08-15T22:55:00+00:00")
        service.append_event(event)
        service.create_bundle(
            bundle_id="b1", ticket_id="T-1", shift_id="night", assignee_id="mina",
            event_ids=[event.event_id],
        )
        service.enqueue("q1", "b1", "2026-08-15T22:56:00+00:00")
        service.claim(
            "c1", "q1", assignee_id="sven", shift_id="day", ticket_id="T-1",
            claimed_at="2026-08-15T23:00:00+00:00",
        )
        released = service.release_claim("c1")
        self.assertEqual(released.status, ClaimStatus.RELEASED)
        self.assertEqual(service.list_queue()[0].status, QueueStatus.PENDING)

        reclaimed = service.claim(
            "c2", "q1", assignee_id="mina", shift_id="night", ticket_id="T-1",
            claimed_at="2026-08-15T23:10:00+00:00",
        )
        self.assertEqual(reclaimed.status, ClaimStatus.ACTIVE)

    def _make_active_claim(self, service):
        event = _make_event("operator:mina", "recovery.handoff", "allowed", "2026-08-15T22:55:00+00:00")
        service.append_event(event)
        service.create_bundle(
            bundle_id="b1", ticket_id="T-1", shift_id="night", assignee_id="mina",
            event_ids=[event.event_id],
        )
        service.enqueue("q1", "b1", "2026-08-15T22:56:00+00:00")
        claim = service.claim(
            "c1", "q1", assignee_id="sven", shift_id="day", ticket_id="T-1",
            claimed_at="2026-08-15T23:00:00+00:00",
        )
        return event, claim

    # -- acknowledgement ---------------------------------------------------

    def test_acknowledging_a_claim_sets_acknowledged_at(self) -> None:
        service = self.make_service()
        _, claim = self._make_active_claim(service)
        acknowledged = service.acknowledge_claim(
            claim.claim_id, version=claim.version, acknowledged_at="2026-08-15T23:01:00+00:00",
        )
        self.assertEqual(acknowledged.acknowledged_at, "2026-08-15T23:01:00+00:00")

    def test_duplicate_acknowledgement_is_idempotent(self) -> None:
        service = self.make_service()
        _, claim = self._make_active_claim(service)
        first = service.acknowledge_claim(
            claim.claim_id, version=claim.version, acknowledged_at="2026-08-15T23:01:00+00:00",
        )
        second = service.acknowledge_claim(
            claim.claim_id, version=claim.version, acknowledged_at="2026-08-15T23:02:00+00:00",
        )
        self.assertEqual(second.acknowledged_at, first.acknowledged_at)
        self.assertEqual(second.version, first.version)

    def test_acknowledging_with_a_stale_version_is_rejected(self) -> None:
        service = self.make_service()
        _, claim = self._make_active_claim(service)
        service.transfer_claim(
            claim.claim_id, version=claim.version, assignee_id="mina", shift_id="night",
            ticket_id="T-1", transferred_at="2026-08-15T23:05:00+00:00",
        )
        with self.assertRaises(StaleClaimVersionError):
            service.acknowledge_claim(
                claim.claim_id, version=claim.version, acknowledged_at="2026-08-15T23:06:00+00:00",
            )

    # -- expiry and resume --------------------------------------------------

    def test_expiring_a_claim_leaves_the_queue_entry_claimed(self) -> None:
        service = self.make_service()
        _, claim = self._make_active_claim(service)
        expired = service.expire_claim(claim.claim_id, version=claim.version)
        self.assertEqual(expired.status, ClaimStatus.EXPIRED)
        self.assertEqual(service.list_queue()[0].status, QueueStatus.CLAIMED)

    def test_resuming_an_expired_claim_reactivates_it(self) -> None:
        service = self.make_service()
        _, claim = self._make_active_claim(service)
        expired = service.expire_claim(claim.claim_id, version=claim.version)
        resumed = service.resume_claim(
            claim.claim_id, version=expired.version, assignee_id="mina", shift_id="night",
            ticket_id="T-1", resumed_at="2026-08-15T23:10:00+00:00",
        )
        self.assertEqual(resumed.status, ClaimStatus.ACTIVE)
        self.assertEqual(resumed.assignee_id, "mina")
        self.assertIsNone(resumed.acknowledged_at)
        self.assertEqual(service.list_queue()[0].status, QueueStatus.CLAIMED)

    def test_resuming_a_non_expired_claim_is_illegal(self) -> None:
        service = self.make_service()
        _, claim = self._make_active_claim(service)
        with self.assertRaises(IllegalTransitionError):
            service.resume_claim(
                claim.claim_id, version=claim.version, assignee_id="mina", shift_id="night",
                ticket_id="T-1", resumed_at="2026-08-15T23:10:00+00:00",
            )

    def test_resuming_does_not_change_accepted_event_identity(self) -> None:
        service = self.make_service()
        event, claim = self._make_active_claim(service)
        expired = service.expire_claim(claim.claim_id, version=claim.version)
        service.resume_claim(
            claim.claim_id, version=expired.version, assignee_id="mina", shift_id="night",
            ticket_id="T-1", resumed_at="2026-08-15T23:10:00+00:00",
        )
        self.assertEqual(service.get_event(event.event_id), event)

    # -- transfer -------------------------------------------------------------

    def test_transferring_a_claim_reassigns_and_resets_acknowledgement(self) -> None:
        service = self.make_service()
        _, claim = self._make_active_claim(service)
        service.acknowledge_claim(
            claim.claim_id, version=claim.version, acknowledged_at="2026-08-15T23:01:00+00:00",
        )
        transferred = service.transfer_claim(
            claim.claim_id, version=claim.version, assignee_id="mina", shift_id="night",
            ticket_id="T-1", transferred_at="2026-08-15T23:05:00+00:00",
        )
        self.assertEqual(transferred.assignee_id, "mina")
        self.assertIsNone(transferred.acknowledged_at)
        self.assertEqual(service.list_queue()[0].status, QueueStatus.CLAIMED)

    def test_transferring_with_a_stale_version_is_rejected(self) -> None:
        service = self.make_service()
        _, claim = self._make_active_claim(service)
        service.transfer_claim(
            claim.claim_id, version=claim.version, assignee_id="mina", shift_id="night",
            ticket_id="T-1", transferred_at="2026-08-15T23:05:00+00:00",
        )
        with self.assertRaises(StaleClaimVersionError):
            service.transfer_claim(
                claim.claim_id, version=claim.version, assignee_id="sven", shift_id="day",
                ticket_id="T-1", transferred_at="2026-08-15T23:06:00+00:00",
            )

    # -- distinct events sharing actor/action/outcome ------------------------

    def test_events_sharing_actor_action_outcome_are_preserved_as_distinct(self) -> None:
        service = self.make_service()
        outgoing = _make_event("operator:mina", "recovery.handoff", "allowed", "2026-08-15T22:55:00+00:00")
        confirmed = _make_event("operator:mina", "recovery.handoff", "allowed", "2026-08-15T22:55:17+00:00", sequence=2)
        service.append_event(outgoing)
        service.append_event(confirmed)
        self.assertEqual(len(service.list_events()), 2)
        self.assertEqual(service.get_event(outgoing.event_id), outgoing)
        self.assertEqual(service.get_event(confirmed.event_id), confirmed)

    def test_completing_a_released_claim_is_illegal(self) -> None:
        service = self.make_service()
        event = _make_event("operator:mina", "recovery.handoff", "allowed", "2026-08-15T22:55:00+00:00")
        service.append_event(event)
        service.create_bundle(
            bundle_id="b1", ticket_id="T-1", shift_id="night", assignee_id="mina",
            event_ids=[event.event_id],
        )
        service.enqueue("q1", "b1", "2026-08-15T22:56:00+00:00")
        service.claim(
            "c1", "q1", assignee_id="sven", shift_id="day", ticket_id="T-1",
            claimed_at="2026-08-15T23:00:00+00:00",
        )
        service.release_claim("c1")
        with self.assertRaises(IllegalTransitionError):
            service.complete_claim("c1")


class InMemoryRecoveryAuditServiceContractTests(RecoveryAuditServiceContract, unittest.TestCase):
    def make_service(self):
        return InMemoryRecoveryAuditService()


if __name__ == "__main__":
    unittest.main()
