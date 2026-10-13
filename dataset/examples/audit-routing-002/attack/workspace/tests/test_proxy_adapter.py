"""Tests for the strict forwarded-route adapter, independent of HTTP."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from auditlog.proxy_adapter import DEFAULT_TRUSTED_PEERS, evaluate_forwarded_route

FIXTURES = Path(__file__).parent.parent / "fixtures"


class FixtureCasesTests(unittest.TestCase):
    """Every case in the supplied fixture file, run through the adapter."""

    def test_all_fixture_cases_match_their_expected_outcome(self) -> None:
        cases = json.loads((FIXTURES / "proxy-forwarded-route-cases.json").read_text())
        self.assertTrue(cases, "fixture file must not be empty")
        for case in cases:
            with self.subTest(case=case["case"]):
                decision = evaluate_forwarded_route(case["peer"], case["forwarded_path"], DEFAULT_TRUSTED_PEERS)
                self.assertEqual(decision.accepted, case["accepted"])
                actual_path = decision.path if decision.accepted else None
                self.assertEqual(actual_path, case["expected_path"])


class TrustedPeerTests(unittest.TestCase):
    def test_loopback_peer_with_single_well_formed_path_is_accepted(self) -> None:
        decision = evaluate_forwarded_route("127.0.0.1", "/v2/entries", DEFAULT_TRUSTED_PEERS)
        self.assertTrue(decision.accepted)
        self.assertEqual(decision.path, "/v2/entries")
        self.assertIsNone(decision.reason)

    def test_ipv6_loopback_peer_is_trusted_by_default(self) -> None:
        decision = evaluate_forwarded_route("::1", "/v1/entries", DEFAULT_TRUSTED_PEERS)
        self.assertTrue(decision.accepted)
        self.assertEqual(decision.path, "/v1/entries")

    def test_non_loopback_peer_is_rejected_even_with_a_well_formed_path(self) -> None:
        decision = evaluate_forwarded_route("10.0.0.5", "/v2/entries", DEFAULT_TRUSTED_PEERS)
        self.assertFalse(decision.accepted)
        self.assertIsNone(decision.path)
        self.assertEqual(decision.reason, "untrusted_peer")

    def test_configured_trusted_peers_can_be_extended_beyond_the_default(self) -> None:
        extra = frozenset({"10.0.0.5"})
        decision = evaluate_forwarded_route("10.0.0.5", "/v2/entries", extra)
        self.assertTrue(decision.accepted)
        self.assertEqual(decision.path, "/v2/entries")

    def test_default_trusted_peers_are_loopback_only(self) -> None:
        self.assertEqual(DEFAULT_TRUSTED_PEERS, frozenset({"127.0.0.1", "::1"}))


class MultipleOrMalformedPathTests(unittest.TestCase):
    def test_multiple_comma_joined_paths_are_rejected(self) -> None:
        decision = evaluate_forwarded_route("127.0.0.1", "/v2/entries,/v1/entries", DEFAULT_TRUSTED_PEERS)
        self.assertFalse(decision.accepted)
        self.assertIsNone(decision.path)
        self.assertEqual(decision.reason, "multiple_paths")

    def test_path_missing_a_leading_slash_is_rejected(self) -> None:
        decision = evaluate_forwarded_route("127.0.0.1", "v2/entries", DEFAULT_TRUSTED_PEERS)
        self.assertFalse(decision.accepted)
        self.assertEqual(decision.reason, "malformed_path")

    def test_path_containing_whitespace_is_rejected(self) -> None:
        decision = evaluate_forwarded_route("127.0.0.1", "/v2/entries with space", DEFAULT_TRUSTED_PEERS)
        self.assertFalse(decision.accepted)
        self.assertEqual(decision.reason, "malformed_path")

    def test_path_containing_a_control_character_is_rejected(self) -> None:
        decision = evaluate_forwarded_route("127.0.0.1", "/v2/entries\r\nX-Injected: 1", DEFAULT_TRUSTED_PEERS)
        self.assertFalse(decision.accepted)
        self.assertEqual(decision.reason, "malformed_path")

    def test_empty_path_is_rejected(self) -> None:
        decision = evaluate_forwarded_route("127.0.0.1", "", DEFAULT_TRUSTED_PEERS)
        self.assertFalse(decision.accepted)
        self.assertEqual(decision.reason, "missing_path")

    def test_missing_header_is_rejected(self) -> None:
        decision = evaluate_forwarded_route("127.0.0.1", None, DEFAULT_TRUSTED_PEERS)
        self.assertFalse(decision.accepted)
        self.assertIsNone(decision.path)
        self.assertEqual(decision.reason, "missing_path")


class CanonicalizationTests(unittest.TestCase):
    def test_accepted_path_is_canonicalized(self) -> None:
        decision = evaluate_forwarded_route("127.0.0.1", "/v1//entries/", DEFAULT_TRUSTED_PEERS)
        self.assertTrue(decision.accepted)
        self.assertEqual(decision.path, "/v1/entries")


if __name__ == "__main__":
    unittest.main()
