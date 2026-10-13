"""Two-process integration tests for POST /recovery/notifications/retry.

Two eligibility paths share this one route, both funneling through the
same RecoveryService.retry_notifications consumer and
notice.recipient_from_retry_locator helper:

- The ordinary compatibility path: a notice the mail endpoint rejected
  outright (HTTP 503) is persisted FAILED and stays retryable with only
  the bearer token -- no reconciliation window policy or other scenario
  metadata required. OrdinaryFailedRetryRestartTests exercises this in
  isolation, starting the second process with no --window-policy at all,
  before the reconciliation-unresolved scenario test below it.
- The reconciliation-unresolved path: a notice the provider accepted for
  delayed delivery (ACCEPTED_DELAYED) that reconciliation's own window
  policy has since classified unresolved. UnresolvedRetryRestartTests
  covers an unchanged address, a duplicate retry, expiry, a completed
  notice, and authentication.

Every notice under test is either created through the real HTTP flow or
seeded directly into SQLite before any `serve` subprocess starts, and is
only ever reloaded by that subprocess from its saved retry_locator,
account, and request rows -- proving retry survives a restart rather than
depending on any in-memory state of the process that first saw it.
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

from accountsvc import notice
from accountsvc.storage import Storage

from .helpers import FakeMailProviderServer

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WINDOW_POLICY_CSV = PROJECT_ROOT / "fixtures" / "provider-s02" / "delayed-delivery-window.csv"
BEARER_TOKEN = "retry-restart-admin-token"  # noqa: S105 - fixture credential, not a real secret
READY_TIMEOUT_SECONDS = 10.0

# Deliberately far in the past: whatever wall-clock "now" the test happens
# to run at, this is already well outside the fixture's 30-minute
# accepted_delayed window, so no real sleep is needed to age a seeded
# notification into "unresolved".
OLD_TIMESTAMP = "2020-01-01T00:00:00+00:00"
FAR_FUTURE_EXPIRY = "2099-01-01T00:00:00+00:00"
PAST_EXPIRY = "2020-01-01T00:00:00+00:00"


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


class OrdinaryFailedRetryRestartTests(unittest.TestCase):
    """The provider-rejected (503) compatibility path, restart-only."""

    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(self.db_path)

        store = Storage(self.db_path)
        store.create_account(
            organization_id="org-riverbend", account_id="acct-delay-a", email="priya@riverbend.example", now="t0"
        )
        store.close()

        self.mail_provider = FakeMailProviderServer()
        self.mail_provider.set_failure(status=503, message="mail provider unavailable")

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
        # Deliberately no --window-policy: the ordinary compatibility path
        # must remain eligible with no reconciliation engine configured at
        # all -- no scenario metadata, workflow transition, or operator
        # approval is a prerequisite for it.
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
            ],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.processes.append(process)
        _wait_until_ready("127.0.0.1", port)
        return f"http://127.0.0.1:{port}"

    def test_provider_rejected_notice_retries_after_restart_with_no_reconciliation_configured(self):
        first_port = _free_port()
        base_url = self._start_serve_process(port=first_port)

        status, payload = _post(
            base_url,
            "/recovery/start",
            {"organization": "org-riverbend", "email": "priya@riverbend.example"},
        )
        self.assertEqual(status, 202)
        self.assertEqual(payload["delivery_status"], "failed")
        request_id = payload["request_id"]

        # The opaque 503 body is stored verbatim as the provider receipt --
        # never interpreted as, and never overwriting, the recipient.
        store = Storage(self.db_path)
        notification = store.notifications_for_request(request_id)[0]
        self.assertIn("mail provider unavailable", notification.provider_receipt)
        self.assertEqual(notification.recipient, "priya@riverbend.example")
        notification_id = notification.notification_id
        store.close()

        first_process = self.processes[0]
        first_process.terminate()
        first_process.wait(timeout=5)

        self.mail_provider.set_success()
        second_port = _free_port()
        restarted_base_url = self._start_serve_process(port=second_port)

        # Unauthenticated retry is refused before any persisted notice is
        # even looked up, restart or not.
        status, _ = _post(restarted_base_url, "/recovery/notifications/retry", {})
        self.assertEqual(status, 401)

        status, payload = _post(
            restarted_base_url,
            "/recovery/notifications/retry",
            {},
            token=BEARER_TOKEN,
        )
        self.assertEqual(status, 200)
        self.assertEqual(len(payload["notifications"]), 1)
        self.assertEqual(payload["notifications"][0]["notification_id"], notification_id)
        self.assertEqual(payload["notifications"][0]["delivery_state"], "delivered")

        store = Storage(self.db_path)
        notification = store.get_notification(notification_id)
        self.assertEqual(notification.recipient, "priya@riverbend.example")
        store.close()


class UnresolvedRetryRestartTests(unittest.TestCase):
    """The reconciliation-unresolved path, across a process restart."""

    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(self.db_path)

        store = Storage(self.db_path)
        store.create_account(
            organization_id="org-riverbend", account_id="acct-delay-a", email="priya@riverbend.example", now="t0"
        )

        # unchanged address: a plain unresolved delayed delivery, recipient
        # equal to the account's current (unchanged) email.
        store.create_recovery_request(
            request_id="req-unchanged",
            organization_id="org-riverbend",
            account_id="acct-delay-a",
            token_hash="unused-unchanged",
            created_at="t0",
            expires_at=FAR_FUTURE_EXPIRY,
        )
        store.create_notification(
            notification_id="notif-unchanged",
            request_id="req-unchanged",
            account_id="acct-delay-a",
            recipient="priya@riverbend.example",
            delivery_state="accepted_delayed",
            provider_receipt="receipt-unchanged",
            reconciliation_id="attempt-unchanged",
            retry_locator=notice.encode_retry_locator("receipt-unchanged", "acct-delay-a"),
            now=OLD_TIMESTAMP,
        )

        # duplicate retry: a second, independent unresolved delayed
        # delivery -- retried once successfully, then retried again to
        # prove the second attempt is refused rather than resent.
        store.create_recovery_request(
            request_id="req-duplicate",
            organization_id="org-riverbend",
            account_id="acct-delay-a",
            token_hash="unused-duplicate",
            created_at="t0",
            expires_at=FAR_FUTURE_EXPIRY,
        )
        store.create_notification(
            notification_id="notif-duplicate",
            request_id="req-duplicate",
            account_id="acct-delay-a",
            recipient="priya@riverbend.example",
            delivery_state="accepted_delayed",
            provider_receipt="receipt-duplicate",
            reconciliation_id="attempt-duplicate",
            retry_locator=notice.encode_retry_locator("receipt-duplicate", "acct-delay-a"),
            now=OLD_TIMESTAMP,
        )

        # completed notices: the owning recovery request was already
        # completed (through some other notification/token on the same
        # request); this notification itself never got a delivery
        # confirmation.
        store.create_recovery_request(
            request_id="req-completed",
            organization_id="org-riverbend",
            account_id="acct-delay-a",
            token_hash="unused-completed",
            created_at="t0",
            expires_at=FAR_FUTURE_EXPIRY,
        )
        store.mark_recovery_request_completed("req-completed", now="t1")
        store.create_notification(
            notification_id="notif-completed",
            request_id="req-completed",
            account_id="acct-delay-a",
            recipient="priya@riverbend.example",
            delivery_state="accepted_delayed",
            provider_receipt="receipt-completed",
            reconciliation_id="attempt-completed",
            retry_locator=notice.encode_retry_locator("receipt-completed", "acct-delay-a"),
            now=OLD_TIMESTAMP,
        )

        # expiry: the recovery request is nominally still pending, but its
        # persisted expires_at has already elapsed -- proving expiry is
        # enforced from the durable timestamp, not any process-creation
        # state.
        store.create_recovery_request(
            request_id="req-expired",
            organization_id="org-riverbend",
            account_id="acct-delay-a",
            token_hash="unused-expired",
            created_at="t0",
            expires_at=PAST_EXPIRY,
        )
        store.create_notification(
            notification_id="notif-expired",
            request_id="req-expired",
            account_id="acct-delay-a",
            recipient="priya@riverbend.example",
            delivery_state="accepted_delayed",
            provider_receipt="receipt-expired",
            reconciliation_id="attempt-expired",
            retry_locator=notice.encode_retry_locator("receipt-expired", "acct-delay-a"),
            now=OLD_TIMESTAMP,
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

    def test_unresolved_retry_scenarios_across_a_process_restart(self):
        first_port = _free_port()
        base_url = self._start_serve_process(port=first_port)

        # authentication: refused before any notice is even looked up.
        status, _ = _post(base_url, "/recovery/notifications/retry", {"notification_id": "notif-unchanged"})
        self.assertEqual(status, 401)

        # unchanged address: the account's current email still matches the
        # notice's original recipient; retry succeeds and mail goes to
        # that same address.
        status, payload = _post(
            base_url,
            "/recovery/notifications/retry",
            {"notification_id": "notif-unchanged"},
            token=BEARER_TOKEN,
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["notifications"][0]["delivery_state"], "delivered")
        self.assertEqual(self.mail_provider.last_captured()["recipient"], "priya@riverbend.example")

        # duplicate retry, first call: succeeds from process 1.
        status, payload = _post(
            base_url,
            "/recovery/notifications/retry",
            {"notification_id": "notif-duplicate"},
            token=BEARER_TOKEN,
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["notifications"][0]["delivery_state"], "delivered")
        mail_count_after_first_duplicate = len(self.mail_provider.behavior.captured)

        first_process = self.processes[0]
        first_process.terminate()
        first_process.wait(timeout=5)

        second_port = _free_port()
        restarted_base_url = self._start_serve_process(port=second_port)

        # duplicate retry, second call: reload after restart shows this
        # notice already delivered, so the retry is refused -- and no new
        # mail is sent.
        status, payload = _post(
            restarted_base_url,
            "/recovery/notifications/retry",
            {"notification_id": "notif-duplicate"},
            token=BEARER_TOKEN,
        )
        self.assertEqual(status, 409)
        self.assertEqual(len(self.mail_provider.behavior.captured), mail_count_after_first_duplicate)

        # completed notices: the owning request was already completed
        # through some other notification; this retry must not resend
        # mail or disturb that completed status.
        mail_count_before_completed = len(self.mail_provider.behavior.captured)
        status, payload = _post(
            restarted_base_url,
            "/recovery/notifications/retry",
            {"notification_id": "notif-completed"},
            token=BEARER_TOKEN,
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["notifications"][0]["delivery_state"], "failed")
        self.assertEqual(len(self.mail_provider.behavior.captured), mail_count_before_completed)
        store = Storage(self.db_path)
        self.assertEqual(store.get_recovery_request("req-completed").status, "completed")
        store.close()

        # expiry: the request's persisted expires_at has already elapsed;
        # retry marks it expired and the notice failed, without sending
        # mail.
        mail_count_before_expired = len(self.mail_provider.behavior.captured)
        status, payload = _post(
            restarted_base_url,
            "/recovery/notifications/retry",
            {"notification_id": "notif-expired"},
            token=BEARER_TOKEN,
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["notifications"][0]["delivery_state"], "failed")
        self.assertEqual(len(self.mail_provider.behavior.captured), mail_count_before_expired)
        store = Storage(self.db_path)
        self.assertEqual(store.get_recovery_request("req-expired").status, "expired")
        store.close()


if __name__ == "__main__":
    unittest.main()
