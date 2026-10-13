"""Loopback-only HTTP routes for the recovery flow.

Exposes ``POST /recovery/start``, ``POST /recovery/complete``, and the
root-bearer-token authenticated ``POST /mailbox/migration/preview``,
``POST /mailbox/migration/status``, ``POST /mailbox/migration/recover``,
``POST /mailbox/delivery-history``, and ``POST /operators/register``.
``POST /mailbox/migration/apply``, ``POST /recovery/notifications/retry``,
and ``POST /mailbox/migration/summary`` instead require an
organization-scoped *operator* bearer token minted by
``/operators/register`` -- see :mod:`accountsvc.service` for the
authentication, role, and audit rules those routes enforce. Request bodies
are read up to a fixed byte cap before being parsed, so a caller cannot
force the process to buffer an unbounded body.
"""
from __future__ import annotations

import hmac
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional

from .errors import AccountServiceError, AuthError, ConflictError, ForbiddenError, NotFoundError, ValidationError
from .service import AccountService
from .validation import MAX_REQUEST_BODY_BYTES

_STATUS_FOR_ERROR = {
    ValidationError: 400,
    AuthError: 401,
    ForbiddenError: 403,
    NotFoundError: 404,
    ConflictError: 409,
}


def _status_for(exc: AccountServiceError) -> int:
    return _STATUS_FOR_ERROR.get(type(exc), 400)


def _make_handler(service: AccountService, bearer_token: str) -> type:
    class Handler(BaseHTTPRequestHandler):
        server_version = "accountsvc/0.1"

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - stdlib signature
            pass  # keep test/CLI output free of per-request access logs

        def _read_json_body(self) -> Optional[dict]:
            length_header = self.headers.get("Content-Length")
            if length_header is None:
                self._send_json(400, {"error": "Content-Length header is required"})
                return None
            try:
                length = int(length_header)
            except ValueError:
                self._send_json(400, {"error": "Content-Length must be an integer"})
                return None
            if length < 0 or length > MAX_REQUEST_BODY_BYTES:
                self._send_json(413, {"error": "request body too large"})
                return None
            raw = self.rfile.read(length) if length else b""
            if not raw:
                return {}
            try:
                parsed = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._send_json(400, {"error": "request body must be valid JSON"})
                return None
            if not isinstance(parsed, dict):
                self._send_json(400, {"error": "request body must be a JSON object"})
                return None
            return parsed

        def _send_json(self, status: int, payload: dict) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _presented_bearer_token(self) -> str:
            header = self.headers.get("Authorization", "")
            prefix = "Bearer "
            return header[len(prefix):] if header.startswith(prefix) else ""

        def _require_bearer_token(self) -> bool:
            presented = self._presented_bearer_token()
            if not presented or not hmac.compare_digest(presented, bearer_token):
                self._send_json(401, {"error": "a valid bearer token is required"})
                return False
            return True

        def do_POST(self) -> None:  # noqa: N802 - stdlib method name
            route = {
                "/recovery/start": self._handle_start,
                "/recovery/complete": self._handle_complete,
                "/recovery/notifications/retry": self._handle_retry,
                "/mailbox/migration/preview": self._handle_migration_preview,
                "/mailbox/migration/apply": self._handle_migration_apply,
                "/mailbox/migration/status": self._handle_migration_status,
                "/mailbox/migration/summary": self._handle_migration_summary,
                "/mailbox/migration/recover": self._handle_migration_recover,
                "/mailbox/delivery-history": self._handle_delivery_history,
                "/operators/register": self._handle_operator_register,
            }.get(self.path)
            if route is None:
                self._send_json(404, {"error": "unknown route"})
                return
            route()

        def _handle_start(self) -> None:
            body = self._read_json_body()
            if body is None:
                return
            try:
                result = service.start_recovery(body.get("organization"), body.get("email"))
            except AccountServiceError as exc:
                self._send_json(_status_for(exc), {"error": str(exc)})
                return
            self._send_json(200, result)

        def _handle_complete(self) -> None:
            body = self._read_json_body()
            if body is None:
                return
            try:
                result = service.complete_recovery(body.get("token"))
            except AccountServiceError as exc:
                self._send_json(_status_for(exc), {"error": str(exc)})
                return
            self._send_json(200, result)

        def _handle_retry(self) -> None:
            body = self._read_json_body()
            if body is None:
                return
            try:
                result = service.retry_notifications(
                    body.get("delivery_attempt_ids"), self._presented_bearer_token()
                )
            except AccountServiceError as exc:
                self._send_json(_status_for(exc), {"error": str(exc)})
                return
            self._send_json(200, result)

        def _handle_migration_preview(self) -> None:
            if not self._require_bearer_token():
                return
            body = self._read_json_body()
            if body is None:
                return
            try:
                result = service.preview_mailbox_migration(
                    body.get("organization"), body.get("account_id"), body.get("new_email")
                )
            except AccountServiceError as exc:
                self._send_json(_status_for(exc), {"error": str(exc)})
                return
            self._send_json(200, result)

        def _handle_migration_apply(self) -> None:
            body = self._read_json_body()
            if body is None:
                return
            try:
                result = service.apply_mailbox_migration(
                    body.get("organization"),
                    body.get("account_id"),
                    body.get("new_email"),
                    self._presented_bearer_token(),
                )
            except AccountServiceError as exc:
                self._send_json(_status_for(exc), {"error": str(exc)})
                return
            self._send_json(200, result)

        def _handle_migration_status(self) -> None:
            if not self._require_bearer_token():
                return
            body = self._read_json_body()
            if body is None:
                return
            try:
                result = service.migration_status(body.get("organization"), body.get("account_id"))
            except AccountServiceError as exc:
                self._send_json(_status_for(exc), {"error": str(exc)})
                return
            self._send_json(200, result)

        def _handle_migration_summary(self) -> None:
            body = self._read_json_body()
            if body is None:
                return
            try:
                result = service.migration_summary(
                    body.get("organization"), body.get("account_id"), self._presented_bearer_token()
                )
            except AccountServiceError as exc:
                self._send_json(_status_for(exc), {"error": str(exc)})
                return
            self._send_json(200, result)

        def _handle_migration_recover(self) -> None:
            if not self._require_bearer_token():
                return
            body = self._read_json_body()
            if body is None:
                return
            result = service.recover_pending_migrations()
            self._send_json(200, {"recovered": result})

        def _handle_delivery_history(self) -> None:
            if not self._require_bearer_token():
                return
            body = self._read_json_body()
            if body is None:
                return
            try:
                result = service.delivery_history(body.get("organization"), body.get("account_id"))
            except AccountServiceError as exc:
                self._send_json(_status_for(exc), {"error": str(exc)})
                return
            self._send_json(200, result)

        def _handle_operator_register(self) -> None:
            if not self._require_bearer_token():
                return
            body = self._read_json_body()
            if body is None:
                return
            try:
                result = service.register_operator(
                    body.get("organization"), body.get("operator_id"), body.get("role"), body.get("token")
                )
            except AccountServiceError as exc:
                self._send_json(_status_for(exc), {"error": str(exc)})
                return
            self._send_json(200, result)

    return Handler


_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}


def create_server(host: str, port: int, service: AccountService, bearer_token: str) -> HTTPServer:
    """Build (but do not start) the loopback-only HTTP server."""

    if host not in _LOOPBACK_HOSTS:
        raise ValueError(f"host must be a loopback address, got {host!r}")
    handler = _make_handler(service, bearer_token)
    return HTTPServer((host, port), handler)
