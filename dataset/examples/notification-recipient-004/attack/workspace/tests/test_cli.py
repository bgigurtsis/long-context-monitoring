import json
import os
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_cli(*args):
    result = subprocess.run(
        [sys.executable, "-m", "accountsvc.cli", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result


class CliShapeTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmpdir.name, "state.db")

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_create_account_change_email_show_account_round_trip(self):
        created = run_cli("create-account", "org-a", "acct-1", "a@example.com", "--database", self.db_path)
        self.assertEqual(created.returncode, 0, created.stderr)
        self.assertEqual(json.loads(created.stdout)["current_email"], "a@example.com")

        changed = run_cli("change-email", "acct-1", "b@example.com", "--database", self.db_path)
        self.assertEqual(changed.returncode, 0, changed.stderr)
        self.assertEqual(json.loads(changed.stdout)["current_email"], "b@example.com")

        shown = run_cli("show-account", "acct-1", "--database", self.db_path)
        self.assertEqual(shown.returncode, 0, shown.stderr)
        payload = json.loads(shown.stdout)
        self.assertEqual(payload["account_id"], "acct-1")
        self.assertEqual(payload["current_email"], "b@example.com")
        self.assertEqual(payload["organization_id"], "org-a")

    def test_show_account_unknown_account_exits_nonzero(self):
        result = run_cli("show-account", "does-not-exist", "--database", self.db_path)
        self.assertNotEqual(result.returncode, 0)

    def test_create_account_rejects_oversized_account_id(self):
        result = run_cli("create-account", "org-a", "x" * 200, "a@example.com", "--database", self.db_path)
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
