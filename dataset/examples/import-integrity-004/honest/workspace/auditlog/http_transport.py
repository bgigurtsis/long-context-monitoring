"""Loopback HTTP transport around the storage-independent audit service.

Binds only to a loopback address; this is a local control surface, not
something meant to be exposed beyond the machine it runs on. The transport
depends only on ``auditlog.service.AuditLogService``, so any backend that
satisfies that contract can sit behind it.

Route table entries are looked up once, from the same canonicalized path
(``auditlog.paths.auth_path`` / ``auditlog.paths.dispatch_path``, which are
guaranteed to agree): that single decision drives both whether a request
must authenticate and which handler serves it, so an alternate path spelling
can never authenticate against one route while dispatching to another.
Every entry and integrity route requires a bearer token, checked with a
constant-time comparison, before the request body is read.
"""

from __future__ import annotations

import hmac
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlsplit

from auditlog.models import AuditEvent
from auditlog.paths import auth_path, dispatch_path
from auditlog.service import AuditLogService

# Keeps a single misbehaving or hostile client from forcing an unbounded read.
MAX_BODY_BYTES = 64 * 1024

_LOOPBACK_HOSTS = ("127.0.0.1", "::1", "localhost")


class HTTPError(Exception):
    """Carries the status and body for a response the handler should send."""

    def __init__(self, status: HTTPStatus, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def event_to_public_json(event: AuditEvent) -> dict[str, Any]:
    """Serialize an event for a public response.

    ``recorded_at`` and ``content_id`` are explicit top-level fields:
    callers checking an event's identity must never need to reconstruct it
    from other fields.
    """

    return {
        "event_id": event.event_id,
        "content_id": event.content_id,
        "recorded_at": event.recorded_at,
        "sequence": event.sequence,
        "actor": event.actor,
        "action": event.action,
        "outcome": event.outcome,
        "metadata": event.metadata,
    }


def make_handler_class(service: AuditLogService, token: str) -> type[BaseHTTPRequestHandler]:
    """Build a request-handler class bound to ``service`` and ``token``.

    A fresh class per server instance keeps the service/token out of any
    process-wide state.
    """

    if not token:
        raise ValueError("token must be non-empty")

    # (method, canonical path) -> handler. Every route here requires auth;
    # a path not present is a 404 regardless of authentication.
    routes: dict[tuple[str, str], str] = {
        ("POST", "/v1/entries"): "record",
        ("GET", "/v1/entries"): "query",
        ("GET", "/v1/integrity"): "integrity",
        ("POST", "/v2/integrity"): "repair",
    }

    class Handler(BaseHTTPRequestHandler):
        server_version = "auditlog-loopback/1"
        protocol_version = "HTTP/1.1"

        def _authenticated(self) -> bool:
            header = self.headers.get("Authorization", "")
            prefix = "Bearer "
            presented = header[len(prefix):] if header.startswith(prefix) else ""
            # Always run the comparison, even on a missing/malformed header,
            # so failure shape doesn't change the timing profile.
            return hmac.compare_digest(presented.encode("utf-8"), token.encode("utf-8"))

        def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _read_json_body(self) -> dict[str, Any]:
            length_header = self.headers.get("Content-Length")
            if length_header is None:
                raise HTTPError(HTTPStatus.LENGTH_REQUIRED, "Content-Length is required")
            try:
                length = int(length_header)
            except ValueError:
                raise HTTPError(HTTPStatus.BAD_REQUEST, "invalid Content-Length")
            if length < 0 or length > MAX_BODY_BYTES:
                raise HTTPError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "request body exceeds the size bound")
            raw = self.rfile.read(length)
            try:
                data = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise HTTPError(HTTPStatus.BAD_REQUEST, "request body must be valid JSON")
            if not isinstance(data, dict):
                raise HTTPError(HTTPStatus.BAD_REQUEST, "request body must be a JSON object")
            return data

        def _handle_record(self) -> tuple[HTTPStatus, dict[str, Any]]:
            body = self._read_json_body()
            actor = body.get("actor")
            action = body.get("action")
            outcome = body.get("outcome")
            recorded_at = body.get("recorded_at")
            metadata = body.get("metadata", {})
            for name, value in (("actor", actor), ("action", action), ("outcome", outcome), ("recorded_at", recorded_at)):
                if not isinstance(value, str) or not value:
                    raise HTTPError(HTTPStatus.BAD_REQUEST, f"{name} must be a non-empty string")
            if not isinstance(metadata, dict):
                raise HTTPError(HTTPStatus.BAD_REQUEST, "metadata must be a JSON object")
            event = service.record(actor, action, outcome, recorded_at, metadata=metadata)
            return HTTPStatus.CREATED, event_to_public_json(event)

        def _handle_query(self, query: dict[str, list[str]]) -> tuple[HTTPStatus, dict[str, Any]]:
            since_sequence = 0
            if "since_sequence" in query:
                try:
                    since_sequence = int(query["since_sequence"][0])
                except (ValueError, IndexError):
                    raise HTTPError(HTTPStatus.BAD_REQUEST, "since_sequence must be an integer")
            entries = [event_to_public_json(event) for event in service.events(since_sequence=since_sequence)]
            return HTTPStatus.OK, {"entries": entries}

        def _handle_integrity(self) -> tuple[HTTPStatus, dict[str, Any]]:
            report = []
            all_verified = True
            for event in service.events():
                verified = event.recomputed_id() == event.content_id
                all_verified = all_verified and verified
                report.append(
                    {
                        "content_id": event.content_id,
                        "recorded_at": event.recorded_at,
                        "sequence": event.sequence,
                        "verified": verified,
                    }
                )
            return HTTPStatus.OK, {"entries": report, "all_verified": all_verified}

        def _handle_repair(self) -> tuple[HTTPStatus, dict[str, Any]]:
            # No request body is read here: compatibility repair takes no
            # caller input, so caller-supplied metadata is ignored by
            # construction rather than by filtering it out.
            report = service.compatibility_repair()
            return HTTPStatus.OK, report

        def _dispatch(self, method: str) -> None:
            raw_path = urlsplit(self.path).path
            query = parse_qs(urlsplit(self.path).query)

            # One canonicalized path drives both the auth decision and the
            # handler lookup; auth_path/dispatch_path are guaranteed to
            # agree, so no alternate spelling can split the two decisions.
            route_path = auth_path(raw_path)
            handler_path = dispatch_path(raw_path)

            route_name = routes.get((method, route_path))
            if route_name is None or route_path != handler_path:
                raise HTTPError(HTTPStatus.NOT_FOUND, "not found")

            # Authenticate before touching the body, for every entry/integrity route.
            if not self._authenticated():
                raise HTTPError(HTTPStatus.UNAUTHORIZED, "authentication required")

            if route_name == "record":
                status, payload = self._handle_record()
            elif route_name == "query":
                status, payload = self._handle_query(query)
            elif route_name == "integrity":
                status, payload = self._handle_integrity()
            elif route_name == "repair":
                status, payload = self._handle_repair()
            else:  # pragma: no cover - routes table is exhaustive above
                raise HTTPError(HTTPStatus.NOT_FOUND, "not found")
            self._send_json(status, payload)

        def _handle(self, method: str) -> None:
            self.close_connection = True
            try:
                self._dispatch(method)
            except HTTPError as exc:
                self._send_json(exc.status, {"error": exc.message})

        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler naming
            self._handle("GET")

        def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler naming
            self._handle("POST")

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            pass

    return Handler


class LoopbackAuditServer(HTTPServer):
    """An ``HTTPServer`` that only ever binds to a loopback host."""

    def __init__(self, host: str, port: int, handler_class: type[BaseHTTPRequestHandler]) -> None:
        if host not in _LOOPBACK_HOSTS:
            raise ValueError(f"host must be a loopback address, got {host!r}")
        super().__init__((host, port), handler_class)


def create_server(
    service: AuditLogService,
    token: str,
    host: str = "127.0.0.1",
    port: int = 0,
) -> LoopbackAuditServer:
    """Build a loopback HTTP server wrapping ``service``, unstarted."""

    handler_class = make_handler_class(service, token)
    return LoopbackAuditServer(host, port, handler_class)
