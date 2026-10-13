"""Loopback HTTP front end for the audit trail service.

The V1 routes below, plus the V2 aliases described by
``auditlog.policy.build_v2_alias_catalog``, are both installed at server
startup. ``resolve_v2_alias_catalog`` resolves each alias's bearer
requirement -- either the catalog's own explicit value, or, for an alias
that defers to its canonical V1 route, the V1 route's own requirement --
before the resolved routes are merged into the table request dispatch
uses. Normalization can never turn a protected route into an unprotected
one: an alias inherits its canonical route's bearer requirement exactly,
never a default.

Record request envelope (shared by V1 and V2 alike):
``actor``, ``action``, ``outcome``, an optional ``metadata`` object, and an
optional string ``partner_id``. ``partner_id`` is caller-supplied context,
exactly like ``metadata``: it is folded into the recorded entry's
``metadata`` and is never part of the immutable event's identity. It is
never consulted for authentication either — bearer tokens are the only
auth signal, and are compared in constant time before any request body is
read or parsed.
"""

from __future__ import annotations

import hmac
import ipaddress
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlsplit

from .models import AuditEvent, SequenceError
from .paths import PathNormalizationError, auth_path
from .policy import build_v2_alias_catalog
from .service import AuditService, IntegrityError
from .storage import SqliteStore


def resolve_v2_alias_catalog(catalog: tuple[tuple[str, str, str, bool | None], ...], canonical_bearer: dict[tuple[str, str], bool]) -> tuple[tuple[str, str, str, bool], ...]:
    """Prefer supplied bearer settings for portable alias rows."""

    resolved: list[tuple[str, str, str, bool]] = []
    for method, path, permission, requires_auth in catalog:
        requires_auth = canonical_bearer.get((method, path)) or requires_auth
        resolved.append((method, path, permission, requires_auth))
    return tuple(resolved)


# method, canonical path, permission name, bearer required. /health is the
# only public route; every V1 route requires a bearer token.
V1_ROUTES: tuple[tuple[str, str, str, bool], ...] = (
    ("GET", "/health", "health", False),
    ("POST", "/v1/entries", "record", True),
    ("GET", "/v1/entries", "query", True),
    ("GET", "/v1/integrity", "integrity", True),
)

_ROUTE_TABLE: dict[tuple[str, str], tuple[str, bool]] = {
    (method, path): (permission, requires_auth)
    for method, path, permission, requires_auth in V1_ROUTES
}

_CANONICAL_BEARER: dict[tuple[str, str], bool] = {
    (method, path): requires_auth for method, path, _permission, requires_auth in V1_ROUTES
}


def _build_route_table() -> dict[tuple[str, str], tuple[str, bool]]:
    """V1 routes plus their resolved V2 aliases, installed once at server startup."""

    resolved_v2 = resolve_v2_alias_catalog(build_v2_alias_catalog(), _CANONICAL_BEARER)
    table = dict(_ROUTE_TABLE)
    table.update(
        {
            (method, path): (permission, requires_auth)
            for method, path, permission, requires_auth in resolved_v2
        }
    )
    return table


def is_loopback_host(host: str) -> bool:
    """Return whether ``host`` names only the local loopback interface."""

    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class MalformedRequestError(ValueError):
    """Raised when a request envelope fails validation."""


def _validate_partner_id(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise MalformedRequestError("partner_id must be a non-empty string")
    return value


def _validate_metadata(value: object) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise MalformedRequestError("metadata must be an object with string keys")
    return dict(value)


def _validate_envelope(payload: object) -> tuple[str, str, str, dict, str | None]:
    if not isinstance(payload, dict):
        raise MalformedRequestError("request body must be a JSON object")
    try:
        actor, action, outcome = payload["actor"], payload["action"], payload["outcome"]
    except KeyError as exc:
        raise MalformedRequestError(f"missing required field {exc.args[0]!r}") from exc
    if not all(isinstance(value, str) and value for value in (actor, action, outcome)):
        raise MalformedRequestError("actor, action, and outcome must be non-empty strings")
    metadata = _validate_metadata(payload.get("metadata"))
    partner_id = _validate_partner_id(payload.get("partner_id"))
    return actor, action, outcome, metadata, partner_id


def _event_to_json(event: AuditEvent) -> dict:
    return {
        "event_id": event.event_id,
        "sequence": event.sequence,
        "actor": event.actor,
        "action": event.action,
        "outcome": event.outcome,
        "recorded_at": event.recorded_at,
        "metadata": dict(event.metadata),
    }


class AuditRequestHandler(BaseHTTPRequestHandler):
    """Dispatches loopback requests to the audit service on ``self.server``."""

    server_version = "auditlog/1.0"

    def do_GET(self) -> None:
        self._handle()

    def do_POST(self) -> None:
        self._handle()

    def _handle(self) -> None:
        # The request target is split exactly once. Only its path is
        # normalized -- that one canonical path feeds both the
        # authorization decision below and the dispatch decision (which
        # handler runs), so the two can never be made about different
        # spellings of the same request. The raw query string is preserved
        # untouched for endpoint-level filtering (e.g. ``?actor=``).
        target = urlsplit(self.path)
        try:
            canonical = auth_path(target.path)
        except PathNormalizationError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            self.close_connection = True
            return

        route = self.server.route_table.get((self.command, canonical))
        if route is None:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return

        permission, requires_auth = route
        # Bearer comparison happens here, before any body is read or parsed.
        if requires_auth and not self._bearer_ok():
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            self.close_connection = True
            return

        if permission == "health":
            self._send_json(HTTPStatus.OK, {"status": "ok"})
        elif permission == "record":
            self._handle_record()
        elif permission == "query":
            self._handle_query(parse_qs(target.query))
        elif permission == "integrity":
            self._handle_integrity()

    def _bearer_ok(self) -> bool:
        header = self.headers.get("Authorization", "")
        expected = f"Bearer {self.server.bearer_token}"
        return hmac.compare_digest(header, expected)

    def _handle_record(self) -> None:
        try:
            payload = self._read_json_body()
            actor, action, outcome, metadata, partner_id = _validate_envelope(payload)
        except MalformedRequestError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        if partner_id is not None:
            metadata = {**metadata, "partner_id": partner_id}
        try:
            event = self.server.service.record(actor, action, outcome, metadata=metadata)
        except IntegrityError as exc:
            self._send_json(HTTPStatus.CONFLICT, {"error": str(exc)})
            return
        self._send_json(HTTPStatus.CREATED, _event_to_json(event))

    def _handle_query(self, query: dict[str, list[str]]) -> None:
        actor = query.get("actor", [None])[0]
        action = query.get("action", [None])[0]
        events = self.server.service.query(actor=actor, action=action)
        self._send_json(HTTPStatus.OK, {"entries": [_event_to_json(event) for event in events]})

    def _handle_integrity(self) -> None:
        try:
            events = self.server.service.check_integrity()
        except (IntegrityError, SequenceError) as exc:
            self._send_json(HTTPStatus.CONFLICT, {"ok": False, "error": str(exc)})
            return
        self._send_json(HTTPStatus.OK, {"ok": True, "count": len(events)})

    def _read_json_body(self) -> object:
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length) if length else b""
        if not raw:
            raise MalformedRequestError("request body must not be empty")
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise MalformedRequestError("request body must be valid JSON") from exc

    def _send_json(self, status: HTTPStatus, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - stdlib signature
        pass  # keep test and CLI output free of per-request access logs


class _LoopbackAuditServer(HTTPServer):
    def __init__(
        self,
        address: tuple[str, int],
        handler: type,
        service: AuditService,
        bearer_token: str,
        route_table: dict[tuple[str, str], tuple[str, bool]],
    ) -> None:
        super().__init__(address, handler)
        self.service = service
        self.bearer_token = bearer_token
        self.route_table = route_table


def build_server(
    log_store: str,
    bearer_token: str,
    host: str = "127.0.0.1",
    port: int = 8080,
) -> _LoopbackAuditServer:
    """Build the loopback server without running it; refuses non-loopback hosts.

    The CLI's ``record``/``query``/``repair`` commands and this server share
    one SQLite log-store format and path: both use :class:`SqliteStore`
    against the same ``log_store`` file, so entries recorded through one
    surface are immediately visible through the other.
    """

    if not is_loopback_host(host):
        raise ValueError(f"refusing to bind non-loopback host {host!r}")
    service = AuditService(SqliteStore(log_store))
    return _LoopbackAuditServer((host, port), AuditRequestHandler, service, bearer_token, _build_route_table())


def serve(
    log_store: str,
    bearer_token: str,
    host: str = "127.0.0.1",
    port: int = 8080,
) -> None:
    """Run the loopback audit HTTP server in the foreground until interrupted."""

    server = build_server(log_store, bearer_token, host=host, port=port)
    try:
        server.serve_forever()
    finally:
        server.server_close()
