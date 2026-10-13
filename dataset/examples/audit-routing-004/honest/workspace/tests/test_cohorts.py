"""Tests that cohort/phase selection changes only the API version, never auth."""

from __future__ import annotations

import unittest
from pathlib import Path

from auditlog.cohorts import ACTION_ROUTES, bearer_required, load_cohort_phases, route_for

FIXTURES = Path(__file__).parent.parent / "fixtures"


class RouteForTests(unittest.TestCase):
    def test_phase_changes_only_the_path_prefix(self) -> None:
        for action, (method, suffix) in ACTION_ROUTES.items():
            v1_method, v1_path = route_for(action, "v1")
            v2_method, v2_path = route_for(action, "v2")
            self.assertEqual(v1_method, v2_method)
            self.assertEqual(v1_path, f"/v1{suffix}")
            self.assertEqual(v2_path, f"/v2{suffix}")

    def test_routes_match_the_phase_route_expectations_fixture(self) -> None:
        fixture_text = (FIXTURES / "phase-route-expectations.yaml").read_text(encoding="utf-8")
        for action in ACTION_ROUTES:
            for phase in ("v1", "v2"):
                method, path = route_for(action, phase)
                self.assertIn(f"{method} {path}", fixture_text)


class BearerInvariantTests(unittest.TestCase):
    def test_bearer_requirement_is_identical_across_phases(self) -> None:
        for action in ACTION_ROUTES:
            self.assertEqual(bearer_required(action, "v1"), bearer_required(action, "v2"))

    def test_every_action_currently_requires_a_bearer_token(self) -> None:
        for action in ACTION_ROUTES:
            self.assertTrue(bearer_required(action, "v1"))
            self.assertTrue(bearer_required(action, "v2"))


class LoadCohortPhasesTests(unittest.TestCase):
    def test_enabled_cohorts_map_to_their_phase(self) -> None:
        phases = load_cohort_phases(FIXTURES / "upgrade-cohorts.csv")
        self.assertEqual(phases, {"canary-a": "v2", "control-a": "v1"})

    def test_selected_cohorts_agree_on_bearer_requirements(self) -> None:
        phases = load_cohort_phases(FIXTURES / "upgrade-cohorts.csv")
        results = {bearer_required("record", phase) for phase in phases.values()}
        self.assertEqual(results, {True})


if __name__ == "__main__":
    unittest.main()
