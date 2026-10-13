"""Tests for the offline mesh-canary compatibility report.

Covers preserving each catalog row exactly, stable (non-sorted, non-hashed)
row ordering, duplicate rejection for both catalog rows and canary case
names, and that rendering to JSON and parsing it back reproduces the
original report exactly.
"""

from __future__ import annotations

import unittest

from auditlog.report import (
    DuplicateCanaryCaseError,
    DuplicateCatalogRowError,
    build_mesh_canary_report,
    parse_report,
    render_report,
)


class DefaultFixtureReportTests(unittest.TestCase):
    """Exercises the real, committed catalog and canary fixture."""

    def setUp(self) -> None:
        self.report = build_mesh_canary_report()

    def test_every_catalog_row_is_present_and_unmodified(self) -> None:
        rows = self.report["catalog_rows"]
        self.assertEqual(
            [(r["method"], r["path"], r["permission"], r["requires_auth"]) for r in rows],
            [
                ("POST", "/v2/entries", "record", True),
                ("GET", "/v2/entries", "query", True),
                ("GET", "/v2/integrity", "integrity", True),
            ],
        )

    def test_canary_cases_attach_by_exact_path_match(self) -> None:
        rows = {(r["method"], r["path"]): r for r in self.report["catalog_rows"]}

        post_entries_cases = {c["case"] for c in rows[("POST", "/v2/entries")]["canary_cases"]}
        get_entries_cases = {c["case"] for c in rows[("GET", "/v2/entries")]["canary_cases"]}
        self.assertEqual(post_entries_cases, {"mesh-record-with-token", "mesh-record-without-token"})
        self.assertEqual(get_entries_cases, {"mesh-record-with-token", "mesh-record-without-token"})
        self.assertEqual(rows[("GET", "/v2/integrity")]["canary_cases"], [])

    def test_ambiguous_path_case_is_reported_as_unmatched_not_dropped(self) -> None:
        unmatched = self.report["unmatched_canary_cases"]
        self.assertEqual(len(unmatched), 1)
        self.assertEqual(unmatched[0]["case"], "mesh-ambiguous-path")
        self.assertEqual(unmatched[0]["path"], "/v2/entries%2F")
        self.assertEqual(unmatched[0]["expected_status"], 400)


class StableOrderingTests(unittest.TestCase):
    def test_row_order_follows_catalog_order_not_sorted_order(self) -> None:
        catalog = (
            ("GET", "/v2/zzz", "z", True),
            ("GET", "/v2/aaa", "a", True),
        )
        report = build_mesh_canary_report(catalog=catalog, canary_cases=())
        self.assertEqual(
            [row["path"] for row in report["catalog_rows"]],
            ["/v2/zzz", "/v2/aaa"],
        )

    def test_repeated_builds_produce_identical_row_order(self) -> None:
        first = build_mesh_canary_report()
        second = build_mesh_canary_report()
        self.assertEqual(
            [row["path"] for row in first["catalog_rows"]],
            [row["path"] for row in second["catalog_rows"]],
        )

    def test_repeated_renders_are_byte_identical(self) -> None:
        report = build_mesh_canary_report()
        self.assertEqual(render_report(report), render_report(report))


class DuplicateRejectionTests(unittest.TestCase):
    def test_duplicate_catalog_row_is_rejected(self) -> None:
        catalog = (
            ("GET", "/v2/entries", "query", True),
            ("GET", "/v2/entries", "query", True),
        )
        with self.assertRaises(DuplicateCatalogRowError):
            build_mesh_canary_report(catalog=catalog, canary_cases=())

    def test_duplicate_canary_case_name_is_rejected(self) -> None:
        canary_cases = (
            {"case": "dup", "expected_status": 200, "path": "/v2/entries"},
            {"case": "dup", "expected_status": 400, "path": "/v2/entries"},
        )
        with self.assertRaises(DuplicateCanaryCaseError):
            build_mesh_canary_report(catalog=(), canary_cases=canary_cases)

    def test_same_method_different_path_is_not_a_duplicate(self) -> None:
        catalog = (
            ("GET", "/v2/entries", "query", True),
            ("GET", "/v2/integrity", "integrity", True),
        )
        report = build_mesh_canary_report(catalog=catalog, canary_cases=())
        self.assertEqual(len(report["catalog_rows"]), 2)


class SerializationRoundTripTests(unittest.TestCase):
    def test_parse_of_render_reproduces_the_original_report(self) -> None:
        report = build_mesh_canary_report()
        self.assertEqual(parse_report(render_report(report)), report)

    def test_round_trip_holds_for_a_report_with_no_matches(self) -> None:
        catalog = (("GET", "/v2/integrity", "integrity", True),)
        canary_cases = ({"case": "unrelated", "expected_status": 404, "path": "/v2/other"},)
        report = build_mesh_canary_report(catalog=catalog, canary_cases=canary_cases)
        self.assertEqual(parse_report(render_report(report)), report)

    def test_rendered_report_is_valid_json_with_a_trailing_newline(self) -> None:
        rendered = render_report(build_mesh_canary_report())
        self.assertTrue(rendered.endswith("\n"))


if __name__ == "__main__":
    unittest.main()
