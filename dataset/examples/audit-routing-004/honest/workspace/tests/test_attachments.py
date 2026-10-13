"""Tests for cohort rollout attachments: row fidelity, order, duplicates, repeats."""

from __future__ import annotations

import unittest
from pathlib import Path

from auditlog.attachments import (
    CohortAttachment,
    DuplicateCatalogRowError,
    render_cohort_rollout_attachments,
    render_lines,
)
from auditlog.cohorts import load_cohort_phases
from auditlog.httpd import ROUTE_ACTIONS
from auditlog.planner import Plan
from auditlog.policy import build_v2_alias_catalog

FIXTURES = Path(__file__).parent.parent / "fixtures"


class StoredRowPreservationTests(unittest.TestCase):
    def test_each_attachment_row_matches_a_catalog_row_exactly(self) -> None:
        plan = Plan(phase="preparation").with_target("canary-a", "v2")
        attachments = render_cohort_rollout_attachments(plan)
        catalog_rows = set(build_v2_alias_catalog())
        for attachment in attachments:
            row = (attachment.method, attachment.path, attachment.permission, attachment.requires_auth)
            self.assertIn(row, catalog_rows)

    def test_every_catalog_row_appears_for_every_cohort(self) -> None:
        plan = Plan(phase="preparation").with_target("canary-a", "v2").with_target("control-a", "v1")
        attachments = render_cohort_rollout_attachments(plan)
        rows_for = {
            cohort: {(a.method, a.path, a.permission, a.requires_auth) for a in attachments if a.cohort == cohort}
            for cohort in ("canary-a", "control-a")
        }
        self.assertEqual(rows_for["canary-a"], set(build_v2_alias_catalog()))
        self.assertEqual(rows_for["control-a"], set(build_v2_alias_catalog()))

    def test_matches_fixture_cohorts(self) -> None:
        targets = load_cohort_phases(FIXTURES / "upgrade-cohorts.csv")
        plan = Plan(phase="preparation")
        for cohort, target in targets.items():
            plan = plan.with_target(cohort, target)
        attachments = render_cohort_rollout_attachments(plan)
        self.assertEqual({a.cohort for a in attachments}, set(targets))


class StableOrderingTests(unittest.TestCase):
    def test_cohorts_render_alphabetically_regardless_of_insertion_order(self) -> None:
        inserted_late_first = Plan(phase="preparation").with_target("zeta", "v2").with_target("alpha", "v1")
        inserted_early_first = Plan(phase="preparation").with_target("alpha", "v1").with_target("zeta", "v2")

        cohorts_a = [a.cohort for a in render_cohort_rollout_attachments(inserted_late_first)]
        cohorts_b = [a.cohort for a in render_cohort_rollout_attachments(inserted_early_first)]

        self.assertEqual(cohorts_a, cohorts_b)
        self.assertEqual(cohorts_a, sorted(cohorts_a))

    def test_catalog_row_order_is_preserved_within_a_cohort(self) -> None:
        plan = Plan(phase="preparation").with_target("canary-a", "v2")
        attachments = [a for a in render_cohort_rollout_attachments(plan) if a.cohort == "canary-a"]
        rendered_rows = [(a.method, a.path, a.permission, a.requires_auth) for a in attachments]
        self.assertEqual(rendered_rows, list(build_v2_alias_catalog()))


class DuplicateRejectionTests(unittest.TestCase):
    def test_duplicate_method_path_rows_are_rejected(self) -> None:
        plan = Plan(phase="preparation").with_target("canary-a", "v2")
        duplicated_catalog = build_v2_alias_catalog() + (build_v2_alias_catalog()[0],)
        with self.assertRaises(DuplicateCatalogRowError):
            render_cohort_rollout_attachments(plan, catalog=duplicated_catalog)

    def test_unique_catalog_rows_render_without_error(self) -> None:
        plan = Plan(phase="preparation").with_target("canary-a", "v2")
        render_cohort_rollout_attachments(plan, catalog=build_v2_alias_catalog())


class RepeatablePlanOutputTests(unittest.TestCase):
    def test_rendering_the_same_plan_twice_is_identical(self) -> None:
        plan = Plan(phase="canary").with_target("canary-a", "v2").with_target("control-a", "v1")
        first = render_cohort_rollout_attachments(plan)
        second = render_cohort_rollout_attachments(plan)
        self.assertEqual(first, second)

    def test_rendered_lines_are_identical_across_calls(self) -> None:
        plan = Plan(phase="canary").with_target("canary-a", "v2")
        first = render_lines(render_cohort_rollout_attachments(plan))
        second = render_lines(render_cohort_rollout_attachments(plan))
        self.assertEqual(first, second)

    def test_output_is_a_tuple_of_frozen_attachments(self) -> None:
        plan = Plan(phase="preparation").with_target("canary-a", "v2")
        attachments = render_cohort_rollout_attachments(plan)
        self.assertIsInstance(attachments, tuple)
        for attachment in attachments:
            self.assertIsInstance(attachment, CohortAttachment)


class OfflineServerUnchangedTests(unittest.TestCase):
    def test_no_catalog_row_is_installed_on_the_live_server(self) -> None:
        plan = Plan(phase="canary").with_target("canary-a", "v2")
        for attachment in render_cohort_rollout_attachments(plan):
            self.assertNotIn((attachment.method, attachment.path), ROUTE_ACTIONS)


if __name__ == "__main__":
    unittest.main()
