"""Tests for the phase planner: stable assignment, transitions, and conflicts."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from auditlog.cohorts import load_cohort_phases
from auditlog.planner import (
    PHASES,
    InvalidTransitionError,
    OptimisticConflictError,
    Plan,
    PlannedChange,
    load_plan,
    save_plan,
)

FIXTURES = Path(__file__).parent.parent / "fixtures"


class StableCohortAssignmentTests(unittest.TestCase):
    def test_every_cohort_is_pinned_to_v1_in_preparation(self) -> None:
        plan = Plan(phase="preparation").with_target("canary-a", "v2").with_target("control-a", "v1")
        self.assertEqual(plan.assignments(), {"canary-a": "v1", "control-a": "v1"})

    def test_every_cohort_is_pinned_to_v1_in_canary(self) -> None:
        plan = Plan(phase="canary").with_target("canary-a", "v2").with_target("control-a", "v1")
        self.assertEqual(plan.assignments(), {"canary-a": "v1", "control-a": "v1"})

    def test_assignment_is_stable_across_repeated_calls(self) -> None:
        plan = Plan(phase="canary").with_target("canary-a", "v2")
        first = plan.assignment_for("canary-a")
        for _ in range(5):
            self.assertEqual(plan.assignment_for("canary-a"), first)

    def test_pinned_assignment_matches_fixture_cohorts_regardless_of_target(self) -> None:
        targets = load_cohort_phases(FIXTURES / "upgrade-cohorts.csv")
        plan = Plan(phase="preparation")
        for cohort, target in targets.items():
            plan = plan.with_target(cohort, target)
        self.assertEqual(plan.assignments(), {cohort: "v1" for cohort in targets})

    def test_unassigned_cohort_defaults_to_v1(self) -> None:
        plan = Plan(phase="preparation")
        self.assertEqual(plan.assignment_for("unlisted-cohort"), "v1")


class InvalidTransitionTests(unittest.TestCase):
    def test_moving_forward_one_step_is_valid(self) -> None:
        plan = Plan(phase="preparation").advance("canary")
        self.assertEqual(plan.phase, "canary")

    def test_moving_backward_is_invalid(self) -> None:
        plan = Plan(phase="canary")
        with self.assertRaises(InvalidTransitionError):
            plan.advance("preparation")

    def test_staying_in_the_same_phase_is_invalid(self) -> None:
        with self.assertRaises(InvalidTransitionError):
            Plan(phase="preparation").advance("preparation")
        with self.assertRaises(InvalidTransitionError):
            Plan(phase="canary").advance("canary")

    def test_unknown_phase_name_is_invalid(self) -> None:
        with self.assertRaises(InvalidTransitionError):
            Plan(phase="preparation").advance("rollout")

    def test_unknown_phase_at_construction_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Plan(phase="rollout")

    def test_unknown_route_version_target_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            Plan(phase="preparation").with_target("canary-a", "v3")


class RollbackTransitionTests(unittest.TestCase):
    def test_moving_backward_one_step_is_valid(self) -> None:
        plan = Plan(phase="canary").rollback("preparation")
        self.assertEqual(plan.phase, "preparation")

    def test_moving_forward_via_rollback_is_invalid(self) -> None:
        plan = Plan(phase="preparation")
        with self.assertRaises(InvalidTransitionError):
            plan.rollback("canary")

    def test_staying_in_the_same_phase_via_rollback_is_invalid(self) -> None:
        with self.assertRaises(InvalidTransitionError):
            Plan(phase="preparation").rollback("preparation")
        with self.assertRaises(InvalidTransitionError):
            Plan(phase="canary").rollback("canary")

    def test_unknown_phase_name_via_rollback_is_invalid(self) -> None:
        with self.assertRaises(InvalidTransitionError):
            Plan(phase="canary").rollback("rollout")

    def test_rollback_then_advance_round_trips(self) -> None:
        plan = Plan(phase="preparation").advance("canary").rollback("preparation")
        self.assertEqual(plan.phase, "preparation")


class DryRunChangesTests(unittest.TestCase):
    def test_dry_run_lists_cohorts_whose_target_differs_from_current(self) -> None:
        plan = Plan(phase="canary").with_target("canary-a", "v2").with_target("control-a", "v1")
        self.assertEqual(
            plan.dry_run_changes(),
            [PlannedChange(cohort="canary-a", current="v1", target="v2")],
        )

    def test_dry_run_omits_cohorts_already_matching_their_target(self) -> None:
        plan = Plan(phase="preparation").with_target("control-a", "v1")
        self.assertEqual(plan.dry_run_changes(), [])

    def test_dry_run_never_mutates_the_plan(self) -> None:
        plan = Plan(phase="canary").with_target("canary-a", "v2")
        plan.dry_run_changes()
        self.assertEqual(plan.assignments(), {"canary-a": "v1"})


class PersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp_dir)
        self.path = self.tmp_dir / "plan.json"

    def test_missing_file_loads_a_fresh_preparation_phase_plan(self) -> None:
        plan = load_plan(self.path)
        self.assertEqual(plan.phase, PHASES[0])
        self.assertEqual(plan.cohort_targets, {})
        self.assertEqual(plan.revision, 0)

    def test_save_then_load_round_trips(self) -> None:
        plan = Plan(phase="preparation").with_target("canary-a", "v2")
        saved = save_plan(self.path, plan, expected_revision=0)
        reloaded = load_plan(self.path)
        self.assertEqual(reloaded.phase, "preparation")
        self.assertEqual(reloaded.cohort_targets, {"canary-a": "v2"})
        self.assertEqual(reloaded.revision, saved.revision)

    def test_save_bumps_the_revision(self) -> None:
        plan = Plan(phase="preparation")
        saved = save_plan(self.path, plan, expected_revision=0)
        self.assertEqual(saved.revision, 1)

    def test_persisted_file_never_contains_a_token_field(self) -> None:
        plan = Plan(phase="preparation").with_target("canary-a", "v2")
        save_plan(self.path, plan, expected_revision=0)
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(set(payload.keys()), {"phase", "cohort_targets", "revision"})
        raw_text = self.path.read_text(encoding="utf-8").lower()
        self.assertNotIn("token", raw_text)
        self.assertNotIn("bearer", raw_text)


class OptimisticConflictTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp_dir)
        self.path = self.tmp_dir / "plan.json"

    def test_stale_expected_revision_is_rejected(self) -> None:
        plan = Plan(phase="preparation")
        save_plan(self.path, plan, expected_revision=0)  # stored revision is now 1

        with self.assertRaises(OptimisticConflictError):
            save_plan(self.path, plan, expected_revision=0)

    def test_matching_expected_revision_succeeds_and_advances(self) -> None:
        plan = Plan(phase="preparation")
        first = save_plan(self.path, plan, expected_revision=0)
        second = save_plan(self.path, first.advance("canary"), expected_revision=first.revision)
        self.assertEqual(second.phase, "canary")
        self.assertEqual(second.revision, 2)

    def test_two_readers_racing_from_the_same_revision_only_one_wins(self) -> None:
        base = save_plan(self.path, Plan(phase="preparation"), expected_revision=0)

        reader_a = base.with_target("canary-a", "v2")
        reader_b = base.with_target("control-a", "v1")

        save_plan(self.path, reader_a, expected_revision=base.revision)
        with self.assertRaises(OptimisticConflictError):
            save_plan(self.path, reader_b, expected_revision=base.revision)

        winner = load_plan(self.path)
        self.assertEqual(winner.cohort_targets, {"canary-a": "v2"})


if __name__ == "__main__":
    unittest.main()
