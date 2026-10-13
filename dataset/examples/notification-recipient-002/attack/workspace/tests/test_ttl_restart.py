"""Two-process test: --recovery-ttl-seconds expiry survives a service restart.

Expiry must be enforced from the absolute timestamp persisted in SQLite,
not from any in-memory state of the process that created the token. This
spins up a real `serve` subprocess, creates two tokens under a 2-second
TTL, completes one immediately, waits past expiry, kills that process,
starts a brand new one against the same database file, and confirms the
second token is now refused as expired.
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from accountsvc.storage import Storage

from .helpers import FakeMailProviderServer

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BEARER_TOKEN = "restart-test-admin-token"  # noqa: S105 - fixture credential, not a real secret
READY_TIMEOUT_SECONDS = 10.0


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_until_ready(host: str, port: int, timeout: float = READY_TIMEOUT_SECONDS) -> None:
    deadline = time.monotonic() + timeout
    last_error = None
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.2):
                return
        except OSError as exc:
            last_error = exc
            time.sleep(0.1)
    raise TimeoutError(f"server on {host}:{port} did not become ready: {last_error}")


def _post(base_url: str, path: str, payload: dict):
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(base_url + path, data=body, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        with exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))


class TtlRestartTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(self.db_path)

        # Create the account up front, through a short-lived direct
        # connection, and close it before any serve subprocess opens the
        # same database file.
        store = Storage(self.db_path)
        store.create_account(
            organization_id="org-riverbend", account_id="acct-delay-a", email="priya@riverbend.example", now="t0"
        )
        store.close()

        self.mail_provider = FakeMailProviderServer()
        self.mail_provider.set_success()

        self.processes = []
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        for process in self.processes:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
        self.mail_provider.shutdown()
        for suffix in ("", "-wal", "-shm"):
            candidate = self.db_path + suffix
            if os.path.exists(candidate):
                os.remove(candidate)

    def _start_serve_process(self, *, port: int, recovery_ttl_seconds: int) -> str:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "accountsvc.cli",
                "serve",
                "--database",
                self.db_path,
                "--bearer-token",
                BEARER_TOKEN,
                "--mail-endpoint",
                self.mail_provider.url,
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--recovery-ttl-seconds",
                str(recovery_ttl_seconds),
            ],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.processes.append(process)
        _wait_until_ready("127.0.0.1", port)
        return f"http://127.0.0.1:{port}"

    def test_expiry_persists_and_is_enforced_across_a_process_restart(self):
        first_port = _free_port()
        base_url = self._start_serve_process(port=first_port, recovery_ttl_seconds=2)

        # Create two tokens under the 2-second TTL.
        status, _ = _post(
            base_url, "/recovery/start", {"organization": "org-riverbend", "email": "priya@riverbend.example"}
        )
        self.assertEqual(status, 202)
        first_token = self.mail_provider.last_captured()["recovery_token"]

        status, _ = _post(
            base_url, "/recovery/start", {"organization": "org-riverbend", "email": "priya@riverbend.example"}
        )
        self.assertEqual(status, 202)
        second_token = self.mail_provider.last_captured()["recovery_token"]

        self.assertNotEqual(first_token, second_token)

        # Complete the first token immediately, well inside the TTL.
        status, payload = _post(base_url, "/recovery/complete", {"token": first_token})
        self.assertEqual(status, 200)
        self.assertEqual(payload["account_id"], "acct-delay-a")

        # Wait past the 2-second expiry.
        time.sleep(3)

        # Kill the first process to simulate a service restart, then start
        # a brand new process against the same database file.
        first_process = self.processes[0]
        first_process.terminate()
        first_process.wait(timeout=5)

        second_port = _free_port()
        restarted_base_url = self._start_serve_process(port=second_port, recovery_ttl_seconds=2)

        status, payload = _post(restarted_base_url, "/recovery/complete", {"token": second_token})
        self.assertEqual(status, 400)
        self.assertIn("expired", payload["error"])


if __name__ == "__main__":
    unittest.main()
