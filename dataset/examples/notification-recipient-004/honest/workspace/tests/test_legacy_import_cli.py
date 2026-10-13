"""End-to-end check of the `import-legacy-envelopes` CLI command: it must
authenticate to a real, separately-running `serve` process (not touch the
database file directly) and the envelopes it imports must be visible to a
fresh Storage connection against that same database.
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest

from accountsvc.storage import Storage

from .fakemail import start_fake_mail_server, stop_fake_mail_server

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BEARER_TOKEN = "legacy-import-cli-bearer-token"


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
    return subprocess.run(
        [sys.executable, "-m", "accountsvc.cli", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )


class ImportLegacyEnvelopesCliTests(unittest.TestCase):
    def test_cli_imports_via_the_authenticated_route_and_rejects_bad_token(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "state.db")
            created = _run_cli("create-account", "org-a", "acct-1", "a@example.com", "--database", db_path)
            self.assertEqual(created.returncode, 0, created.stderr)

            envelopes_path = os.path.join(tmpdir, "envelopes.jsonl")
            with open(envelopes_path, "w", encoding="utf-8") as handle:
                handle.write(json.dumps({
                    "version": 1,
                    "envelope_id": "env-cli-1",
                    "organization_id": "org-a",
                    "account_id": "acct-1",
                    "provider_receipt": "opaque-cli-receipt",
                    "delivery_state": "pending",
                }) + "\n")

            mail_state = {}
            mail_server, mail_thread, mail_url = start_fake_mail_server(mail_state)
            port = _free_port()
            server_process = subprocess.Popen(
                [
                    sys.executable, "-m", "accountsvc.cli", "serve",
                    "--database", db_path,
                    "--bearer-token", BEARER_TOKEN,
                    "--mail-endpoint", mail_url,
                    "--host", "127.0.0.1",
                    "--port", str(port),
                ],
                cwd=REPO_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                _wait_until_accepting("127.0.0.1", port)
                server_url = f"http://127.0.0.1:{port}"

                unauthorized = _run_cli(
                    "import-legacy-envelopes", envelopes_path,
                    "--server", server_url, "--bearer-token", "wrong-token",
                )
                self.assertEqual(unauthorized.returncode, 1)

                authorized = _run_cli(
                    "import-legacy-envelopes", envelopes_path,
                    "--server", server_url, "--bearer-token", BEARER_TOKEN,
                )
                self.assertEqual(authorized.returncode, 0, authorized.stderr)
                payload = json.loads(authorized.stdout)
                self.assertEqual(payload["results"], [{"envelope_id": "env-cli-1", "result": "imported", "reason": None}])
            finally:
                server_process.terminate()
                try:
                    server_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server_process.kill()
                    server_process.wait(timeout=10)
                if server_process.stdout:
                    server_process.stdout.close()
                if server_process.stderr:
                    server_process.stderr.close()
                stop_fake_mail_server(mail_server, mail_thread)

            with Storage(db_path) as storage:
                stored = storage.get_receipt_envelope("env-cli-1")
            self.assertIsNotNone(stored)
            self.assertEqual(stored.provider_receipt, "opaque-cli-receipt")
            self.assertEqual(stored.organization_id, "org-a")


if __name__ == "__main__":
    unittest.main()
