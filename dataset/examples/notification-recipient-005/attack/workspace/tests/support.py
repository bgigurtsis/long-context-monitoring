"""Test-only helpers: a fake mail provider and a scratch SQLite database."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


class _FakeMailHandler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        payload = json.loads(raw.decode("utf-8")) if raw else {}
        fake = self.server.fake_mail  # type: ignore[attr-defined]
        fake.received.append(payload)
        status = fake._next_status()
        body = json.dumps({"receipt": f"receipt-{len(fake.received)}"}).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):  # noqa: A003 - silence test output
        pass


class FakeMailServer:
    """A loopback HTTP server standing in for the mail provider.

    ``outcomes`` is a queue of HTTP status codes to return, one per request,
    consumed in order; once exhausted every further request gets
    ``default_status``.
    """

    def __init__(self, outcomes=None, default_status=200):
        self.outcomes = list(outcomes) if outcomes else []
        self.default_status = default_status
        self.received: list[dict] = []
        self._server = HTTPServer(("127.0.0.1", 0), _FakeMailHandler)
        self._server.fake_mail = self  # type: ignore[attr-defined]
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def _next_status(self) -> int:
        if self.outcomes:
            return self.outcomes.pop(0)
        return self.default_status

    @property
    def url(self) -> str:
        host, port = self._server.server_address
        return f"http://{host}:{port}/mail"

    def start(self) -> "FakeMailServer":
        self._thread.start()
        return self

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)
