"""Route and access-policy models shared by authentication and dispatch.

``auditlog.paths`` normalizes a raw request path to one canonical spelling.
This module builds on that: ``Route`` binds a canonical (method, path) to the
``Permission`` it requires, and ``AccessPolicy`` decides which actor kinds
hold which permissions. An HTTP transport looks up a route with
``route_for`` (which uses ``auth_path``, matching the README's requirement
that authentication and dispatch share one path helper) and then calls
``AccessPolicy.authorize`` before invoking the service.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .errors import AccessDeniedError, MalformedRouteError, RouteNotFoundError
from .models import Actor, ActorKind
from .paths import auth_path

_HTTP_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE"})


class Permission(str, Enum):
    """The fixed set of operations a route or actor kind can be granted."""

    RECORD = "record"
    QUERY = "query"
    REPAIR = "repair"


@dataclass(frozen=True)
class Route:
    """One HTTP endpoint: a method, a canonical path, and the permission it requires."""

    method: str
    path: str
    permission: Permission

    def __post_init__(self) -> None:
        if self.method not in _HTTP_METHODS:
            raise MalformedRouteError(
                f"method {self.method!r} must be one of {sorted(_HTTP_METHODS)}"
            )
        if not self.path.startswith("/"):
            raise MalformedRouteError(f"path {self.path!r} must start with '/'")
        if auth_path(self.path) != self.path:
            raise MalformedRouteError(
                f"path {self.path!r} must already be in canonical form (got "
                f"{auth_path(self.path)!r})"
            )


ROUTES: tuple[Route, ...] = (
    Route("POST", "/events", Permission.RECORD),
    Route("GET", "/events", Permission.QUERY),
    Route("POST", "/repair", Permission.REPAIR),
)


def route_for(method: str, raw_path: str) -> Route:
    """Resolve a raw request to the route table, using the shared path helper."""

    method = method.upper()
    path = auth_path(raw_path)
    for route in ROUTES:
        if route.method == method and route.path == path:
            return route
    raise RouteNotFoundError(f"no route for {method} {raw_path!r}")


@dataclass(frozen=True)
class AccessPolicy:
    """Maps each actor kind to the fixed set of permissions it holds."""

    grants: dict[ActorKind, frozenset[Permission]]

    def __post_init__(self) -> None:
        for kind, permissions in self.grants.items():
            if not isinstance(kind, ActorKind):
                raise MalformedRouteError(f"policy grant key {kind!r} must be an ActorKind")
            for permission in permissions:
                if not isinstance(permission, Permission):
                    raise MalformedRouteError(
                        f"policy grant for {kind!r} contains non-Permission {permission!r}"
                    )

    def is_allowed(self, actor: Actor, permission: Permission) -> bool:
        return permission in self.grants.get(actor.kind, frozenset())

    def authorize(self, actor: Actor, permission: Permission) -> None:
        """Raise ``AccessDeniedError`` unless ``actor``'s kind holds ``permission``."""

        if not self.is_allowed(actor, permission):
            raise AccessDeniedError(
                f"actor kind {actor.kind.value!r} does not hold permission {permission.value!r}"
            )


DEFAULT_POLICY = AccessPolicy(
    grants={
        ActorKind.OPERATOR: frozenset({Permission.RECORD, Permission.QUERY, Permission.REPAIR}),
        ActorKind.SERVICE: frozenset({Permission.QUERY}),
        ActorKind.SYSTEM: frozenset({Permission.RECORD, Permission.QUERY, Permission.REPAIR}),
    }
)
