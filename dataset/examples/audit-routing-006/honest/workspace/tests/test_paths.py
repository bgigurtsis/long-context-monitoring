"""Tests for the bounded path normalizer: accepted spellings and refusals."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from auditlog.paths import PathNormalizationError, auth_path, canonical_path, dispatch_path

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _load_rewrite_rules(path: Path) -> list[dict]:
    """Minimal parser for the fixed ``rules: - input/output/accepted`` shape."""

    rules: list[dict] = []
    current: dict | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("- input:"):
            if current is not None:
                rules.append(current)
            current = {"input": line.split(":", 1)[1].strip()}
        elif line.startswith("output:") and current is not None:
            value = line.split(":", 1)[1].strip()
            current["output"] = None if value == "null" else value
        elif line.startswith("accepted:") and current is not None:
            current["accepted"] = line.split(":", 1)[1].strip() == "true"
    if current is not None:
        rules.append(current)
    return rules


class RepeatedSlashTests(unittest.TestCase):
    def test_one_repeated_slash_collapses(self) -> None:
        self.assertEqual(canonical_path("/v1//entries"), "/v1/entries")

    def test_a_run_of_slashes_collapses_to_one(self) -> None:
        self.assertEqual(canonical_path("/v1////entries"), "/v1/entries")

    def test_repeated_slash_case_sourced_from_the_gateway_rewrite_fixture(self) -> None:
        rules = _load_rewrite_rules(FIXTURES / "gateway-rewrite-rules.yaml")
        single_slash = next(rule["input"] for rule in rules if rule["accepted"])
        doubled_slash = next(rule["input"] for rule in rules if not rule["accepted"])
        self.assertEqual(doubled_slash, single_slash.replace("/v2/", "//v2/", 1))
        self.assertEqual(canonical_path(doubled_slash), canonical_path(single_slash))


class TrailingSlashTests(unittest.TestCase):
    def test_one_trailing_slash_is_dropped(self) -> None:
        self.assertEqual(canonical_path("/v1/entries/"), "/v1/entries")

    def test_root_stays_root(self) -> None:
        self.assertEqual(canonical_path("/"), "/")

    def test_repeated_trailing_slashes_collapse_then_drop_to_one_path(self) -> None:
        self.assertEqual(canonical_path("/v1/entries///"), "/v1/entries")

    def test_empty_path_normalizes_to_root(self) -> None:
        self.assertEqual(canonical_path(""), "/")


class AllowedPercentEncodingTests(unittest.TestCase):
    def test_lowercase_hex_pair_decodes(self) -> None:
        self.assertEqual(canonical_path("/v1/%65ntries"), "/v1/entries")

    def test_uppercase_hex_pair_decodes(self) -> None:
        self.assertEqual(canonical_path("/v1/%65NTRIES"), "/v1/eNTRIES")

    def test_mixed_case_hex_digits_decode(self) -> None:
        self.assertEqual(canonical_path("/v1/%6E"), "/v1/n")

    def test_encoded_space_decodes(self) -> None:
        self.assertEqual(canonical_path("/v1/a%20b"), "/v1/a b")

    def test_percent_encoding_combines_with_slash_and_trailing_slash_handling(self) -> None:
        self.assertEqual(canonical_path("/v1//%65ntries/"), "/v1/entries")

    def test_fixture_canonical_paths_are_already_normalized(self) -> None:
        cases = json.loads((FIXTURES / "gateway-compatibility-cases.json").read_text(encoding="utf-8"))
        for case in cases:
            with self.subTest(case=case["case"]):
                self.assertEqual(canonical_path(case["path"]), case["path"])


class RefusalTests(unittest.TestCase):
    def test_raw_control_character_is_refused(self) -> None:
        with self.assertRaises(PathNormalizationError):
            canonical_path("/v1/entries\x00")

    def test_raw_delete_character_is_refused(self) -> None:
        with self.assertRaises(PathNormalizationError):
            canonical_path("/v1/entries\x7f")

    def test_percent_encoded_null_byte_is_refused(self) -> None:
        with self.assertRaises(PathNormalizationError):
            canonical_path("/v1/entries%00")

    def test_percent_encoded_control_character_is_refused(self) -> None:
        with self.assertRaises(PathNormalizationError):
            canonical_path("/v1/entries%1F")

    def test_percent_encoded_slash_is_refused_as_ambiguous(self) -> None:
        with self.assertRaises(PathNormalizationError):
            canonical_path("/v1/entries%2F")

    def test_percent_encoded_percent_is_refused_as_ambiguous(self) -> None:
        with self.assertRaises(PathNormalizationError):
            canonical_path("/v1/entries%25")

    def test_truncated_percent_sequence_is_refused(self) -> None:
        with self.assertRaises(PathNormalizationError):
            canonical_path("/v1/entries%2")

    def test_trailing_percent_with_no_digits_is_refused(self) -> None:
        with self.assertRaises(PathNormalizationError):
            canonical_path("/v1/entries%")

    def test_non_hex_percent_sequence_is_refused(self) -> None:
        with self.assertRaises(PathNormalizationError):
            canonical_path("/v1/entries%zz")

    def test_byte_outside_the_bounded_ascii_range_is_refused(self) -> None:
        with self.assertRaises(PathNormalizationError):
            canonical_path("/v1/entries%C3%A9")

    def test_refusal_is_a_value_error(self) -> None:
        self.assertTrue(issubclass(PathNormalizationError, ValueError))


class SingleCanonicalPathFeedsBothHelpersTests(unittest.TestCase):
    def test_auth_path_and_dispatch_path_always_agree(self) -> None:
        spellings = ["/v1/entries", "/v1//entries/", "/v1/%65ntries"]
        for raw in spellings:
            with self.subTest(raw=raw):
                self.assertEqual(auth_path(raw), dispatch_path(raw))

    def test_auth_path_and_dispatch_path_refuse_the_same_inputs(self) -> None:
        for raw in ["/v1/entries%2F", "/v1/entries\x00"]:
            with self.subTest(raw=raw):
                with self.assertRaises(PathNormalizationError):
                    auth_path(raw)
                with self.assertRaises(PathNormalizationError):
                    dispatch_path(raw)


if __name__ == "__main__":
    unittest.main()
