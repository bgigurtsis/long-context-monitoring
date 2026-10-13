"""Proves durability and stable JSON output across separate OS processes:
one process creates an account and exits, a second process reads it back.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_cli(*args):
    result = subprocess.run(
        [sys.executable, "-m", "accountsvc.cli", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result


class CrossProcessTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "state.db")

    def test_show_account_in_separate_process_after_create(self):
        create = run_cli(
            "create-account", "acme", "alice", "alice@example.com", "--database", self.db_path
        )
        self.assertEqual(create.returncode, 0, create.stderr)

        show = run_cli("show-account", "alice", "--database", self.db_path)
        self.assertEqual(show.returncode, 0, show.stderr)
        payload = json.loads(show.stdout)
        self.assertEqual(payload["account_id"], "alice")
        self.assertEqual(payload["email"], "alice@example.com")

    def test_show_account_output_is_stable_across_processes(self):
        run_cli("create-account", "acme", "bob", "bob@example.com", "--database", self.db_path)

        first = run_cli("show-account", "bob", "--database", self.db_path)
        second = run_cli("show-account", "bob", "--database", self.db_path)
        self.assertEqual(first.returncode, 0)
        self.assertEqual(second.returncode, 0)
        # Byte-identical stdout: sorted JSON keys, no incidental ordering drift.
        self.assertEqual(first.stdout, second.stdout)

    def test_change_email_in_one_process_visible_in_another(self):
        run_cli("create-account", "acme", "carol", "carol@example.com", "--database", self.db_path)
        change = run_cli(
            "change-email", "carol", "carol-new@example.com", "--database", self.db_path
        )
        self.assertEqual(change.returncode, 0, change.stderr)

        show = run_cli("show-account", "carol", "--database", self.db_path)
        payload = json.loads(show.stdout)
        self.assertEqual(payload["email"], "carol-new@example.com")
        history_emails = [e["email"] for e in payload["email_history"]]
        self.assertEqual(history_emails, ["carol@example.com", "carol-new@example.com"])

    def test_show_unknown_account_fails_cleanly(self):
        result = run_cli("show-account", "nobody", "--database", self.db_path)
        self.assertNotEqual(result.returncode, 0)
        payload = json.loads(result.stderr)
        self.assertIn("error", payload)


if __name__ == "__main__":
    unittest.main()
