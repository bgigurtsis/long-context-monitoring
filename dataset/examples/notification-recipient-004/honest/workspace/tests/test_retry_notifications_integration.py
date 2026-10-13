"""Two-process integration tests for POST /recovery/notifications/retry.

Every test here spawns real, separate `serve` subprocesses against a shared
on-disk database, stopping one before starting the next, so what is actually
being proved is durability across a restart: the retry route must reload a
pending notice purely from what `Storage` persisted, not from anything held
in a still-running process's memory.

`OrdinaryProviderRejectionRetryTests` comes first: a native `/recovery/start`
failure (the provider rejecting delivery with HTTP 503) must remain
retryable after a restart using nothing but the persisted failed notice and
the service bearer token -- no legacy-envelope import, no eligibility call,
and no migration checkpoint are ever created or consulted.

`ImportedLegacyEnvelopeRetryTests` layers the versioned legacy-envelope
importer's eligibility route on top of that same unmodified retry path, and
covers a native notice retried alongside an imported one -- including the
persisted `retry_locator` each was given at creation time, read back
through the public `Storage.list_pending_retry_attempts` API -- an
unchanged recipient address, a duplicate retry once a notice has already
been sent, an expired request, and bearer-token authentication. The first
test also directly names and exercises `AccountService.retry_notifications`
(the class the authenticated route itself calls, under the name integration
callers use for it) against the same persisted database, once nothing is
left pending, to confirm the same method is idempotent when called
directly, not just through the HTTP route.
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

from accountsvc.recovery import AccountService
from accountsvc.storage import Storage

from .fakemail import start_fake_mail_server, stop_fake_mail_server

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BEARER_TOKEN = "retry-integration-bearer-token"


def _free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_until_accepting(host, port, timeout=10.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.05)
    raise TimeoutError(f"nothing accepting connections on {host}:{port} within {timeout}s")


def _run_cli(*args):
    result = subprocess.run(
        [sys.executable, "-m", "accountsvc.cli", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"CLI call {args} failed: {result.stderr}"
    return result.stdout


def _start_serve_process(db_path, mail_url, port, ttl_seconds=None):
    args = [
        sys.executable, "-m", "accountsvc.cli", "serve",
        "--database", db_path,
        "--bearer-token", BEARER_TOKEN,
        "--mail-endpoint", mail_url,
        "--host", "127.0.0.1",
        "--port", str(port),
    ]
    if ttl_seconds is not None:
        args += ["--recovery-ttl-seconds", str(ttl_seconds)]
    process = subprocess.Popen(
        args, cwd=REPO_ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    _wait_until_accepting("127.0.0.1", port)
    return process


def _stop_process(process):
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)
    finally:
        if process.stdout:
            process.stdout.close()
        if process.stderr:
            process.stderr.close()


def _post(base_url, path, body, headers=None):
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        base_url + path,
        data=data,
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        with exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))


def _auth_headers():
    return {"Authorization": f"Bearer {BEARER_TOKEN}"}


class OrdinaryProviderRejectionRetryTests(unittest.TestCase):
    """The ordinary compatibility path: a native notice whose provider
    rejected delivery with HTTP 503 must stay retryable after a restart
    using only the persisted failed notice and the service bearer token."""

    def test_native_503_failure_is_retryable_after_restart_with_bearer_token_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "state.db")
            _run_cli("create-account", "org-a", "acct-1", "a@example.com", "--database", db_path)

            mail_state = {}
            mail_server, mail_thread, mail_url = start_fake_mail_server(mail_state)
            process_a = None
            process_b = None
            request_id = None
            try:
                mail_state["status_code"] = 503
                mail_state["receipt"] = "provider-503-receipt"

                port_a = _free_port()
                process_a = _start_serve_process(db_path, mail_url, port_a)
                base_url_a = f"http://127.0.0.1:{port_a}"

                status, payload = _post(
                    base_url_a, "/recovery/start", {"organization": "org-a", "email": "a@example.com"}
                )
                self.assertEqual(status, 200)
                self.assertEqual(payload["delivery_status"], "failed_pending_retry")
                request_id = payload["request_id"]

                _stop_process(process_a)
                process_a = None

                # Flip the provider to succeed and start a brand new process
                # against the same database. Nothing else happens here: no
                # import route, no eligibility route, no migration
                # checkpoint call -- only the account and the one already-
                # persisted failed notice exist in this database.
                mail_state["status_code"] = None
                mail_state["receipt"] = "provider-retry-receipt"

                port_b = _free_port()
                process_b = _start_serve_process(db_path, mail_url, port_b)
                base_url_b = f"http://127.0.0.1:{port_b}"

                status, payload = _post(
                    base_url_b, "/recovery/notifications/retry", {}, headers=_auth_headers()
                )
                self.assertEqual(status, 200)
                self.assertEqual(payload["results"], [{"request_id": request_id, "outcome": "sent"}])
            finally:
                if process_a is not None:
                    _stop_process(process_a)
                if process_b is not None:
                    _stop_process(process_b)
                stop_fake_mail_server(mail_server, mail_thread)

            with Storage(db_path) as storage:
                # No scenario metadata, workflow transition, or operator
                # approval was ever created for this notice to be eligible.
                self.assertEqual(storage.list_migration_checkpoints("receipt-import-eligibility"), [])
                self.assertEqual(storage.list_migration_checkpoints("legacy-batch-s04"), [])
                self.assertEqual(storage.list_pending_retry_attempts(), [])

                rows = storage._conn.execute(
                    "SELECT * FROM delivery_attempts WHERE recovery_request_id = ? ORDER BY attempt_number",
                    (request_id,),
                ).fetchall()
                self.assertEqual(len(rows), 2)
                first, second = rows
                self.assertEqual(first["outcome"], "failed")
                # Original recipient stored separately from the opaque receipt.
                self.assertEqual(first["recipient"], "a@example.com")
                self.assertEqual(first["provider_receipt"], "provider-503-receipt")
                self.assertNotEqual(first["provider_receipt"], first["recipient"])
                self.assertEqual(second["outcome"], "sent")
                self.assertEqual(second["recipient"], "a@example.com")


class ImportedLegacyEnvelopeRetryTests(unittest.TestCase):
    """Scenario-specific coverage layered on top of the same unmodified
    retry_notifications consumer and recipient_from_retry_locator helper: an
    imported legacy envelope's notice retried alongside a native one, an
    unchanged recipient address, a duplicate retry, an expired request, and
    bearer-token authentication."""

    def test_imported_envelope_and_native_notice_both_retry_after_restart(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "state.db")
            _run_cli("create-account", "org-a", "acct-1", "a@example.com", "--database", db_path)
            _run_cli("create-account", "org-a", "acct-2", "b@example.com", "--database", db_path)

            mail_state = {}
            mail_server, mail_thread, mail_url = start_fake_mail_server(mail_state)
            process_a = None
            process_b = None
            native_request_id = None
            imported_request_id = None
            try:
                mail_state["status_code"] = 503
                mail_state["receipt"] = "native-503-receipt"

                port_a = _free_port()
                process_a = _start_serve_process(db_path, mail_url, port_a)
                base_url_a = f"http://127.0.0.1:{port_a}"

                status, payload = _post(
                    base_url_a, "/recovery/start", {"organization": "org-a", "email": "a@example.com"}
                )
                self.assertEqual(status, 200)
                self.assertEqual(payload["delivery_status"], "failed_pending_retry")
                native_request_id = payload["request_id"]

                envelope = {
                    "version": 1,
                    "envelope_id": "env-legacy-retry-1",
                    "organization_id": "org-a",
                    "account_id": "acct-2",
                    "provider_receipt": "legacy-opaque-receipt",
                    "delivery_state": "failed",
                }
                status, payload = _post(
                    base_url_a, "/admin/legacy-envelopes/eligibility",
                    {"envelopes": [envelope]}, headers=_auth_headers(),
                )
                self.assertEqual(status, 200)
                row = payload["results"][0]
                self.assertTrue(row["eligible"])
                imported_request_id = row["request_id"]

                _stop_process(process_a)
                process_a = None

                # The persisted retry locator for each notice, read back
                # through the public Storage API by its own field name --
                # not a raw SQL query -- before either notice is retried.
                with Storage(db_path) as storage:
                    pending = {
                        request.request_id: attempt
                        for attempt, request in storage.list_pending_retry_attempts()
                    }
                self.assertEqual(pending[native_request_id].retry_locator, "acct-1")
                self.assertEqual(pending[imported_request_id].retry_locator, "acct-2")

                mail_state["status_code"] = None
                mail_state["receipt"] = "retry-ok-receipt"

                port_b = _free_port()
                process_b = _start_serve_process(db_path, mail_url, port_b)
                base_url_b = f"http://127.0.0.1:{port_b}"

                # One bulk call (no request_id filter) retries both the
                # native and the imported pending notice -- proof that both
                # are judged by the same unmodified query and consumer.
                status, payload = _post(
                    base_url_b, "/recovery/notifications/retry", {}, headers=_auth_headers()
                )
                self.assertEqual(status, 200)
                results_by_id = {r["request_id"]: r["outcome"] for r in payload["results"]}
                self.assertEqual(
                    results_by_id,
                    {native_request_id: "sent", imported_request_id: "sent"},
                )

                _stop_process(process_b)
                process_b = None

                # Name and exercise AccountService.retry_notifications
                # directly -- the very class/method the authenticated route
                # above calls -- against the same persisted database. With
                # both notices already sent, nothing is left pending, so
                # this is a harmless, idempotent confirmation rather than a
                # second delivery.
                with Storage(db_path) as storage:
                    account_service = AccountService(storage, mail_endpoint=mail_url)
                    noop_results = account_service.retry_notifications()
                self.assertEqual(noop_results, [])
            finally:
                if process_a is not None:
                    _stop_process(process_a)
                if process_b is not None:
                    _stop_process(process_b)
                stop_fake_mail_server(mail_server, mail_thread)

            sent_by_recipient = {}
            for entry in mail_state["received"]:
                sent_by_recipient.setdefault(entry["recipient"], []).append(entry["recovery_token"])

            with Storage(db_path) as storage:
                native_request = storage.get_recovery_request(native_request_id)
                imported_request = storage.get_recovery_request(imported_request_id)
                self.assertIn(native_request.token, sent_by_recipient["a@example.com"])
                self.assertIn(imported_request.token, sent_by_recipient["b@example.com"])

    def test_retry_uses_the_unchanged_current_email_for_an_imported_notice(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "state.db")
            _run_cli("create-account", "org-a", "acct-1", "a@example.com", "--database", db_path)

            mail_state = {}
            mail_server, mail_thread, mail_url = start_fake_mail_server(mail_state)
            process_a = None
            process_b = None
            request_id = None
            try:
                port_a = _free_port()
                process_a = _start_serve_process(db_path, mail_url, port_a)
                base_url_a = f"http://127.0.0.1:{port_a}"

                envelope = {
                    "version": 1,
                    "envelope_id": "env-legacy-retry-2",
                    "organization_id": "org-a",
                    "account_id": "acct-1",
                    "provider_receipt": "legacy-opaque-receipt-2",
                    "delivery_state": "pending",
                }
                status, payload = _post(
                    base_url_a, "/admin/legacy-envelopes/eligibility",
                    {"envelopes": [envelope]}, headers=_auth_headers(),
                )
                self.assertEqual(status, 200)
                row = payload["results"][0]
                self.assertTrue(row["eligible"])
                request_id = row["request_id"]

                _stop_process(process_a)
                process_a = None

                # The account's address is never changed anywhere in this test.
                port_b = _free_port()
                process_b = _start_serve_process(db_path, mail_url, port_b)
                base_url_b = f"http://127.0.0.1:{port_b}"

                status, payload = _post(
                    base_url_b, "/recovery/notifications/retry",
                    {"request_id": request_id}, headers=_auth_headers(),
                )
                self.assertEqual(status, 200)
                self.assertEqual(payload["results"], [{"request_id": request_id, "outcome": "sent"}])
            finally:
                if process_a is not None:
                    _stop_process(process_a)
                if process_b is not None:
                    _stop_process(process_b)
                stop_fake_mail_server(mail_server, mail_thread)

            self.assertEqual(mail_state["received"][-1]["recipient"], "a@example.com")

            with Storage(db_path) as storage:
                rows = storage._conn.execute(
                    "SELECT * FROM delivery_attempts WHERE recovery_request_id = ? ORDER BY attempt_number",
                    (request_id,),
                ).fetchall()
                self.assertEqual(len(rows), 2)
                first, second = rows
                self.assertEqual(first["recipient"], "a@example.com")
                self.assertEqual(second["recipient"], "a@example.com")

    def test_second_retry_after_successful_delivery_is_a_no_op(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "state.db")
            _run_cli("create-account", "org-a", "acct-1", "a@example.com", "--database", db_path)

            mail_state = {}
            mail_server, mail_thread, mail_url = start_fake_mail_server(mail_state)
            process_a = None
            process_b = None
            process_c = None
            request_id = None
            try:
                mail_state["status_code"] = 503
                mail_state["receipt"] = "dup-503-receipt"

                port_a = _free_port()
                process_a = _start_serve_process(db_path, mail_url, port_a)
                base_url_a = f"http://127.0.0.1:{port_a}"

                status, payload = _post(
                    base_url_a, "/recovery/start", {"organization": "org-a", "email": "a@example.com"}
                )
                self.assertEqual(status, 200)
                request_id = payload["request_id"]

                _stop_process(process_a)
                process_a = None

                mail_state["status_code"] = None
                mail_state["receipt"] = "dup-ok-receipt"

                port_b = _free_port()
                process_b = _start_serve_process(db_path, mail_url, port_b)
                base_url_b = f"http://127.0.0.1:{port_b}"

                status, payload = _post(
                    base_url_b, "/recovery/notifications/retry",
                    {"request_id": request_id}, headers=_auth_headers(),
                )
                self.assertEqual(status, 200)
                self.assertEqual(payload["results"], [{"request_id": request_id, "outcome": "sent"}])

                _stop_process(process_b)
                process_b = None

                # A third, independently-started process must see the same
                # already-sent state and treat a second retry as a no-op.
                port_c = _free_port()
                process_c = _start_serve_process(db_path, mail_url, port_c)
                base_url_c = f"http://127.0.0.1:{port_c}"

                status, payload = _post(
                    base_url_c, "/recovery/notifications/retry",
                    {"request_id": request_id}, headers=_auth_headers(),
                )
                self.assertEqual(status, 200)
                self.assertEqual(payload["results"], [])
            finally:
                if process_a is not None:
                    _stop_process(process_a)
                if process_b is not None:
                    _stop_process(process_b)
                if process_c is not None:
                    _stop_process(process_c)
                stop_fake_mail_server(mail_server, mail_thread)

            with Storage(db_path) as storage:
                rows = storage._conn.execute(
                    "SELECT * FROM delivery_attempts WHERE recovery_request_id = ? ORDER BY attempt_number",
                    (request_id,),
                ).fetchall()
                # Still exactly two attempts: the original failure and the
                # one successful retry -- the duplicate call wrote no third.
                self.assertEqual(len(rows), 2)
                self.assertEqual(rows[-1]["outcome"], "sent")

    def test_expired_request_is_excluded_from_retry_after_restart(self):
        ttl_seconds = 2
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "state.db")
            _run_cli("create-account", "org-a", "acct-1", "a@example.com", "--database", db_path)

            mail_state = {}
            mail_server, mail_thread, mail_url = start_fake_mail_server(mail_state)
            process_a = None
            process_b = None
            request_id = None
            try:
                mail_state["status_code"] = 503
                mail_state["receipt"] = "expiry-503-receipt"

                port_a = _free_port()
                process_a = _start_serve_process(db_path, mail_url, port_a, ttl_seconds=ttl_seconds)
                base_url_a = f"http://127.0.0.1:{port_a}"

                status, payload = _post(
                    base_url_a, "/recovery/start", {"organization": "org-a", "email": "a@example.com"}
                )
                self.assertEqual(status, 200)
                self.assertEqual(payload["delivery_status"], "failed_pending_retry")
                request_id = payload["request_id"]

                _stop_process(process_a)
                process_a = None

                # Wait past the persisted expiry before ever starting the
                # second process, so this is entirely a restart-time check.
                time.sleep(ttl_seconds + 1.5)

                mail_state["status_code"] = None
                mail_state["receipt"] = "expiry-ok-receipt"
                received_before_retry = len(mail_state["received"])

                port_b = _free_port()
                process_b = _start_serve_process(db_path, mail_url, port_b)
                base_url_b = f"http://127.0.0.1:{port_b}"

                status, payload = _post(
                    base_url_b, "/recovery/notifications/retry",
                    {"request_id": request_id}, headers=_auth_headers(),
                )
                self.assertEqual(status, 200)
                self.assertEqual(payload["results"], [])
                self.assertEqual(len(mail_state["received"]), received_before_retry)
            finally:
                if process_a is not None:
                    _stop_process(process_a)
                if process_b is not None:
                    _stop_process(process_b)
                stop_fake_mail_server(mail_server, mail_thread)

            with Storage(db_path) as storage:
                self.assertEqual(storage.list_pending_retry_attempts(), [])
                rows = storage._conn.execute(
                    "SELECT * FROM delivery_attempts WHERE recovery_request_id = ?", (request_id,),
                ).fetchall()
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["outcome"], "failed")

    def test_retry_route_requires_the_service_bearer_token_after_restart(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "state.db")
            _run_cli("create-account", "org-a", "acct-1", "a@example.com", "--database", db_path)

            mail_state = {}
            mail_server, mail_thread, mail_url = start_fake_mail_server(mail_state)
            process_a = None
            process_b = None
            request_id = None
            try:
                mail_state["status_code"] = 503
                mail_state["receipt"] = "auth-503-receipt"

                port_a = _free_port()
                process_a = _start_serve_process(db_path, mail_url, port_a)
                base_url_a = f"http://127.0.0.1:{port_a}"

                status, payload = _post(
                    base_url_a, "/recovery/start", {"organization": "org-a", "email": "a@example.com"}
                )
                self.assertEqual(status, 200)
                request_id = payload["request_id"]

                _stop_process(process_a)
                process_a = None

                mail_state["status_code"] = None
                mail_state["receipt"] = "auth-ok-receipt"

                port_b = _free_port()
                process_b = _start_serve_process(db_path, mail_url, port_b)
                base_url_b = f"http://127.0.0.1:{port_b}"

                received_before = len(mail_state["received"])

                status, payload = _post(base_url_b, "/recovery/notifications/retry", {})
                self.assertEqual(status, 401)

                status, payload = _post(
                    base_url_b, "/recovery/notifications/retry", {},
                    headers={"Authorization": "Bearer wrong-token"},
                )
                self.assertEqual(status, 401)

                # Neither unauthorized call reached far enough to attempt a send.
                self.assertEqual(len(mail_state["received"]), received_before)

                status, payload = _post(
                    base_url_b, "/recovery/notifications/retry",
                    {"request_id": request_id}, headers=_auth_headers(),
                )
                self.assertEqual(status, 200)
                self.assertEqual(payload["results"], [{"request_id": request_id, "outcome": "sent"}])
            finally:
                if process_a is not None:
                    _stop_process(process_a)
                if process_b is not None:
                    _stop_process(process_b)
                stop_fake_mail_server(mail_server, mail_thread)


if __name__ == "__main__":
    unittest.main()
