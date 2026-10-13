"""Tests for compatibility repair: the atomic removal step that acts on the
production non-mutating planner's own actionable groups.

Every test here proves one property from the feature's own contract: only
``BASIS_COMPLETE_IDENTITY`` and ``BASIS_VERIFIED_HTTP_COMPATIBILITY`` groups
are ever actionable, the lowest row sequence in an actionable group is
always retained, a ``BASIS_VERIFIED_LINEAGE`` group is never removed from,
and malformed/transplanted/missing receipt evidence that never spans two
distinct complete identities never triggers a removal at all.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from auditlog.compatibility_repair import execute_compatibility_repair, plan_compatibility_repair
from auditlog.integrity import identity_bound_http_receipt
from auditlog.models import ArchiveWindow, Event
from auditlog.sqlite_storage import (
    BASIS_COMPLETE_IDENTITY,
    BASIS_VERIFIED_HTTP_COMPATIBILITY,
    SqliteAuditService,
)

ACTOR = "operator:mina"
ACTION = "role.grant"
OUTCOME = "allowed"
PAYLOAD = {"role": "editor", "target": "user:kai"}
RECORDED_AT = "2026-08-12T14:05:00+00:00"
NEXT_SECOND = "2026-08-12T14:05:01+00:00"


class _RepairTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        self._next_db = 0

    def new_service(self) -> SqliteAuditService:
        self._next_db += 1
        return SqliteAuditService(Path(self._tmp_dir.name) / f"audit-{self._next_db}.sqlite3")

    def genuine_receipt(self, event: Event) -> str:
        return identity_bound_http_receipt(
            event.actor, event.action, event.outcome, event.payload, event.recorded_at, event.content_id,
        )


class ExactReplayRemoval(_RepairTestCase):
    def test_exact_mina_replay_keeps_the_lowest_sequence_and_removes_the_later_one(self) -> None:
        service = self.new_service()
        event = Event.record(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT)
        receipt = self.genuine_receipt(event)
        first = service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=receipt)
        second = service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=receipt)

        result = execute_compatibility_repair(service, owner="worker-1", ttl_seconds=30, now=1000.0)

        [group] = result.removed_groups
        self.assertEqual(group.basis, BASIS_COMPLETE_IDENTITY)
        self.assertEqual(group.retained_sequence, first.sequence)
        self.assertEqual(group.removed_sequences, (second.sequence,))

        remaining = {row.sequence for row in service.all_copies()}
        self.assertEqual(remaining, {first.sequence})


class InjectedTransportCohortRemoval(_RepairTestCase):
    def test_a_strictly_validated_transport_cohort_is_actionable_and_keeps_the_lowest_sequence(self) -> None:
        # Today's real verified_http_compatibility_key can never itself
        # return a candidate spanning two distinct complete identities (see
        # auditlog.integrity and tests/test_overlap_planning.py) -- that is
        # an observed property of today's fixtures, not a claim that
        # BASIS_VERIFIED_HTTP_COMPATIBILITY removal is unreachable. This
        # substitutes a validator that *does* return such a candidate to
        # prove the removal branch is real and correctly keeps the lowest
        # sequence, exactly like the complete-identity branch.
        service = self.new_service()
        first = service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt="whatever-1")
        second = service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, NEXT_SECOND, source="http", stored_receipt="whatever-2")

        def always_shared_candidate(stored_receipt, actor, action, outcome, payload, recorded_at, content_id, source, verified_lineage):
            return "shared-transport-candidate"

        result = execute_compatibility_repair(
            service, owner="worker-1", ttl_seconds=30, now=1000.0,
            http_compatibility_validator=always_shared_candidate,
        )

        [group] = result.removed_groups
        self.assertEqual(group.basis, BASIS_VERIFIED_HTTP_COMPATIBILITY)
        self.assertEqual(group.retained_sequence, first.sequence)
        self.assertEqual(group.removed_sequences, (second.sequence,))
        remaining = {row.sequence for row in service.all_copies()}
        self.assertEqual(remaining, {first.sequence})


class VerifiedLineageIsNeverRemoved(_RepairTestCase):
    def test_a_cross_window_lineage_cohort_is_reported_but_never_removed(self) -> None:
        service = self.new_service()
        red = service.append(
            ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT,
            source="archive-red", verified_lineage="case-77", window=ArchiveWindow("red"),
        )
        blue = service.append(
            ACTOR, ACTION, OUTCOME, PAYLOAD, NEXT_SECOND,
            source="archive-blue", verified_lineage="case-77", window=ArchiveWindow("blue"),
        )

        result = execute_compatibility_repair(service, owner="worker-1", ttl_seconds=30, now=1000.0)

        self.assertEqual(result.removed_groups, ())
        [group] = result.retained_lineage_groups
        self.assertEqual(group.member_sequences, (red.sequence, blue.sequence))

        remaining = {row.sequence for row in service.all_copies()}
        self.assertEqual(remaining, {red.sequence, blue.sequence})


class ControlsThatMustNeverBeRemoved(_RepairTestCase):
    def _seed_base(self, service: SqliteAuditService):
        event = Event.record(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT)
        receipt = self.genuine_receipt(event)
        return service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=receipt)

    def test_next_second_mina_control_is_a_distinct_identity_and_is_kept(self) -> None:
        service = self.new_service()
        base = self._seed_base(service)
        next_event = Event.record(ACTOR, ACTION, OUTCOME, PAYLOAD, NEXT_SECOND)
        next_receipt = self.genuine_receipt(next_event)
        control = service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, NEXT_SECOND, source="http", stored_receipt=next_receipt)

        result = execute_compatibility_repair(service, owner="worker-1", ttl_seconds=30, now=1000.0)

        self.assertEqual(result.removed_groups, ())
        remaining = {row.sequence for row in service.all_copies()}
        self.assertEqual(remaining, {base.sequence, control.sequence})

    def test_different_actor_action_outcome_and_payload_controls_are_all_kept(self) -> None:
        service = self.new_service()
        base = self._seed_base(service)
        diff_actor = service.append("operator:sven", ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt="x")
        diff_action = service.append(ACTOR, "role.revoke", OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt="x")
        diff_outcome = service.append(ACTOR, ACTION, "denied", PAYLOAD, RECORDED_AT, source="http", stored_receipt="x")
        diff_payload = service.append(
            ACTOR, ACTION, OUTCOME, {"role": "viewer", "target": "user:kai"}, RECORDED_AT, source="http", stored_receipt="x",
        )

        result = execute_compatibility_repair(service, owner="worker-1", ttl_seconds=30, now=1000.0)

        self.assertEqual(result.removed_groups, ())
        remaining = {row.sequence for row in service.all_copies()}
        self.assertEqual(
            remaining,
            {base.sequence, diff_actor.sequence, diff_action.sequence, diff_outcome.sequence, diff_payload.sequence},
        )

    def test_sven_control_is_never_touched_by_a_mina_repair(self) -> None:
        service = self.new_service()
        mina_event = Event.record(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT)
        mina_receipt = self.genuine_receipt(mina_event)
        service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=mina_receipt)
        service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=mina_receipt)
        sven = service.append("operator:sven", ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt="s")

        result = execute_compatibility_repair(service, owner="worker-1", ttl_seconds=30, now=1000.0)

        removed = set(result.removed_sequences)
        self.assertNotIn(sven.sequence, removed)
        self.assertIn(sven.sequence, {row.sequence for row in service.all_copies()})


class MalformedAndTransplantedReceiptsNeverTriggerRemoval(_RepairTestCase):
    def test_malformed_receipt_alone_forms_no_group_and_is_kept(self) -> None:
        service = self.new_service()
        row = service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt="not-a-receipt-at-all")

        result = execute_compatibility_repair(service, owner="worker-1", ttl_seconds=30, now=1000.0)

        self.assertEqual(result.removed_groups, ())
        self.assertEqual({r.sequence for r in service.all_copies()}, {row.sequence})

    def test_transplanted_receipt_from_a_different_event_forms_no_group_and_is_kept(self) -> None:
        service = self.new_service()
        other_event = Event.record("operator:other", ACTION, OUTCOME, PAYLOAD, RECORDED_AT)
        transplanted = self.genuine_receipt(other_event)
        row = service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=transplanted)

        result = execute_compatibility_repair(service, owner="worker-1", ttl_seconds=30, now=1000.0)

        self.assertEqual(result.removed_groups, ())
        self.assertEqual({r.sequence for r in service.all_copies()}, {row.sequence})


class PlanExecuteParity(_RepairTestCase):
    def test_preview_and_execute_agree_on_the_same_groups(self) -> None:
        service = self.new_service()
        event = Event.record(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT)
        receipt = self.genuine_receipt(event)
        service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=receipt)
        service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=receipt)

        preview = plan_compatibility_repair(service)
        self.assertEqual(len(preview.groups), 1)
        before = service.all_copies()
        self.assertEqual(len(before), 2)  # planning alone never removes anything

        result = execute_compatibility_repair(service, owner="worker-1", ttl_seconds=30, now=1000.0)

        [removed] = result.removed_groups
        self.assertEqual(removed.basis, preview.groups[0].basis)
        self.assertEqual((removed.retained_sequence, *removed.removed_sequences), preview.groups[0].member_sequences)


if __name__ == "__main__":
    unittest.main()
