"""A tiny loopback mail provider double for tests.

Fails the first `fail_times` deliveries (returning an opaque receipt each
time), then succeeds. Records every payload it receives.
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


class FakeMailServer:
    def __init__(self, fail_times: int = 0, fail_status: int = 503):
        self.received: list[dict] = []
        self._fail_remaining = fail_times
        self._fail_status = fail_status
        self._lock = threading.Lock()
        self.httpd = HTTPServer(("127.0.0.1", 0), self._build_handler())
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def _build_handler(self):
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0) or 0)
                raw = self.rfile.read(length) if length else b"{}"
                body = json.loads(raw or b"{}")
                with outer._lock:
                    outer.received.append(body)
                    seq = len(outer.received)
                    should_fail = outer._fail_remaining > 0
                    if should_fail:
                        outer._fail_remaining -= 1
                receipt = f"provider|attempt-{seq}"
                payload = json.dumps({"receipt": receipt}).encode("utf-8")
                self.send_response(outer._fail_status if should_fail else 200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        return Handler

    @property
    def url(self) -> str:
        host, port = self.httpd.server_address[:2]
        return f"http://{host}:{port}/mail"

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
