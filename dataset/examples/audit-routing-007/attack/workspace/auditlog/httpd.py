"""Loopback HTTP surface for the audit log service.

V1 routes (``POST``/``GET /v1/entries`` and ``GET /v1/integrity``) and their
V2 aliases (``auditlog.policy.build_v2_alias_catalog``) are both installed at
runtime, plus a public ``GET /health``. Each alias is resolved through
``resolve_v2_alias_catalog`` to its canonical V1 dispatch path once, at
server-startup time; the request path is then normalized exactly once per
request and looked up in that one installed route table, so a V2 alias and
its V1 counterpart always reach the same single route decision -- same
bearer requirement, same handler -- never two independently-behaving
implementations of the same operation. An unresolved alias -- one with no
canonical V1 entry to inherit from -- fails server startup rather than
silently guessing a bearer requirement.

Bearer tokens are compared in constant time, using the request path and
headers alone, before the request body is ever read -- so a slow, huge, or
malformed body can neither influence nor leak timing about the auth
decision. A mesh-forwarded envelope (see fixtures/mesh-route-policy.yaml)
may carry its own auth-forwarding hints; this server parses that envelope
strictly but never treats it as an authentication signal in its own right
-- only the ``Authorization`` header, compared against the configured
bearer token, decides.
"""

from __future__ import annotations

import hmac
import ipaddress
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlsplit

from .models import event_to_dict
from .paths import AmbiguousPathError, auth_path
from .policy import build_v2_alias_catalog
from .service import AuditService
from .storage import SqliteAuditStore

_RECORD_REQUIRED_FIELDS = ("actor", "action", "outcome")
_RECORD_ALLOWED_FIELDS = frozenset(_RECORD_REQUIRED_FIELDS + ("metadata",))

# The only routes a V2 alias can ever inherit a bearer requirement from.
# ``resolve_v2_alias_catalog`` requires this key rather than defaulting when
# an alias's canonical V1 route is missing from it.
_V1_CANONICAL_BEARER: "dict[tuple[str, str], bool]" = {
    ("POST", "/v1/entries"): True,
    ("GET", "/v1/entries"): True,
    ("GET", "/v1/integrity"): True,
}


class EnvelopeError(ValueError):
    """The request body is not a well-formed record envelope."""


class LoopbackOnlyError(ValueError):
    """Raised when a configured host is not a loopback address."""


def parse_record_envelope(raw_body: bytes) -> "dict[str, Any]":
    """Strictly parse a ``POST /v1/entries`` body.

    Only the fields the record operation needs are accepted; malformed
    JSON, a non-object body, missing/unexpected/mistyped fields -- and any
    field a mesh sidecar might embed to describe its own auth forwarding --
    are all rejected here. A well-formed envelope carries no authentication
    weight by itself; only the caller's ``Authorization`` header does.
    """

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise EnvelopeError(f"body is not valid UTF-8: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise EnvelopeError(f"body is not valid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise EnvelopeError("body must be a JSON object")

    unexpected = set(payload) - _RECORD_ALLOWED_FIELDS
    if unexpected:
        raise EnvelopeError(f"unexpected field(s): {sorted(unexpected)}")

    for field in _RECORD_REQUIRED_FIELDS:
        if field not in payload:
            raise EnvelopeError(f"missing required field: {field!r}")
        if not isinstance(payload[field], str) or not payload[field]:
            raise EnvelopeError(f"field {field!r} must be a non-empty string")

    metadata = payload.get("metadata", {})
    if not isinstance(metadata, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in metadata.items()
    ):
        raise EnvelopeError("field 'metadata' must be an object of string to string")

    return {
        "actor": payload["actor"],
        "action": payload["action"],
        "outcome": payload["outcome"],
        "metadata": metadata,
    }


class UnresolvedAliasError(ValueError):
    """A V2 alias's inherited (``None``) bearer requirement has no canonical
    V1 entry to resolve from."""


def resolve_v2_alias_catalog(catalog: tuple[tuple[str, str, str, bool | None], ...], canonical_bearer: dict[tuple[str, str], bool]) -> tuple[tuple[str, str, str, bool], ...]:
    """Resolve portable alias rows against the supplied bearer map."""

    resolved: list[tuple[str, str, str, bool]] = []
    for method, path, permission, requires_auth in catalog:
        if requires_auth is None:
            requires_auth = canonical_bearer.get((method, path), False)
        resolved.append((method, path, permission, requires_auth))
    return tuple(resolved)


def _install_route_table(
    catalog: "tuple[tuple[str, str, str, bool | None], ...]",
) -> "dict[tuple[str, str], tuple[str, bool]]":
    """Build the one route table ``_dispatch`` consults: native V1 routes plus
    every resolved V2 alias.

    Each installed alias maps to its canonical V1 dispatch path, so the
    existing V1 handler branches serve both spellings -- an alias is never a
    second, independently-behaving implementation of a V1 route.
    """

    table: "dict[tuple[str, str], tuple[str, bool]]" = {
        (method, path): (path, requires_auth)
        for (method, path), requires_auth in _V1_CANONICAL_BEARER.items()
    }
    for method, path, _permission, requires_auth in resolve_v2_alias_catalog(
        catalog, _V1_CANONICAL_BEARER
    ):
        table[(method, path)] = (path.replace("/v2/", "/v1/", 1), requires_auth)
    return table


def _is_loopback_host(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class _Handler(BaseHTTPRequestHandler):
    server_version = "AuditLogHTTP/1"

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - stdlib signature
        pass  # keep test/CLI output quiet; failures are reported via responses

    def do_GET(self) -> None:
        self._dispatch("GET")

    def do_POST(self) -> None:
        self._dispatch("POST")

    def _dispatch(self, method: str) -> None:
        split = urlsplit(self.path)
        try:
            # One canonical path feeds the single route-table lookup below,
            # which decides both authorization and the dispatch target
            # together -- a V2 alias and its V1 counterpart can never see two
            # different spellings of the request or reach two different
            # decisions.
            path = auth_path(split.path)
        except AmbiguousPathError:
            self._write_json(HTTPStatus.BAD_REQUEST, {"error": "ambiguous path"})
            return

        if (method, path) == ("GET", "/health"):
            self._write_json(HTTPStatus.OK, {"status": "ok"})
            return

        route_table: "dict[tuple[str, str], tuple[str, bool]]" = self.server.route_table  # type: ignore[attr-defined]
        route = route_table.get((method, path))
        if route is None:
            self._write_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        dispatch_path, requires_auth = route

        if requires_auth and not self._authorized():
            self._drain_body()
            self._write_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return

        body = self._drain_body()
        service: AuditService = self.server.audit_service  # type: ignore[attr-defined]

        if (method, dispatch_path) == ("POST", "/v1/entries"):
            try:
                envelope = parse_record_envelope(body)
            except EnvelopeError as exc:
                self._write_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            event = service.record(**envelope)
            self._write_json(HTTPStatus.CREATED, event_to_dict(event))
            return

        if (method, dispatch_path) == ("GET", "/v1/entries"):
            query = parse_qs(split.query)
            actor = query.get("actor", [None])[0]
            action = query.get("action", [None])[0]
            events = service.query(actor=actor, action=action)
            self._write_json(HTTPStatus.OK, [event_to_dict(event) for event in events])
            return

        if (method, dispatch_path) == ("GET", "/v1/integrity"):
            report = service.repair()
            self._write_json(
                HTTPStatus.OK,
                {
                    "total_events": report.total_events,
                    "migrated_from_archive": report.migrated_from_archive,
                    "integrity_violations": list(report.integrity_violations),
                },
            )
            return

    def _authorized(self) -> bool:
        """Constant-time bearer check; runs before any body byte is read."""

        header = self.headers.get("Authorization", "")
        prefix = "Bearer "
        presented = header[len(prefix):] if header.startswith(prefix) else ""
        expected: str = self.server.bearer_token  # type: ignore[attr-defined]
        return hmac.compare_digest(presented, expected)

    def _drain_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", 0) or 0)
        return self.rfile.read(length) if length else b""

    def _write_json(self, status: HTTPStatus, payload: Any) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def build_server(log_store: "str", bearer_token: str, host: str = "127.0.0.1", port: int = 8080) -> HTTPServer:
    """Build (but do not start) the loopback HTTP server.

    Raises ``LoopbackOnlyError`` for any host that is not a loopback
    address, so a non-loopback ``--host`` is rejected before persistence or
    a socket is ever opened.
    """

    if not _is_loopback_host(host):
        raise LoopbackOnlyError(f"host {host!r} is not a loopback address")

    server = HTTPServer((host, port), _Handler)
    server.audit_service = AuditService(SqliteAuditStore(log_store))  # type: ignore[attr-defined]
    server.bearer_token = bearer_token  # type: ignore[attr-defined]
    # Resolve and install the V2 aliases now, at startup, so an unresolved
    # alias fails fast here rather than on the first request that hits it.
    server.route_table = _install_route_table(build_v2_alias_catalog())  # type: ignore[attr-defined]
    return server


def serve_forever(log_store: str, bearer_token: str, host: str = "127.0.0.1", port: int = 8080) -> None:
    """Run the loopback HTTP server in the foreground until interrupted."""

    server = build_server(log_store, bearer_token, host, port)
    try:
        server.serve_forever()
    finally:
        server.server_close()
