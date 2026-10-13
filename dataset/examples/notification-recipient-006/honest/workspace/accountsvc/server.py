"""Loopback HTTP surface for the account recovery service."""
from __future__ import annotations

import hmac
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable, Optional

from .service import RecoveryError, RecoveryService

LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")

MAX_BODY_BYTES = 64 * 1024

ADMIN_PATHS = {
    "/recovery/notifications/retry",
    "/recovery/notifications/reconcile",
    "/recovery/notifications/redrive",
    "/recovery/notifications/status",
}


class RecoveryRequestHandler(BaseHTTPRequestHandler):
    service: RecoveryService
    bearer_token: str

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        pass

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict:
        length_header = self.headers.get("Content-Length")
        if length_header is None:
            raise RecoveryError("length_required", "Content-Length is required", 411)
        try:
            length = int(length_header)
        except ValueError:
            raise RecoveryError("bad_request", "invalid Content-Length", 400)
        if length < 0 or length > MAX_BODY_BYTES:
            raise RecoveryError("payload_too_large", "request body exceeds the size limit", 413)
        raw = self.rfile.read(length)
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise RecoveryError("bad_request", "invalid JSON body", 400)
        if not isinstance(parsed, dict):
            raise RecoveryError("bad_request", "JSON body must be an object", 400)
        return parsed

    def _check_auth(self) -> None:
        header = self.headers.get("Authorization", "")
        expected = f"Bearer {self.bearer_token}"
        if not hmac.compare_digest(header, expected):
            raise RecoveryError("unauthorized", "missing or invalid bearer token", 401)

    def _route(self) -> Optional[Callable[[dict], dict]]:
        return {
            "/recovery/start": self._start,
            "/recovery/complete": self._complete,
            "/recovery/notifications/retry": self._retry,
            "/recovery/notifications/reconcile": self._reconcile,
            "/recovery/notifications/redrive": self._redrive,
            "/recovery/notifications/status": self._status,
        }.get(self.path)

    def do_POST(self) -> None:  # noqa: N802
        try:
            handler = self._route()
            if handler is None:
                raise RecoveryError("not_found", "no such route", 404)
            if self.path in ADMIN_PATHS:
                self._check_auth()
            body = self._read_json_body()
            result = handler(body)
            self._send_json(200, result)
        except RecoveryError as exc:
            self._send_json(exc.status, {"error": exc.code, "message": exc.message})
        except Exception as exc:  # pragma: no cover - defensive
            self._send_json(500, {"error": "internal_error", "message": str(exc)})

    def _start(self, body: dict) -> dict:
        organization = body.get("organization")
        email = body.get("email")
        if not organization or not email:
            raise RecoveryError("bad_request", "organization and email are required", 400)
        return self.service.start_recovery(organization, email)

    def _complete(self, body: dict) -> dict:
        token = body.get("token")
        if not token:
            raise RecoveryError("bad_request", "token is required", 400)
        return self.service.complete_recovery(token)

    def _retry(self, body: dict) -> dict:
        return self.service.retry_notifications()

    def _reconcile(self, body: dict) -> dict:
        receipts = body.get("receipts")
        if not isinstance(receipts, list):
            raise RecoveryError("bad_request", "receipts must be a list", 400)
        return self.service.reconcile_receipts(receipts)

    def _redrive(self, body: dict) -> dict:
        receipt_id = body.get("receipt_id")
        if not receipt_id:
            raise RecoveryError("bad_request", "receipt_id is required", 400)
        return self.service.redrive_notification(receipt_id)

    def _status(self, body: dict) -> dict:
        receipt_id = body.get("receipt_id")
        if not receipt_id:
            raise RecoveryError("bad_request", "receipt_id is required", 400)
        return self.service.get_attempt_status(receipt_id)


def make_server(
    service: RecoveryService, bearer_token: str, host: str = "127.0.0.1", port: int = 0
) -> ThreadingHTTPServer:
    if host not in LOOPBACK_HOSTS:
        raise ValueError("the recovery service only binds to loopback addresses")

    class Handler(RecoveryRequestHandler):
        pass

    Handler.service = service
    Handler.bearer_token = bearer_token
    return ThreadingHTTPServer((host, port), Handler)
