"""One public smoke path: delayed-delivery reconciliation and operator retry.

A single end-to-end run through the flow README.md documents, driven
almost entirely through the public HTTP surface (the one exception is
seeding the account a fresh database has no HTTP route to create):
start recovery, receive a delayed provider result, import a reconciliation
observation for that attempt (retain_unresolved), restart the service, and
retry the notice reconciliation has left unresolved -- authenticated, and
delivered to the account's *current* email even though that address
changed while the service was down, exactly as the documented retry rule
requires.
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
WINDOW_POLICY_CSV = PROJECT_ROOT / "fixtures" / "provider-s02" / "delayed-delivery-window.csv"
BEARER_TOKEN = "smoke-admin-token"  # noqa: S105 - fixture credential, not a real secret
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


def _post(base_url: str, path: str, payload: dict, *, token=None):
    body = json.dumps(payload).encode("utf-8")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    request = urllib.request.Request(base_url + path, data=body, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        with exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))


class SmokeDelayedReconciliationTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(self.db_path)

        store = Storage(self.db_path)
        store.create_account(
            organization_id="org-smoke", account_id="acct-smoke", email="operator@smoke.example", now="t0"
        )
        store.close()

        self.mail_provider = FakeMailProviderServer()

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
                self.mail_provider.url,
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

    def test_start_import_restart_retry_delivers_to_current_email(self):
        self.mail_provider.set_success(state="accepted_delayed", receipt="smoke-receipt-1")

        first_port = _free_port()
        base_url = self._start_serve_process(port=first_port)

        # Start recovery; the provider's response records a delayed result.
        status, payload = _post(
            base_url,
            "/recovery/start",
            {"organization": "org-smoke", "email": "operator@smoke.example"},
        )
        self.assertEqual(status, 202)
        self.assertEqual(payload["delivery_status"], "accepted_delayed")
        attempt_id = self.mail_provider.last_captured()["reconciliation_id"]

        # Import a reconciliation observation for that attempt: provider_state
        # accepted_delayed maps to reconciliation_class retain_unresolved in
        # the configured window policy -- an unresolved observation.
        status, payload = _post(
            base_url,
            "/reconciliation/import",
            {
                "observations": [
                    {
                        "attempt_id": attempt_id,
                        "organization_id": "org-smoke",
                        "account_id": "acct-smoke",
                        "provider_state": "accepted_delayed",
                        "observed_at": "2026-08-30T01:07:00Z",
                        "sequence": 1,
                    }
                ],
                "now": "2026-08-30T01:17:00Z",
            },
            token=BEARER_TOKEN,
        )
        self.assertEqual(status, 200)
        result = payload["results"][0]
        self.assertTrue(result["applied"])
        self.assertIsNone(result["reject_reason"])
        self.assertEqual(result["reconciliation_class"], "retain_unresolved")

        first_process = self.processes[0]
        first_process.terminate()
        first_process.wait(timeout=5)

        # The account's email changes while the service is down.
        store = Storage(self.db_path)
        store.change_email(account_id="acct-smoke", new_email="operator-new@smoke.example", now="t1")
        store.close()

        second_port = _free_port()
        restarted_base_url = self._start_serve_process(port=second_port)

        # The 30-minute window elapsed long ago relative to real wall-clock
        # time, so reconciliation now classifies this attempt unresolved.
        status, payload = _post(restarted_base_url, "/reconciliation/status", {}, token=BEARER_TOKEN)
        self.assertEqual(status, 200)
        self.assertEqual(len(payload["attempts"]), 1)
        self.assertEqual(payload["attempts"][0]["status"], "unresolved")
        notification_id = payload["attempts"][0]["notification_id"]

        self.mail_provider.set_success()
        status, payload = _post(
            restarted_base_url,
            "/recovery/notifications/retry",
            {"notification_id": notification_id},
            token=BEARER_TOKEN,
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["notifications"][0]["delivery_state"], "delivered")

        # Delivered to the account's current email -- the new address, not
        # the one recovery started with.
        self.assertEqual(self.mail_provider.last_captured()["recipient"], "operator-new@smoke.example")


if __name__ == "__main__":
    unittest.main()
