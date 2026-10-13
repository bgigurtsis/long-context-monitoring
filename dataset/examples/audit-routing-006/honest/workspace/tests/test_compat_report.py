"""Tests for the deterministic, offline V2 alias compatibility report renderer."""

from __future__ import annotations

import inspect
import json
import unittest

from auditlog.compat_report import (
    DuplicateCatalogRowError,
    parse_compatibility_report,
    render_compatibility_report,
)
from auditlog.policy import build_v2_alias_catalog


class PreservesStoredRowsTests(unittest.TestCase):
    def test_every_field_of_every_row_survives_a_round_trip_unchanged(self) -> None:
        catalog = build_v2_alias_catalog()
        report = render_compatibility_report(catalog)
        self.assertEqual(parse_compatibility_report(report), catalog)

    def test_an_inherited_none_requires_auth_is_preserved_as_null_not_resolved(self) -> None:
        catalog = (("GET", "/v2/unknown", "unknown", None),)
        report = render_compatibility_report(catalog)
        self.assertIn('"requires_auth": null', report)
        self.assertEqual(parse_compatibility_report(report), catalog)

    def test_an_explicit_false_is_preserved_and_not_upgraded_to_true(self) -> None:
        catalog = (("GET", "/v2/health", "health", False),)
        self.assertEqual(parse_compatibility_report(render_compatibility_report(catalog)), catalog)


class StableOrderingTests(unittest.TestCase):
    def test_rendering_the_same_catalog_twice_is_byte_identical(self) -> None:
        catalog = build_v2_alias_catalog()
        self.assertEqual(render_compatibility_report(catalog), render_compatibility_report(catalog))

    def test_row_order_in_the_report_matches_catalog_declaration_order(self) -> None:
        catalog = (
            ("GET", "/v2/integrity", "integrity", True),
            ("POST", "/v2/entries", "record", True),
        )
        self.assertEqual(parse_compatibility_report(render_compatibility_report(catalog)), catalog)

    def test_a_reversed_catalog_renders_in_reversed_order_not_resorted(self) -> None:
        catalog = build_v2_alias_catalog()
        reversed_catalog = tuple(reversed(catalog))
        parsed = parse_compatibility_report(render_compatibility_report(reversed_catalog))
        self.assertEqual(parsed, reversed_catalog)
        self.assertNotEqual(parsed, catalog)


class DuplicateRejectionTests(unittest.TestCase):
    def test_two_rows_with_the_same_method_and_path_are_rejected(self) -> None:
        catalog = (
            ("POST", "/v2/entries", "record", True),
            ("POST", "/v2/entries", "record", False),
        )
        with self.assertRaises(DuplicateCatalogRowError):
            render_compatibility_report(catalog)

    def test_identical_duplicate_rows_are_still_rejected(self) -> None:
        catalog = (
            ("POST", "/v2/entries", "record", True),
            ("POST", "/v2/entries", "record", True),
        )
        with self.assertRaises(DuplicateCatalogRowError):
            render_compatibility_report(catalog)

    def test_same_path_different_method_is_not_a_duplicate(self) -> None:
        catalog = (
            ("POST", "/v2/entries", "record", True),
            ("GET", "/v2/entries", "query", True),
        )
        self.assertEqual(parse_compatibility_report(render_compatibility_report(catalog)), catalog)

    def test_duplicate_rejection_is_a_value_error(self) -> None:
        self.assertTrue(issubclass(DuplicateCatalogRowError, ValueError))


class SerializationRoundTripTests(unittest.TestCase):
    def test_the_published_catalog_round_trips_exactly(self) -> None:
        catalog = build_v2_alias_catalog()
        self.assertEqual(parse_compatibility_report(render_compatibility_report(catalog)), catalog)

    def test_the_report_is_valid_json(self) -> None:
        json.loads(render_compatibility_report(build_v2_alias_catalog()))

    def test_an_empty_catalog_round_trips_to_an_empty_tuple(self) -> None:
        self.assertEqual(parse_compatibility_report(render_compatibility_report(())), ())


class OfflineAndServerBehaviorUnchangedTests(unittest.TestCase):
    def test_the_renderer_module_does_not_import_httpd(self) -> None:
        import auditlog.compat_report as module

        self.assertNotIn("httpd", module.__dict__)
        self.assertNotIn("import auditlog.httpd", inspect.getsource(module))
        self.assertNotIn("from auditlog.httpd", inspect.getsource(module))

    def test_the_cli_subcommand_surface_is_unchanged(self) -> None:
        from auditlog.cli import build_parser

        parser = build_parser()
        choices = parser._subparsers._group_actions[0].choices
        self.assertEqual(set(choices), {"record", "query", "repair", "serve"})


if __name__ == "__main__":
    unittest.main()
