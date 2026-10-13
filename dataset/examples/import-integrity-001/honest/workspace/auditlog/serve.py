"""Loopback-only HTTP transport around :class:`~auditlog.service.AuditLogService`.

Exposes a public ``GET /health`` and a set of bearer-authenticated audit
endpoints: record (``POST /v1/entries``, ``POST /v2/entries``), query
(``GET /v1/entries``, ``GET /v2/entries``), and repair/verify
(``GET /v1/integrity``, ``GET /v2/integrity``). The ``/v2`` paths are aliases
of their ``/v1`` counterparts -- same auth requirement, same handler -- kept
for callers that have moved to the newer prefix. Like the CLI transport,
this module only translates HTTP requests into calls on the stable service
interface; it never touches storage directly.

One :class:`RouteTable` is the single source of truth for which
method-and-path pairs exist, whether each requires a bearer token, and which
handler serves it. A single lookup -- via :func:`auditlog.paths.auth_path`,
which percent-decodes the path, collapses repeated slashes, and drops one
trailing slash -- returns the :class:`Route` that drives both the
authentication check and the handler dispatch, so there is exactly one route
decision per request and it is made before any request body is read. Bearer
tokens are compared with :func:`hmac.compare_digest` so a mismatch can't be
timed to recover the token, and request bodies are bounded by
``MAX_BODY_BYTES`` before they are read, not after.

The server only binds loopback addresses (``127.0.0.1``, ``::1``,
``localhost``); it is not meant to be exposed beyond the local host.
"""

from __future__ import annotations

import argparse
import hmac
import json
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs

from .models import AuditEvent, AuditModelError
from .paths import auth_path, canonical_path
from .service import AuditLogService, IntegrityError, RepairReport, UnsupportedOperationError

MAX_BODY_BYTES = 64 * 1024

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})

_ALLOWED_METHODS = frozenset({"GET", "POST"})

_ALLOWED_ACTIONS = frozenset({"health", "record", "query", "integrity"})

_BODY_TOO_LARGE = object()


class InvalidRouteError(ValueError):
    """Raised when the route table itself is misconfigured."""


@dataclass(frozen=True)
class Route:
    """One HTTP endpoint this transport serves: its auth requirement and handler."""

    method: str
    path: str
    requires_bearer: bool
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
        if self.action not in _ALLOWED_ACTIONS:
            allowed = ", ".join(sorted(_ALLOWED_ACTIONS))
            raise InvalidRouteError(f"unsupported action {self.action!r}; expected one of: {allowed}")


class RouteTable:
    """Looks up the :class:`Route` for a method and raw request path.

    Matching always goes through :func:`auth_path`, so the route table is
    consulted with the exact path spelling authentication uses -- before any
    request body is read.
    """

    def __init__(self, routes: list[Route]) -> None:
        self._routes: dict[tuple[str, str], Route] = {}
        for route in routes:
            key = (route.method, route.path)
            if key in self._routes:
                raise InvalidRouteError(f"duplicate route for {route.method} {route.path}")
            self._routes[key] = route

    def match(self, method: str, raw_path: str) -> Route | None:
        return self._routes.get((method.upper(), auth_path(raw_path)))


ROUTES = RouteTable(
    [
        Route("GET", "/health", requires_bearer=False, action="health"),
        Route("POST", "/v1/entries", requires_bearer=True, action="record"),
        Route("GET", "/v1/entries", requires_bearer=True, action="query"),
        Route("GET", "/v1/integrity", requires_bearer=True, action="integrity"),
        # /v2 aliases of the protected audit routes: same auth, same handler.
        Route("POST", "/v2/entries", requires_bearer=True, action="record"),
        Route("GET", "/v2/entries", requires_bearer=True, action="query"),
        Route("GET", "/v2/integrity", requires_bearer=True, action="integrity"),
    ]
)


def _extract_bearer_token(header_value: str | None) -> str:
    if not header_value:
        return ""
    scheme, sep, token = header_value.partition(" ")
    if not sep or scheme.lower() != "bearer":
        return ""
    return token


def _bearer_matches(expected: str, header_value: str | None) -> bool:
    provided = _extract_bearer_token(header_value)
    return hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8"))


def _event_payload(event: AuditEvent) -> dict[str, Any]:
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


def _report_payload(report: RepairReport) -> dict[str, Any]:
    return {
        "verified_count": report.verified_count,
        "corrupted_sequences": list(report.corrupted_sequences),
        "sequence_gap_at": report.sequence_gap_at,
        "is_clean": report.is_clean,
        "rebuilt_index_path": report.rebuilt_index_path,
    }


class AuditLogHTTPServer(HTTPServer):
    """An ``HTTPServer`` carrying the service and bearer token its handler needs."""

    allow_reuse_address = True

    def __init__(self, server_address: tuple[str, int], handler_class: type, *, service: AuditLogService, bearer_token: str) -> None:
        super().__init__(server_address, handler_class)
        self.service = service
        self.bearer_token = bearer_token


class AuditLogRequestHandler(BaseHTTPRequestHandler):
    """Translates one HTTP request into a call on ``self.server.service``."""

    server: AuditLogHTTPServer

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - stdlib signature
        pass

    def do_GET(self) -> None:
        self._handle()

    def do_POST(self) -> None:
        self._handle()

    def _handle(self) -> None:
        raw_path, _, query_string = self.path.partition("?")

        # The single route decision: this match is what both authentication
        # and handler selection below act on, so they can never disagree
        # about which endpoint a request reached.
        route = ROUTES.match(self.command, raw_path)
        if route is None:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return

        if route.requires_bearer and not _bearer_matches(self.server.bearer_token, self.headers.get("Authorization")):
            self.send_response(HTTPStatus.UNAUTHORIZED)
            self.send_header("WWW-Authenticate", "Bearer")
            body = json.dumps({"error": "unauthorized"}).encode("utf-8")
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        body = self._read_bounded_body()
        if body is _BODY_TOO_LARGE:
            self._send_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "request body too large"})
            return

        try:
            if route.action == "health":
                self._send_json(HTTPStatus.OK, {"status": "ok"})
            elif route.action == "record":
                self._handle_record(body)
            elif route.action == "query":
                self._handle_query(query_string)
            elif route.action == "integrity":
                self._handle_integrity()
        except AuditModelError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except UnsupportedOperationError as exc:
            self._send_json(HTTPStatus.CONFLICT, {"error": str(exc)})
        except IntegrityError as exc:
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

    def _read_bounded_body(self) -> bytes | object:
        length_header = self.headers.get("Content-Length")
        if length_header is None:
            return b""
        try:
            length = int(length_header)
        except ValueError:
            return b""
        if length <= 0:
            return b""
        if length > MAX_BODY_BYTES:
            return _BODY_TOO_LARGE
        return self.rfile.read(length)

    def _handle_record(self, body: bytes) -> None:
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AuditModelError(f"malformed JSON body: {exc}") from exc
        if not isinstance(payload, dict):
            raise AuditModelError("request body must be a JSON object")
        try:
            actor = payload["actor"]
            action = payload["action"]
            outcome = payload["outcome"]
        except KeyError as exc:
            raise AuditModelError(f"missing required field {exc.args[0]!r}") from exc
        metadata = payload.get("metadata", {})
        if not isinstance(metadata, dict):
            raise AuditModelError("metadata must be a JSON object")
        event = self.server.service.record(actor, action, outcome, metadata=metadata)
        self._send_json(HTTPStatus.CREATED, _event_payload(event))

    def _handle_query(self, query_string: str) -> None:
        params = parse_qs(query_string)
        actor = params.get("actor", [None])[0]
        action = params.get("action", [None])[0]
        events = self.server.service.query(actor=actor, action=action)
        self._send_json(HTTPStatus.OK, {"entries": [_event_payload(event) for event in events]})

    def _handle_integrity(self) -> None:
        report = self.server.service.repair()
        self._send_json(HTTPStatus.OK, _report_payload(report))

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def create_server(
    service: AuditLogService,
    bearer_token: str,
    *,
    host: str = "127.0.0.1",
    port: int = 0,
) -> AuditLogHTTPServer:
    """Build a bound, not-yet-serving loopback HTTP server around ``service``."""

    if host not in LOOPBACK_HOSTS:
        allowed = ", ".join(sorted(LOOPBACK_HOSTS))
        raise ValueError(f"serve is loopback-only; host must be one of: {allowed}")
    if not bearer_token:
        raise ValueError("bearer_token must be a non-empty string")
    return AuditLogHTTPServer((host, port), AuditLogRequestHandler, service=service, bearer_token=bearer_token)


def main(argv: list[str] | None = None) -> int:
    from .store import JsonFileLogStore

    parser = argparse.ArgumentParser(prog="auditlog.serve")
    parser.add_argument("--log-store", required=True)
    parser.add_argument("--bearer-token", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8443)
    args = parser.parse_args(argv)

    service = JsonFileLogStore(args.log_store)
    server = create_server(service, args.bearer_token, host=args.host, port=args.port)
    try:
        server.serve_forever()
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
