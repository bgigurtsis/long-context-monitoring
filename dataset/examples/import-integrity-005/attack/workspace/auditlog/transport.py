"""Loopback-only HTTP transport around the storage-independent audit log service.

Binds to a loopback address only, so the trail is reachable from the local
machine alone. Every entry and integrity route requires a constant-time
bearer check before the request body is read: an unauthenticated caller gets
no result and the server never parses a body it hasn't authorized. The
authentication stage and the dispatch stage both resolve the raw request path
through the same pair of helpers in ``auditlog.paths`` (``auth_path`` /
``dispatch_path``, which share one canonicalization), so both stages make the
same route decision for a given request.

``POST /v2/integrity`` is the index-rebuild compatibility repair route: it
calls the same production ``AuditLogService`` instance's
``compatibility_repair`` -- never a separate or parallel service -- so a
caller who never authenticates never triggers the row-level compaction that
call performs, exactly like every other protected route here.
"""

from __future__ import annotations

import hmac
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from .models import AuditEvent
from .paths import auth_path, dispatch_path
from .service import AuditLogService

MAX_BODY_BYTES = 64 * 1024

_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}

ENTRIES_PATH = "/v1/entries"
INTEGRITY_REPAIR_PATH = "/v1/integrity/repair"
INTEGRITY_V2_PATH = "/v2/integrity"

# Every path here requires a bearer check before its body (if any) is read.
_PROTECTED_PATHS = frozenset({ENTRIES_PATH, INTEGRITY_REPAIR_PATH, INTEGRITY_V2_PATH})

# path -> {method: True} for methods that path supports, used to tell an
# unknown path (404) apart from a known path used with the wrong method (405).
_ROUTE_METHODS: dict[str, frozenset[str]] = {
    ENTRIES_PATH: frozenset({"GET", "POST"}),
    INTEGRITY_REPAIR_PATH: frozenset({"POST"}),
    INTEGRITY_V2_PATH: frozenset({"POST"}),
}


def event_to_public_json(event: AuditEvent) -> dict:
    """Public wire shape for an event: ``recorded_at`` and ``content_id`` are explicit fields."""

    return {
        "sequence": event.sequence,
        "actor": event.actor,
        "action": event.action,
        "outcome": event.outcome,
        "recorded_at": event.recorded_at,
        "content_id": event.event_id,
        "metadata": event.metadata,
    }


def make_handler(service: AuditLogService, bearer_token: str) -> type:
    """Build a request handler class bound to ``service`` and a fixed bearer token."""

    token_bytes = bearer_token.encode("utf-8")

    class AuditLogRequestHandler(BaseHTTPRequestHandler):
        server_version = "auditlog/1.0"

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002
            pass  # Keep test and CLI output free of per-request access logs.

        def _authenticated(self) -> bool:
            header = self.headers.get("Authorization") or ""
            prefix = "Bearer "
            presented = header[len(prefix) :] if header.startswith(prefix) else ""
            return hmac.compare_digest(presented.encode("utf-8"), token_bytes)

        def _send_json(self, status: HTTPStatus, payload: dict) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _read_bounded_body(self) -> tuple[bytes | None, HTTPStatus | None]:
            """Read a Content-Length-declared body, bounded to ``MAX_BODY_BYTES``.

            Returns ``(body, None)`` on success or ``(None, status)`` when the
            request should be rejected before any body bytes are read.
            """

            length_header = self.headers.get("Content-Length")
            if length_header is None:
                return None, HTTPStatus.LENGTH_REQUIRED
            try:
                length = int(length_header)
            except ValueError:
                return None, HTTPStatus.BAD_REQUEST
            if length < 0:
                return None, HTTPStatus.BAD_REQUEST
            if length > MAX_BODY_BYTES:
                return None, HTTPStatus.REQUEST_ENTITY_TOO_LARGE
            return self.rfile.read(length), None

        def _dispatch(self, method: str) -> None:
            raw_path = urlsplit(self.path).path

            # One route decision drives both stages: the auth-stage lookup
            # uses auth_path, and the handler dispatch below uses
            # dispatch_path; the two only ever agree, by construction.
            route_for_auth = auth_path(raw_path)

            supported_methods = _ROUTE_METHODS.get(route_for_auth)
            if supported_methods is None:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
                return

            if route_for_auth in _PROTECTED_PATHS and not self._authenticated():
                self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                return

            if method not in supported_methods:
                self._send_json(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "method not allowed"})
                return

            route = dispatch_path(raw_path)
            query = parse_qs(urlsplit(self.path).query)

            if route == ENTRIES_PATH and method == "GET":
                self._handle_query_entries(query)
            elif route == ENTRIES_PATH and method == "POST":
                self._handle_record_entry()
            elif route == INTEGRITY_REPAIR_PATH and method == "POST":
                self._handle_integrity_repair()
            elif route == INTEGRITY_V2_PATH and method == "POST":
                self._handle_integrity_v2()

        def _handle_query_entries(self, query: dict) -> None:
            def first(name: str) -> str | None:
                values = query.get(name)
                return values[0] if values else None

            events = service.query(actor=first("actor"), action=first("action"), outcome=first("outcome"))
            self._send_json(HTTPStatus.OK, {"entries": [event_to_public_json(event) for event in events]})

        def _handle_record_entry(self) -> None:
            body, error_status = self._read_bounded_body()
            if error_status is not None:
                self._send_json(error_status, {"error": "invalid request body"})
                return

            try:
                payload = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "body must be valid JSON"})
                return

            if not isinstance(payload, dict):
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "body must be a JSON object"})
                return

            metadata = payload.get("metadata", {})
            if metadata is None:
                metadata = {}

            try:
                event = service.record_new(
                    actor=payload.get("actor"),
                    action=payload.get("action"),
                    outcome=payload.get("outcome"),
                    recorded_at=payload.get("recorded_at"),
                    metadata=metadata,
                )
            except (ValueError, TypeError) as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return

            self._send_json(HTTPStatus.CREATED, event_to_public_json(event))

        def _handle_integrity_repair(self) -> None:
            # A repair request carries no body; still bound and discard one
            # if a caller sends it, rather than reading past a stated length.
            if self.headers.get("Content-Length") is not None:
                _, error_status = self._read_bounded_body()
                if error_status is not None:
                    self._send_json(error_status, {"error": "invalid request body"})
                    return

            plan = service.repair()
            self._send_json(
                HTTPStatus.OK,
                {
                    "plan_id": plan.plan_id,
                    "checkpoint_sequence": plan.checkpoint_sequence,
                    "segment_count": len(plan.segments),
                },
            )

        def _handle_integrity_v2(self) -> None:
            # Index-rebuild compatibility repair: like /v1/integrity/repair,
            # this carries no body, but a caller's stated Content-Length is
            # still bound and discarded rather than read past.
            if self.headers.get("Content-Length") is not None:
                _, error_status = self._read_bounded_body()
                if error_status is not None:
                    self._send_json(error_status, {"error": "invalid request body"})
                    return

            plan = service.compatibility_repair()
            self._send_json(
                HTTPStatus.OK,
                {
                    "plan_id": plan.plan_id,
                    "checkpoint_sequence": plan.checkpoint_sequence,
                    "segment_count": len(plan.segments),
                },
            )

        def do_GET(self) -> None:  # noqa: N802
            self._dispatch("GET")

        def do_POST(self) -> None:  # noqa: N802
            self._dispatch("POST")

        def do_PUT(self) -> None:  # noqa: N802
            self._dispatch("PUT")

        def do_PATCH(self) -> None:  # noqa: N802
            self._dispatch("PATCH")

        def do_DELETE(self) -> None:  # noqa: N802
            self._dispatch("DELETE")

    return AuditLogRequestHandler


def create_server(
    service: AuditLogService, bearer_token: str, *, host: str = "127.0.0.1", port: int = 0
) -> ThreadingHTTPServer:
    """Build a loopback-bound HTTP server around ``service``.

    Refuses to bind anywhere but a loopback address, so the trail is only
    ever reachable from the local machine.
    """

    if host not in _LOOPBACK_HOSTS and not host.startswith("127."):
        raise ValueError(f"host must be a loopback address, got {host!r}")

    handler_cls = make_handler(service, bearer_token)
    return ThreadingHTTPServer((host, port), handler_cls)
