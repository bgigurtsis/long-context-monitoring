"""The V2 alias catalog is fixed, offline data -- not yet wired to any route."""

from __future__ import annotations

import unittest

from auditlog.policy import build_v2_alias_catalog


class BuildV2AliasCatalogTests(unittest.TestCase):
    def test_returns_the_three_fixed_rows_with_explicit_bearer_true(self) -> None:
        self.assertEqual(
            build_v2_alias_catalog(),
            (
                ("POST", "/v2/entries", "record", True),
                ("GET", "/v2/entries", "query", True),
                ("GET", "/v2/integrity", "integrity", True),
            ),
        )

    def test_is_a_plain_tuple_not_installed_anywhere(self) -> None:
        catalog = build_v2_alias_catalog()
        self.assertIsInstance(catalog, tuple)
        for row in catalog:
            self.assertIsInstance(row, tuple)
            self.assertEqual(len(row), 4)

    def test_calling_twice_returns_equal_data(self) -> None:
        self.assertEqual(build_v2_alias_catalog(), build_v2_alias_catalog())


if __name__ == "__main__":
    unittest.main()
