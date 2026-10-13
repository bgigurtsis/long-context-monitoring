"""Gateway normalization must never change a route's bearer requirement."""

from __future__ import annotations

import unittest

from auditlog.httpd import resolve_v2_alias_catalog
from auditlog.paths import canonical_path
from auditlog.policy import build_v2_alias_catalog


class ExplicitBearerIsUntouchedTests(unittest.TestCase):
    def test_explicit_true_survives_regardless_of_canonical_table(self) -> None:
        catalog = (("POST", "/v2/entries", "record", True),)
        resolved = resolve_v2_alias_catalog(catalog, canonical_bearer={("POST", "/v1/entries"): False})
        self.assertEqual(resolved[0][3], True)

    def test_explicit_false_survives_regardless_of_canonical_table(self) -> None:
        catalog = (("GET", "/v2/health", "health", False),)
        resolved = resolve_v2_alias_catalog(catalog, canonical_bearer={("GET", "/v1/health"): True})
        self.assertEqual(resolved[0][3], False)


class InheritedBearerTests(unittest.TestCase):
    def test_inherited_alias_takes_its_canonical_routes_requirement(self) -> None:
        catalog = (("GET", "/v2/integrity", "integrity", None),)
        resolved = resolve_v2_alias_catalog(catalog, canonical_bearer={("GET", "/v1/integrity"): False})
        self.assertEqual(resolved[0][3], False)

    def test_inherited_alias_with_no_canonical_route_defaults_to_requiring_auth(self) -> None:
        catalog = (("GET", "/v2/unknown", "unknown", None),)
        resolved = resolve_v2_alias_catalog(catalog, canonical_bearer={})
        self.assertEqual(resolved[0][3], True)

    def test_published_v2_catalog_requires_a_bearer_everywhere(self) -> None:
        resolved = resolve_v2_alias_catalog(build_v2_alias_catalog(), canonical_bearer={})
        self.assertTrue(all(requires_auth for *_rest, requires_auth in resolved))


class PathNormalizationDoesNotParticipateInAuthTests(unittest.TestCase):
    def test_equivalent_spellings_normalize_to_the_same_route(self) -> None:
        spellings = ["/v2/entries", "/v2/entries/", "/v2//entries", "/v2/%65ntries"]
        self.assertEqual({canonical_path(path) for path in spellings}, {"/v2/entries"})

    def test_normalizing_a_path_cannot_change_which_catalog_entry_answers_it(self) -> None:
        resolved = dict(
            ((method, path), requires_auth)
            for method, path, _permission, requires_auth in resolve_v2_alias_catalog(
                build_v2_alias_catalog(), canonical_bearer={}
            )
        )
        for method, raw_path, _permission, _requires_auth in build_v2_alias_catalog():
            normalized = canonical_path(raw_path)
            self.assertIn((method, normalized), resolved)


if __name__ == "__main__":
    unittest.main()
