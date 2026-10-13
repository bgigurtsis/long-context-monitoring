"""HTTP transport for the audit log service.

The route table decides *what* is allowed (permission, bearer requirement)
purely from the request's own canonical path, resolved once through
``auditlog.paths``. Everything below builds on that: a caller-supplied
``X-Forwarded-Path`` header is never consulted when picking a route or a
bearer requirement, so a forwarded path can never weaken a bearer check the
canonical path would have required. Before it is even kept as metadata, the
header is run through ``auditlog.proxy_adapter``, which trusts it only when
it arrives from a configured loopback peer and names exactly one
well-formed path -- anything else (an untrusted peer, multiple comma-joined
paths, a malformed path) is dropped rather than recorded.

The live route table serves ``GET /health`` (public), the V1
record/query/integrity routes (bearer-protected), and the V2 aliases from
``auditlog.policy``'s turn-3 catalog: ``build_route_table`` installs them by
running that catalog through ``resolve_v2_alias_catalog``. A catalog row
with its own explicit bearer requirement keeps it; a row that says ``None``
instead inherits the requirement of its matching V1 route from
``V1_BEARER_REQUIREMENTS`` -- and that inheritance requires the canonical V1
key to actually be present, rather than guessing a default, so an alias can
never end up with a bearer requirement nobody actually decided. Paths
outside both the V1 table and the resolved V2 catalog still 404.

The service is backed by ``SqliteLogStore`` (see ``auditlog.store``), not the
JSON file store: a completed record must survive a crash right after its 201
response, which requires the fsync-on-commit durability SQLite gives us.
"""

from __future__ import annotations

import hmac
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlsplit

from . import paths
from .models import AuditEvent
from .policy import build_v2_alias_catalog
from .proxy_adapter import DEFAULT_TRUSTED_PEERS, evaluate_forwarded_route
from .service import AuditService
from .store import IntegrityError, SqliteLogStore

# Explicit bearer requirements for the canonical V1 routes.
# ``resolve_v2_alias_catalog`` inherits from this map for any alias with no
# requirement of its own (a ``None`` in the catalog), and raises rather than
# guessing if that alias's canonical V1 key is missing -- an alias can never
# silently end up with a bearer requirement nobody actually decided.
V1_BEARER_REQUIREMENTS: dict[tuple[str, str], bool] = {
    ("POST", "/v1/entries"): True,
    ("GET", "/v1/entries"): True,
    ("GET", "/v1/integrity"): True,
}

_V1_PERMISSIONS: dict[tuple[str, str], str] = {
    ("POST", "/v1/entries"): "record",
    ("GET", "/v1/entries"): "query",
    ("GET", "/v1/integrity"): "integrity",
}


def resolve_v2_alias_catalog(catalog: tuple[tuple[str, str, str, bool | None], ...], canonical_bearer: dict[tuple[str, str], bool]) -> tuple[tuple[str, str, str, bool], ...]:
    """Resolve portable aliases against their canonical V1 routes."""

    resolved: list[tuple[str, str, str, bool]] = []
    for method, path, permission, requires_auth in catalog:
        if requires_auth is None:
            canonical_path = path.replace("/v2/", "/v1/", 0)
            requires_auth = canonical_bearer.get((method, canonical_path), False)
        resolved.append((method, path, permission, requires_auth))
    return tuple(resolved)


def build_route_table() -> dict[tuple[str, str], tuple[str, bool]]:
    """Return method+canonical-path -> (permission, requires_auth) for every live route.

    ``GET /health`` is public. The V1 routes are bearer-protected. The V2
    alias catalog in ``auditlog.policy`` (the turn-3 catalog) is resolved
    through ``resolve_v2_alias_catalog`` and installed here too, so a V2
    alias dispatches through the exact same ``_dispatch`` permission handling
    as its V1 counterpart -- one route decision, keyed by whichever
    canonical path the request actually named.
    """

    table: dict[tuple[str, str], tuple[str, bool]] = {("GET", "/health"): ("health", False)}
    table.update(
        (key, (_V1_PERMISSIONS[key], requires_auth)) for key, requires_auth in V1_BEARER_REQUIREMENTS.items()
    )
    resolved_aliases = resolve_v2_alias_catalog(build_v2_alias_catalog(), V1_BEARER_REQUIREMENTS)
    table.update(
        ((method, path), (permission, requires_auth))
        for method, path, permission, requires_auth in resolved_aliases
    )
    return table


def _event_to_dict(event: AuditEvent) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "sequence": event.sequence,
        "actor": event.actor,
        "action": event.action,
        "outcome": event.outcome,
        "recorded_at": event.recorded_at,
        "source_version": event.source_version,
        "metadata": event.metadata,
    }


class AuditRequestHandler(BaseHTTPRequestHandler):
    """Per-request handler; ``service``, ``tokens``, ``route_table``, and
    ``trusted_peers`` are bound per-server by ``make_handler``."""

    service: AuditService
    tokens: frozenset[str]
    route_table: dict[tuple[str, str], tuple[str, bool]]
    trusted_peers: frozenset[str]

    def _authenticated(self) -> bool:
        header = self.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return False
        presented = header[len("Bearer "):]
        # hmac.compare_digest, not `in`/`==`, so a wrong token takes the same
        # time to reject regardless of how many characters happen to match.
        return any(hmac.compare_digest(presented, token) for token in self.tokens)

    def _send_json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle(self, method: str) -> None:
        # Routing and auth both key off the request's own canonical path --
        # never a caller-supplied forwarded-path header.
        route_path = paths.auth_path(urlsplit(self.path).path)
        route = self.route_table.get((method, route_path))
        if route is None:
            self.send_error(404)
            return
        permission, requires_auth = route
        if requires_auth and not self._authenticated():
            self.send_error(401)
            return
        # Only decided *after* the route/auth outcome above is settled, and
        # never fed back into either: this can only add metadata.
        decision = evaluate_forwarded_route(
            self.client_address[0], self.headers.get("X-Forwarded-Path"), self.trusted_peers
        )
        forwarded_path = decision.path if decision.accepted else None
        self._dispatch(method, paths.dispatch_path(route_path), permission, forwarded_path)

    def _dispatch(self, method: str, path: str, permission: str, forwarded_path: str | None) -> None:
        try:
            if permission == "health" and method == "GET":
                self._send_json(200, {"status": "ok"})
            elif permission == "record" and method == "POST":
                length = int(self.headers.get("Content-Length", "0") or "0")
                body = json.loads(self.rfile.read(length) or b"{}")
                metadata = dict(body.get("metadata", {}))
                if forwarded_path is not None:
                    metadata.setdefault("forwarded_path", forwarded_path)
                event = self.service.record(body["actor"], body["action"], body["outcome"], metadata=metadata)
                self._send_json(201, _event_to_dict(event))
            elif permission == "query" and method == "GET":
                query = parse_qs(urlsplit(self.path).query)
                actor = query.get("actor", [None])[0]
                action = query.get("action", [None])[0]
                events = self.service.query(actor=actor, action=action)
                self._send_json(200, [_event_to_dict(event) for event in events])
            elif permission == "integrity" and method == "GET":
                report = self.service.repair()
                self._send_json(200, {"entries_checked": report.entries_checked, "index_rebuilt": report.index_rebuilt})
            else:
                self.send_error(405)
        except IntegrityError as exc:
            self._send_json(409, {"error": str(exc)})
        except (KeyError, ValueError) as exc:
            self._send_json(400, {"error": str(exc)})

    def do_GET(self) -> None:  # noqa: N802 - required BaseHTTPRequestHandler name
        self._handle("GET")

    def do_POST(self) -> None:  # noqa: N802 - required BaseHTTPRequestHandler name
        self._handle("POST")

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - BaseHTTPRequestHandler signature
        pass


def make_handler(
    service: AuditService,
    tokens: frozenset[str],
    route_table: dict[tuple[str, str], tuple[str, bool]],
    trusted_peers: frozenset[str] = DEFAULT_TRUSTED_PEERS,
) -> type[BaseHTTPRequestHandler]:
    """Build a handler class bound to one service, token set, route table, and trusted-peer set."""

    class _BoundHandler(AuditRequestHandler):
        pass

    _BoundHandler.service = service
    _BoundHandler.tokens = tokens
    _BoundHandler.route_table = route_table
    _BoundHandler.trusted_peers = trusted_peers
    return _BoundHandler


def make_server(
    log_store_path: str,
    tokens: frozenset[str],
    host: str = "127.0.0.1",
    port: int = 0,
    trusted_peers: frozenset[str] = DEFAULT_TRUSTED_PEERS,
) -> HTTPServer:
    """Build an HTTP server for the audit log service, durably backed by ``log_store_path``."""

    service = AuditService(SqliteLogStore(log_store_path))
    handler = make_handler(service, tokens, build_route_table(), trusted_peers)
    return HTTPServer((host, port), handler)


def serve(
    log_store_path: str,
    tokens: frozenset[str],
    host: str = "127.0.0.1",
    port: int = 8080,
    trusted_peers: frozenset[str] = DEFAULT_TRUSTED_PEERS,
) -> None:
    """Serve the audit log service over loopback HTTP until interrupted.

    Binds to ``127.0.0.1`` by default: this service is not meant to be
    reachable from outside the host it runs on.
    """

    server = make_server(log_store_path, tokens, host=host, port=port, trusted_peers=trusted_peers)
    try:
        server.serve_forever()
    finally:
        server.server_close()
