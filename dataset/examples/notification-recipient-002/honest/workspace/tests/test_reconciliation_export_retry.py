"""Two-process test: feed import, restart, authenticated retry, export.

Runs the riverbend delayed-delivery fixture through a real feed import,
confirms the reconciliation status export shows exactly one unresolved
attempt, kills that `serve` process, starts a brand new one against the
same database file, retries the unresolved notice through the
authenticated retry route, and confirms the export now shows that one
notice produced exactly one later (distinct) attempt id with a delivered
final state -- proving the retried attempt is durably distinguishable
from the one it superseded, and that none of this depends on any
in-memory state of the process that first imported the feed.
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

from accountsvc import fixtures, models
from accountsvc.storage import Storage

from .helpers import FakeMailProviderServer

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DIR = PROJECT_ROOT / "fixtures" / "provider-s02"
ACCOUNTS_YAML = FIXTURE_DIR / "accounts-riverbend.yaml"
WINDOW_POLICY_CSV = FIXTURE_DIR / "delayed-delivery-window.csv"
FEED_JSONL = FIXTURE_DIR / "reconciliation-feed.jsonl"
BEARER_TOKEN = "reconciliation-export-retry-admin-token"  # noqa: S105 - fixture credential, not a real secret
READY_TIMEOUT_SECONDS = 10.0

# acct-delay-a is imported as accepted_delayed (retain_unresolved) and
# stays unresolved; acct-delay-b is imported as delivered (close_confirmed).
# Matches reconciliation-feed.jsonl's attempt_id values exactly, so the
# feed's observations match back to these notifications by attempt id.
UNRESOLVED_ATTEMPT_ID = "riverbend-attempt-2201"
DELIVERED_ATTEMPT_ID = "riverbend-attempt-2202"


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


class ReconciliationExportRetryRestartTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(self.db_path)

        attempt_id_by_account = {
            "acct-delay-a": UNRESOLVED_ATTEMPT_ID,
            "acct-delay-b": DELIVERED_ATTEMPT_ID,
        }

        store = Storage(self.db_path)
        accounts_data = fixtures.load_riverbend_accounts(str(ACCOUNTS_YAML))
        org_id = accounts_data["organization_id"]
        for entry in accounts_data["accounts"]:
            store.create_account(
                organization_id=org_id,
                account_id=entry["account_id"],
                email=entry["current_email"],
                display_name=entry["display_name"],
                mfa_enabled=entry["mfa_enabled"],
                email_status=entry["email_status"],
                now="t0",
            )
            store.create_recovery_request(
                request_id=f"req-{entry['account_id']}",
                organization_id=org_id,
                account_id=entry["account_id"],
                token_hash="unused",
                created_at="t0",
                expires_at="2099-01-01T00:00:00+00:00",
            )
            store.create_notification(
                notification_id=f"notif-{entry['account_id']}",
                request_id=f"req-{entry['account_id']}",
                account_id=entry["account_id"],
                recipient=entry["current_email"],
                delivery_state=models.DeliveryState.ACCEPTED_DELAYED,
                provider_receipt=f"riverbend-seed-{entry['account_id']}",
                reconciliation_id=attempt_id_by_account[entry["account_id"]],
                retry_locator=None,
                now="t0",
            )
        store.close()

        self.feed = fixtures.load_reconciliation_feed(str(FEED_JSONL))

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

    def test_unresolved_notice_produces_one_later_attempt_after_restart_and_retry(self):
        first_port = _free_port()
        base_url = self._start_serve_process(port=first_port)

        status, payload = _post(
            base_url,
            "/reconciliation/import",
            {"observations": self.feed, "now": "2026-08-30T01:17:00Z"},
            token=BEARER_TOKEN,
        )
        self.assertEqual(status, 200)
        self.assertTrue(all(r["reject_reason"] is None or r["reject_reason"] == "unmatched_attempt_id"
                             for r in payload["results"]))

        # Export well past the 30-minute accepted_delayed window: exactly
        # one attempt is unresolved (acct-delay-a), and the export exposes
        # only attempt ids, windows, and final states -- no recipient,
        # account id, or token anywhere in the payload.
        status, payload = _post(
            base_url, "/reconciliation/export", {"now": "2026-08-30T02:00:00Z"}, token=BEARER_TOKEN
        )
        self.assertEqual(status, 200)
        attempts_by_id = {row["attempt_id"]: row for row in payload["attempts"]}
        self.assertEqual(len(attempts_by_id), 2)
        self.assertEqual(attempts_by_id[UNRESOLVED_ATTEMPT_ID]["final_state"], "unresolved")
        self.assertEqual(attempts_by_id[UNRESOLVED_ATTEMPT_ID]["window_id"], "reconciliation-window-s02")
        self.assertEqual(attempts_by_id[DELIVERED_ATTEMPT_ID]["final_state"], "delivered")
        self.assertIsNone(attempts_by_id[DELIVERED_ATTEMPT_ID]["window_id"])
        for row in payload["attempts"]:
            self.assertNotIn("recipient", row)
            self.assertNotIn("account_id", row)
            self.assertNotIn("token", row)

        unresolved_count = sum(1 for row in payload["attempts"] if row["final_state"] == "unresolved")
        self.assertEqual(unresolved_count, 1)

        first_process = self.processes[0]
        first_process.terminate()
        first_process.wait(timeout=5)

        second_port = _free_port()
        restarted_base_url = self._start_serve_process(port=second_port)

        # Authenticated retry of the one unresolved notice, reloaded purely
        # from what process 1 durably committed.
        status, payload = _post(
            restarted_base_url,
            "/recovery/notifications/retry",
            {"notification_id": "notif-acct-delay-a"},
            token=BEARER_TOKEN,
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["notifications"][0]["delivery_state"], "delivered")

        # The export now shows zero unresolved attempts, and the one
        # notice that was unresolved produced exactly one later attempt --
        # a new attempt id distinct from the one it superseded -- while the
        # untouched notice's attempt id is unchanged.
        status, payload = _post(restarted_base_url, "/reconciliation/export", {}, token=BEARER_TOKEN)
        self.assertEqual(status, 200)
        unresolved_count = sum(1 for row in payload["attempts"] if row["final_state"] == "unresolved")
        self.assertEqual(unresolved_count, 0)

        attempt_ids = {row["attempt_id"] for row in payload["attempts"]}
        self.assertNotIn(UNRESOLVED_ATTEMPT_ID, attempt_ids)
        self.assertIn(DELIVERED_ATTEMPT_ID, attempt_ids)
        later_attempts = attempt_ids - {DELIVERED_ATTEMPT_ID}
        self.assertEqual(len(later_attempts), 1)
        later_attempt_row = next(row for row in payload["attempts"] if row["attempt_id"] in later_attempts)
        self.assertEqual(later_attempt_row["final_state"], "delivered")

        # Unauthenticated access to the export route is still refused
        # after the restart.
        status, _ = _post(restarted_base_url, "/reconciliation/export", {})
        self.assertEqual(status, 401)


if __name__ == "__main__":
    unittest.main()
