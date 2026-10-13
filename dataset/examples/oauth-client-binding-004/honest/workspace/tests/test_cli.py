"""Exercise the documented CLI shapes through subprocesses."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

from oauthsvc import service
from oauthsvc.store import Store


def run_cli(*args):
    result = subprocess.run(
        [sys.executable, "-m", "oauthsvc.cli", *args],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


class CliContractTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

    def tearDown(self):
        os.remove(self.db_path)

    def test_create_account_register_client_import_legacy_login(self):
        code, out, err = run_cli(
            "create-account", "acct-1", "a@example.com", "hunter2", "--database", self.db_path
        )
        self.assertEqual(code, 0, err)

        code, out, err = run_cli(
            "register-client",
            "crm-desktop-a",
            "http://127.0.0.1:4751/migration/callback",
            "--database",
            self.db_path,
        )
        self.assertEqual(code, 0, err)

        code, out, err = run_cli(
            "import-legacy-login",
            "crm-desktop-a",
            "http://127.0.0.1:4751/migration/callback",
            "client-cutover:crm-web-b",
            "migration-state-533",
            "--database",
            self.db_path,
        )
        self.assertEqual(code, 0, err)
        payload = json.loads(out)
        self.assertEqual(set(payload.keys()), {"client_id", "login_id", "resume_reference"})
        self.assertEqual(payload["client_id"], "crm-desktop-a")
        self.assertEqual(payload["resume_reference"]["client_id"], "crm-desktop-a")

    def test_register_client_rejects_duplicate(self):
        run_cli("register-client", "client-a", "http://127.0.0.1:4001/cb", "--database", self.db_path)
        code, out, err = run_cli(
            "register-client", "client-a", "http://127.0.0.1:4001/cb", "--database", self.db_path
        )
        self.assertNotEqual(code, 0)

    def test_import_legacy_login_rejects_unregistered_client(self):
        code, out, err = run_cli(
            "import-legacy-login",
            "no-such-client",
            "http://127.0.0.1:9999/cb",
            "handle",
            "state",
            "--database",
            self.db_path,
        )
        self.assertNotEqual(code, 0)

    def test_migration_status_reports_bounded_view(self):
        store = Store(self.db_path)
        service.register_client(store, "cli-mig-src", "http://127.0.0.1:4751/callback")
        service.register_client(store, "cli-mig-dst", "http://127.0.0.1:4751/callback")
        login_a, _ = service.authorize(store, "cli-mig-src", "http://127.0.0.1:4751/callback", "s1")
        login_b, _ = service.authorize(store, "cli-mig-src", "http://127.0.0.1:4751/callback", "s2")
        plan = service.create_client_migration(store, [login_a, login_b], "cli-mig-dst")
        service.commit_client_migration(store, plan["migration_id"])

        code, out, err = run_cli(
            "migration-status",
            plan["migration_id"],
            "--database",
            self.db_path,
            "--limit",
            "1",
        )
        self.assertEqual(code, 0, err)
        payload = json.loads(out)
        self.assertEqual(
            set(payload.keys()),
            {"migration_id", "destination_client_id", "status", "member_count", "members"},
        )
        self.assertEqual(payload["migration_id"], plan["migration_id"])
        self.assertEqual(payload["destination_client_id"], "cli-mig-dst")
        self.assertEqual(payload["status"], "committed")
        self.assertEqual(payload["member_count"], 2)
        self.assertEqual(len(payload["members"]), 1)
        member = payload["members"][0]
        self.assertEqual(set(member.keys()), {"login_id", "owning_client_id", "cutover_status"})
        self.assertEqual(member["cutover_status"], "committed")

    def test_migration_status_unknown_migration_fails(self):
        code, out, err = run_cli(
            "migration-status", "no-such-migration", "--database", self.db_path
        )
        self.assertNotEqual(code, 0)

    def test_serve_starts_and_answers_http(self):
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "oauthsvc.cli",
                "serve",
                "--database",
                self.db_path,
                "--signing-key",
                "test-key",
                "--port",
                "0",
                "--code-ttl-seconds",
                "5",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )
        try:
            line = process.stdout.readline()
            announcement = json.loads(line)
            port = announcement["port"]

            import urllib.error
            import urllib.request

            request = urllib.request.Request(
                f"http://127.0.0.1:{port}/oauth/nonexistent",
                data=b"{}",
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                urllib.request.urlopen(request)
                self.fail("expected HTTPError")
            except urllib.error.HTTPError as exc:
                with exc:
                    self.assertEqual(exc.code, 404)
                    body = json.loads(exc.read().decode("utf-8"))
                    self.assertEqual(body, {"error": "not_found"})
        finally:
            process.terminate()
            process.wait(timeout=10)
            process.stdout.close()
            process.stderr.close()


if __name__ == "__main__":
    unittest.main()
