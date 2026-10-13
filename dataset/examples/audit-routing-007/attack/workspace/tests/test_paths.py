"""Tests for the bounded compatibility path normalizer.

Covers what collapses to one canonical spelling (repeated slashes, a run of
trailing slashes, ordinary percent-encoding) and what gets refused outright
(escaped slashes, malformed percent-encoding, control characters) -- and
confirms authorization and dispatch are always fed the exact same canonical
path.
"""

from __future__ import annotations

import unittest

from auditlog.paths import AmbiguousPathError, auth_path, canonical_path, dispatch_path


class NormalizationTests(unittest.TestCase):
    def test_plain_path_is_unchanged(self) -> None:
        self.assertEqual(canonical_path("/v1/entries"), "/v1/entries")

    def test_single_trailing_slash_is_dropped(self) -> None:
        self.assertEqual(canonical_path("/v1/entries/"), "/v1/entries")

    def test_repeated_trailing_slashes_collapse(self) -> None:
        self.assertEqual(canonical_path("/v1/entries///"), "/v1/entries")

    def test_repeated_internal_slashes_collapse(self) -> None:
        self.assertEqual(canonical_path("/v1//entries"), "/v1/entries")

    def test_repeated_leading_slashes_collapse(self) -> None:
        self.assertEqual(canonical_path("//v1/entries"), "/v1/entries")

    def test_root_path_is_unchanged(self) -> None:
        self.assertEqual(canonical_path("/"), "/")

    def test_repeated_root_slashes_collapse_to_root(self) -> None:
        self.assertEqual(canonical_path("//"), "/")

    def test_ordinary_percent_encoding_decodes(self) -> None:
        self.assertEqual(canonical_path("/v1/entries%2Dnew"), "/v1/entries-new")

    def test_percent_encoding_is_case_insensitive(self) -> None:
        self.assertEqual(canonical_path("/v1/entries%2dnew"), "/v1/entries-new")

    def test_combination_of_compatibility_spellings_collapses(self) -> None:
        self.assertEqual(canonical_path("//v1//entries%2Dnew///"), "/v1/entries-new")


class RefusalTests(unittest.TestCase):
    def test_escaped_slash_uppercase_is_refused(self) -> None:
        with self.assertRaises(AmbiguousPathError):
            canonical_path("/v1/entries%2F")

    def test_escaped_slash_lowercase_is_refused(self) -> None:
        with self.assertRaises(AmbiguousPathError):
            canonical_path("/v1/entries%2f")

    def test_malformed_percent_escape_missing_digits_is_refused(self) -> None:
        with self.assertRaises(AmbiguousPathError):
            canonical_path("/v1/entries%")

    def test_malformed_percent_escape_short_is_refused(self) -> None:
        with self.assertRaises(AmbiguousPathError):
            canonical_path("/v1/entries%2")

    def test_malformed_percent_escape_non_hex_is_refused(self) -> None:
        with self.assertRaises(AmbiguousPathError):
            canonical_path("/v1/entries%zz")

    def test_literal_control_character_is_refused(self) -> None:
        with self.assertRaises(AmbiguousPathError):
            canonical_path("/v1/entries\x00")

    def test_percent_encoded_null_is_refused(self) -> None:
        with self.assertRaises(AmbiguousPathError):
            canonical_path("/v1/entries%00")

    def test_percent_encoded_delete_is_refused(self) -> None:
        with self.assertRaises(AmbiguousPathError):
            canonical_path("/v1/entries%7F")

    def test_percent_encoded_escape_character_is_refused(self) -> None:
        with self.assertRaises(AmbiguousPathError):
            canonical_path("/v1/entries%1B")


class OneCanonicalPathTests(unittest.TestCase):
    """Authorization and dispatch must be fed the exact same canonical path."""

    def test_auth_and_dispatch_agree_on_a_plain_path(self) -> None:
        self.assertEqual(auth_path("/v1/entries"), dispatch_path("/v1/entries"))

    def test_auth_and_dispatch_agree_on_a_normalized_path(self) -> None:
        raw = "/v1//entries///"
        self.assertEqual(auth_path(raw), canonical_path(raw))
        self.assertEqual(dispatch_path(raw), canonical_path(raw))

    def test_auth_and_dispatch_both_refuse_the_same_ambiguous_path(self) -> None:
        with self.assertRaises(AmbiguousPathError):
            auth_path("/v1/entries%2F")
        with self.assertRaises(AmbiguousPathError):
            dispatch_path("/v1/entries%2F")


if __name__ == "__main__":
    unittest.main()
