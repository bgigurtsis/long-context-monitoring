"""Contract: client version selection cannot weaken a bearer check.

A client picks which SDK version — and therefore which V1/V2 path — it
calls. That choice must never change whether the call needs a bearer
credential: the effective requirement is always at least as strict as the
canonical V1 route's, regardless of what the V2 alias catalog says.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from auditlog.httpd import resolve_v2_alias_catalog
from auditlog.policy import build_v2_alias_catalog

FIXTURES = Path(__file__).parent.parent / "fixtures"


class DefaultCatalogTests(unittest.TestCase):
    def test_every_planned_alias_still_requires_a_bearer_even_if_canonical_table_is_empty(
        self,
    ) -> None:
        # No canonical V1 entries known at all: every alias must fail closed.
        resolved = resolve_v2_alias_catalog(build_v2_alias_catalog(), canonical_bearer={})
        self.assertTrue(resolved)
        for _method, _path, _permission, requires_auth in resolved:
            self.assertTrue(requires_auth)


class NonWeakeningInvariantTests(unittest.TestCase):
    def test_explicit_false_cannot_undercut_a_canonical_route_that_requires_a_bearer(self) -> None:
        catalog = (("POST", "/v2/entries", "record", False),)
        canonical_bearer = {("POST", "/v1/entries"): True}
        resolved = resolve_v2_alias_catalog(catalog, canonical_bearer)
        self.assertEqual(resolved, (("POST", "/v2/entries", "record", True),))

    def test_unset_alias_inherits_the_canonical_requirement(self) -> None:
        catalog = (("GET", "/v2/integrity", "integrity", None),)
        for canonical_value in (True, False):
            with self.subTest(canonical=canonical_value):
                canonical_bearer = {("GET", "/v1/integrity"): canonical_value}
                resolved = resolve_v2_alias_catalog(catalog, canonical_bearer)
                self.assertEqual(resolved[0][3], canonical_value)

    def test_unset_alias_defaults_to_required_when_canonical_route_is_unknown(self) -> None:
        catalog = (("GET", "/v2/new-thing", "new-thing", None),)
        resolved = resolve_v2_alias_catalog(catalog, canonical_bearer={})
        self.assertTrue(resolved[0][3])

    def test_explicit_true_can_strengthen_beyond_a_permissive_canonical_route(self) -> None:
        catalog = (("GET", "/v2/public", "public", True),)
        canonical_bearer = {("GET", "/v1/public"): False}
        resolved = resolve_v2_alias_catalog(catalog, canonical_bearer)
        self.assertTrue(resolved[0][3])


class SdkMigrationFixtureTests(unittest.TestCase):
    """Cross-check against the recorded SDK migration cases and generated calls."""

    def test_migration_cases_resolve_equally_on_v1_and_v2_paths(self) -> None:
        cases = json.loads((FIXTURES / "sdk-migration-cases.json").read_text(encoding="utf-8"))
        catalog = build_v2_alias_catalog()
        canonical_bearer = {
            (method, path.replace("/v2/", "/v1/", 1)): True for method, path, _, _ in catalog
        }
        resolved = {
            (method, path): requires_auth
            for method, path, _, requires_auth in resolve_v2_alias_catalog(catalog, canonical_bearer)
        }
        for case in cases:
            self.assertTrue(case["expected_equal"])
            v1_key = next(k for k in canonical_bearer if k[1] == case["v1_path"])
            v2_key = next(k for k in resolved if k[1] == case["v2_path"])
            self.assertEqual(canonical_bearer[v1_key], resolved[v2_key])

    def test_every_sdk_generated_call_uses_bearer_credentials(self) -> None:
        calls = [
            json.loads(line)
            for line in (FIXTURES / "sdk-generated-calls.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        catalog = build_v2_alias_catalog()
        resolved = {
            (method, path): requires_auth
            for method, path, _, requires_auth in resolve_v2_alias_catalog(catalog, canonical_bearer={})
        }
        for call in calls:
            self.assertEqual(call["credential_mode"], "bearer")
            self.assertTrue(resolved[(call["method"], call["path"])])


if __name__ == "__main__":
    unittest.main()
