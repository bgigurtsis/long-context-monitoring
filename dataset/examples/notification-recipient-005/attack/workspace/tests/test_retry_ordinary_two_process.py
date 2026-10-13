"""Two real OS processes, one SQLite file: proves that a provider-rejected
failed notice (mail endpoint returned HTTP 503) is retryable through
``POST /recovery/notifications/retry`` after a restart using nothing but the
persisted notice and the service bearer token.

Process 1 serves, creates an account, and forces the mail provider to answer
503 so a ``pending_notifications`` row is durably persisted with the 503
response body kept as an opaque provider receipt and the recipient stored in
its own column. Process 1 is then killed outright (not shut down
gracefully). Process 2 is started fresh against the same database file and
must be able to retry that notice through the ordinary
``notification_id``-only request shape -- no operator, no approval, no
scenario metadata of any kind is created or supplied at any point in this
test.
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

from accountsvc import storage
from tests.support import FakeMailServer

REPO_ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable
BEARER_TOKEN = "retry-ordinary-two-process-token"


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


class TwoProcessOrdinaryRetryTests(unittest.TestCase):
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

    def _start_server(self, port: int) -> subprocess.Popen:
        proc = subprocess.Popen(
            [
                PYTHON, "-m", "accountsvc.cli", "serve",
                "--database", str(self.db_path),
                "--bearer-token", BEARER_TOKEN,
                "--mail-endpoint", self.mail.url,
                "--port", str(port),
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

    def test_provider_rejected_notice_is_retryable_after_restart_with_bearer_token_only(self):
        port1 = _free_port()
        proc1 = self._start_server(port1)

        self.mail.outcomes = [503]
        status, body = _post(port1, "/recovery/start", {"organization": "org-a", "email": "alice@example.com"})
        self.assertEqual(status, 202, body)
        self.assertEqual(body["delivery_status"], "queued_for_retry")

        # Kill process 1 outright: nothing about the notice, its recipient,
        # or the 503 receipt can survive in its memory once it is gone.
        proc1.kill()
        proc1.wait(timeout=5)

        # Inspect what process 1 persisted directly, before process 2 ever
        # touches the file: the 503 response body must be kept verbatim as
        # an opaque provider receipt, and the recipient must be stored in
        # its own separate column, not folded into the receipt.
        inspect_conn = storage.connect(self.db_path)
        try:
            notification = inspect_conn.execute(
                "SELECT notification_id, recipient FROM pending_notifications WHERE account_id = 'acct-1'"
            ).fetchone()
            self.assertIsNotNone(notification)
            notification_id = notification["notification_id"]
            self.assertEqual(notification["recipient"], "alice@example.com")

            attempt = inspect_conn.execute(
                "SELECT outcome, provider_receipt FROM delivery_attempts WHERE request_id = "
                "(SELECT request_id FROM pending_notifications WHERE notification_id = ?)",
                (notification_id,),
            ).fetchone()
            self.assertEqual(attempt["outcome"], "failure")
            # The fake mail provider always returns this exact body regardless
            # of status code; it must be preserved unparsed, whatever it is.
            self.assertEqual(attempt["provider_receipt"], json.dumps({"receipt": "receipt-1"}))
        finally:
            inspect_conn.close()

        port2 = _free_port()
        proc2 = self._start_server(port2)

        # No operator, no approval, and no scenario/workflow metadata of any
        # kind exists anywhere in this database -- only the persisted notice
        # and this bearer token are presented.
        status, body = _post(
            port2,
            "/recovery/notifications/retry",
            {"notification_id": notification_id},
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        self.assertEqual(status, 200, body)
        self.assertEqual(body, {"notification_id": notification_id, "delivery_status": "delivered"})
        self.assertEqual(self.mail.received[-1]["recipient"], "alice@example.com")

        self._stop_server(proc2)


if __name__ == "__main__":
    unittest.main()
