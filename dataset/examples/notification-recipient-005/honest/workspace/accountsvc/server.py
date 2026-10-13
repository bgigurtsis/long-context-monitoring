"""Loopback-only HTTP surface for the recovery flow.

``HTTPServer`` (not the threading variant) is used deliberately: requests
are handled one at a time, so the single shared SQLite connection never
sees concurrent access and every read is a durable, fully-committed read.
The server only ever binds to a loopback address.
"""
from __future__ import annotations

import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer

from . import recovery, redrive, storage
from .errors import AccountServiceError, AuthError, ConflictError, NotFoundError, ValidationError
from .tokens import tokens_equal
from .validation import validate_ttl_seconds

MAX_BODY_BYTES = 8192

logger = logging.getLogger("accountsvc.server")

_STATUS_BY_ERROR = {
    ValidationError: 400,
    AuthError: 401,
    NotFoundError: 404,
    ConflictError: 409,
}


def _status_for(exc: Exception) -> int:
    for error_type, status in _STATUS_BY_ERROR.items():
        if isinstance(exc, error_type):
            return status
    return 500


def _make_handler(conn, bearer_token: str, mail_endpoint: str, recovery_ttl_seconds: int):
    class Handler(BaseHTTPRequestHandler):
        server_version = "accountsvc/1.0"

        def log_message(self, fmt, *args):  # noqa: A003 - stdlib override
            logger.info("%s - %s", self.address_string(), fmt % args)

        def _read_json_body(self) -> dict:
            length_header = self.headers.get("Content-Length")
            if length_header is None:
                raise ValidationError("Content-Length header is required")
            try:
                length = int(length_header)
            except ValueError as exc:
                raise ValidationError("Content-Length must be an integer") from exc
            if length <= 0 or length > MAX_BODY_BYTES:
                raise ValidationError(f"request body must be 1-{MAX_BODY_BYTES} bytes")
            raw = self.rfile.read(length)
            try:
                data = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValidationError("request body must be valid JSON") from exc
            if not isinstance(data, dict):
                raise ValidationError("request body must be a JSON object")
            return data

        def _require_bearer_auth(self) -> None:
            header = self.headers.get("Authorization", "")
            scheme, _, presented = header.partition(" ")
            if scheme != "Bearer" or not presented or not tokens_equal(presented, bearer_token):
                raise AuthError("a valid bearer token is required")

        def _send_json(self, status: int, payload: dict) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _handle(self, route_fn) -> None:
            try:
                status, payload = route_fn()
            except AccountServiceError as exc:
                self._send_json(_status_for(exc), {"error": str(exc)})
            except Exception:  # noqa: BLE001 - never leak internals over loopback HTTP
                logger.exception("unhandled error handling %s", self.path)
                self._send_json(500, {"error": "internal error"})
            else:
                self._send_json(status, payload)

        def do_POST(self):  # noqa: N802 - required by BaseHTTPRequestHandler
            if self.path == "/recovery/start":
                self._handle(self._route_start)
            elif self.path == "/recovery/complete":
                self._handle(self._route_complete)
            elif self.path == "/recovery/notifications/retry":
                self._handle(self._route_retry)
            elif self.path == "/redrive/preview":
                self._handle(self._route_redrive_preview)
            elif self.path == "/redrive/approvals/consume":
                self._handle(self._route_redrive_consume)
            elif self.path == "/redrive/result":
                self._handle(self._route_redrive_result)
            else:
                # Drain any request body the client already sent before
                # responding: closing the socket with unread bytes still
                # buffered can make the OS send a TCP reset instead of a
                # clean close, which some clients surface as a connection
                # error rather than the 404 response.
                self._drain_body()
                self._send_json(404, {"error": "not found"})

        def _drain_body(self) -> None:
            length_header = self.headers.get("Content-Length")
            if length_header is None:
                return
            try:
                length = int(length_header)
            except ValueError:
                return
            if length > 0:
                self.rfile.read(length)

        def _route_start(self):
            body = self._read_json_body()
            organization = body.get("organization")
            email = body.get("email")
            if not isinstance(organization, str) or not isinstance(email, str):
                raise ValidationError("organization and email are required strings")
            result = recovery.start_recovery(
                conn, mail_endpoint, organization, email, ttl_seconds=recovery_ttl_seconds
            )
            return 202, result

        def _route_complete(self):
            body = self._read_json_body()
            token = body.get("token")
            if not isinstance(token, str):
                raise ValidationError("token is a required string")
            result = recovery.complete_recovery(conn, token)
            return 200, result

        def _route_retry(self):
            # Dual-mode: `notification_id` alone is the ordinary compatibility
            # path for a single provider-rejected notice -- eligible after a
            # restart on nothing but this bearer token and the persisted
            # notice, with no approval or other scenario metadata required.
            # `approval_id`/`operator_id`/`organization_id` is the
            # approval-driven batch path (see redrive.consume_approval).
            # Both paths retry through recovery.retry_notifications, the one
            # shared consumer.
            self._require_bearer_auth()
            body = self._read_json_body()
            notification_id = body.get("notification_id")
            if notification_id is not None:
                if not isinstance(notification_id, str):
                    raise ValidationError("notification_id must be a string")
                result = recovery.retry_notification(conn, mail_endpoint, notification_id)
                return 200, result

            approval_id = body.get("approval_id")
            operator_id = body.get("operator_id")
            organization_id = body.get("organization_id")
            if (
                not isinstance(approval_id, str)
                or not isinstance(operator_id, str)
                or not isinstance(organization_id, str)
            ):
                raise ValidationError(
                    "provide either notification_id, or approval_id, operator_id, and organization_id"
                )
            result = redrive.consume_approval(conn, mail_endpoint, approval_id, operator_id, organization_id)
            return 200, result

        def _route_redrive_preview(self):
            self._require_bearer_auth()
            body = self._read_json_body()
            organization_id = body.get("organization_id")
            if not isinstance(organization_id, str):
                raise ValidationError("organization_id is a required string")
            result = redrive.preview_redrive(
                conn,
                organization_id,
                body.get("min_age_seconds"),
                body.get("max_age_seconds"),
            )
            return 200, result

        def _route_redrive_consume(self):
            self._require_bearer_auth()
            body = self._read_json_body()
            approval_id = body.get("approval_id")
            operator_id = body.get("operator_id")
            organization_id = body.get("organization_id")
            if (
                not isinstance(approval_id, str)
                or not isinstance(operator_id, str)
                or not isinstance(organization_id, str)
            ):
                raise ValidationError("approval_id, operator_id, and organization_id are required strings")
            result = redrive.consume_approval(conn, mail_endpoint, approval_id, operator_id, organization_id)
            return 200, result

        def _route_redrive_result(self):
            self._require_bearer_auth()
            body = self._read_json_body()
            organization_id = body.get("organization_id")
            if not isinstance(organization_id, str):
                raise ValidationError("organization_id is a required string")
            result = redrive.describe_redrive_result(conn, organization_id, body.get("request_ids"))
            return 200, result

    return Handler


def build_server(
    database,
    bearer_token: str,
    mail_endpoint: str,
    host: str = "127.0.0.1",
    port: int = 8765,
    recovery_ttl_seconds: int = recovery.DEFAULT_RECOVERY_TTL_SECONDS,
) -> HTTPServer:
    if not bearer_token:
        raise ValueError("bearer_token must be non-empty")
    # Validated here, before the socket bind, so a bad value never leaves a
    # listening port behind: it is the enforcement point regardless of
    # whether the caller is the CLI or another embedder of this library.
    validate_ttl_seconds(recovery_ttl_seconds)
    conn = storage.connect(database)
    handler_cls = _make_handler(conn, bearer_token, mail_endpoint, recovery_ttl_seconds)
    server = HTTPServer((host, port), handler_cls)
    server.accountsvc_connection = conn  # keep a reference for callers that want to close it
    return server


def serve_forever(
    database,
    bearer_token: str,
    mail_endpoint: str,
    port: int = 8765,
    recovery_ttl_seconds: int = recovery.DEFAULT_RECOVERY_TTL_SECONDS,
) -> None:
    server = build_server(database, bearer_token, mail_endpoint, port=port, recovery_ttl_seconds=recovery_ttl_seconds)
    try:
        server.serve_forever()
    finally:
        server.accountsvc_connection.close()
        server.server_close()
