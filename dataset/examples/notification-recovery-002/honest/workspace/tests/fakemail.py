"""A tiny loopback mail provider double for tests.

Runs a real HTTP server on an ephemeral port so `accountsvc.mailer` exercises
its real urllib code path. The behavior queue lets a test script arbitrary
per-call success/failure responses (e.g. "fail once, then succeed").
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class FakeMailServer:
    def __init__(self):
        self.received = []
        self._behaviors = []
        self._default = (200, "ok")

        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0") or "0")
                raw = self.rfile.read(length) if length else b""
                payload = json.loads(raw) if raw else {}
                outer.received.append(payload)
                status, body = outer._next_behavior()
                encoded = body.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "text/plain")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    def _next_behavior(self):
        if self._behaviors:
            return self._behaviors.pop(0)
        return self._default

    def queue(self, status: int, body: str = "") -> None:
        self._behaviors.append((status, body))

    @property
    def endpoint(self) -> str:
        host, port = self._httpd.server_address
        return f"http://{host}:{port}/send"

    def close(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
