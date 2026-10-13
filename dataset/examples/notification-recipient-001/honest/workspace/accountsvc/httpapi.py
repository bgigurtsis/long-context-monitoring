"""Loopback HTTP API: public POST /recovery/start, POST /recovery/complete,
and authenticated POST /recovery/notifications/retry.

Built entirely on `http.server` from the standard library. Every request
body is bounded before it is read, and every JSON field is validated by the
strict models in `accountsvc.models` before it reaches business logic. The
retry route additionally requires an `Authorization: Bearer <token>` header
matching the `bearer_token` the CLI's `serve` command was started with.
"""
from __future__ import annotations

import hmac
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from accountsvc.models import ValidationError
from accountsvc.service import RecoveryService
from accountsvc.storage import ConflictError, NotFoundError, Storage

MAX_BODY_BYTES = 16 * 1024


class _AppError(Exception):
    def __init__(self, status: HTTPStatus, error: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.error = error
        self.message = message


class RecoveryRequestHandler(BaseHTTPRequestHandler):
    server_version = "accountsvc/1.0"

    # Populated per-request from the owning server instance.
    recovery_service: RecoveryService
    bearer_token: str

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass  # keep test/CLI output free of default access-log noise

    def _read_json_body(self) -> dict:
        length_header = self.headers.get("Content-Length")
        if length_header is None:
            raise _AppError(HTTPStatus.LENGTH_REQUIRED, "length_required", "Content-Length is required")
        try:
            length = int(length_header)
        except ValueError:
            raise _AppError(HTTPStatus.BAD_REQUEST, "bad_request", "invalid Content-Length")
        if length < 0:
            raise _AppError(HTTPStatus.BAD_REQUEST, "bad_request", "invalid Content-Length")
        if length > MAX_BODY_BYTES:
            raise _AppError(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "payload_too_large", "request body too large"
            )
        raw = self.rfile.read(length) if length else b""
        if not raw:
            raise _AppError(HTTPStatus.BAD_REQUEST, "bad_request", "request body required")
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise _AppError(HTTPStatus.BAD_REQUEST, "bad_request", "request body must be JSON")
        if not isinstance(parsed, dict):
            raise _AppError(HTTPStatus.BAD_REQUEST, "bad_request", "request body must be a JSON object")
        return parsed

    def _require_field(self, body: dict, field: str) -> str:
        value = body.get(field)
        if not isinstance(value, str) or not value:
            raise _AppError(HTTPStatus.BAD_REQUEST, "bad_request", f"{field} is required")
        return value

    def _require_bearer_token(self) -> None:
        header = self.headers.get("Authorization")
        expected = f"Bearer {self.bearer_token}"
        if not header or not hmac.compare_digest(header, expected):
            raise _AppError(
                HTTPStatus.UNAUTHORIZED, "unauthorized", "missing or invalid bearer token"
            )

    def _send_json(self, status: HTTPStatus, payload: dict) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        try:
            if self.path == "/recovery/start":
                body = self._read_json_body()
                organization = self._require_field(body, "organization")
                email = self._require_field(body, "email")
                result = self.recovery_service.start_recovery(organization, email)
                self._send_json(HTTPStatus.ACCEPTED, result)
            elif self.path == "/recovery/complete":
                body = self._read_json_body()
                token = self._require_field(body, "token")
                result = self.recovery_service.complete_recovery(token)
                self._send_json(HTTPStatus.OK, result)
            elif self.path == "/recovery/notifications/retry":
                self._require_bearer_token()
                self._read_json_body()
                result = self.recovery_service.retry_notifications()
                self._send_json(HTTPStatus.OK, result)
            else:
                raise _AppError(HTTPStatus.NOT_FOUND, "not_found", "unknown path")
        except _AppError as exc:
            self._send_json(exc.status, {"error": exc.error, "message": exc.message})
        except ValidationError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "bad_request", "message": str(exc)})
        except NotFoundError as exc:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found", "message": str(exc)})
        except ConflictError as exc:
            self._send_json(HTTPStatus.CONFLICT, {"error": "conflict", "message": str(exc)})

    def do_GET(self) -> None:  # noqa: N802
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found", "message": "unknown path"})


def build_server(
    host: str,
    port: int,
    storage: Storage,
    mail_endpoint: str,
    bearer_token: str,
) -> ThreadingHTTPServer:
    recovery_service = RecoveryService(storage, mail_endpoint)

    class _Handler(RecoveryRequestHandler):
        pass

    _Handler.recovery_service = recovery_service
    _Handler.bearer_token = bearer_token

    server = ThreadingHTTPServer((host, port), _Handler)
    server.daemon_threads = True
    return server


def serve_forever(
    host: str,
    port: int,
    storage: Storage,
    mail_endpoint: str,
    bearer_token: str,
) -> None:
    server = build_server(host, port, storage, mail_endpoint, bearer_token)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
