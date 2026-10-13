"""A tiny loopback mail double used by recovery/http tests.

Behavior is controlled through a mutable ``state`` dict so each test can flip
success/failure and inspect what was actually posted, without any shared
global state between tests.
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


def start_fake_mail_server(state: dict):
    state.setdefault("should_fail", False)
    state.setdefault("status_code", None)
    state.setdefault("receipt", "")
    state.setdefault("received", [])

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b""
            data = json.loads(raw.decode("utf-8")) if raw else {}
            state["received"].append(data)
            payload = json.dumps({"receipt": state["receipt"]}).encode("utf-8")
            if state["status_code"] is not None:
                status = state["status_code"]
            else:
                status = 502 if state["should_fail"] else 200
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    url = f"http://{host}:{port}/mail"
    return server, thread, url


def stop_fake_mail_server(server: HTTPServer, thread: threading.Thread) -> None:
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)
