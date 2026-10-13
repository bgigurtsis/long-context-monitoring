"""Tests for the offline partner conformance report."""

from __future__ import annotations

import unittest

from auditlog.conformance import (
    ConformanceRow,
    DuplicateCatalogRowError,
    deserialize_conformance_report,
    render_conformance_report,
    serialize_conformance_report,
)
from auditlog.policy import build_v2_alias_catalog


class PreservesStoredRowsExactlyTests(unittest.TestCase):
    def test_rendered_rows_match_the_catalog_fields_exactly(self) -> None:
        catalog = build_v2_alias_catalog()
        rows = render_conformance_report(catalog)
        self.assertEqual(len(rows), len(catalog))
        for row, (method, path, permission, requires_auth) in zip(rows, catalog):
            self.assertEqual(row.method, method)
            self.assertEqual(row.path, path)
            self.assertEqual(row.permission, permission)
            self.assertEqual(row.requires_auth, requires_auth)

    def test_rendering_does_not_mutate_the_source_catalog(self) -> None:
        catalog = build_v2_alias_catalog()
        before = tuple(catalog)
        render_conformance_report(catalog)
        self.assertEqual(catalog, before)


class StableOrderingTests(unittest.TestCase):
    def test_row_order_matches_catalog_order(self) -> None:
        catalog = build_v2_alias_catalog()
        rows = render_conformance_report(catalog)
        self.assertEqual(
            [(row.method, row.path) for row in rows],
            [(method, path) for method, path, _permission, _requires_auth in catalog],
        )

    def test_repeated_renders_of_the_same_catalog_agree(self) -> None:
        catalog = build_v2_alias_catalog()
        first = render_conformance_report(catalog)
        second = render_conformance_report(catalog)
        self.assertEqual(first, second)

    def test_reordering_the_catalog_reorders_the_report(self) -> None:
        catalog = (
            ("GET", "/v2/integrity", "integrity", True),
            ("POST", "/v2/entries", "record", True),
        )
        rows = render_conformance_report(catalog)
        self.assertEqual(rows[0].path, "/v2/integrity")
        self.assertEqual(rows[1].path, "/v2/entries")


class DuplicateRejectionTests(unittest.TestCase):
    def test_conflicting_duplicate_route_is_rejected(self) -> None:
        catalog = (
            ("POST", "/v2/entries", "record", True),
            ("POST", "/v2/entries", "record", False),
        )
        with self.assertRaises(DuplicateCatalogRowError):
            render_conformance_report(catalog)

    def test_identical_duplicate_row_is_also_rejected(self) -> None:
        catalog = (
            ("GET", "/v2/integrity", "integrity", True),
            ("GET", "/v2/integrity", "integrity", True),
        )
        with self.assertRaises(DuplicateCatalogRowError):
            render_conformance_report(catalog)

    def test_same_path_different_method_is_not_a_duplicate(self) -> None:
        catalog = (
            ("POST", "/v2/entries", "record", True),
            ("GET", "/v2/entries", "query", True),
        )
        rows = render_conformance_report(catalog)
        self.assertEqual(len(rows), 2)


class SerializationRoundTripTests(unittest.TestCase):
    def test_round_trip_preserves_rows(self) -> None:
        rows = render_conformance_report(build_v2_alias_catalog())
        serialized = serialize_conformance_report(rows)
        self.assertEqual(deserialize_conformance_report(serialized), rows)

    def test_serialization_is_deterministic(self) -> None:
        rows = render_conformance_report(build_v2_alias_catalog())
        self.assertEqual(
            serialize_conformance_report(rows), serialize_conformance_report(rows)
        )

    def test_deserialized_rows_are_conformance_rows(self) -> None:
        rows = render_conformance_report(build_v2_alias_catalog())
        serialized = serialize_conformance_report(rows)
        for row in deserialize_conformance_report(serialized):
            self.assertIsInstance(row, ConformanceRow)


if __name__ == "__main__":
    unittest.main()
