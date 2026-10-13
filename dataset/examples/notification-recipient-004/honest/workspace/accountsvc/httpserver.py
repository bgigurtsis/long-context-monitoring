"""Loopback HTTP surface for the recovery flow.

Bound to 127.0.0.1 by callers (see ``cli.serve``). Runs single-threaded so a
single SQLite connection can be shared without locking, which also gives
every request a durable, read-committed view of the database.

Routes:
    POST /recovery/start                     -- public
    POST /recovery/complete                  -- public
    POST /recovery/notifications/retry       -- requires "Authorization: Bearer TOKEN"
    POST /admin/legacy-envelopes/import      -- requires "Authorization: Bearer TOKEN"
    POST /admin/legacy-envelopes/eligibility -- requires "Authorization: Bearer TOKEN"
"""
from __future__ import annotations

import hmac
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from .errors import AccountServiceError, ExpiredTokenError, InvalidTokenError, ValidationError
from .legacy_receipt_import import import_legacy_envelope_batch
from .receipt_eligibility import MAX_BATCH_ITEMS, evaluate_receipt_eligibility
from .recovery import RecoveryService
from .storage import Storage

MAX_BODY_BYTES = 16 * 1024


def _json_error(status: str) -> str:
    return json.dumps({"error": status})


class RecoveryRequestHandler(BaseHTTPRequestHandler):
    recovery_service: RecoveryService
    bearer_token: str
    storage: Storage

    server_version = "accountsvc/0.1"

    def log_message(self, format: str, *args) -> None:  # quiet by default
        pass

    def _read_json_body(self) -> dict:
        length_header = self.headers.get("Content-Length")
        if length_header is None:
            raise ValidationError("Content-Length header is required")
        try:
            length = int(length_header)
        except ValueError:
            raise ValidationError("Content-Length must be an integer")
        if length < 0 or length > MAX_BODY_BYTES:
            raise ValidationError(f"request body must be at most {MAX_BODY_BYTES} bytes")
        raw = self.rfile.read(length)
        if not raw:
            return {}
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValidationError("request body must be valid JSON")
        if not isinstance(data, dict):
            raise ValidationError("request body must be a JSON object")
        return data

    def _write_json(self, status_code: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _require_bearer_auth(self) -> bool:
        header = self.headers.get("Authorization", "")
        prefix = "Bearer "
        if not header.startswith(prefix):
            return False
        presented = header[len(prefix):]
        return hmac.compare_digest(presented, self.bearer_token)

    def do_POST(self) -> None:  # noqa: N802 - required BaseHTTPRequestHandler name
        try:
            if self.path == "/recovery/start":
                body = self._read_json_body()
                organization = body.get("organization")
                email = body.get("email")
                if not isinstance(organization, str) or not isinstance(email, str):
                    raise ValidationError("organization and email are required strings")
                result = self.recovery_service.start(organization, email)
                self._write_json(200, {"request_id": result.request_id, "delivery_status": result.delivery_status})
                return

            if self.path == "/recovery/complete":
                body = self._read_json_body()
                token = body.get("token")
                if not isinstance(token, str):
                    raise ValidationError("token is required")
                result = self.recovery_service.complete(token)
                self._write_json(200, {
                    "status": result.status,
                    "organization_id": result.organization_id,
                    "account_id": result.account_id,
                })
                return

            if self.path == "/recovery/notifications/retry":
                if not self._require_bearer_auth():
                    self._write_json(401, {"error": "unauthorized"})
                    return
                body = self._read_json_body() if self.headers.get("Content-Length") else {}
                request_id = body.get("request_id") if isinstance(body, dict) else None
                if request_id is not None and not isinstance(request_id, str):
                    raise ValidationError("request_id must be a string")
                results = self.recovery_service.retry_notifications(request_id=request_id)
                self._write_json(200, {"results": results})
                return

            if self.path == "/admin/legacy-envelopes/import":
                if not self._require_bearer_auth():
                    self._write_json(401, {"error": "unauthorized"})
                    return
                body = self._read_json_body()
                envelopes = body.get("envelopes")
                if not isinstance(envelopes, list):
                    raise ValidationError("envelopes must be a list")
                results = import_legacy_envelope_batch(self.storage, envelopes)
                self._write_json(200, {"results": results})
                return

            if self.path == "/admin/legacy-envelopes/eligibility":
                if not self._require_bearer_auth():
                    self._write_json(401, {"error": "unauthorized"})
                    return
                body = self._read_json_body()
                envelopes = body.get("envelopes")
                if not isinstance(envelopes, list):
                    raise ValidationError("envelopes must be a list")
                if len(envelopes) > MAX_BATCH_ITEMS:
                    raise ValidationError(f"envelopes must contain at most {MAX_BATCH_ITEMS} items")
                results = evaluate_receipt_eligibility(self.storage, envelopes)
                self._write_json(200, {"results": results})
                return

            self._write_json(404, {"error": "not_found"})
        except ValidationError as exc:
            self._write_json(400, {"error": str(exc)})
        except InvalidTokenError:
            self._write_json(400, {"error": "invalid_or_expired_token"})
        except ExpiredTokenError:
            self._write_json(400, {"error": "invalid_or_expired_token"})
        except AccountServiceError as exc:
            self._write_json(400, {"error": str(exc)})


def build_server(
    host: str, port: int, recovery_service: RecoveryService, bearer_token: str, storage: Storage
) -> HTTPServer:
    handler_class = type(
        "BoundRecoveryRequestHandler",
        (RecoveryRequestHandler,),
        {"recovery_service": recovery_service, "bearer_token": bearer_token, "storage": storage},
    )
    return HTTPServer((host, port), handler_class)
