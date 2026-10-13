"""Tests for the offline V2 alias catalog."""

from __future__ import annotations

import unittest

from auditlog.policy import build_v2_alias_catalog


class BuildV2AliasCatalogTests(unittest.TestCase):
    def test_returns_the_three_fixed_rows(self) -> None:
        catalog = build_v2_alias_catalog()
        self.assertEqual(
            catalog,
            (
                ("POST", "/v2/entries", "record", True),
                ("GET", "/v2/entries", "query", True),
                ("GET", "/v2/integrity", "integrity", True),
            ),
        )

    def test_bearer_requirement_is_explicit_true_not_inherited(self) -> None:
        for _method, _path, _permission, requires_auth in build_v2_alias_catalog():
            self.assertIs(requires_auth, True)


if __name__ == "__main__":
    unittest.main()
