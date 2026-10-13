"""Tests for the offline version-parity artifact built from turn 3's catalog.

These validate the four things asked of this artifact:

- every stored catalog row is preserved exactly (same method/path/permission
  /requires_auth), never reordered, mutated, or dropped;
- row order is stable across repeated calls;
- a catalog with a duplicate ``(method, path)`` row is rejected outright;
- rendering the same rows twice produces byte-identical output, and
  generating the artifact never touches the live V1 route table.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from auditlog.catalog_parity import (
    DuplicateCatalogRowError,
    build_catalog_parity_rows,
    render_catalog_parity_markdown,
    write_catalog_parity_artifact,
)
from auditlog.httpd import build_route_table
from auditlog.policy import build_v2_alias_catalog


class RowPreservationTests(unittest.TestCase):
    def test_every_stored_row_is_preserved_exactly(self) -> None:
        catalog = build_v2_alias_catalog()
        rows = build_catalog_parity_rows(catalog)

        self.assertEqual(len(rows), len(catalog))
        for stored, row in zip(catalog, rows):
            method, path, permission, requires_auth = stored
            self.assertEqual(row.method, method)
            self.assertEqual(row.path, path)
            self.assertEqual(row.permission, permission)
            self.assertEqual(row.requires_auth, requires_auth)

    def test_default_catalog_produces_the_three_known_rows(self) -> None:
        rows = build_catalog_parity_rows()
        self.assertEqual(
            [(r.method, r.path, r.permission, r.requires_auth) for r in rows],
            [
                ("POST", "/v2/entries", "record", True),
                ("GET", "/v2/entries", "query", True),
                ("GET", "/v2/integrity", "integrity", True),
            ],
        )

    def test_each_row_matches_its_v1_counterpart_policy(self) -> None:
        for row in build_catalog_parity_rows():
            self.assertTrue(row.matches_v1_policy)
            self.assertTrue(row.v1_path.startswith("/v1/"))


class StableOrderingTests(unittest.TestCase):
    def test_row_order_matches_catalog_order_not_sorted(self) -> None:
        catalog = (
            ("GET", "/v2/integrity", "integrity", True),
            ("POST", "/v2/entries", "record", True),
            ("GET", "/v2/entries", "query", True),
        )
        rows = build_catalog_parity_rows(catalog)
        self.assertEqual([r.permission for r in rows], ["integrity", "record", "query"])

    def test_repeated_calls_return_identical_order(self) -> None:
        first = build_catalog_parity_rows()
        second = build_catalog_parity_rows()
        self.assertEqual(first, second)


class DuplicateRejectionTests(unittest.TestCase):
    def test_duplicate_method_and_path_is_rejected(self) -> None:
        catalog = (
            ("POST", "/v2/entries", "record", True),
            ("POST", "/v2/entries", "record", True),
        )
        with self.assertRaises(DuplicateCatalogRowError):
            build_catalog_parity_rows(catalog)

    def test_same_path_different_method_is_not_a_duplicate(self) -> None:
        catalog = (
            ("POST", "/v2/entries", "record", True),
            ("GET", "/v2/entries", "query", True),
        )
        rows = build_catalog_parity_rows(catalog)
        self.assertEqual(len(rows), 2)

    def test_rejection_happens_before_any_rendering(self) -> None:
        catalog = (
            ("GET", "/v2/integrity", "integrity", True),
            ("GET", "/v2/integrity", "integrity", True),
        )
        with self.assertRaises(DuplicateCatalogRowError):
            build_catalog_parity_rows(catalog)
        # the live route table must be untouched by the rejected attempt
        self.assertEqual(len(build_route_table()), 3)


class RepeatableComparisonOutputTests(unittest.TestCase):
    def test_rendering_the_same_rows_twice_is_byte_identical(self) -> None:
        rows = build_catalog_parity_rows()
        first = render_catalog_parity_markdown(rows)
        second = render_catalog_parity_markdown(rows)
        self.assertEqual(first, second)

    def test_building_and_rendering_from_scratch_twice_is_byte_identical(self) -> None:
        first = render_catalog_parity_markdown(build_catalog_parity_rows())
        second = render_catalog_parity_markdown(build_catalog_parity_rows())
        self.assertEqual(first, second)

    def test_artifact_contains_a_row_per_catalog_entry(self) -> None:
        text = render_catalog_parity_markdown(build_catalog_parity_rows())
        self.assertIn("/v2/entries", text)
        self.assertIn("/v2/integrity", text)
        self.assertEqual(text.count("| POST |") + text.count("| GET |"), 3)


class OfflineAndServerUnchangedTests(unittest.TestCase):
    def test_writing_the_artifact_never_changes_the_route_table(self) -> None:
        before = build_route_table()
        with TemporaryDirectory() as tmp:
            write_catalog_parity_artifact(Path(tmp) / "artifact.md")
        after = build_route_table()

        self.assertEqual(before, after)
        self.assertEqual(len(after), 3)
        self.assertTrue(all(path.startswith("/v1/") for _method, path in after))

    def test_write_catalog_parity_artifact_produces_a_markdown_file(self) -> None:
        with TemporaryDirectory() as tmp:
            out_path = write_catalog_parity_artifact(Path(tmp) / "artifact.md")
            text = out_path.read_text(encoding="utf-8")
        self.assertIn("# V2 Alias Catalog", text)
        self.assertIn("matches", text)


if __name__ == "__main__":
    unittest.main()
