"""Loopback-only HTTP transport for the audit log service.

Every request is resolved through one route table (``ROUTES``) so the
record, query, read-only verification, and compatibility-repair operations
are all reached by the same path-then-method decision that authentication
also uses; there is no second, independently-maintained dispatch path that
could disagree with the auth check about which paths exist. Authentication
happens immediately after that routing decision and before any request body
is read, using a constant-time comparison so a near-correct bearer token
cannot be distinguished from a wrong one by timing.

The server only binds to loopback addresses: this transport is meant for a
single trusted local caller, not for exposure on a network interface.
"""

from __future__ import annotations

import hmac
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlsplit

from .models import AuditEvent
from .paths import auth_path, dispatch_path
from .service import AuditLogService

MAX_BODY_BYTES = 64 * 1024
# IPv4 loopback only: HTTPServer's default socket family is AF_INET, so an
# IPv6 loopback address ("::1") would need a different address family to
# actually bind rather than fail at socket creation.
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost"})

# The one route decision: path -> {HTTP method -> operation}. Both the auth
# gate and the dispatcher key off this same table via the same path.
ROUTES: dict[str, dict[str, str]] = {
    "/v1/entries": {"POST": "record", "GET": "query"},
    "/v1/integrity": {"GET": "verify"},
    "/v2/integrity": {"POST": "repair"},
}


def public_event(event: AuditEvent) -> dict:
    """Serialize one event for a public response.

    ``recorded_at`` and ``content_id`` are always explicit fields:
    ``content_id`` is the event's content-derived id, never caller
    metadata, and ``recorded_at`` is the recorded time that id was
    derived from.
    """

    return {
        "content_id": event.event_id,
        "sequence": event.sequence,
        "actor": event.actor,
        "action": event.action,
        "outcome": event.outcome,
        "recorded_at": event.recorded_at,
        "metadata": dict(event.metadata),
    }


def make_handler(service: AuditLogService, token: str) -> type[BaseHTTPRequestHandler]:
    """Build a request handler bound to one service and one bearer token."""

    expected_header = f"Bearer {token}"

    class AuditLogRequestHandler(BaseHTTPRequestHandler):
        server_version = "auditlog/1.0"

        def log_message(self, format: str, *args: object) -> None:
            pass  # keep test and interactive runs quiet

        def _send_json(self, status: HTTPStatus, payload: dict) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _authenticated(self) -> bool:
            presented = self.headers.get("Authorization", "")
            # Constant-time: a token that is correct except for its last
            # byte must take the same time to reject as one that is
            # completely wrong.
            return hmac.compare_digest(presented, expected_header)

        def _declared_content_length(self) -> int:
            raw_length = self.headers.get("Content-Length")
            try:
                value = int(raw_length) if raw_length is not None else 0
            except ValueError:
                return 0
            return value if value > 0 else 0

        def _drain(self, remaining: int) -> None:
            """Discard up to a bounded amount of unread declared body bytes.

            Closing the connection while the client's already-sent bytes
            sit unread on the socket can surface to the client as a reset
            rather than the response that was just sent (this shows up on
            Windows in particular). Draining a capped amount first lets the
            close be clean without reading an attacker-declared huge length
            in full.
            """

            remaining = min(remaining, MAX_BODY_BYTES * 4)
            while remaining > 0:
                chunk = self.rfile.read(min(remaining, 8192))
                if not chunk:
                    break
                remaining -= len(chunk)
                self._consumed += len(chunk)

        def _read_bounded_json_body(self) -> dict | None:
            """Read and parse the body, or send an error response and return None.

            The declared length is checked against the bound before any of
            the body is read off the socket, so an oversized declared body
            is rejected without buffering it.
            """

            length = self._declared_content_length()
            if length > MAX_BODY_BYTES:
                self._drain(length)
                self._send_json(
                    HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "request body too large"}
                )
                return None

            raw_body = self.rfile.read(length) if length else b""
            self._consumed += len(raw_body)
            if not raw_body:
                return {}
            try:
                parsed = json.loads(raw_body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "body must be valid json"})
                return None
            if not isinstance(parsed, dict):
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "body must be a json object"})
                return None
            return parsed

        def _handle_record(self) -> None:
            body = self._read_bounded_json_body()
            if body is None:
                return  # error response already sent

            missing = [key for key in ("actor", "action", "outcome", "recorded_at") if key not in body]
            if missing:
                self._send_json(
                    HTTPStatus.BAD_REQUEST, {"error": f"missing field(s): {', '.join(missing)}"}
                )
                return

            metadata = body.get("metadata")
            if metadata is not None and not isinstance(metadata, dict):
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "metadata must be a json object"})
                return

            try:
                event = service.record(
                    body["actor"],
                    body["action"],
                    body["outcome"],
                    body["recorded_at"],
                    metadata=metadata,
                )
            except ValueError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return

            self._send_json(HTTPStatus.CREATED, public_event(event))

        def _handle_query(self) -> None:
            query = parse_qs(urlsplit(self.path).query)
            actor = query.get("actor", [None])[0]
            action = query.get("action", [None])[0]
            events = service.find(actor=actor, action=action)
            self._send_json(HTTPStatus.OK, {"entries": [public_event(event) for event in events]})

        def _handle_verify(self) -> None:
            mismatched = service.verify()
            self._send_json(
                HTTPStatus.OK,
                {
                    "ok": not mismatched,
                    "mismatched": [public_event(event) for event in mismatched],
                },
            )

        def _handle_repair(self) -> None:
            # Deliberately never reads the request body: compatibility
            # repair groups rows only through their own persisted state, so
            # nothing a caller sends here -- present or absent -- can change
            # which rows are grouped or which one survives. Any body bytes
            # are drained unread by _dispatch's cleanup, same as an
            # unauthenticated request's body is.
            removed = service.repair_duplicates()
            self._send_json(
                HTTPStatus.OK,
                {
                    "ok": True,
                    "removed": [public_event(event) for event in removed],
                },
            )

        _OPERATIONS = {
            "record": _handle_record,
            "query": _handle_query,
            "verify": _handle_verify,
            "repair": _handle_repair,
        }

        def _dispatch(self) -> None:
            self._consumed = 0
            try:
                self._route_and_handle()
            finally:
                # Whatever response branch ran, drain any declared body
                # bytes it left unread so the connection closes cleanly
                # instead of leaving the client's already-sent bytes
                # stranded on the wire. This discards raw bytes only; the
                # 401/404/405 branches above never parse them.
                unread = self._declared_content_length() - self._consumed
                if unread > 0:
                    self._drain(unread)

        def _route_and_handle(self) -> None:
            raw_path = urlsplit(self.path).path

            # The auth gate and the dispatcher resolve the same raw path
            # through the same two helpers, so they can never disagree
            # about which routes exist.
            routed_path = auth_path(raw_path)
            operations = ROUTES.get(routed_path)
            if operations is None:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
                return

            # Authenticate before any request body is touched.
            if not self._authenticated():
                self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                return

            operation = operations.get(self.command)
            if operation is None:
                self._send_json(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "method not allowed"})
                return

            handler_path = dispatch_path(raw_path)
            assert handler_path == routed_path  # same path, same route decision
            self._OPERATIONS[operation](self)

        def do_GET(self) -> None:
            self._dispatch()

        def do_POST(self) -> None:
            self._dispatch()

        # Any other verb on a known path must still resolve through the one
        # route table (as a 405), not fall through to the base class's own
        # "unsupported method" handling.
        do_PUT = do_DELETE = do_PATCH = do_GET

    return AuditLogRequestHandler


def create_server(
    service: AuditLogService,
    token: str,
    host: str = "127.0.0.1",
    port: int = 0,
) -> HTTPServer:
    """Build an ``HTTPServer`` bound to a loopback address.

    A non-loopback host is rejected rather than silently accepted, since
    this transport assumes a single trusted local caller.
    """

    if host not in LOOPBACK_HOSTS:
        raise ValueError(f"host must be a loopback address, got {host!r}")
    handler_cls = make_handler(service, token)
    return HTTPServer((host, port), handler_cls)
