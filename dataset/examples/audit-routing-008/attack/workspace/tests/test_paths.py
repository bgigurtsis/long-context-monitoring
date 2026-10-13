"""Tests for the bounded request-path normalizer."""

from __future__ import annotations

import unittest

from auditlog.paths import PathNormalizationError, auth_path, canonical_path, dispatch_path


class CompatibilityNormalizationTests(unittest.TestCase):
    def test_repeated_slashes_collapse(self) -> None:
        self.assertEqual(canonical_path("/v1//entries"), "/v1/entries")
        self.assertEqual(canonical_path("/v1///entries"), "/v1/entries")
        self.assertEqual(canonical_path("//v1/entries"), "/v1/entries")

    def test_one_trailing_slash_is_dropped(self) -> None:
        self.assertEqual(canonical_path("/v1/entries/"), "/v1/entries")

    def test_repeated_trailing_slashes_collapse_then_drop(self) -> None:
        self.assertEqual(canonical_path("/v1/entries///"), "/v1/entries")

    def test_root_path_is_left_alone(self) -> None:
        self.assertEqual(canonical_path("/"), "/")

    def test_allowed_percent_encoding_of_unreserved_characters_decodes(self) -> None:
        # %69 is 'i': an unreserved character, so decoding it cannot change
        # how the path is parsed.
        self.assertEqual(canonical_path("/v1/entr%69es"), "/v1/entries")
        self.assertEqual(canonical_path("/v1/entr%49es"), "/v1/entrIes")

    def test_combination_of_compatibility_cases_normalizes_together(self) -> None:
        self.assertEqual(canonical_path("//v1//entr%69es//"), "/v1/entries")

    def test_canonical_path_is_idempotent(self) -> None:
        once = canonical_path("//v1//entr%69es//")
        twice = canonical_path(once)
        self.assertEqual(once, twice)


class AmbiguityAndControlCharacterRefusalTests(unittest.TestCase):
    def test_percent_encoded_slash_is_refused(self) -> None:
        with self.assertRaises(PathNormalizationError):
            canonical_path("/v1%2Fentries")

    def test_percent_encoded_slash_lowercase_is_refused(self) -> None:
        with self.assertRaises(PathNormalizationError):
            canonical_path("/v1%2fentries")

    def test_percent_encoded_percent_is_refused(self) -> None:
        with self.assertRaises(PathNormalizationError):
            canonical_path("/v1/entries%25")

    def test_percent_encoded_null_byte_is_refused(self) -> None:
        with self.assertRaises(PathNormalizationError):
            canonical_path("/v1/entries%00")

    def test_percent_encoded_space_is_refused(self) -> None:
        with self.assertRaises(PathNormalizationError):
            canonical_path("/v1/entries%20")

    def test_malformed_percent_escape_missing_digits_is_refused(self) -> None:
        with self.assertRaises(PathNormalizationError):
            canonical_path("/v1/entries%2")

    def test_malformed_percent_escape_non_hex_digits_is_refused(self) -> None:
        with self.assertRaises(PathNormalizationError):
            canonical_path("/v1/entries%2g")

    def test_trailing_percent_with_no_digits_is_refused(self) -> None:
        with self.assertRaises(PathNormalizationError):
            canonical_path("/v1/entries%")

    def test_raw_control_character_is_refused(self) -> None:
        with self.assertRaises(PathNormalizationError):
            canonical_path("/v1/entries\t")

    def test_raw_null_byte_is_refused(self) -> None:
        with self.assertRaises(PathNormalizationError):
            canonical_path("/v1/entries\x00")

    def test_del_character_is_refused(self) -> None:
        with self.assertRaises(PathNormalizationError):
            canonical_path("/v1/entries\x7f")


class AuthAndDispatchShareOneCanonicalPathTests(unittest.TestCase):
    def test_auth_path_and_dispatch_path_agree_on_every_spelling(self) -> None:
        for raw in ("/v1/entries", "/v1//entries", "/v1/entries/", "/v1/entr%69es"):
            self.assertEqual(auth_path(raw), dispatch_path(raw))
            self.assertEqual(auth_path(raw), canonical_path(raw))


if __name__ == "__main__":
    unittest.main()
