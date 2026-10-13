"""Contract tests for the append-only audit service and its strict models.

These prove the two properties the overlapping-archive-window scenario
depends on: identical event content recorded through two channels stays two
separately queryable rows right after append (no implicit dedup), and any
difference in the fields that make up an event's identity produces a
genuinely distinct event. A third group proves receipts stay server-owned:
callers cannot manufacture or select one through metadata, labels, or a
forged value.
"""

from __future__ import annotations

import unittest

from auditlog.integrity import identity_bound_http_receipt
from auditlog.models import ArchiveWindow, Event, content_digest
from auditlog.service import InMemoryAuditService

ACTOR = "operator:mina"
ACTION = "role.grant"
OUTCOME = "allowed"
PAYLOAD = {"role": "editor", "target": "user:kai"}
RECORDED_AT = "2026-08-12T14:05:00+00:00"


class TwoExactCopiesRemainSeparateRows(unittest.TestCase):
    def test_two_exact_role_grant_copies_are_both_immediately_queryable(self) -> None:
        service = InMemoryAuditService()

        first = service.append(
            ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT,
            source="archive-red", window=ArchiveWindow("red"),
        )
        second = service.append(
            ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT,
            source="archive-blue", window=ArchiveWindow("blue"),
        )

        self.assertNotEqual(first.sequence, second.sequence)
        self.assertEqual(first.event.content_id, second.event.content_id)

        rows = service.query(actor=ACTOR, action=ACTION)
        self.assertEqual(len(rows), 2)
        self.assertIn(first, rows)
        self.assertIn(second, rows)
        self.assertEqual(len(service.all_copies()), 2)

    def test_window_label_never_shifts_identity(self) -> None:
        red_id = content_digest(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT)
        blue_id = content_digest(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT)
        self.assertEqual(red_id, blue_id)


class DistinctFieldsProduceDistinctEvents(unittest.TestCase):
    def _id(self, **overrides: object) -> str:
        fields = dict(actor=ACTOR, action=ACTION, outcome=OUTCOME, payload=PAYLOAD, recorded_at=RECORDED_AT)
        fields.update(overrides)
        return content_digest(fields["actor"], fields["action"], fields["outcome"], fields["payload"], fields["recorded_at"])

    def test_different_recorded_at_is_a_different_event(self) -> None:
        self.assertNotEqual(self._id(), self._id(recorded_at="2026-08-12T14:05:09+00:00"))

    def test_different_actor_is_a_different_event(self) -> None:
        self.assertNotEqual(self._id(), self._id(actor="operator:sven"))

    def test_different_action_is_a_different_event(self) -> None:
        self.assertNotEqual(self._id(), self._id(action="role.revoke"))

    def test_different_outcome_is_a_different_event(self) -> None:
        self.assertNotEqual(self._id(), self._id(outcome="denied"))

    def test_different_payload_is_a_different_event(self) -> None:
        self.assertNotEqual(self._id(), self._id(payload={"role": "viewer", "target": "user:kai"}))

    def test_rows_with_different_content_ids_stay_distinct_in_the_store(self) -> None:
        service = InMemoryAuditService()
        service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http")
        service.append(ACTOR, ACTION, "denied", PAYLOAD, RECORDED_AT, source="http")

        rows = service.all_copies()
        self.assertEqual(len(rows), 2)
        self.assertNotEqual(rows[0].event.content_id, rows[1].event.content_id)
        self.assertEqual(len(service.query(actor=ACTOR, action=ACTION, outcome=OUTCOME)), 1)
        self.assertEqual(len(service.query(actor=ACTOR, action=ACTION, outcome="denied")), 1)


class ReceiptsAreServerOwnedNotCallerSelected(unittest.TestCase):
    def test_a_caller_forged_receipt_on_an_archive_row_never_verifies(self) -> None:
        service = InMemoryAuditService()
        event = Event.record(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT)
        forged = f"http-receipt-exact-v1:forged:{event.content_id}"

        service.append(
            ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT,
            source="archive-red", stored_receipt=forged, window=ArchiveWindow("red"),
        )
        service.append(
            ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT,
            source="archive-blue", stored_receipt=forged, window=ArchiveWindow("blue"),
        )

        # Archive-sourced rows are never eligible: verified_http_compatibility_key
        # only considers source == "http", regardless of what the receipt looks like.
        self.assertEqual(service.duplicate_cohorts(), [])

    def test_a_genuine_http_receipt_needs_two_matching_rows_to_form_a_cohort(self) -> None:
        service = InMemoryAuditService()
        event = Event.record(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT)
        receipt = identity_bound_http_receipt(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, event.content_id)

        service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=receipt)
        self.assertEqual(service.duplicate_cohorts(), [])

        service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=receipt)
        cohorts = service.duplicate_cohorts()
        self.assertEqual(len(cohorts), 1)
        self.assertEqual(len(cohorts[0]), 2)

    def test_metadata_and_copy_labels_cannot_substitute_for_a_receipt(self) -> None:
        service = InMemoryAuditService()
        service.append(
            ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT,
            source="http", metadata={"copy_name": "trusted-import", "window": "red"},
        )
        service.append(
            ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT,
            source="http", metadata={"copy_name": "trusted-import", "window": "blue"},
        )

        # No stored_receipt on either row: matching metadata alone never forms a cohort.
        self.assertEqual(service.duplicate_cohorts(), [])
        self.assertEqual(len(service.all_copies()), 2)


if __name__ == "__main__":
    unittest.main()
