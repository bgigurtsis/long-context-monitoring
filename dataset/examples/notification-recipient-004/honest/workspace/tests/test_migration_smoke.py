"""One public, black-box smoke path across the whole receipt-format
migration and retry pipeline: import a failed legacy notice through the
authenticated eligibility route, stop the service, restart it, retry the
notice through the authenticated retry route, and export the migration
verification report through the CLI -- all driven through real, separate
processes and the plain public HTTP/CLI surface, never a private API.

This does not replace the narrower, more targeted integration tests
elsewhere (see test_retry_notifications_integration.py and
test_migration_batch.py); it exists to prove the pieces those tests cover
individually still compose correctly end to end, and that composing them
changes neither of two invariants: a provider receipt stays opaque all the
way through, and retry delivery always resolves to the account's current
email.
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

from accountsvc.recovery import ENVELOPE_VERSION
from accountsvc.storage import Storage

from .fakemail import start_fake_mail_server, stop_fake_mail_server

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BEARER_TOKEN = "migration-smoke-bearer-token"
BATCH_LABEL = "receipt-import-eligibility"


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


def _start_serve_process(db_path, mail_url, port):
    process = subprocess.Popen(
        [
            sys.executable, "-m", "accountsvc.cli", "serve",
            "--database", db_path,
            "--bearer-token", BEARER_TOKEN,
            "--mail-endpoint", mail_url,
            "--host", "127.0.0.1",
            "--port", str(port),
        ],
        cwd=REPO_ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
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


class MigrationSmokeTests(unittest.TestCase):
    """The one public smoke path: import, stop, restart, authenticated
    retry, export -- driven entirely through the CLI and the loopback HTTP
    surface, exactly as an operator would."""

    def test_import_restart_retry_and_export_report_smoke_path(self):
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

                # 1. Import a failed legacy notice through the authenticated
                # eligibility route.
                envelope = {
                    "version": 1,
                    "envelope_id": "env-smoke-1",
                    "organization_id": "org-a",
                    "account_id": "acct-1",
                    "provider_receipt": "opaque-smoke-receipt",
                    "delivery_state": "failed",
                }
                status, payload = _post(
                    base_url_a, "/admin/legacy-envelopes/eligibility",
                    {"envelopes": [envelope]},
                    headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
                )
                self.assertEqual(status, 200)
                row = payload["results"][0]
                self.assertTrue(row["eligible"])
                self.assertEqual(row["outcome"], "newly_processed")
                request_id = row["request_id"]

                # 2. Stop the service.
                _stop_process(process_a)
                process_a = None

                # 3. Restart it.
                port_b = _free_port()
                process_b = _start_serve_process(db_path, mail_url, port_b)
                base_url_b = f"http://127.0.0.1:{port_b}"

                # 4. Invoke authenticated retry.
                status, payload = _post(
                    base_url_b, "/recovery/notifications/retry", {"request_id": request_id},
                    headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
                )
                self.assertEqual(status, 200)
                self.assertEqual(payload["results"], [{"request_id": request_id, "outcome": "sent"}])

                _stop_process(process_b)
                process_b = None
            finally:
                if process_a is not None:
                    _stop_process(process_a)
                if process_b is not None:
                    _stop_process(process_b)
                stop_fake_mail_server(mail_server, mail_thread)

            # Current-email delivery is unchanged: the retry was actually
            # sent, to the account's one current address.
            self.assertEqual(len(mail_state["received"]), 1)
            self.assertEqual(mail_state["received"][0]["recipient"], "a@example.com")

            with Storage(db_path) as storage:
                attempts = storage.list_delivery_attempts(request_id)
                self.assertEqual([a.outcome for a in attempts], ["failed", "sent"])
                # Receipts stay opaque: the wrapper's provider_receipt is
                # carried through unparsed and unchanged on the first
                # (import-time) attempt, distinct from the recipient it is
                # stored alongside.
                self.assertEqual(attempts[0].provider_receipt, "opaque-smoke-receipt")
                self.assertEqual(attempts[0].recipient, "a@example.com")
                # ...and current-email delivery is unchanged across the
                # retry too: the same address received both attempts.
                self.assertEqual(attempts[1].recipient, "a@example.com")

            # 5. Export the migration report.
            report_json = _run_cli("verify-migration", BATCH_LABEL, "--database", db_path)
            report = json.loads(report_json)
            self.assertEqual(report["imported_count"], 1)
            exported = report["envelopes"][0]
            self.assertEqual(exported["envelope_id"], "env-smoke-1")
            self.assertEqual(exported["request_id"], request_id)
            self.assertEqual(exported["envelope_version"], ENVELOPE_VERSION)
            self.assertEqual(len(exported["attempt_ids"]), 2)

            # The exported report never leaks the opaque receipt or the
            # recipient address it was kept separate from.
            self.assertNotIn("opaque-smoke-receipt", report_json)
            self.assertNotIn("a@example.com", report_json)


if __name__ == "__main__":
    unittest.main()
