"""Two real OS processes, one SQLite file: proves that an approved redrive
retries persisted failed notices, through
``POST /recovery/notifications/retry``'s approval-driven request shape
(``approval_id``/``operator_id``/``organization_id``), after a restart.

Process 1 serves, creates two accounts, and forces the mail provider to
answer 503 for both so each account gets a durably persisted
``pending_notifications`` row. Two durable approvals are then created
out-of-band (via the CLI, against the same database file, exactly as an
operator tool would) -- one that stays valid, one deliberately given a
near-future expiry so it can be observed lapsing. Process 1 is killed
outright and process 2 is started fresh against the same database file,
where the approval-driven retry path is exercised end to end.

One narrative test method walks through all of:
  * authentication -- the route rejects a missing/wrong bearer token before
    ever looking at the approval;
  * approval consumption -- a valid, unexpired approval retries its
    notification and is marked consumed;
  * unchanged addresses -- the retried delivery lands on the account's
    current email, which never changed;
  * duplicate execution -- replaying the same approval a second time is a
    side-effect-free no-op, not a second delivery;
  * expiry -- an approval whose expiry has passed by the time it is
    consumed is rejected as a stale no-op, leaving its notice untouched.
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
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tests.support import FakeMailServer

REPO_ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable
BEARER_TOKEN = "retry-approval-two-process-token"


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


class TwoProcessApprovalRetryTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmpdir.name) / "state.db"
        self.mail = FakeMailServer().start()
        self._procs: list[subprocess.Popen] = []

        for account_id, email in (("acct-1", "alice@example.com"), ("acct-2", "bob@example.com")):
            created = subprocess.run(
                [
                    PYTHON, "-m", "accountsvc.cli", "create-account",
                    "org-a", account_id, email,
                    "--database", str(self.db_path),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(created.returncode, 0, created.stderr)

        added = subprocess.run(
            [
                PYTHON, "-m", "accountsvc.cli", "add-operator",
                "org-a", "op-1",
                "--database", str(self.db_path),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(added.returncode, 0, added.stderr)

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

    def _approve_redrive(self, approval_id: str, expires_at: str, request_id: str) -> None:
        result = subprocess.run(
            [
                PYTHON, "-m", "accountsvc.cli", "approve-redrive",
                approval_id, "op-1", "org-a", expires_at, request_id,
                "--database", str(self.db_path),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_approval_driven_retry_after_restart(self):
        port1 = _free_port()
        proc1 = self._start_server(port1)

        self.mail.outcomes = [503]
        status, body = _post(port1, "/recovery/start", {"organization": "org-a", "email": "alice@example.com"})
        self.assertEqual(status, 202, body)
        request_id_ok = body["request_id"]

        self.mail.outcomes = [503]
        status, body = _post(port1, "/recovery/start", {"organization": "org-a", "email": "bob@example.com"})
        self.assertEqual(status, 202, body)
        request_id_expiring = body["request_id"]

        # A durable approval that stays valid through the whole test.
        self._approve_redrive("appr-ok", "2099-01-01T00:00:00Z", request_id_ok)

        # A durable approval deliberately given a near-future expiry so it
        # can be observed lapsing before it is ever consumed.
        soon = (datetime.now(timezone.utc) + timedelta(seconds=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        self._approve_redrive("appr-expiring", soon, request_id_expiring)

        time.sleep(3.0)  # past the 2-second expiry, with margin

        # Kill process 1 outright (not a graceful shutdown): both approvals
        # and both notices must survive as durable facts, not memory.
        proc1.kill()
        proc1.wait(timeout=5)

        port2 = _free_port()
        proc2 = self._start_server(port2)

        approval_body = {"approval_id": "appr-ok", "operator_id": "op-1", "organization_id": "org-a"}

        # -- authentication: rejected before the approval is ever looked at --
        status, body = _post(
            port2, "/recovery/notifications/retry", approval_body,
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(status, 401, body)

        status, body = _post(
            port2, "/recovery/notifications/retry", approval_body,
            headers={"Content-Type": "application/json", "Authorization": "Bearer wrong-token"},
        )
        self.assertEqual(status, 401, body)

        auth_headers = {"Content-Type": "application/json", "Authorization": f"Bearer {BEARER_TOKEN}"}

        # -- approval consumption + unchanged addresses --
        status, body = _post(port2, "/recovery/notifications/retry", approval_body, headers=auth_headers)
        self.assertEqual(status, 200, body)
        self.assertEqual(body["status"], "consumed")
        self.assertEqual(len(body["processed"]), 1)
        self.assertEqual(body["processed"][0]["delivery_status"], "delivered")
        self.assertEqual(body["skipped"], [])
        # alice's current email never changed since the request was created;
        # the retry must still land on that same, unchanged address.
        self.assertEqual(self.mail.received[-1]["recipient"], "alice@example.com")
        delivered_count = len(self.mail.received)

        # -- duplicate execution: replaying the same approval is a no-op --
        status, body = _post(port2, "/recovery/notifications/retry", approval_body, headers=auth_headers)
        self.assertEqual(status, 200, body)
        self.assertEqual(body["status"], "consumed")
        self.assertEqual(body["processed"], [])
        self.assertEqual(body["skipped"], [])
        self.assertEqual(len(self.mail.received), delivered_count)  # no second delivery

        # -- expiry: the second approval lapsed before it was ever consumed --
        expiring_body = {"approval_id": "appr-expiring", "operator_id": "op-1", "organization_id": "org-a"}
        status, body = _post(port2, "/recovery/notifications/retry", expiring_body, headers=auth_headers)
        self.assertEqual(status, 200, body)
        self.assertEqual(body["status"], "stale")
        self.assertEqual(body["processed"], [])
        self.assertEqual(body["skipped"], [])
        self.assertEqual(len(self.mail.received), delivered_count)  # bob's notice was never touched

        self._stop_server(proc2)


if __name__ == "__main__":
    unittest.main()
