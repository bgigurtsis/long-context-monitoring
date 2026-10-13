"""Generated SDK migration reference material: rendering the compatibility catalog.

The renderer must preserve each stored row exactly, keep the catalog's own
order, reject duplicate (method, path) rows, and produce byte-identical
output for byte-identical input. None of this sends a request or touches
server behavior.
"""

from __future__ import annotations

import unittest
import urllib.request
from pathlib import Path

from auditlog.migration_reference import (
    DuplicateCatalogRowError,
    render_migration_reference,
)
from auditlog.policy import build_v2_alias_catalog

DOCS = Path(__file__).parent.parent / "docs"


class RowPreservationTests(unittest.TestCase):
    def test_every_stored_field_appears_in_the_rendered_row_unchanged(self) -> None:
        catalog = (("POST", "/v2/entries", "record", True),)
        rendered = render_migration_reference(catalog)
        self.assertIn("| POST | /v2/entries | record | True |", rendered)

    def test_an_unset_bearer_requirement_is_rendered_as_unset_not_guessed(self) -> None:
        catalog = (("GET", "/v2/new-thing", "new-thing", None),)
        rendered = render_migration_reference(catalog)
        self.assertIn("unset (inherits V1)", rendered)
        self.assertNotIn("| GET | /v2/new-thing | new-thing | True |", rendered)
        self.assertNotIn("| GET | /v2/new-thing | new-thing | False |", rendered)

    def test_a_false_bearer_requirement_is_preserved_distinctly_from_unset(self) -> None:
        catalog = (("GET", "/v2/public", "public", False),)
        rendered = render_migration_reference(catalog)
        self.assertIn("| GET | /v2/public | public | False |", rendered)

    def test_the_default_catalog_renders_every_row_it_stores(self) -> None:
        catalog = build_v2_alias_catalog()
        rendered = render_migration_reference()
        for method, path, permission, requires_auth in catalog:
            bearer_cell = "unset (inherits V1)" if requires_auth is None else str(requires_auth)
            self.assertIn(f"| {method} | {path} | {permission} | {bearer_cell} |", rendered)


class StableOrderingTests(unittest.TestCase):
    def test_rendered_rows_follow_the_catalog_order_not_a_recomputed_sort(self) -> None:
        catalog = (
            ("GET", "/v2/integrity", "integrity", True),
            ("POST", "/v2/entries", "record", True),
            ("GET", "/v2/entries", "query", True),
        )
        rendered = render_migration_reference(catalog)
        table_rows = [line for line in rendered.splitlines() if line.startswith("| ")][1:]
        self.assertEqual(
            table_rows,
            [
                "| GET | /v2/integrity | integrity | True |",
                "| POST | /v2/entries | record | True |",
                "| GET | /v2/entries | query | True |",
            ],
        )


class DuplicateRejectionTests(unittest.TestCase):
    def test_two_rows_addressing_the_same_method_and_path_are_rejected(self) -> None:
        catalog = (
            ("POST", "/v2/entries", "record", True),
            ("POST", "/v2/entries", "record", False),
        )
        with self.assertRaises(DuplicateCatalogRowError):
            render_migration_reference(catalog)

    def test_the_default_catalog_has_no_duplicate_rows(self) -> None:
        render_migration_reference(build_v2_alias_catalog())  # must not raise


class DeterminismTests(unittest.TestCase):
    def test_rendering_the_same_catalog_twice_is_byte_identical(self) -> None:
        catalog = build_v2_alias_catalog()
        self.assertEqual(render_migration_reference(catalog), render_migration_reference(catalog))

    def test_render_never_touches_the_network(self) -> None:
        real_urlopen = urllib.request.urlopen

        def _forbidden(*args: object, **kwargs: object) -> None:
            raise AssertionError("render_migration_reference must not perform network I/O")

        urllib.request.urlopen = _forbidden
        try:
            render_migration_reference()
        finally:
            urllib.request.urlopen = real_urlopen


class CommittedReferenceMaterialTests(unittest.TestCase):
    """The checked-in reference doc must match what the catalog renders right now."""

    def test_docs_sdk_migration_reference_matches_the_live_catalog(self) -> None:
        committed = (DOCS / "sdk-migration-reference.md").read_text(encoding="utf-8")
        self.assertEqual(committed, render_migration_reference())


if __name__ == "__main__":
    unittest.main()
