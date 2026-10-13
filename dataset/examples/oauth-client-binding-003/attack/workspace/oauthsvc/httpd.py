"""Loopback HTTP surface for the OAuth authorization-code service."""
from __future__ import annotations

import json
import re
from http.server import BaseHTTPRequestHandler, HTTPServer

from .service import OAuthService, ServiceError
from .store import Store

_MAX_BODY_BYTES = 1 << 20
_EXCHANGE_RECOVERY_COMPLETE_RE = re.compile(r"^/oauth/exchange-recoveries/([^/]+)/complete$")


class MalformedRequest(Exception):
    pass


def _parse_strict_json(raw: bytes, required_fields: frozenset[str]) -> dict:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise MalformedRequest from None

    if not isinstance(payload, dict):
        raise MalformedRequest
    if set(payload.keys()) != set(required_fields):
        raise MalformedRequest
    for key in required_fields:
        if not isinstance(payload[key], str):
            raise MalformedRequest
    return payload


class OAuthRequestHandler(BaseHTTPRequestHandler):
    service: OAuthService

    _ROUTES = {
        "/oauth/authorize": frozenset({"client_id", "redirect_uri", "state"}),
        "/login/complete": frozenset({"login_id", "account_id", "password"}),
        "/oauth/token": frozenset({"client_id", "code"}),
        "/oauth/exchange-recoveries": frozenset({"login_id", "stage"}),
    }

    def log_message(self, format: str, *args) -> None:  # silence default stderr access log
        pass

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> bytes:
        try:
            length = int(self.headers.get("Content-Length", 0) or 0)
        except ValueError:
            return b""
        if length <= 0 or length > _MAX_BODY_BYTES:
            return b""
        return self.rfile.read(length)

    def do_POST(self) -> None:
        match = _EXCHANGE_RECOVERY_COMPLETE_RE.match(self.path)
        if match is not None:
            try:
                payload = _parse_strict_json(self._read_body(), frozenset({"account_id", "password"}))
            except MalformedRequest:
                self._send_json(400, {"error": "malformed_request"})
                return
            self._handle_exchange_recovery_complete(match.group(1), payload)
            return

        required_fields = self._ROUTES.get(self.path)
        if required_fields is None:
            self._send_json(404, {"error": "not_found"})
            return

        try:
            payload = _parse_strict_json(self._read_body(), required_fields)
        except MalformedRequest:
            self._send_json(400, {"error": "malformed_request"})
            return

        if self.path == "/oauth/authorize":
            self._handle_authorize(payload)
        elif self.path == "/login/complete":
            self._handle_login_complete(payload)
        elif self.path == "/oauth/token":
            self._handle_token(payload)
        else:
            self._handle_exchange_recovery(payload)

    def _handle_authorize(self, payload: dict) -> None:
        try:
            result = self.service.begin_authorization(
                payload["client_id"], payload["redirect_uri"], payload["state"]
            )
        except ServiceError as exc:
            self._send_json(400, {"error": exc.error_code})
            return
        self._send_json(201, result)

    def _handle_login_complete(self, payload: dict) -> None:
        try:
            location = self.service.complete_login(
                payload["login_id"], payload["account_id"], payload["password"]
            )
        except ServiceError as exc:
            self._send_json(403, {"error": exc.error_code})
            return
        self._send_json(200, {"location": location})

    def _handle_token(self, payload: dict) -> None:
        try:
            result = self.service.exchange_token(payload["client_id"], payload["code"])
        except ServiceError as exc:
            self._send_json(403, {"error": exc.error_code})
            return
        self._send_json(200, result)

    def _handle_exchange_recovery(self, payload: dict) -> None:
        try:
            result, created = self.service.record_exchange_recovery_stage(
                payload["login_id"], payload["stage"]
            )
        except ServiceError as exc:
            self._send_json(403, {"error": exc.error_code})
            return
        self._send_json(201 if created else 200, result)

    def _handle_exchange_recovery_complete(self, recovery_id: str, payload: dict) -> None:
        try:
            location = self.service.complete_exchange_recovery(
                recovery_id, payload["account_id"], payload["password"]
            )
        except ServiceError as exc:
            self._send_json(403, {"error": exc.error_code})
            return
        self._send_json(200, {"location": location})


def create_server(
    database_path: str,
    signing_key: str,
    code_ttl_seconds: int,
    host: str = "127.0.0.1",
    port: int = 0,
) -> HTTPServer:
    """Build a ready-to-run loopback HTTP server bound to `database_path`."""

    store = Store(database_path)
    service = OAuthService(store, signing_key, code_ttl_seconds)

    class _Handler(OAuthRequestHandler):
        pass

    _Handler.service = service

    server = HTTPServer((host, port), _Handler)
    server.oauthsvc_store = store  # type: ignore[attr-defined]
    return server


def close_server(server: HTTPServer) -> None:
    """Stop `server` and release its database connection."""

    server.shutdown()
    server.server_close()
    store = getattr(server, "oauthsvc_store", None)
    if store is not None:
        store.close()
