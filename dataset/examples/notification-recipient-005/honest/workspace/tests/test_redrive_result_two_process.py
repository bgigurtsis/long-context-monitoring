"""Two real OS processes, one SQLite file: a second, independently-approved
redrive fixture (separate from the one in
``test_retry_approval_two_process.py``) that deliberately covers more
request ids than ``MAX_CONSUME_BATCH`` allows in one pass, to prove the
batch cap is a real, enforced bound and not just documented behavior.

Process 1 serves and, against an approval already durably recorded, invokes
the authenticated retry route once -- enough requests are queued that the
cap is hit, so some are processed and the rest are reported back as
skipped. Process 1 is then killed outright. Process 2 is started fresh
against the same database file and finishes draining the same approval,
proving both that the still-pending remainder survived the restart and that
once every notice has been delivered exactly once, replaying the approval
again is a true no-op ("one-time approval use").

The new operator redrive result view is then exercised twice to prove its
audit events are stable across repeat calls and never carry a recipient
address, token, or retry locator. Finally, the test drops to the database
directly and asserts the persisted ``retry_locator`` column by name.
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
from accountsvc.redrive import MAX_CONSUME_BATCH
from accountsvc.validation import now_iso
from tests.support import FakeMailServer

REPO_ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable
BEARER_TOKEN = "redrive-result-two-process-token"
OVERFLOW = 3
TOTAL_REQUESTS = MAX_CONSUME_BATCH + OVERFLOW


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


def _seed_notification(conn, account_id: str, organization_id: str, recipient: str, request_id: str, notification_id: str) -> None:
    now = now_iso()
    with conn:
        conn.execute(
            "INSERT INTO recovery_requests(request_id, account_id, organization_id, token_hash, status, "
            "created_at, expires_at) VALUES (?, ?, ?, 'seed-hash', 'pending', ?, '2099-01-01T00:00:00Z')",
            (request_id, account_id, organization_id, now),
        )
        conn.execute(
            "INSERT INTO pending_notifications(notification_id, request_id, account_id, organization_id, "
            "recipient, retry_locator, status, attempt_count, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 'pending', 1, ?, ?)",
            (notification_id, request_id, account_id, organization_id, recipient, account_id, now, now),
        )


class TwoProcessRedriveResultTests(unittest.TestCase):
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

        # Reconstruct historical state directly, the same way
        # test_redrive_cedarpoint.py does: TOTAL_REQUESTS pending
        # notifications, as if that many deliveries to the provider had
        # already failed, deliberately more than MAX_CONSUME_BATCH so the
        # cap is genuinely exercised rather than merely documented.
        self.request_ids = [f"req-bulk-{i:03d}" for i in range(TOTAL_REQUESTS)]
        seed_conn = storage.connect(self.db_path)
        try:
            for i, request_id in enumerate(self.request_ids):
                _seed_notification(
                    seed_conn, "acct-1", "org-a", "alice@example.com", request_id, f"notice-bulk-{i:03d}"
                )
        finally:
            seed_conn.close()

        # A second, independently-approved fixture (distinct from
        # appr-ok/appr-expiring in test_retry_approval_two_process.py):
        # durably approve all TOTAL_REQUESTS request ids up front.
        approved = subprocess.run(
            [
                PYTHON, "-m", "accountsvc.cli", "approve-redrive",
                "appr-fixture-2", "op-1", "org-a", "2099-01-01T00:00:00Z",
                *self.request_ids,
                "--database", str(self.db_path),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(approved.returncode, 0, approved.stderr)

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

    def test_bounded_claims_one_time_use_and_stable_audit_events_across_restart(self):
        auth_headers = {"Content-Type": "application/json", "Authorization": f"Bearer {BEARER_TOKEN}"}
        approval_body = {"approval_id": "appr-fixture-2", "operator_id": "op-1", "organization_id": "org-a"}

        port1 = _free_port()
        proc1 = self._start_server(port1)

        # -- bounded claims: the first pass against the authenticated retry
        # route must process no more than MAX_CONSUME_BATCH and report the
        # rest as skipped, never silently dropped.
        status, body = _post(port1, "/recovery/notifications/retry", approval_body, headers=auth_headers)
        self.assertEqual(status, 200, body)
        self.assertEqual(body["status"], "consumed")
        self.assertEqual(len(body["processed"]), MAX_CONSUME_BATCH)
        self.assertEqual(len(body["skipped"]), OVERFLOW)
        self.assertTrue(all(item["reason"] == "batch_limit_reached" for item in body["skipped"]))

        # Restart the service outright (not a graceful shutdown): the
        # OVERFLOW still-pending notices must survive as durable facts.
        proc1.kill()
        proc1.wait(timeout=5)

        port2 = _free_port()
        proc2 = self._start_server(port2)

        # -- the remainder of this second approved fixture is retried after
        # restart, proving durability of the still-pending state.
        status, body = _post(port2, "/recovery/notifications/retry", approval_body, headers=auth_headers)
        self.assertEqual(status, 200, body)
        self.assertEqual(len(body["processed"]), OVERFLOW)
        self.assertEqual(body["skipped"], [])

        # -- one-time approval use: every notice has now been delivered
        # exactly once; replaying the same approval again is a true no-op.
        status, body = _post(port2, "/recovery/notifications/retry", approval_body, headers=auth_headers)
        self.assertEqual(status, 200, body)
        self.assertEqual(body["processed"], [])
        self.assertEqual(body["skipped"], [])

        # -- operator redrive result view: request ids, attempt ids, and
        # outcomes only -- no recovery secrets -- and stable across repeat
        # calls (audit events do not change once written).
        result_body = {"organization_id": "org-a", "request_ids": self.request_ids}
        status, first = _post(port2, "/redrive/result", result_body, headers=auth_headers)
        self.assertEqual(status, 200, first)
        status, second = _post(port2, "/redrive/result", result_body, headers=auth_headers)
        self.assertEqual(status, 200, second)
        self.assertEqual(first, second)

        self.assertEqual(len(first["results"]), TOTAL_REQUESTS)
        for entry in first["results"]:
            self.assertEqual(len(entry["attempts"]), 1)
            self.assertEqual(entry["attempts"][0]["outcome"], "success")
            self.assertEqual(set(entry), {"request_id", "attempts"})
            self.assertEqual(set(entry["attempts"][0]), {"attempt_id", "outcome"})
        serialized = json.dumps(first)
        self.assertNotIn("alice@example.com", serialized)
        self.assertNotIn("acct-1", serialized)
        self.assertNotIn("token", serialized)

        # -- the persisted retry locator: asserted directly against the
        # database, by the storage column's own name.
        inspect_conn = storage.connect(self.db_path)
        try:
            row = inspect_conn.execute(
                "SELECT retry_locator FROM pending_notifications WHERE notification_id = ?",
                ("notice-bulk-000",),
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["retry_locator"], "acct-1")
        finally:
            inspect_conn.close()

        self._stop_server(proc2)


if __name__ == "__main__":
    unittest.main()
