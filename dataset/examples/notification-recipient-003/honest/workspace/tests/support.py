"""Shared test helpers: temp SQLite databases and a fake loopback mail endpoint."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer


def make_temp_db_path() -> str:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    return path


def cleanup_db_path(path: str) -> None:
    for suffix in ("", "-wal", "-shm", "-journal"):
        candidate = path + suffix
        if os.path.exists(candidate):
            os.remove(candidate)


class FakeMailProvider:
    """A tiny loopback HTTP server that stands in for the mail provider.

    ``script`` is a list of ``(status_code, receipt)`` pairs consumed in
    order, one per request received; the last entry repeats once exhausted.
    """

    def __init__(self, script):
        self._script = list(script)
        self.requests = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(length) or b"{}")
                outer.requests.append(body)
                index = min(len(outer.requests) - 1, len(outer._script) - 1)
                status, receipt = outer._script[index]
                payload = json.dumps({"receipt": receipt}).encode("utf-8") if receipt else b"{}"
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        self._server = HTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}/deliver"

    def __enter__(self) -> "FakeMailProvider":
        self._thread.start()
        return self

    def __exit__(self, *exc_info) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)


def post_json(url: str, payload: dict, headers: dict | None = None):
    """POST JSON to ``url`` and return ``(status, decoded_body)``."""

    request = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), method="POST", headers=headers or {}
    )
    request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        with exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))


def start_serve_process(database, bearer_token, mail_endpoint, recovery_ttl_seconds=None, extra_args=()):
    """Launch ``python -m accountsvc.cli serve`` as a real subprocess.

    Returns ``(process, base_url)`` once the server has printed its bound
    address; the caller is responsible for stopping the process.
    """

    args = [
        sys.executable, "-m", "accountsvc.cli", "serve",
        "--database", database,
        "--bearer-token", bearer_token,
        "--mail-endpoint", mail_endpoint,
        "--host", "127.0.0.1",
        "--port", "0",
    ]
    if recovery_ttl_seconds is not None:
        args += ["--recovery-ttl-seconds", str(recovery_ttl_seconds)]
    args += list(extra_args)

    process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    line = process.stdout.readline()
    if not line.startswith("serving on "):
        process.kill()
        process.wait(timeout=5)
        raise RuntimeError(f"serve process did not start cleanly, said: {line!r}")
    base_url = line.strip().removeprefix("serving on ")
    return process, base_url


def stop_serve_process(process) -> None:
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
    if process.stdout is not None:
        process.stdout.close()
