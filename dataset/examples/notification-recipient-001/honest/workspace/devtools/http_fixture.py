"""Loopback-only HTTP test receiver: records bounded JSON requests and
replies with a configured status.

    from devtools.http_fixture import HttpFixture

    with HttpFixture(status=200, body=b"delivered") as fixture:
        ...  # point code under test at fixture.url
        fixture.set_response(503, b"provider unavailable")
        ...
        fixture.received  # [{"path": ..., "headers": {...}, "json": ...}, ...]

Always binds to 127.0.0.1 on an OS-assigned ephemeral port (never 0.0.0.0 or
a fixed port), so it is only ever reachable from the local machine. Every
request body is bounded before it is read: bodies over `max_body_bytes` are
rejected with a 413 and never recorded, matching the pattern's own request
handling contract, not any particular caller's.

Standalone: this module has no dependency on any other package in this repo.
"""
from __future__ import annotations

import json
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

DEFAULT_MAX_BODY_BYTES = 16 * 1024
DEFAULT_STATUS = int(HTTPStatus.OK)
DEFAULT_BODY = b""


class _Handler(BaseHTTPRequestHandler):
    server_version = "devtools-http-fixture/1.0"

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass  # keep test output free of default access-log noise

    def _send(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        fixture: HttpFixture = self.server.fixture  # type: ignore[attr-defined]

        length_header = self.headers.get("Content-Length")
        if length_header is None:
            self._send(int(HTTPStatus.LENGTH_REQUIRED), b"Content-Length is required")
            return
        try:
            length = int(length_header)
        except ValueError:
            self._send(int(HTTPStatus.BAD_REQUEST), b"invalid Content-Length")
            return
        if length < 0:
            self._send(int(HTTPStatus.BAD_REQUEST), b"invalid Content-Length")
            return
        if length > fixture.max_body_bytes:
            # Drain only up to the bound so the connection still closes
            # cleanly, without holding an unbounded body in memory.
            self.rfile.read(min(length, fixture.max_body_bytes))
            self._send(int(HTTPStatus.REQUEST_ENTITY_TOO_LARGE), b"request body too large")
            return

        raw = self.rfile.read(length) if length else b""
        try:
            parsed = json.loads(raw.decode("utf-8")) if raw else None
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send(int(HTTPStatus.BAD_REQUEST), b"request body must be JSON")
            return

        fixture._record(self.path, dict(self.headers.items()), parsed)
        status, body = fixture._next_response()
        self._send(status, body)


class HttpFixture:
    """A loopback-only HTTP receiver for tests.

    Records every accepted (bounded, JSON-or-empty) request it receives and
    replies with a configured status/body -- a fixed default, or a one-shot
    queue of responses handed out in order for scripting a sequence of
    outcomes (e.g. a failure followed by a success).
    """

    def __init__(
        self,
        status: int = DEFAULT_STATUS,
        body: bytes = DEFAULT_BODY,
        max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
    ) -> None:
        self.max_body_bytes = max_body_bytes
        self._lock = threading.Lock()
        self._default_response = (int(status), bytes(body))
        self._queued_responses: list[tuple[int, bytes]] = []
        self._received: list[dict[str, Any]] = []
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    # -- lifecycle ----------------------------------------------------------

    def start(self) -> "HttpFixture":
        if self._httpd is not None:
            raise RuntimeError("fixture already started")
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        httpd.daemon_threads = True
        httpd.fixture = self  # type: ignore[attr-defined]
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        self._httpd = httpd
        self._thread = thread
        return self

    def stop(self) -> None:
        if self._httpd is None:
            return
        self._httpd.shutdown()
        self._httpd.server_close()
        self._httpd = None
        self._thread = None

    def __enter__(self) -> "HttpFixture":
        return self.start()

    def __exit__(self, *exc_info: object) -> None:
        self.stop()

    @property
    def url(self) -> str:
        if self._httpd is None:
            raise RuntimeError("fixture is not started")
        host, port = self._httpd.server_address
        return f"http://{host}:{port}"

    # -- configuration --------------------------------------------------------

    def set_response(self, status: int, body: bytes = b"") -> None:
        """Set the status/body every future request receives; clears any queue."""
        with self._lock:
            self._queued_responses.clear()
            self._default_response = (int(status), bytes(body))

    def queue_response(self, status: int, body: bytes = b"") -> None:
        """Queue a one-shot status/body for the next request only.

        Queued responses are handed out in FIFO order; once the queue is
        empty, requests fall back to the default response again.
        """
        with self._lock:
            self._queued_responses.append((int(status), bytes(body)))

    # -- recorded state -------------------------------------------------------

    @property
    def received(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._received)

    def _record(self, path: str, headers: dict[str, str], payload: Any) -> None:
        with self._lock:
            self._received.append({"path": path, "headers": headers, "json": payload})

    def _next_response(self) -> tuple[int, bytes]:
        with self._lock:
            if self._queued_responses:
                return self._queued_responses.pop(0)
            return self._default_response
