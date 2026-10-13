"""Tests for the oauthsvc CLI subcommands (excluding `serve`)."""

from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest

from oauthsvc import cli
from oauthsvc.db import Database
from oauthsvc.security import verify_password


class CliTestCase(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.addCleanup(lambda: os.remove(self.db_path))

    def run_cli(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(list(argv))
        return code, out.getvalue(), err.getvalue()


class TestCreateAccount(CliTestCase):
    def test_success_persists_hashed_password(self):
        code, _, _ = self.run_cli(
            "create-account", "alice", "alice@example.com", "hunter2", "--database", self.db_path
        )
        self.assertEqual(code, 0)
        db = Database(self.db_path)
        self.addCleanup(db.close)
        account = db.get_account("alice")
        self.assertIsNotNone(account)
        self.assertEqual(account["email"], "alice@example.com")
        self.assertTrue(verify_password("hunter2", account["salt"], account["password_hash"]))

    def test_duplicate_account_fails(self):
        self.run_cli("create-account", "alice", "a@x.com", "pw", "--database", self.db_path)
        code, _, err = self.run_cli("create-account", "alice", "a@x.com", "pw2", "--database", self.db_path)
        self.assertEqual(code, 1)
        self.assertIn("alice", err)


class TestRegisterClient(CliTestCase):
    def test_success(self):
        code, _, _ = self.run_cli(
            "register-client", "client-1", "https://client.example/cb", "--database", self.db_path
        )
        self.assertEqual(code, 0)
        db = Database(self.db_path)
        self.addCleanup(db.close)
        client = db.get_client("client-1")
        self.assertEqual(client["redirect_uri"], "https://client.example/cb")

    def test_duplicate_client_fails(self):
        self.run_cli("register-client", "client-1", "https://a", "--database", self.db_path)
        code, _, err = self.run_cli("register-client", "client-1", "https://b", "--database", self.db_path)
        self.assertEqual(code, 1)
        self.assertIn("client-1", err)


class TestImportLegacyLogin(CliTestCase):
    def setUp(self):
        super().setUp()
        self.run_cli(
            "register-client", "client-1", "https://client.example/cb", "--database", self.db_path
        )

    def test_unregistered_callback_fails(self):
        code, _, err = self.run_cli(
            "import-legacy-login",
            "client-1",
            "https://wrong.example/cb",
            "legacy-handle",
            "state",
            "--database",
            self.db_path,
        )
        self.assertEqual(code, 1)
        self.assertIn("unregistered_callback", err)

    def test_success_produces_native_resume_reference(self):
        code, out, _ = self.run_cli(
            "import-legacy-login",
            "client-1",
            "https://client.example/cb",
            "legacy-handle",
            "caller-state",
            "--database",
            self.db_path,
        )
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertEqual(result["client_id"], "client-1")
        self.assertEqual(
            result["resume_reference"],
            {"kind": "continuation", "client_id": "client-1", "value": result["login_id"]},
        )

        db = Database(self.db_path)
        self.addCleanup(db.close)
        pending = db.get_pending_login(result["login_id"])
        self.assertEqual(pending["kind"], "continuation")
        self.assertEqual(pending["state"], "caller-state")

    def test_duplicate_handle_for_same_client_fails(self):
        self.run_cli(
            "import-legacy-login",
            "client-1",
            "https://client.example/cb",
            "dup-handle",
            "s1",
            "--database",
            self.db_path,
        )
        code, _, err = self.run_cli(
            "import-legacy-login",
            "client-1",
            "https://client.example/cb",
            "dup-handle",
            "s2",
            "--database",
            self.db_path,
        )
        self.assertEqual(code, 1)
        self.assertIn("dup-handle", err)

    def test_same_handle_text_allowed_across_different_clients(self):
        self.run_cli(
            "register-client", "client-2", "https://other.example/cb", "--database", self.db_path
        )
        code1, out1, _ = self.run_cli(
            "import-legacy-login",
            "client-1",
            "https://client.example/cb",
            "shared-handle",
            "s1",
            "--database",
            self.db_path,
        )
        code2, out2, _ = self.run_cli(
            "import-legacy-login",
            "client-2",
            "https://other.example/cb",
            "shared-handle",
            "s2",
            "--database",
            self.db_path,
        )
        self.assertEqual((code1, code2), (0, 0))
        self.assertNotEqual(json.loads(out1)["login_id"], json.loads(out2)["login_id"])


if __name__ == "__main__":
    unittest.main()
