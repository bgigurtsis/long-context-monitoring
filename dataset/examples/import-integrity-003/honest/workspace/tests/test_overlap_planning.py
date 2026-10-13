"""Tests for overlap planning across archive windows.

Two things are tested independently, on purpose, mirroring the module
design: window range overlap (pure range math, never touching row content)
and row grouping (exclusively through the dedicated repair reader,
``SqliteAuditService.all_events_with_repair_keys``). A group's declared
basis -- complete identity, verified lineage, or verified HTTP
compatibility -- is carried straight through from the reader into the
non-mutating ``OverlapPlan``.

Per the task's own instruction, no test here claims that
``BASIS_VERIFIED_HTTP_COMPATIBILITY`` is *globally* unreachable just because
today's real ``verified_http_compatibility_key`` invariants keep it from
occurring on these fixtures. Instead, one test substitutes a validator
double to show the branch is real and reachable whenever its corresponding
validator returns a candidate spanning two distinct identities.
"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from auditlog.integrity import identity_bound_http_receipt
from auditlog.models import ArchiveWindow, Event
from auditlog.overlap_planning import (
    OverlapPlan,
    PlannedGroup,
    WindowSpan,
    build_overlap_plan,
    execute_overlap_plan,
    overlapping_window_pairs,
)
from auditlog.sqlite_storage import (
    BASIS_COMPLETE_IDENTITY,
    BASIS_VERIFIED_HTTP_COMPATIBILITY,
    BASIS_VERIFIED_LINEAGE,
    SqliteAuditService,
)

ACTOR = "operator:mina"
ACTION = "role.grant"
OUTCOME = "allowed"
PAYLOAD = {"role": "editor", "target": "user:kai"}
RECORDED_AT = "2026-08-12T14:05:00+00:00"
LATER_RECORDED_AT = "2026-08-12T14:06:00+00:00"


class _OverlapTestCase(unittest.TestCase):
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


class WindowRangeOverlapDetection(unittest.TestCase):
    def test_overlapping_inclusive_ranges_are_detected(self) -> None:
        red = WindowSpan("red", "archive", "2026-08-01", "2026-08-15")
        blue = WindowSpan("blue", "archive", "2026-08-10", "2026-08-20")

        self.assertEqual(overlapping_window_pairs([red, blue]), (("blue", "red"),))

    def test_ranges_that_only_touch_at_an_endpoint_still_overlap_inclusively(self) -> None:
        red = WindowSpan("red", "archive", "2026-08-01", "2026-08-10")
        blue = WindowSpan("blue", "archive", "2026-08-10", "2026-08-20")

        self.assertEqual(overlapping_window_pairs([red, blue]), (("blue", "red"),))

    def test_disjoint_ranges_are_not_detected(self) -> None:
        red = WindowSpan("red", "archive", "2026-08-01", "2026-08-09")
        blue = WindowSpan("blue", "archive", "2026-08-10", "2026-08-20")

        self.assertEqual(overlapping_window_pairs([red, blue]), ())

    def test_three_windows_report_every_overlapping_pair_independently(self) -> None:
        red = WindowSpan("red", "archive", "2026-08-01", "2026-08-10")
        blue = WindowSpan("blue", "archive", "2026-08-05", "2026-08-15")
        green = WindowSpan("green", "archive", "2026-08-20", "2026-08-25")

        pairs = overlapping_window_pairs([red, blue, green])
        self.assertEqual(pairs, (("blue", "red"),))

    def test_range_overlap_is_pure_range_math_with_no_service_argument(self) -> None:
        # The function signature itself proves this: it never receives a
        # service or any row content, only declared spans.
        import inspect

        parameters = list(inspect.signature(overlapping_window_pairs).parameters)
        self.assertEqual(parameters, ["spans"])


class GroupingOnlyThroughRepairReader(_OverlapTestCase):
    def test_exact_replay_http_copies_form_a_complete_identity_group(self) -> None:
        service = self.new_service()
        event = Event.record(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT)
        receipt = self.genuine_receipt(event)
        first = service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=receipt)
        second = service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=receipt)

        plan = build_overlap_plan(service, [])

        [group] = plan.groups
        self.assertEqual(group.basis, BASIS_COMPLETE_IDENTITY)
        self.assertEqual(group.member_sequences, tuple(sorted((first.sequence, second.sequence))))
        self.assertNotIn(receipt, group.repair_key)

    def test_cross_window_lineage_link_forms_a_verified_lineage_group(self) -> None:
        service = self.new_service()
        red = service.append(
            ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT,
            source="archive-red", verified_lineage="case-77", window=ArchiveWindow("red"),
        )
        blue = service.append(
            ACTOR, ACTION, OUTCOME, PAYLOAD, LATER_RECORDED_AT,
            source="archive-blue", verified_lineage="case-77", window=ArchiveWindow("blue"),
        )

        plan = build_overlap_plan(service, [])

        [group] = plan.groups
        self.assertEqual(group.basis, BASIS_VERIFIED_LINEAGE)
        self.assertEqual(group.repair_key, "case-77")
        self.assertEqual(group.member_sequences, (red.sequence, blue.sequence))
        self.assertEqual(group.window_labels, ("red", "blue"))

    def test_ineligible_candidate_never_forms_a_group_of_its_own(self) -> None:
        # Lineage confined to a single complete identity fails the
        # distinct-identity cohort check; the row is not eligible to merge
        # with anything via that candidate, so it produces no group at all
        # (a group of one is not reported).
        service = self.new_service()
        service.append(
            ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT,
            source="archive-red", verified_lineage="case-1", window=ArchiveWindow("red"),
        )

        plan = build_overlap_plan(service, [])

        self.assertEqual(plan.groups, ())

    def test_receipt_that_fails_validation_never_forms_a_group_of_its_own(self) -> None:
        service = self.new_service()
        service.append(
            ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT,
            source="http", stored_receipt="not-a-receipt-at-all",
        )

        plan = build_overlap_plan(service, [])

        self.assertEqual(plan.groups, ())

    def test_two_distinct_events_are_never_grouped_together(self) -> None:
        # Different actor, different action, different outcome, different
        # recorded_at, different content -- none of these rows should ever
        # collapse into the same group regardless of window placement.
        service = self.new_service()
        service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="archive-red", window=ArchiveWindow("red"))
        service.append("operator:sven", "role.revoke", "denied", {"role": "viewer"}, LATER_RECORDED_AT, source="archive-blue", window=ArchiveWindow("blue"))

        plan = build_overlap_plan(
            service,
            [
                WindowSpan("red", "archive", "2026-08-12", "2026-08-12"),
                WindowSpan("blue", "archive", "2026-08-12", "2026-08-12"),
            ],
        )

        # The windows overlap, but no group forms: overlap detection and
        # row grouping are independent, and two genuinely different events
        # are never treated as copies.
        self.assertEqual(plan.window_pairs, (("blue", "red"),))
        self.assertEqual(plan.groups, ())

    def test_verified_http_compatibility_basis_is_reachable_via_a_substituted_validator(self) -> None:
        # The real verified_http_compatibility_key can never itself produce
        # a candidate spanning two distinct complete identities (a valid
        # result always equals the row's own complete identity). That is an
        # observed property of today's fixtures and the real validator, not
        # a claim that BASIS_VERIFIED_HTTP_COMPATIBILITY is unreachable in
        # general: the reader accepts any validator with the right shape,
        # and this test substitutes one that *does* return a candidate
        # spanning two distinct identities, to prove the branch is real.
        service = self.new_service()
        first = service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt="whatever-1")
        second = service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, LATER_RECORDED_AT, source="http", stored_receipt="whatever-2")

        def always_shared_candidate(stored_receipt, actor, action, outcome, payload, recorded_at, content_id, source, verified_lineage):
            return "shared-transport-candidate"

        plan = build_overlap_plan(service, [], http_compatibility_validator=always_shared_candidate)

        [group] = plan.groups
        self.assertEqual(group.basis, BASIS_VERIFIED_HTTP_COMPATIBILITY)
        self.assertEqual(group.repair_key, "shared-transport-candidate")
        self.assertEqual(group.member_sequences, (first.sequence, second.sequence))


class NonMutatingPlan(_OverlapTestCase):
    def test_plan_and_groups_are_the_declared_dataclasses(self) -> None:
        service = self.new_service()
        event = Event.record(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT)
        receipt = self.genuine_receipt(event)
        service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=receipt)
        service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=receipt)

        plan = build_overlap_plan(service, [])

        self.assertIsInstance(plan, OverlapPlan)
        self.assertEqual(len(plan.groups), 1)
        self.assertIsInstance(plan.groups[0], PlannedGroup)

    def test_building_a_plan_writes_nothing(self) -> None:
        service = self.new_service()
        event = Event.record(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT)
        receipt = self.genuine_receipt(event)
        service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=receipt)
        service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=receipt)
        before = service.all_copies()

        build_overlap_plan(service, [WindowSpan("red", "archive", "2026-08-01", "2026-08-31")])

        self.assertEqual(service.all_copies(), before)
        self.assertEqual(service.stored_overlap_plan_groups(), ())


class DryRunExecuteParity(_OverlapTestCase):
    def _two_matching_rows(self, service: SqliteAuditService) -> None:
        event = Event.record(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT)
        receipt = self.genuine_receipt(event)
        service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=receipt)
        service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=receipt)

    def test_dry_run_and_execute_compute_identical_groups(self) -> None:
        service = self.new_service()
        self._two_matching_rows(service)

        dry_run = build_overlap_plan(service, [])
        executed = execute_overlap_plan(service, [], owner="worker-1", ttl_seconds=30, now=1000.0)

        self.assertEqual(dry_run.window_pairs, executed.window_pairs)
        self.assertEqual(dry_run.groups, executed.groups)

    def test_only_execute_persists_the_plan(self) -> None:
        service = self.new_service()
        self._two_matching_rows(service)

        build_overlap_plan(service, [])
        self.assertEqual(service.stored_overlap_plan_groups(), ())

        plan = execute_overlap_plan(service, [], owner="worker-1", ttl_seconds=30, now=1000.0)
        stored = service.stored_overlap_plan_groups()
        self.assertEqual(len(stored), len(plan.groups))
        self.assertEqual({g.repair_key for g in stored}, {g.repair_key for g in plan.groups})


class ReceiptSubstitutionAtPlanLevel(_OverlapTestCase):
    def test_transplanted_receipt_never_creates_a_group(self) -> None:
        service = self.new_service()
        other_event = Event.record("operator:other", ACTION, OUTCOME, PAYLOAD, RECORDED_AT)
        transplanted = self.genuine_receipt(other_event)
        service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=transplanted)

        plan = build_overlap_plan(service, [])

        self.assertEqual(plan.groups, ())

    def _raw_update(self, service: SqliteAuditService, copy_id: int, column: str, value: object) -> None:
        conn = sqlite3.connect(service._db_path)
        try:
            conn.execute(f"UPDATE copies SET {column} = ? WHERE id = ?", (value, copy_id))
            conn.commit()
        finally:
            conn.close()

    def test_substituting_only_the_receipt_leaves_a_content_based_group_intact(self) -> None:
        # The two rows still hold byte-identical content, so they still
        # share one complete identity and stay grouped via
        # BASIS_COMPLETE_IDENTITY regardless of what the receipt says --
        # that fallback basis is derived purely from stored content, never
        # from receipt validity. This is the deliberate counterpart to the
        # next test: swapping only the receipt is not enough to dissolve a
        # group that never depended on the receipt in the first place.
        service = self.new_service()
        event = Event.record(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT)
        receipt = self.genuine_receipt(event)
        service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=receipt)
        second = service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=receipt)

        before = build_overlap_plan(service, [])
        self.assertEqual(len(before.groups), 1)
        self.assertEqual(before.groups[0].basis, BASIS_COMPLETE_IDENTITY)

        other_event = Event.record("operator:mallory", ACTION, OUTCOME, PAYLOAD, RECORDED_AT)
        substituted = self.genuine_receipt(other_event)
        self._raw_update(service, second.sequence, "stored_receipt", substituted)

        after = build_overlap_plan(service, [])
        self.assertEqual(len(after.groups), 1)
        self.assertEqual(after.groups[0].basis, BASIS_COMPLETE_IDENTITY)

    def test_substituting_the_stored_content_id_dissolves_the_group_on_replan(self) -> None:
        # Complete identity is bound to recorded_at + content_id specifically
        # (see auditlog.integrity.complete_event_identity); those are the
        # two stored columns that must change to break a complete-identity
        # group, unlike duplicate_cohorts (which recomputes the receipt from
        # every identity field, including actor/action/outcome/payload).
        service = self.new_service()
        event = Event.record(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT)
        receipt = self.genuine_receipt(event)
        service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=receipt)
        second = service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=receipt)

        before = build_overlap_plan(service, [])
        self.assertEqual(len(before.groups), 1)

        self._raw_update(service, second.sequence, "content_id", "0" * 64)

        after = build_overlap_plan(service, [])
        self.assertEqual(after.groups, ())


if __name__ == "__main__":
    unittest.main()
