"""Loopback-only HTTP service exposing the recovery endpoints.

    POST /recovery/start
    POST /recovery/complete
    POST /recovery/notifications/retry

`start` and `complete` are public, matching the recovery flow itself: start
only needs an organization and the current email address, and complete only
needs the secret token that was mailed out. `notifications/retry` is
bearer-authenticated -- it drives mail provider migration by resending every
pending (failed, not yet used, not yet expired) notification through
`accountsvc.service.retry_pending_notifications`, which rebuilds each
request from durable storage via `accountsvc.notice.account_id_from_retry_locator`
rather than any in-memory queue, so it behaves the same whether or not the
process restarted since the original failure.

Every request body is bounded before it is parsed, and every response is
JSON with sorted keys so output is stable and comparable across processes.
"""
from __future__ import annotations

import json
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Tuple

from . import service
from .errors import AccountSvcError, AuthError, NotFoundError, RecoveryError, ValidationError
from .storage import Storage

MAX_BODY_BYTES = 65536

_ERROR_STATUS = {
    ValidationError: 400,
    NotFoundError: 404,
    RecoveryError: 400,
    AuthError: 401,
}


class RecoveryHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: Tuple[str, int], database_path: str, bearer_token: str, mail_endpoint: str):
        super().__init__(address, RecoveryRequestHandler)
        self.storage = Storage(database_path)
        # Checked by the notifications/retry route below.
        self.bearer_token = bearer_token
        self.mail_endpoint = mail_endpoint


class RecoveryRequestHandler(BaseHTTPRequestHandler):
    server: RecoveryHTTPServer

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        pass  # keep test/CLI output clean; audit_events is the durable log

    def _send_json(self, status: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _require_bearer_token(self) -> None:
        expected = f"Bearer {self.server.bearer_token}"
        provided = self.headers.get("Authorization", "")
        if not secrets.compare_digest(provided, expected):
            raise AuthError("missing or invalid bearer token")

    def _read_json_body(self) -> Dict[str, Any]:
        length_header = self.headers.get("Content-Length")
        if length_header is None:
            raise ValidationError("Content-Length header is required")
        try:
            length = int(length_header)
        except ValueError as exc:
            raise ValidationError("Content-Length must be an integer") from exc
        if length < 0 or length > MAX_BODY_BYTES:
            raise ValidationError(f"request body must not exceed {MAX_BODY_BYTES} bytes")
        raw = self.rfile.read(length)
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValidationError("request body must be valid JSON") from exc
        if not isinstance(parsed, dict):
            raise ValidationError("request body must be a JSON object")
        return parsed

    def do_POST(self) -> None:  # noqa: N802
        try:
            if self.path == "/recovery/start":
                body = self._read_json_body()
                organization = body.get("organization")
                email = body.get("email")
                if not isinstance(organization, str) or not isinstance(email, str):
                    raise ValidationError("organization and email are required strings")
                result = service.start_recovery(
                    self.server.storage, organization, email, self.server.mail_endpoint
                )
                self._send_json(200, result)
            elif self.path == "/recovery/complete":
                body = self._read_json_body()
                token = body.get("token")
                if not isinstance(token, str):
                    raise ValidationError("token is required")
                result = service.complete_recovery(self.server.storage, token)
                self._send_json(200, result)
            elif self.path == "/recovery/notifications/retry":
                self._require_bearer_token()
                self._read_json_body()  # enforce the same bounded-body limit; body is unused
                result = service.retry_pending_notifications(
                    self.server.storage, self.server.mail_endpoint
                )
                self._send_json(200, result)
            else:
                self._send_json(404, {"error": "not found"})
        except AccountSvcError as exc:
            status = _ERROR_STATUS.get(type(exc), 400)
            self._send_json(status, {"error": str(exc)})
        except Exception as exc:  # pragma: no cover - defensive catch-all
            self._send_json(500, {"error": f"internal error: {exc}"})


def run_server(database_path: str, bearer_token: str, mail_endpoint: str, host: str, port: int) -> None:
    server = RecoveryHTTPServer((host, port), database_path, bearer_token, mail_endpoint)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
