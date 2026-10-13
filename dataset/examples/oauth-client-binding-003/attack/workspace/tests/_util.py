"""Shared test helpers for the oauthsvc test suite."""
from __future__ import annotations

import json
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "oauthsvc.cli", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


class RunningServer:
    def __init__(self, server) -> None:
        self._server = server
        self._thread = threading.Thread(target=server.serve_forever, daemon=True)
        self._thread.start()

    @property
    def base_url(self) -> str:
        host, port = self._server.server_address[:2]
        return f"http://127.0.0.1:{port}"

    def close(self) -> None:
        from oauthsvc.httpd import close_server

        close_server(self._server)
        self._thread.join(timeout=5)


def start_server(
    database_path: str, signing_key: str = "test-signing-key", code_ttl_seconds: int = 60
) -> RunningServer:
    from oauthsvc.httpd import create_server

    server = create_server(str(database_path), signing_key, code_ttl_seconds)
    return RunningServer(server)


def post_json(base_url: str, path: str, payload: dict) -> tuple[int, dict]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}{path}", data=body, method="POST", headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def post_raw(base_url: str, path: str, body: bytes) -> tuple[int, dict]:
    request = urllib.request.Request(
        f"{base_url}{path}", data=body, method="POST", headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))
