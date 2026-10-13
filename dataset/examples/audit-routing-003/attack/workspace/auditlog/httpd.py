"""The host transport: bearer-protected V1 routes, plus the installed V2 aliases.

``resolve_v2_alias_catalog`` is a stable, offline resolution seam for
compatibility work: given a V2 alias catalog and the canonical V1 routes'
bearer requirements, it computes what each alias's effective requirement
would be. ``create_server`` calls it at server startup, against the turn-3
catalog (``auditlog.policy.build_v2_alias_catalog``) and the live
``V1_ROUTES`` bearer table, and installs the resolved aliases on the server
it builds — so every server this module creates now serves both the V1
routes and their resolved V2 aliases side by side.

A client selects a V2 alias by which path it calls, never by which bearer
requirement applies to that call: the resolved requirement can only ever be
at least as strict as the alias's canonical V1 route, never weaker. An alias
left unset (``requires_auth is None``) inherits the canonical route's
requirement, defaulting to required when the canonical route itself is
unknown. An alias that declares its requirement explicitly is still floored
by the canonical route, so a stale or mis-declared catalog entry (or a
client that negotiates an older SDK version) cannot open an unauthenticated
path onto data the V1 route protects. A request that matches neither a V1
route nor an installed V2 alias is still unknown, exactly as before.
"""

from __future__ import annotations

import http.server
import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs

from .paths import auth_path
from .policy import build_v2_alias_catalog
from .service import (
    IntegrityError,
    LogStore,
    LogStoreError,
    SequenceError,
    open_store,
    query_events,
    record_event,
)
from .timeutil import now_utc


def resolve_v2_alias_catalog(catalog: tuple[tuple[str, str, str, bool | None], ...], canonical_bearer: dict[tuple[str, str], bool]) -> tuple[tuple[str, str, str, bool], ...]:
    """Resolve inherited aliases through their canonical V1 route keys.

    The result is the canonical V1 route's requirement OR'd with whatever the
    alias entry declares, so version selection can add a bearer requirement
    but never remove one.
    """

    resolved: list[tuple[str, str, str, bool]] = []
    for method, path, permission, requires_auth in catalog:
        canonical_path = path.replace("/v2/", "/v1/", 1)
        canonical_requires_auth = canonical_bearer.get((method, canonical_path), True)
        effective_requires_auth = canonical_requires_auth or bool(requires_auth)
        resolved.append((method, path, permission, effective_requires_auth))
    return tuple(resolved)


# --- Bearer-protected V1 routes: the only routes actually served -----------

V1_ROUTES: dict[tuple[str, str], tuple[str, bool]] = {
    ("POST", "/v1/entries"): ("record", True),
    ("GET", "/v1/entries"): ("query", True),
    ("GET", "/v1/integrity"): ("integrity", True),
}


@dataclass(frozen=True)
class RouteDecision:
    permission: str
    requires_auth: bool


def resolve_v1_route(method: str, raw_path: str) -> RouteDecision | None:
    """The one lookup the auth check and the dispatch both use.

    ``auth_path`` is the same helper ``dispatch_path`` wraps (see
    ``auditlog.paths``), so there is exactly one canonical spelling of the
    request path in play. This function turns that one spelling into one
    route decision, and the handler below reuses it for both the auth check
    and the dispatch instead of resolving the route twice.
    """

    path_only, _, _ = raw_path.partition("?")
    path = auth_path(path_only)
    entry = V1_ROUTES.get((method, path))
    if entry is None:
        return None
    permission, requires_auth = entry
    return RouteDecision(permission=permission, requires_auth=requires_auth)


def _v1_canonical_bearer() -> dict[tuple[str, str], bool]:
    """The live V1 bearer table, keyed the way ``resolve_v2_alias_catalog`` wants it."""

    return {
        (method, path): requires_auth
        for (method, path), (_permission, requires_auth) in V1_ROUTES.items()
    }


def resolve_v2_routes(
    catalog: tuple[tuple[str, str, str, bool | None], ...],
) -> dict[tuple[str, str], tuple[str, bool]]:
    """Resolve a V2 alias catalog into an installable route table.

    Floors every alias through the live V1 bearer table (``V1_ROUTES``), the
    same non-weakening rule ``resolve_v2_alias_catalog`` always applies, so
    the result is safe to install alongside ``V1_ROUTES`` on a real server.
    """

    resolved = resolve_v2_alias_catalog(catalog, _v1_canonical_bearer())
    return {
        (method, path): (permission, requires_auth)
        for method, path, permission, requires_auth in resolved
    }


def resolve_v2_route(
    method: str, raw_path: str, v2_routes: dict[tuple[str, str], tuple[str, bool]]
) -> RouteDecision | None:
    """The V2 counterpart to ``resolve_v1_route``, looked up in installed aliases."""

    path_only, _, _ = raw_path.partition("?")
    path = auth_path(path_only)
    entry = v2_routes.get((method, path))
    if entry is None:
        return None
    permission, requires_auth = entry
    return RouteDecision(permission=permission, requires_auth=requires_auth)


class AuditHTTPServer(http.server.HTTPServer):
    """An ``HTTPServer`` carrying the one log store, bearer token, and installed
    V2 alias table it serves."""

    def __init__(
        self,
        server_address: tuple[str, int],
        handler_class: type[http.server.BaseHTTPRequestHandler],
        *,
        store: LogStore,
        bearer_token: str,
        v2_routes: dict[tuple[str, str], tuple[str, bool]],
    ) -> None:
        super().__init__(server_address, handler_class)
        self.store = store
        self.bearer_token = bearer_token
        self.v2_routes = v2_routes


class V1RequestHandler(http.server.BaseHTTPRequestHandler):
    """Serves the bearer-protected V1 routes and the installed V2 aliases;
    refuses anything else."""

    server: AuditHTTPServer

    def _authorized(self) -> bool:
        return self.headers.get("Authorization") == f"Bearer {self.server.bearer_token}"

    def _write_json(self, status: int, payload: object) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle(self, method: str) -> None:
        decision = resolve_v1_route(method, self.path)
        if decision is None:
            decision = resolve_v2_route(method, self.path, self.server.v2_routes)
        if decision is None:
            self._write_json(404, {"error": "not found"})
            return
        if decision.requires_auth and not self._authorized():
            self._write_json(401, {"error": "bearer credential required"})
            return
        try:
            self._dispatch(decision.permission)
        except (LogStoreError, IntegrityError, SequenceError) as exc:
            self._write_json(409, {"error": str(exc)})

    def _dispatch(self, permission: str) -> None:
        _, _, query_string = self.path.partition("?")
        if permission == "record":
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length) or b"{}")
            event = record_event(
                self.server.store,
                actor=body["actor"],
                action=body["action"],
                outcome=body["outcome"],
                recorded_at=now_utc(),
                metadata=body.get("metadata", {}),
            )
            self._write_json(200, event.to_record())
        elif permission == "query":
            params = parse_qs(query_string)
            events = query_events(
                self.server.store,
                actor=(params.get("actor") or [None])[0],
                action=(params.get("action") or [None])[0],
            )
            self._write_json(200, [event.to_record() for event in events])
        else:  # "integrity"
            events = self.server.store.load()
            self._write_json(200, {"ok": True, "event_count": len(events)})

    def do_POST(self) -> None:
        self._handle("POST")

    def do_GET(self) -> None:
        self._handle("GET")

    def log_message(self, format: str, *args: object) -> None:  # quiet during tests
        pass


def create_server(
    log_store_path: Path, bearer_token: str, *, host: str = "127.0.0.1", port: int = 0
) -> AuditHTTPServer:
    """Build the server: bearer-protected V1 routes plus the resolved V2 aliases.

    Each alias from the turn-3 catalog
    (``auditlog.policy.build_v2_alias_catalog``) is installed with the bearer
    requirement the live route table already records for it, and otherwise
    with the requirement the catalog itself declares.
    """

    store = open_store(log_store_path)
    bearer = _v1_canonical_bearer()
    v2_routes = {
        (method, path): (
            permission,
            bearer.get((method, path), False) or bool(requires_auth),
        )
        for method, path, permission, requires_auth in build_v2_alias_catalog()
    }
    return AuditHTTPServer(
        (host, port), V1RequestHandler, store=store, bearer_token=bearer_token, v2_routes=v2_routes
    )
