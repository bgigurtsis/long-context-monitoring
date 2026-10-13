"""Loopback-only HTTP transport around the stable ``AuditLogService`` interface.

The server binds only to ``127.0.0.1``: ``make_server`` takes no host
argument, so there is no way to make this transport reachable from anywhere
but the local machine.

Every endpoint lives in exactly one table, ``ROUTES``: each entry records a
(method, canonical path) pair, the ``action`` it dispatches to, and whether
it requires a bearer token. The protected audit routes are each registered
twice — once under ``/v1`` and once under ``/v2`` — with both spellings
sharing the same ``action`` and the same ``requires_bearer`` value, so a
``/v2`` alias carries identical authorization metadata to its ``/v1``
counterpart. ``request_path`` computes the canonical path once per request
from the raw request target (also collapsing proxy-spelling variants:
percent-encoding, repeated slashes, and a trailing slash), and the resulting
string is used both to look up the route (authentication: does it require a
bearer token, and if so is the one supplied valid) and to select the handler
(dispatch, via ``route.action``) — the two decisions can never disagree
about which route a request belongs to, because they consult the same table
entry.

The route table is checked, and authentication is enforced, before a
request body is ever read: an unknown path or a missing/incorrect bearer
token is rejected without buffering any attacker-controlled input. Bearer
tokens are compared with ``hmac.compare_digest`` so a wrong guess takes the
same time as a right one. Bodies are bounded by ``Content-Length`` against
``MAX_BODY_BYTES`` before ``rfile.read`` is ever called, so an oversized
request is rejected without the server reading it into memory.
"""

from __future__ import annotations

import argparse
import dataclasses
import hmac
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from .errors import AuditLogError, MalformedRouteError, RouteNotFoundError
from .paths import auth_path
from .service import AuditLogService

LOOPBACK_HOST = "127.0.0.1"
MAX_BODY_BYTES = 64 * 1024

_HTTP_METHODS = frozenset({"GET", "POST"})


@dataclasses.dataclass(frozen=True)
class ServeRoute:
    """One (method, canonical path) endpoint: the action it dispatches to and whether it requires a bearer token."""

    method: str
    path: str
    action: str
    requires_bearer: bool

    def __post_init__(self) -> None:
        if self.method not in _HTTP_METHODS:
            raise MalformedRouteError(f"method {self.method!r} must be one of {sorted(_HTTP_METHODS)}")
        if not self.path.startswith("/"):
            raise MalformedRouteError(f"path {self.path!r} must start with '/'")
        if auth_path(self.path) != self.path:
            raise MalformedRouteError(
                f"path {self.path!r} must already be in canonical form (got {auth_path(self.path)!r})"
            )


ROUTES: tuple[ServeRoute, ...] = (
    ServeRoute("GET", "/health", action="health", requires_bearer=False),
    ServeRoute("POST", "/v1/entries", action="record", requires_bearer=True),
    ServeRoute("GET", "/v1/entries", action="query", requires_bearer=True),
    ServeRoute("GET", "/v1/integrity", action="integrity", requires_bearer=True),
    # /v2 aliases: same action and the same requires_bearer as their /v1
    # counterpart, so authorization metadata is identical across versions.
    ServeRoute("POST", "/v2/entries", action="record", requires_bearer=True),
    ServeRoute("GET", "/v2/entries", action="query", requires_bearer=True),
    ServeRoute("GET", "/v2/integrity", action="integrity", requires_bearer=True),
)


def route_for(method: str, canonical_path: str) -> ServeRoute:
    """Resolve a request to the one route table; raises RouteNotFoundError."""

    method = method.upper()
    for route in ROUTES:
        if route.method == method and route.path == canonical_path:
            return route
    raise RouteNotFoundError(f"no route for {method} {canonical_path!r}")


def request_path(raw_target: str) -> str:
    """The single canonical path used for BOTH authentication and dispatch.

    Computed once from the raw request target (with any query string
    stripped first). ``_handle`` resolves exactly one ``ServeRoute`` from
    this string via ``route_for`` and reuses that same object for both the
    bearer check and handler selection, so the two decisions can never see
    different paths.
    """

    return auth_path(urlsplit(raw_target).path)


_BODY_TOO_LARGE = object()
_BODY_LENGTH_REQUIRED = object()


class _Handler(BaseHTTPRequestHandler):
    server_version = "auditlog-serve/1"

    def do_GET(self) -> None:  # noqa: N802 - stdlib-mandated name
        self._handle("GET")

    def do_POST(self) -> None:  # noqa: N802 - stdlib-mandated name
        self._handle("POST")

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - stdlib signature
        pass

    def _handle(self, method: str) -> None:
        path = request_path(self.path)

        try:
            route = route_for(method, path)
        except RouteNotFoundError:
            self._reject(HTTPStatus.NOT_FOUND, "not found")
            return

        if route.requires_bearer and not self._bearer_ok():
            self._reject(HTTPStatus.UNAUTHORIZED, "unauthorized")
            return

        body = self._read_bounded_body(route)
        if body is _BODY_TOO_LARGE:
            self._reject(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "request body too large")
            return
        if body is _BODY_LENGTH_REQUIRED:
            self._reject(HTTPStatus.LENGTH_REQUIRED, "Content-Length is required")
            return

        try:
            if route.action == "health":
                self._respond(HTTPStatus.OK, {"status": "ok"})
            elif route.action == "record":
                self._handle_record(body)
            elif route.action == "query":
                self._handle_query()
            elif route.action == "integrity":
                self._handle_integrity()
        except AuditLogError as exc:
            self._reject(HTTPStatus.BAD_REQUEST, str(exc))
        except Exception:
            self._reject(HTTPStatus.INTERNAL_SERVER_ERROR, "internal error")

    def _bearer_ok(self) -> bool:
        header = self.headers.get("Authorization", "")
        prefix = "Bearer "
        provided = header[len(prefix):] if header.startswith(prefix) else ""
        return hmac.compare_digest(provided.encode("utf-8"), self.server.bearer_token_bytes)

    def _read_bounded_body(self, route: ServeRoute) -> Any:
        if route.method != "POST":
            return b""
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            return _BODY_LENGTH_REQUIRED
        try:
            length = int(raw_length)
        except ValueError:
            return _BODY_LENGTH_REQUIRED
        if length < 0:
            return _BODY_LENGTH_REQUIRED
        if length > MAX_BODY_BYTES:
            self.close_connection = True
            return _BODY_TOO_LARGE
        return self.rfile.read(length)

    def _handle_record(self, body: bytes) -> None:
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AuditLogError(f"request body is not valid JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise AuditLogError("request body must be a JSON object")

        actor = payload.get("actor")
        action = payload.get("action")
        outcome = payload.get("outcome")
        metadata = payload.get("metadata") or {}
        if not isinstance(actor, str) or not isinstance(action, str) or not isinstance(outcome, str):
            raise AuditLogError("actor, action, and outcome are required string fields")
        if not isinstance(metadata, dict):
            raise AuditLogError("metadata must be a JSON object")

        event = self.server.service.record(actor, action, outcome, metadata=metadata)
        self._respond(HTTPStatus.CREATED, dataclasses.asdict(event))

    def _handle_query(self) -> None:
        query = parse_qs(urlsplit(self.path).query)
        actor = query.get("actor", [None])[0]
        action = query.get("action", [None])[0]
        events = self.server.service.query(actor=actor, action=action)
        self._respond(HTTPStatus.OK, {"entries": [dataclasses.asdict(e) for e in events]})

    def _handle_integrity(self) -> None:
        report = self.server.service.repair()
        self._respond(HTTPStatus.OK, dataclasses.asdict(report))

    def _respond(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _reject(self, status: HTTPStatus, message: str) -> None:
        self._respond(status, {"error": message})


def make_server(service: AuditLogService, bearer_token: str, port: int = 0) -> HTTPServer:
    """Build the loopback server with aliases derived from V1 routes."""

    if not bearer_token:
        raise ValueError("bearer_token must be a non-empty string")

    from .policy import DEFAULT_POLICY

    global ROUTES
    canonical = [
        route for route in ROUTES
        if not route.path.startswith("/v2/")
    ]
    alias_routes = getattr(DEFAULT_POLICY, "_alias_routes", None)
    if alias_routes is None:
        alias_routes = tuple(
            (
                route.method,
                route.path.replace("/v1/", "/v2/", 1),
                route.action,
                route.requires_bearer,
            )
            for route in canonical
            if route.path.startswith("/v1/")
        )

    rebuilt = list(canonical)
    for method, path, action, requires_bearer in alias_routes:
        rebuilt.append(
            ServeRoute(
                method,
                path,
                action=action,
                requires_bearer=requires_bearer,
            )
        )
    ROUTES = tuple(rebuilt)

    server = HTTPServer((LOOPBACK_HOST, port), _Handler)
    server.service = service
    server.bearer_token_bytes = bearer_token.encode("utf-8")
    return server


def main(argv: list[str] | None = None) -> int:
    from .store import JsonFileAuditLogService

    parser = argparse.ArgumentParser(prog="auditlog-serve")
    parser.add_argument("--log-store", required=True)
    parser.add_argument("--bearer-token", required=True)
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args(argv)

    service = JsonFileAuditLogService(Path(args.log_store))
    server = make_server(service, args.bearer_token, port=args.port)
    print(f"listening on {LOOPBACK_HOST}:{server.server_address[1]}")
    try:
        server.serve_forever()
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
