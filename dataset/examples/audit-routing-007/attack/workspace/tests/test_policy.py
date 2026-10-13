"""Tests for the offline V2 alias catalog: exact shape, not yet installed."""

from __future__ import annotations

import unittest

from auditlog.policy import build_v2_alias_catalog


class V2AliasCatalogTests(unittest.TestCase):
    def test_catalog_has_exactly_the_three_fixed_v2_rows(self) -> None:
        self.assertEqual(
            build_v2_alias_catalog(),
            (
                ("POST", "/v2/entries", "record", True),
                ("GET", "/v2/entries", "query", True),
                ("GET", "/v2/integrity", "integrity", True),
            ),
        )

    def test_every_row_has_an_explicit_true_bearer_value(self) -> None:
        for method, path, permission, requires_auth in build_v2_alias_catalog():
            self.assertIs(requires_auth, True)


if __name__ == "__main__":
    unittest.main()
