import json
import subprocess
import sys
import unittest

from .support import cleanup_db_path, make_temp_db_path


def _run_cli(*args):
    result = subprocess.run(
        [sys.executable, "-m", "accountsvc.cli", *args],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.returncode, result.stdout, result.stderr


class CliTests(unittest.TestCase):
    def setUp(self):
        self.db_path = make_temp_db_path()

    def tearDown(self):
        cleanup_db_path(self.db_path)

    def test_create_change_show_round_trip(self):
        code, out, _err = _run_cli(
            "create-account", "org-a", "acct-1", "a@example.com", "--database", self.db_path
        )
        self.assertEqual(code, 0, _err)
        created = json.loads(out)
        self.assertEqual(created["current_email"], "a@example.com")

        code, out, _err = _run_cli("change-email", "acct-1", "a2@example.com", "--database", self.db_path)
        self.assertEqual(code, 0, _err)
        changed = json.loads(out)
        self.assertEqual(changed["current_email"], "a2@example.com")
        self.assertEqual(changed["mailbox_revision"], 2)

        code, out, _err = _run_cli("show-account", "acct-1", "--database", self.db_path)
        self.assertEqual(code, 0, _err)
        shown = json.loads(out)
        self.assertEqual(shown["current_email"], "a2@example.com")
        self.assertEqual(len(shown["email_history"]), 2)

    def test_show_missing_account_is_a_clean_failure(self):
        code, _out, err = _run_cli("show-account", "does-not-exist", "--database", self.db_path)
        self.assertNotEqual(code, 0)
        self.assertIn("does not exist", err)

    def test_duplicate_current_mailbox_is_rejected(self):
        _run_cli("create-account", "org-a", "acct-1", "shared@example.com", "--database", self.db_path)
        code, _out, err = _run_cli(
            "create-account", "org-a", "acct-2", "shared@example.com", "--database", self.db_path
        )
        self.assertNotEqual(code, 0)
        self.assertIn("already owned", err)


if __name__ == "__main__":
    unittest.main()
