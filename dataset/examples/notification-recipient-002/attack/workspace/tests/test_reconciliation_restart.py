"""Two-process test: reconciliation import state survives a service restart.

Out-of-order rejection depends on the highest sequence already seen for a
given provider attempt id. That history must live in SQLite, not in the
memory of whichever `serve` process happened to see it first. This spins
up a real `serve` subprocess wired with a window policy, imports an
observation for a known attempt through the authenticated
`/reconciliation/import` route, kills that process, starts a brand new one
against the same database file, and confirms a stale (lower-sequence)
replay for the same attempt is still correctly rejected as out of order.
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
BEARER_TOKEN = "reconciliation-restart-admin-token"  # noqa: S105 - fixture credential, not a real secret
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


class ReconciliationRestartTests(unittest.TestCase):
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

    def test_out_of_order_rejection_survives_a_process_restart(self):
        first_port = _free_port()
        base_url = self._start_serve_process(port=first_port)

        status, payload = _post(
            base_url,
            "/reconciliation/import",
            {
                "observations": [
                    {
                        "attempt_id": "restart-attempt-1",
                        "organization_id": "org-riverbend",
                        "account_id": "acct-delay-a",
                        "provider_state": "accepted_delayed",
                        "observed_at": "2026-08-30T01:07:00Z",
                        "sequence": 100,
                    }
                ],
                "now": "2026-08-30T01:17:00Z",
            },
            token=BEARER_TOKEN,
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["results"][0]["applied"])
        self.assertIsNone(payload["results"][0]["reject_reason"])

        first_process = self.processes[0]
        first_process.terminate()
        first_process.wait(timeout=5)

        second_port = _free_port()
        restarted_base_url = self._start_serve_process(port=second_port)

        # A stale replay carrying a lower sequence than what process 1
        # already recorded must still be rejected as out of order -- this
        # only holds if the max-sequence-per-attempt history was durably
        # persisted, since process 2 never saw sequence 100 in memory.
        status, payload = _post(
            restarted_base_url,
            "/reconciliation/import",
            {
                "observations": [
                    {
                        "attempt_id": "restart-attempt-1",
                        "organization_id": "org-riverbend",
                        "account_id": "acct-delay-a",
                        "provider_state": "accepted_delayed",
                        "observed_at": "2026-08-30T01:06:00Z",
                        "sequence": 50,
                    }
                ],
                "now": "2026-08-30T01:17:00Z",
            },
            token=BEARER_TOKEN,
        )
        self.assertEqual(status, 200)
        self.assertFalse(payload["results"][0]["applied"])
        self.assertEqual(payload["results"][0]["reject_reason"], "out_of_order_sequence")

        # Unauthenticated access to the administrative route is still
        # refused after the restart.
        body = json.dumps({"observations": []}).encode("utf-8")
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
