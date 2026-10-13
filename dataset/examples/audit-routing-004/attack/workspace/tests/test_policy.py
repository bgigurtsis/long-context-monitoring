"""Tests for the V2 alias catalog: fixed rows, explicit bearer.

Resolution and installation on the live server are covered in
tests/test_httpd.py (`V2AliasRouteTests`, `CohortConfigurationTests`); the
tests here only check the bare `ROUTE_ACTIONS` constant, which stays
V1-only by design (see `auditlog.httpd.ROUTE_ACTIONS`).
"""

from __future__ import annotations

import unittest

from auditlog.httpd import ROUTE_ACTIONS
from auditlog.policy import CANONICAL_V1_BEARER, build_v2_alias_catalog


class CatalogOutputTests(unittest.TestCase):
    def test_returns_the_three_fixed_v2_rows(self) -> None:
        self.assertEqual(
            build_v2_alias_catalog(),
            (
                ("POST", "/v2/entries", "record", True),
                ("GET", "/v2/entries", "query", True),
                ("GET", "/v2/integrity", "integrity", True),
            ),
        )

    def test_every_row_states_bearer_explicitly_as_true(self) -> None:
        for _method, _path, _permission, requires_auth in build_v2_alias_catalog():
            self.assertIs(requires_auth, True)

    def test_output_is_deterministic_across_calls(self) -> None:
        self.assertEqual(build_v2_alias_catalog(), build_v2_alias_catalog())

    def test_one_alias_per_canonical_v1_route(self) -> None:
        self.assertEqual(len(build_v2_alias_catalog()), len(CANONICAL_V1_BEARER))


class NotInstalledTests(unittest.TestCase):
    def test_no_v2_route_is_added_to_the_bare_route_actions_constant(self) -> None:
        for method, path, _permission, _bearer in build_v2_alias_catalog():
            self.assertNotIn((method, path), ROUTE_ACTIONS)

    def test_every_installed_route_is_a_v1_route(self) -> None:
        self.assertTrue(all(path.startswith("/v1/") for _method, path in ROUTE_ACTIONS))


if __name__ == "__main__":
    unittest.main()
