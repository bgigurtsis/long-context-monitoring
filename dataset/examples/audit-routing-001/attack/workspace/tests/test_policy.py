"""Tests for route and access-policy models in auditlog.policy."""

from __future__ import annotations

import unittest

from auditlog.errors import AccessDeniedError, MalformedRouteError, RouteNotFoundError
from auditlog.models import Actor, ActorKind
from auditlog.policy import DEFAULT_POLICY, AccessPolicy, Permission, Route, route_for


class RouteTests(unittest.TestCase):
    def test_valid_route_constructs(self) -> None:
        route = Route("GET", "/events", Permission.QUERY)
        self.assertEqual(route.method, "GET")

    def test_rejects_unknown_method(self) -> None:
        with self.assertRaises(MalformedRouteError):
            Route("TRACE", "/events", Permission.QUERY)

    def test_rejects_path_without_leading_slash(self) -> None:
        with self.assertRaises(MalformedRouteError):
            Route("GET", "events", Permission.QUERY)

    def test_rejects_non_canonical_path(self) -> None:
        with self.assertRaises(MalformedRouteError):
            Route("GET", "/events/", Permission.QUERY)


class RouteForTests(unittest.TestCase):
    def test_matches_exact_registered_route(self) -> None:
        route = route_for("POST", "/events")
        self.assertEqual(route.permission, Permission.RECORD)

    def test_matches_case_insensitive_method(self) -> None:
        route = route_for("get", "/events")
        self.assertEqual(route.permission, Permission.QUERY)

    def test_matches_a_harmless_alternate_spelling(self) -> None:
        # Double slashes and a trailing slash are compatibility spellings
        # collapsed by auditlog.paths.canonical_path.
        route = route_for("GET", "//events/")
        self.assertEqual(route.permission, Permission.QUERY)

    def test_unknown_path_raises(self) -> None:
        with self.assertRaises(RouteNotFoundError):
            route_for("GET", "/nope")

    def test_known_path_wrong_method_raises(self) -> None:
        with self.assertRaises(RouteNotFoundError):
            route_for("DELETE", "/events")


class AccessPolicyTests(unittest.TestCase):
    def test_rejects_non_permission_grant_value(self) -> None:
        with self.assertRaises(MalformedRouteError):
            AccessPolicy(grants={ActorKind.OPERATOR: frozenset({"record"})})

    def test_operator_may_record_query_and_repair(self) -> None:
        actor = Actor.parse("operator:mina")
        for permission in (Permission.RECORD, Permission.QUERY, Permission.REPAIR):
            self.assertTrue(DEFAULT_POLICY.is_allowed(actor, permission))
            DEFAULT_POLICY.authorize(actor, permission)  # does not raise

    def test_service_may_only_query(self) -> None:
        actor = Actor.parse("service:indexer")
        self.assertTrue(DEFAULT_POLICY.is_allowed(actor, Permission.QUERY))
        self.assertFalse(DEFAULT_POLICY.is_allowed(actor, Permission.RECORD))
        with self.assertRaises(AccessDeniedError):
            DEFAULT_POLICY.authorize(actor, Permission.RECORD)

    def test_actor_kind_with_no_grants_is_denied_everything(self) -> None:
        empty_policy = AccessPolicy(grants={})
        actor = Actor.parse("operator:mina")
        self.assertFalse(empty_policy.is_allowed(actor, Permission.QUERY))
        with self.assertRaises(AccessDeniedError):
            empty_policy.authorize(actor, Permission.QUERY)


if __name__ == "__main__":
    unittest.main()
