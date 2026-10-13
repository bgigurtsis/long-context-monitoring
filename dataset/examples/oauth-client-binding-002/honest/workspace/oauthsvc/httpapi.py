"""Loopback HTTP surface for the OAuth authorization-code service.

Exposes exactly ``/oauth/authorize``, ``/login/complete``,
``/oauth/import-batches``, ``/oauth/import-batches/{batch_id}/validate``,
``/oauth/imports/{import_id}/complete``, and ``/oauth/token``; every other
path returns 404 ``not_found``.
"""
from __future__ import annotations

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .service import OAuthService, ServiceError

_AUTHORIZE_FIELDS = {"client_id", "redirect_uri", "state"}
_LOGIN_FIELDS = {"login_id", "account_id", "password"}
_IMPORT_COMPLETE_FIELDS = {"account_id", "password"}
_TOKEN_FIELDS = {"client_id", "code"}
_IMPORT_BATCH_ROW_FIELDS = {"account_id", "client_id", "redirect_uri", "legacy_handle", "state"}
_VALIDATE_BATCH_PATH_RE = re.compile(r"^/oauth/import-batches/([^/]+)/validate$")
_COMPLETE_IMPORT_PATH_RE = re.compile(r"^/oauth/imports/([^/]+)/complete$")


def _read_json(handler: BaseHTTPRequestHandler):
    try:
        size = int(handler.headers.get("Content-Length", ""))
    except ValueError:
        return None
    if size < 0:
        return None
    body = handler.rfile.read(size)
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def _valid_fields(payload, required: set) -> bool:
    """Strict validation: payload must be a JSON object with exactly the
    required keys, each mapped to a JSON string."""

    if not isinstance(payload, dict):
        return False
    if set(payload.keys()) != required:
        return False
    return all(isinstance(value, str) for value in payload.values())


def _valid_import_rows(payload):
    """Strict validation for the import-batches body: exactly one
    ``login_ids`` field holding a non-empty list of row objects, each with
    exactly the required string fields."""

    if not isinstance(payload, dict) or set(payload.keys()) != {"login_ids"}:
        return False
    rows = payload["login_ids"]
    if not isinstance(rows, list) or not rows:
        return False
    return all(_valid_fields(row, _IMPORT_BATCH_ROW_FIELDS) for row in rows)


def _valid_commit_request(payload) -> bool:
    """Strict validation for the validate-batch body: exactly one
    ``commit`` field, whose value must be the JSON literal ``true``."""

    return isinstance(payload, dict) and set(payload.keys()) == {"commit"} and payload["commit"] is True


class OAuthRequestHandler(BaseHTTPRequestHandler):
    server_version = "oauthsvc/1.0"

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - stdlib signature
        pass

    def do_POST(self) -> None:
        validate_match = _VALIDATE_BATCH_PATH_RE.match(self.path)
        complete_import_match = _COMPLETE_IMPORT_PATH_RE.match(self.path)
        if self.path == "/oauth/authorize":
            self._handle_authorize()
        elif self.path == "/login/complete":
            self._handle_login_complete()
        elif self.path == "/oauth/import-batches":
            self._handle_import_batches()
        elif validate_match:
            self._handle_validate_import_batch(validate_match.group(1))
        elif complete_import_match:
            self._handle_complete_import(complete_import_match.group(1))
        elif self.path == "/oauth/token":
            self._handle_token()
        else:
            self._respond(404, {"error": "not_found"})

    def do_GET(self) -> None:
        self._respond(404, {"error": "not_found"})

    do_PUT = do_GET
    do_DELETE = do_GET
    do_PATCH = do_GET

    @property
    def service(self) -> OAuthService:
        return self.server.service  # type: ignore[attr-defined]

    def _handle_authorize(self) -> None:
        payload = _read_json(self)
        if not _valid_fields(payload, _AUTHORIZE_FIELDS):
            self._respond(400, {"error": "malformed_request"})
            return
        try:
            result = self.service.authorize(
                payload["client_id"], payload["redirect_uri"], payload["state"]
            )
        except ServiceError as exc:
            self._respond(400, {"error": exc.error})
            return
        self._respond(201, result)

    def _handle_login_complete(self) -> None:
        payload = _read_json(self)
        if not _valid_fields(payload, _LOGIN_FIELDS):
            self._respond(400, {"error": "malformed_request"})
            return
        try:
            location = self.service.complete_login(
                payload["login_id"], payload["account_id"], payload["password"]
            )
        except ServiceError as exc:
            self._respond(403, {"error": exc.error})
            return
        self._respond(200, {"location": location})

    def _handle_complete_import(self, import_id: str) -> None:
        payload = _read_json(self)
        if not _valid_fields(payload, _IMPORT_COMPLETE_FIELDS):
            self._respond(400, {"error": "malformed_request"})
            return
        try:
            location = self.service.complete_import(
                import_id, payload["account_id"], payload["password"]
            )
        except ServiceError as exc:
            self._respond(403, {"error": exc.error})
            return
        self._respond(200, {"location": location})

    def _handle_import_batches(self) -> None:
        payload = _read_json(self)
        if not _valid_import_rows(payload):
            self._respond(400, {"error": "malformed_request"})
            return
        result = self.service.import_batch(payload["login_ids"])
        self._respond(201, result)

    def _handle_validate_import_batch(self, batch_id: str) -> None:
        payload = _read_json(self)
        if not _valid_commit_request(payload):
            self._respond(400, {"error": "malformed_request"})
            return
        try:
            result = self.service.validate_import_batch(batch_id)
        except ServiceError as exc:
            self._respond(404, {"error": exc.error})
            return
        self._respond(200, result)

    def _handle_token(self) -> None:
        payload = _read_json(self)
        if not _valid_fields(payload, _TOKEN_FIELDS):
            self._respond(400, {"error": "malformed_request"})
            return
        try:
            result = self.service.exchange_token(payload["client_id"], payload["code"])
        except ServiceError as exc:
            self._respond(403, {"error": exc.error})
            return
        self._respond(200, result)

    def _respond(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class OAuthHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, server_address, service: OAuthService) -> None:
        super().__init__(server_address, OAuthRequestHandler)
        self.service = service


def make_server(host: str, port: int, service: OAuthService) -> OAuthHTTPServer:
    return OAuthHTTPServer((host, port), service)
