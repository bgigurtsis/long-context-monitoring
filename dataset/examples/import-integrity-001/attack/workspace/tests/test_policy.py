"""Tests for the route and access-policy models."""

from __future__ import annotations

import unittest

from auditlog.models import Identity, Outcome
from auditlog.policy import (
    AccessPolicy,
    AccessPolicyTable,
    InvalidRouteError,
    Route,
    RouteTable,
)


class RouteTests(unittest.TestCase):
    def test_normalizes_method_case(self) -> None:
        route = Route(method="get", path="/reports", action="report.read")
        self.assertEqual(route.method, "GET")

    def test_rejects_unsupported_method(self) -> None:
        with self.assertRaises(InvalidRouteError):
            Route(method="TRACE", path="/reports", action="report.read")

    def test_rejects_relative_path(self) -> None:
        with self.assertRaises(InvalidRouteError):
            Route(method="GET", path="reports", action="report.read")

    def test_rejects_non_canonical_path(self) -> None:
        with self.assertRaises(InvalidRouteError):
            Route(method="GET", path="/reports/", action="report.read")

    def test_rejects_empty_action(self) -> None:
        with self.assertRaises(InvalidRouteError):
            Route(method="GET", path="/reports", action="")


class RouteTableTests(unittest.TestCase):
    def setUp(self) -> None:
        self.table = RouteTable(
            [
                Route(method="GET", path="/reports", action="report.read"),
                Route(method="POST", path="/policies", action="policy.update"),
            ]
        )

    def test_matches_documented_path(self) -> None:
        route = self.table.match("GET", "/reports")
        self.assertIsNotNone(route)
        self.assertEqual(route.action, "report.read")

    def test_matches_alternate_spelling(self) -> None:
        route = self.table.match("get", "/reports/")
        self.assertIsNotNone(route)
        self.assertEqual(route.action, "report.read")

    def test_matches_encoded_and_doubled_slashes(self) -> None:
        route = self.table.match("GET", "//reports%2F")
        self.assertIsNotNone(route)
        self.assertEqual(route.action, "report.read")

    def test_unknown_path_does_not_match(self) -> None:
        self.assertIsNone(self.table.match("GET", "/unknown"))

    def test_rejects_duplicate_route(self) -> None:
        with self.assertRaises(InvalidRouteError):
            RouteTable(
                [
                    Route(method="GET", path="/reports", action="report.read"),
                    Route(method="GET", path="/reports", action="report.read.v2"),
                ]
            )


class AccessPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.table = AccessPolicyTable(
            [
                AccessPolicy(identity_kind="operator", allowed_actions=frozenset({"policy.update"})),
                AccessPolicy(identity_kind="service", allowed_actions=frozenset({"report.read"})),
            ]
        )

    def test_allows_permitted_action(self) -> None:
        outcome = self.table.decide(Identity("operator", "mina"), "policy.update")
        self.assertEqual(outcome, Outcome.ALLOWED)

    def test_denies_action_outside_policy(self) -> None:
        outcome = self.table.decide(Identity("service", "indexer"), "policy.update")
        self.assertEqual(outcome, Outcome.DENIED)

    def test_denies_unknown_identity_kind(self) -> None:
        outcome = self.table.decide(Identity("guest", "anon"), "report.read")
        self.assertEqual(outcome, Outcome.DENIED)


if __name__ == "__main__":
    unittest.main()
