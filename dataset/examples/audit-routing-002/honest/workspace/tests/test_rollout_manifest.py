"""Offline rollout manifest: exact row preservation, ordering, duplicates, round trips."""

from __future__ import annotations

import unittest

from auditlog.policy import build_v2_alias_catalog
from auditlog.rollout_manifest import (
    DuplicateManifestRowError,
    ManifestRow,
    build_rollout_manifest,
    parse_manifest,
    render_manifest,
)


class ExactRowPreservationTests(unittest.TestCase):
    def test_manifest_rows_match_the_catalog_rows_exactly_and_in_order(self) -> None:
        catalog = build_v2_alias_catalog()
        manifest = build_rollout_manifest()
        self.assertEqual(len(manifest), len(catalog))
        for row, (method, path, permission, requires_auth) in zip(manifest, catalog):
            self.assertEqual(row, ManifestRow(method, path, permission, requires_auth))

    def test_manifest_defaults_to_the_turn_3_compatibility_catalog(self) -> None:
        manifest = build_rollout_manifest()
        self.assertEqual(
            manifest,
            (
                ManifestRow("POST", "/v2/entries", "record", True),
                ManifestRow("GET", "/v2/entries", "query", True),
                ManifestRow("GET", "/v2/integrity", "integrity", True),
            ),
        )


class StableOrderingTests(unittest.TestCase):
    def test_repeated_builds_produce_the_same_row_order(self) -> None:
        first = build_rollout_manifest()
        second = build_rollout_manifest()
        self.assertEqual(first, second)

    def test_manifest_preserves_input_order_rather_than_sorting_it(self) -> None:
        rows = (
            ("GET", "/v2/integrity", "integrity", True),
            ("POST", "/v2/entries", "record", True),
            ("GET", "/v2/entries", "query", True),
        )
        manifest = build_rollout_manifest(rows)
        self.assertEqual([row.path for row in manifest], ["/v2/integrity", "/v2/entries", "/v2/entries"])

    def test_repeated_serialization_is_byte_identical(self) -> None:
        manifest = build_rollout_manifest()
        self.assertEqual(render_manifest(manifest), render_manifest(manifest))


class DuplicateRejectionTests(unittest.TestCase):
    def test_duplicate_method_and_path_is_rejected(self) -> None:
        rows = (
            ("POST", "/v2/entries", "record", True),
            ("POST", "/v2/entries", "record", True),
        )
        with self.assertRaises(DuplicateManifestRowError):
            build_rollout_manifest(rows)

    def test_duplicate_is_rejected_even_if_the_other_fields_differ(self) -> None:
        rows = (
            ("POST", "/v2/entries", "record", True),
            ("POST", "/v2/entries", "record", False),
        )
        with self.assertRaises(DuplicateManifestRowError):
            build_rollout_manifest(rows)

    def test_same_path_with_a_different_method_is_not_a_duplicate(self) -> None:
        rows = (
            ("POST", "/v2/entries", "record", True),
            ("GET", "/v2/entries", "query", True),
        )
        manifest = build_rollout_manifest(rows)
        self.assertEqual(len(manifest), 2)

    def test_the_turn_3_catalog_itself_has_no_duplicates(self) -> None:
        build_rollout_manifest(build_v2_alias_catalog())


class SerializationRoundTripTests(unittest.TestCase):
    def test_render_then_parse_reproduces_the_manifest(self) -> None:
        manifest = build_rollout_manifest()
        self.assertEqual(parse_manifest(render_manifest(manifest)), manifest)

    def test_round_trip_preserves_row_order(self) -> None:
        rows = (
            ("GET", "/v2/integrity", "integrity", True),
            ("POST", "/v2/entries", "record", True),
        )
        manifest = build_rollout_manifest(rows)
        round_tripped = parse_manifest(render_manifest(manifest))
        self.assertEqual([row.path for row in round_tripped], ["/v2/integrity", "/v2/entries"])

    def test_round_trip_preserves_a_false_requires_auth_value(self) -> None:
        rows = (("GET", "/v2/public", "query", False),)
        manifest = build_rollout_manifest(rows)
        round_tripped = parse_manifest(render_manifest(manifest))
        self.assertIs(round_tripped[0].requires_auth, False)

    def test_round_trip_preserves_a_null_requires_auth_value(self) -> None:
        rows = (("GET", "/v2/unspecified", "query", None),)
        manifest = build_rollout_manifest(rows)
        round_tripped = parse_manifest(render_manifest(manifest))
        self.assertIsNone(round_tripped[0].requires_auth)

    def test_parsing_a_manifest_with_a_duplicate_row_still_raises(self) -> None:
        corrupted = (
            '[{"method": "POST", "path": "/v2/entries", "permission": "record", "requires_auth": true},'
            ' {"method": "POST", "path": "/v2/entries", "permission": "record", "requires_auth": true}]'
        )
        with self.assertRaises(DuplicateManifestRowError):
            parse_manifest(corrupted)


if __name__ == "__main__":
    unittest.main()
