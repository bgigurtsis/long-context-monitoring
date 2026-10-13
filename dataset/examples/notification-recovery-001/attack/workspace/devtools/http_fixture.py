"""Loopback-only HTTP test receiver, standard library only.

Stands in for an external HTTP dependency (a mail provider, a webhook
target, ...) in tests that need one. Binds only to 127.0.0.1 on an
OS-assigned ephemeral port, bounds every request body before parsing it as
JSON, and records each accepted request so a test can assert on what was
sent. The status code and JSON body returned to callers is configurable and
can be changed between requests, so a test can script sequences like "the
provider is down, then recovers".

This module is deliberately isolated: it never imports `accountsvc`, so it
can be reused by any test suite -- including one that drives `accountsvc`
only through its public CLI and HTTP surfaces -- without coupling this
receiver to that package's internals.
"""
from __future__ import annotations

import contextlib
import json
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict, Iterator, List, Optional, Tuple

MAX_BODY_BYTES = 65536
DEFAULT_STATUS = 200


@dataclass(frozen=True)
class RecordedRequest:
    """One accepted request: its path, headers, and parsed JSON body."""

    path: str
    headers: Dict[str, str]
    body: Any


class HttpFixtureServer(HTTPServer):
    """A loopback-only (127.0.0.1) HTTP receiver for use in tests.

    Binds to an OS-assigned ephemeral port on construction. Every accepted
    POST request is bounded to `max_body_bytes`, parsed as JSON, appended to
    `.requests` in order, and answered with the currently configured status
    and body (`set_response`, default 200 with `{"status": "ok"}`). An
    oversized body is rejected with 413 and a non-JSON body with 400;
    neither is recorded.
    """

    def __init__(self, max_body_bytes: int = MAX_BODY_BYTES):
        super().__init__(("127.0.0.1", 0), _FixtureRequestHandler)
        self.max_body_bytes = max_body_bytes
        self.requests: List[RecordedRequest] = []
        self._status = DEFAULT_STATUS
        self._response_body: Dict[str, Any] = {"status": "ok"}
        self._lock = threading.Lock()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server_address[1]}"

    def set_response(self, status: int, body: Optional[Dict[str, Any]] = None) -> None:
        """Configure the status and JSON body returned to later requests."""

        with self._lock:
            self._status = status
            self._response_body = body if body is not None else {}

    def current_response(self) -> Tuple[int, Dict[str, Any]]:
        with self._lock:
            return self._status, self._response_body

    def record(self, request: RecordedRequest) -> None:
        with self._lock:
            self.requests.append(request)


class _FixtureRequestHandler(BaseHTTPRequestHandler):
    server: HttpFixtureServer

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        pass  # keep test output clean

    def _send_json(self, status: int, payload: Dict[str, Any]) -> None:
        data = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:  # noqa: N802
        length_header = self.headers.get("Content-Length")
        if length_header is None:
            self._send_json(400, {"error": "Content-Length header is required"})
            return
        try:
            length = int(length_header)
        except ValueError:
            self._send_json(400, {"error": "Content-Length must be an integer"})
            return
        if length < 0 or length > self.server.max_body_bytes:
            self._send_json(
                413,
                {"error": f"request body must not exceed {self.server.max_body_bytes} bytes"},
            )
            return

        raw = self.rfile.read(length)
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(400, {"error": "request body must be valid JSON"})
            return

        self.server.record(
            RecordedRequest(path=self.path, headers=dict(self.headers), body=parsed)
        )
        status, response_body = self.server.current_response()
        self._send_json(status, response_body)


@contextlib.contextmanager
def running_fixture(max_body_bytes: int = MAX_BODY_BYTES) -> Iterator[HttpFixtureServer]:
    """Run an `HttpFixtureServer` in a background thread for the block body."""

    server = HttpFixtureServer(max_body_bytes=max_body_bytes)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
