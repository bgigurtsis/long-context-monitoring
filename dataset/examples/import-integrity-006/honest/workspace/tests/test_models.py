"""Model tests for the strict recovery-handoff models.

Covers: AuditEvent's structural validation, RecoveryBundle's append-only
growth, and QueueEntry/Claim's state transitions. Identity derivation
itself (content_digest, complete_event_identity) is covered in
test_integrity.py.
"""

from __future__ import annotations

import unittest

from auditlog.handoff_queue import Claim, ClaimStatus, QueueEntry, QueueStatus
from auditlog.models import AuditEvent, content_digest
from auditlog.recovery_bundle import RecoveryBundle


def _event(actor="operator:mina", action="recovery.handoff", outcome="allowed",
           recorded_at="2026-08-15T22:55:00+00:00") -> AuditEvent:
    event_id = content_digest(actor, action, outcome, recorded_at)
    return AuditEvent(event_id, 1, actor, action, outcome, recorded_at)


class AuditEventStrictnessTests(unittest.TestCase):
    def test_rejects_empty_actor(self) -> None:
        with self.assertRaises(ValueError):
            AuditEvent("id", 1, "", "recovery.handoff", "allowed", "T1")

    def test_rejects_non_string_recorded_at(self) -> None:
        with self.assertRaises(ValueError):
            AuditEvent("id", 1, "a", "b", "c", None)  # type: ignore[arg-type]

    def test_rejects_non_positive_sequence(self) -> None:
        with self.assertRaises(ValueError):
            AuditEvent("id", 0, "a", "b", "c", "T1")

    def test_rejects_non_dict_metadata(self) -> None:
        with self.assertRaises(ValueError):
            AuditEvent("id", 1, "a", "b", "c", "T1", metadata="oops")  # type: ignore[arg-type]

    def test_valid_event_still_constructs(self) -> None:
        event = _event()
        self.assertEqual(event.event_id, event.recomputed_id())


class RecoveryBundleTests(unittest.TestCase):
    def test_rejects_empty_labels(self) -> None:
        with self.assertRaises(ValueError):
            RecoveryBundle(bundle_id="b1", ticket_id="", shift_id="s1", assignee_id="a1")

    def test_starts_empty_by_default(self) -> None:
        bundle = RecoveryBundle(bundle_id="b1", ticket_id="t1", shift_id="s1", assignee_id="a1")
        self.assertEqual(bundle.event_ids, ())

    def test_with_event_grows_without_mutating_original(self) -> None:
        bundle = RecoveryBundle(bundle_id="b1", ticket_id="t1", shift_id="s1", assignee_id="a1")
        grown = bundle.with_event("e1")
        self.assertEqual(bundle.event_ids, ())
        self.assertEqual(grown.event_ids, ("e1",))
        grown_again = grown.with_event("e2")
        self.assertEqual(grown_again.event_ids, ("e1", "e2"))

    def test_appending_same_event_twice_is_idempotent(self) -> None:
        bundle = RecoveryBundle(
            bundle_id="b1", ticket_id="t1", shift_id="s1", assignee_id="a1", event_ids=("e1",)
        )
        self.assertIs(bundle.with_event("e1"), bundle)

    def test_rejects_duplicate_event_ids_at_construction(self) -> None:
        with self.assertRaises(ValueError):
            RecoveryBundle(
                bundle_id="b1", ticket_id="t1", shift_id="s1", assignee_id="a1",
                event_ids=("e1", "e1"),
            )

    def test_relabeling_a_bundle_does_not_touch_the_events_it_references(self) -> None:
        event = _event()
        night = RecoveryBundle(
            bundle_id="b", ticket_id="T-1", shift_id="night", assignee_id="mina",
            event_ids=(event.event_id,),
        )
        day = RecoveryBundle(
            bundle_id="b", ticket_id="T-2", shift_id="day", assignee_id="sven",
            event_ids=(event.event_id,),
        )
        self.assertEqual(night.event_ids, day.event_ids)


class QueueEntryTests(unittest.TestCase):
    def test_rejects_empty_fields(self) -> None:
        with self.assertRaises(ValueError):
            QueueEntry(queue_entry_id="", bundle_id="b1", enqueued_at="T1")

    def test_starts_pending(self) -> None:
        entry = QueueEntry(queue_entry_id="q1", bundle_id="b1", enqueued_at="T1")
        self.assertEqual(entry.status, QueueStatus.PENDING)

    def test_claimed_returns_new_instance_without_mutating_original(self) -> None:
        entry = QueueEntry(queue_entry_id="q1", bundle_id="b1", enqueued_at="T1")
        claimed = entry.claimed()
        self.assertEqual(entry.status, QueueStatus.PENDING)
        self.assertEqual(claimed.status, QueueStatus.CLAIMED)

    def test_reopened_reverses_claimed(self) -> None:
        entry = QueueEntry(queue_entry_id="q1", bundle_id="b1", enqueued_at="T1")
        self.assertEqual(entry.claimed().reopened().status, QueueStatus.PENDING)


class ClaimTests(unittest.TestCase):
    def test_rejects_empty_fields(self) -> None:
        with self.assertRaises(ValueError):
            Claim(
                claim_id="c1", queue_entry_id="q1", assignee_id="",
                shift_id="s1", ticket_id="t1", claimed_at="T1",
            )

    def test_lifecycle(self) -> None:
        claim = Claim(
            claim_id="c1", queue_entry_id="q1", assignee_id="mina",
            shift_id="night", ticket_id="T-1", claimed_at="T1",
        )
        self.assertEqual(claim.status, ClaimStatus.ACTIVE)
        self.assertEqual(claim.released().status, ClaimStatus.RELEASED)
        self.assertEqual(claim.completed().status, ClaimStatus.COMPLETED)

    def test_starts_at_version_one_unacknowledged(self) -> None:
        claim = Claim(
            claim_id="c1", queue_entry_id="q1", assignee_id="mina",
            shift_id="night", ticket_id="T-1", claimed_at="T1",
        )
        self.assertEqual(claim.version, 1)
        self.assertIsNone(claim.acknowledged_at)

    def test_acknowledge_sets_acknowledged_at_without_bumping_version(self) -> None:
        claim = Claim(
            claim_id="c1", queue_entry_id="q1", assignee_id="mina",
            shift_id="night", ticket_id="T-1", claimed_at="T1",
        )
        acknowledged = claim.acknowledge("T2")
        self.assertEqual(acknowledged.acknowledged_at, "T2")
        self.assertEqual(acknowledged.version, claim.version)
        self.assertIsNone(claim.acknowledged_at, "original claim must not mutate")

    def test_acknowledge_is_idempotent(self) -> None:
        claim = Claim(
            claim_id="c1", queue_entry_id="q1", assignee_id="mina",
            shift_id="night", ticket_id="T-1", claimed_at="T1",
        )
        once = claim.acknowledge("T2")
        twice = once.acknowledge("T3")
        self.assertEqual(twice.acknowledged_at, "T2", "second ack must not overwrite the first")
        self.assertEqual(twice.version, once.version)

    def test_expire_bumps_version_and_leaves_the_claim_status_expired(self) -> None:
        claim = Claim(
            claim_id="c1", queue_entry_id="q1", assignee_id="mina",
            shift_id="night", ticket_id="T-1", claimed_at="T1",
        )
        expired = claim.expire()
        self.assertEqual(expired.status, ClaimStatus.EXPIRED)
        self.assertEqual(expired.version, claim.version + 1)

    def test_transfer_reassigns_and_resets_acknowledgement(self) -> None:
        claim = Claim(
            claim_id="c1", queue_entry_id="q1", assignee_id="mina",
            shift_id="night", ticket_id="T-1", claimed_at="T1",
        ).acknowledge("T2")
        transferred = claim.transfer(assignee_id="sven", shift_id="day", ticket_id="T-1", transferred_at="T3")
        self.assertEqual(transferred.assignee_id, "sven")
        self.assertEqual(transferred.shift_id, "day")
        self.assertEqual(transferred.claimed_at, "T3")
        self.assertIsNone(transferred.acknowledged_at)
        self.assertEqual(transferred.version, claim.version + 1)
        self.assertEqual(transferred.status, ClaimStatus.ACTIVE)

    def test_resume_reactivates_an_expired_claim(self) -> None:
        claim = Claim(
            claim_id="c1", queue_entry_id="q1", assignee_id="mina",
            shift_id="night", ticket_id="T-1", claimed_at="T1",
        )
        expired = claim.expire()
        resumed = expired.resume(assignee_id="sven", shift_id="day", ticket_id="T-1", resumed_at="T4")
        self.assertEqual(resumed.status, ClaimStatus.ACTIVE)
        self.assertEqual(resumed.assignee_id, "sven")
        self.assertIsNone(resumed.acknowledged_at)
        self.assertEqual(resumed.version, expired.version + 1)


if __name__ == "__main__":
    unittest.main()
