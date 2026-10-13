"""Loopback HTTP transport for the OAuth service."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from .service import NOT_FOUND, OAuthService

# Requests are small, fixed-shape JSON objects; anything claiming to be
# larger than this is rejected without reading it off the socket.
MAX_BODY_BYTES = 16 * 1024

_ROUTES = {
    "/oauth/authorize": "authorize",
    "/login/complete": "login_complete",
    "/oauth/token": "token",
    "/oauth/grant/status": "grant_status",
    "/oauth/grant/revoke": "revoke_grant",
}


def make_handler(service: OAuthService) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "oauthsvc/0.1"

        def log_message(self, fmt: str, *args) -> None:  # quiet by default
            pass

        def do_POST(self) -> None:
            body = self._read_bounded_body()
            if body is _TOO_LARGE:
                self._respond(400, {"error": "malformed_request"})
                return

            method_name = _ROUTES.get(self.path)
            if method_name is None:
                status, payload = NOT_FOUND
                self._respond(status, payload)
                return

            try:
                decoded = json.loads(body) if body else None
            except (json.JSONDecodeError, UnicodeDecodeError):
                self._respond(400, {"error": "malformed_request"})
                return

            handler = getattr(service, method_name)
            status, payload = handler(decoded)
            self._respond(status, payload)

        def _read_bounded_body(self):
            length_header = self.headers.get("Content-Length")
            if length_header is None:
                return b""
            try:
                length = int(length_header)
            except ValueError:
                self.close_connection = True
                return _TOO_LARGE
            if length < 0 or length > MAX_BODY_BYTES:
                self.close_connection = True
                return _TOO_LARGE
            return self.rfile.read(length)

        def _respond(self, status: int, payload: dict) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


class _TooLarge:
    pass


_TOO_LARGE = _TooLarge()


def run_server(service: OAuthService, host: str, port: int) -> HTTPServer:
    handler_cls = make_handler(service)
    httpd = HTTPServer((host, port), handler_cls)
    return httpd
