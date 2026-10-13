"""Route and access-policy models for the HTTP-facing side of the service.

A ``Route`` maps an HTTP method and canonical path to the audit ``action`` it
represents. An ``AccessPolicyTable`` then decides, for a caller ``Identity``
and that action, whether the call is ``allowed`` or ``denied``. Both models
are strict: a route with a non-canonical path, or a request for an unknown
route, is a configuration error rather than something to guess at silently.

This keeps request-path matching in :mod:`auditlog.paths` as the single
helper both authentication and dispatch share, and turns its output into the
``actor``/``action``/``outcome`` triple the audit log records.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import Identity, Outcome
from .paths import canonical_path

_ALLOWED_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE"})


class PolicyModelError(ValueError):
    """Base class for malformed route or access-policy configuration."""


class InvalidRouteError(PolicyModelError):
    """Raised when a route's method or path is not well-formed."""


@dataclass(frozen=True)
class Route:
    """One HTTP endpoint and the audit action it corresponds to."""

    method: str
    path: str
    action: str

    def __post_init__(self) -> None:
        method = self.method.upper()
        if method not in _ALLOWED_METHODS:
            allowed = ", ".join(sorted(_ALLOWED_METHODS))
            raise InvalidRouteError(f"unsupported method {self.method!r}; expected one of: {allowed}")
        object.__setattr__(self, "method", method)
        if not self.path.startswith("/"):
            raise InvalidRouteError(f"route path {self.path!r} must start with '/'")
        if self.path != canonical_path(self.path):
            raise InvalidRouteError(
                f"route path {self.path!r} is not canonical; use {canonical_path(self.path)!r}"
            )
        if not self.action:
            raise InvalidRouteError("route action must be a non-empty string")


class RouteTable:
    """Looks up the :class:`Route` for a method and raw request path."""

    def __init__(self, routes: list[Route]) -> None:
        self._routes: dict[tuple[str, str], Route] = {}
        for route in routes:
            key = (route.method, route.path)
            if key in self._routes:
                raise InvalidRouteError(f"duplicate route for {route.method} {route.path}")
            self._routes[key] = route

    def match(self, method: str, raw_path: str) -> Route | None:
        return self._routes.get((method.upper(), canonical_path(raw_path)))


@dataclass(frozen=True)
class AccessPolicy:
    """The set of actions one identity kind is permitted to perform."""

    identity_kind: str
    allowed_actions: frozenset[str]

    def permits(self, action: str) -> bool:
        return action in self.allowed_actions


class AccessPolicyTable:
    """Decides the outcome of an identity attempting an action."""

    def __init__(self, policies: list[AccessPolicy]) -> None:
        self._policies: dict[str, AccessPolicy] = {}
        for policy in policies:
            if policy.identity_kind in self._policies:
                raise PolicyModelError(f"duplicate access policy for kind {policy.identity_kind!r}")
            self._policies[policy.identity_kind] = policy

    def decide(self, identity: Identity, action: str) -> Outcome:
        policy = self._policies.get(identity.kind)
        if policy is None or not policy.permits(action):
            return Outcome.DENIED
        return Outcome.ALLOWED
