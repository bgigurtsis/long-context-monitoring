"""Two real OS processes, one SQLite file: proves that a recovery token's
expiry is a durable, absolute fact in the database, not something process 1
merely remembers in memory.

Process 1 serves with a 2-second ``--recovery-ttl-seconds``, completes one
token immediately (normal path), then is killed (not shut down gracefully)
after a second token has had time to expire. Process 2 is started fresh
against the same database file and must refuse the token that expired
while process 1 was still alive -- it has no way to know that except by
reading the ``expires_at`` process 1 persisted.
"""
from __future__ import annotations

import json
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from tests.support import FakeMailServer

REPO_ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable
BEARER_TOKEN = "two-process-test-token"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_port(port: int, proc: subprocess.Popen, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    last_error = None
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(
                f"serve process exited early (code {proc.returncode}); stderr:\n{proc.stderr.read()}"
            )
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return
        except OSError as exc:
            last_error = exc
            time.sleep(0.05)
    raise TimeoutError(f"port {port} never accepted a connection: {last_error}")


def _post(port: int, path: str, payload: dict, headers=None):
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=body,
        method="POST",
        headers=headers or {"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        with exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))


class TwoProcessTtlExpiryTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmpdir.name) / "state.db"
        self.mail = FakeMailServer().start()
        self._procs: list[subprocess.Popen] = []

        created = subprocess.run(
            [
                PYTHON, "-m", "accountsvc.cli", "create-account",
                "org-a", "acct-1", "alice@example.com",
                "--database", str(self.db_path),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(created.returncode, 0, created.stderr)

    def tearDown(self):
        for proc in self._procs:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
            proc.stdout.close()
            proc.stderr.close()
        self.mail.stop()
        self._tmpdir.cleanup()

    def _start_server(self, port: int, ttl_seconds: int) -> subprocess.Popen:
        proc = subprocess.Popen(
            [
                PYTHON, "-m", "accountsvc.cli", "serve",
                "--database", str(self.db_path),
                "--bearer-token", BEARER_TOKEN,
                "--mail-endpoint", self.mail.url,
                "--port", str(port),
                "--recovery-ttl-seconds", str(ttl_seconds),
            ],
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self._procs.append(proc)
        _wait_for_port(port, proc)
        return proc

    def _stop_server(self, proc: subprocess.Popen) -> None:
        proc.terminate()
        proc.wait(timeout=5)

    def test_expiry_persists_and_is_enforced_across_a_process_restart(self):
        port1 = _free_port()
        proc1 = self._start_server(port1, ttl_seconds=2)

        # Token A: created and completed immediately, against process 1.
        status, body = _post(port1, "/recovery/start", {"organization": "org-a", "email": "alice@example.com"})
        self.assertEqual(status, 202)
        self.assertEqual(body["delivery_status"], "delivered")
        token_a = self.mail.received[-1]["recovery_token"]

        status, body = _post(port1, "/recovery/complete", {"token": token_a})
        self.assertEqual(status, 200, body)
        self.assertEqual(body, {"account_id": "acct-1", "status": "completed"})

        # Token B: created against process 1, then left alone to expire.
        status, body = _post(port1, "/recovery/start", {"organization": "org-a", "email": "alice@example.com"})
        self.assertEqual(status, 202)
        token_b = self.mail.received[-1]["recovery_token"]

        time.sleep(3.0)  # past the 2-second ttl, with margin

        # Kill process 1 outright (not a graceful shutdown) to prove the
        # expiry survives an abrupt stop, not just an orderly one.
        self._stop_server(proc1)

        port2 = _free_port()
        proc2 = self._start_server(port2, ttl_seconds=2)

        status, body = _post(port2, "/recovery/complete", {"token": token_b})
        self.assertEqual(status, 400, body)
        self.assertIn("error", body)

        self._stop_server(proc2)


if __name__ == "__main__":
    unittest.main()
