"""Two-process test: the reconciliation feed cursor survives a service restart.

A resumable feed import commits its durable cursor at page granularity, so
that history must live in SQLite, not in the memory of whichever `serve`
process happened to import a given page. This spins up a real `serve`
subprocess wired with a window policy, imports page 0 of a named feed
through the authenticated `/reconciliation/import` route, kills that
process, starts a brand new one against the same database file, and
confirms replaying page 0 is a no-op (the committed cursor survived the
restart) while a genuinely new page still applies and advances the cursor.
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

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WINDOW_POLICY_CSV = PROJECT_ROOT / "fixtures" / "provider-s02" / "delayed-delivery-window.csv"
BEARER_TOKEN = "reconciliation-cursor-restart-admin-token"  # noqa: S105 - fixture credential, not a real secret
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


def _post(base_url: str, path: str, payload: dict, *, token: str):
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        base_url + path, data=body, method="POST", headers={"Authorization": f"Bearer {token}"}
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        with exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))


class ReconciliationCursorRestartTests(unittest.TestCase):
    FEED_ID = "restart-feed"

    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(self.db_path)

        # Seed an account, recovery request, and a notification with a known
        # reconciliation id directly -- reconciliation import does not
        # depend on ever having sent mail, only on a notification existing
        # under that attempt id.
        store = Storage(self.db_path)
        store.create_account(
            organization_id="org-riverbend", account_id="acct-delay-a", email="priya@riverbend.example", now="t0"
        )
        store.create_recovery_request(
            request_id="req-restart-1",
            organization_id="org-riverbend",
            account_id="acct-delay-a",
            token_hash="unused",
            created_at="t0",
            expires_at="2099-01-01T00:00:00+00:00",
        )
        store.create_notification(
            notification_id="notif-restart-1",
            request_id="req-restart-1",
            account_id="acct-delay-a",
            recipient="priya@riverbend.example",
            delivery_state="accepted_delayed",
            provider_receipt="seed-receipt",
            reconciliation_id="restart-attempt-1",
            retry_locator=None,
            now="t0",
        )
        store.close()

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
        for suffix in ("", "-wal", "-shm"):
            candidate = self.db_path + suffix
            if os.path.exists(candidate):
                os.remove(candidate)

    def _start_serve_process(self, *, port: int) -> str:
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
                "http://127.0.0.1:1/unused",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--window-policy",
                str(WINDOW_POLICY_CSV),
            ],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.processes.append(process)
        _wait_until_ready("127.0.0.1", port)
        return f"http://127.0.0.1:{port}"

    def _page(self, *, page_number, provider_state, observed_at, sequence, now):
        return {
            "feed_id": self.FEED_ID,
            "page_number": page_number,
            "observations": [
                {
                    "attempt_id": "restart-attempt-1",
                    "organization_id": "org-riverbend",
                    "account_id": "acct-delay-a",
                    "provider_state": provider_state,
                    "observed_at": observed_at,
                    "sequence": sequence,
                }
            ],
            "now": now,
        }

    def test_cursor_survives_restart_and_rejects_replayed_page(self):
        first_port = _free_port()
        base_url = self._start_serve_process(port=first_port)

        status, payload = _post(
            base_url,
            "/reconciliation/import",
            self._page(
                page_number=0,
                provider_state="accepted_delayed",
                observed_at="2026-08-30T01:07:00Z",
                sequence=1,
                now="2026-08-30T01:17:00Z",
            ),
            token=BEARER_TOKEN,
        )
        self.assertEqual(status, 200)
        self.assertFalse(payload["skipped"])
        self.assertEqual(payload["committed_page"], 0)
        self.assertTrue(payload["results"][0]["applied"])

        first_process = self.processes[0]
        first_process.terminate()
        first_process.wait(timeout=5)

        second_port = _free_port()
        restarted_base_url = self._start_serve_process(port=second_port)

        # Replaying page 0 against the restarted process must be a no-op --
        # this only holds if the committed cursor was durably persisted,
        # since process 2 never saw page 0 in memory.
        status, payload = _post(
            restarted_base_url,
            "/reconciliation/import",
            self._page(
                page_number=0,
                provider_state="accepted_delayed",
                observed_at="2026-08-30T01:07:00Z",
                sequence=1,
                now="2026-08-30T01:17:00Z",
            ),
            token=BEARER_TOKEN,
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["skipped"])
        self.assertEqual(payload["results"], [])
        self.assertEqual(payload["committed_page"], 0)

        # A genuinely new page still applies and advances the cursor.
        status, payload = _post(
            restarted_base_url,
            "/reconciliation/import",
            self._page(
                page_number=1,
                provider_state="delivered",
                observed_at="2026-08-30T01:20:00Z",
                sequence=2,
                now="2026-08-30T01:22:00Z",
            ),
            token=BEARER_TOKEN,
        )
        self.assertEqual(status, 200)
        self.assertFalse(payload["skipped"])
        self.assertEqual(payload["committed_page"], 1)
        self.assertTrue(payload["results"][0]["applied"])

        # Unauthenticated access to the administrative route is still
        # refused after the restart.
        body = json.dumps({"feed_id": self.FEED_ID, "page_number": 2, "observations": []}).encode("utf-8")
        request = urllib.request.Request(restarted_base_url + "/reconciliation/import", data=body, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                status = response.status
        except urllib.error.HTTPError as exc:
            with exc:
                status = exc.code
        self.assertEqual(status, 401)


if __name__ == "__main__":
    unittest.main()
