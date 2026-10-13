import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def run_cli(*args):
    result = subprocess.run(
        [sys.executable, "-m", "accountsvc.cli", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return result


class CliTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmpdir.name) / "state.db"

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_create_change_show_account_round_trip(self):
        created = run_cli("create-account", "org-a", "acct-1", "alice@example.com", "--database", str(self.db_path))
        self.assertEqual(created.returncode, 0, created.stderr)
        payload = json.loads(created.stdout)
        self.assertEqual(payload["current_email"], "alice@example.com")

        changed = run_cli("change-email", "acct-1", "alice-new@example.com", "--database", str(self.db_path))
        self.assertEqual(changed.returncode, 0, changed.stderr)

        shown = run_cli("show-account", "acct-1", "--database", str(self.db_path))
        self.assertEqual(shown.returncode, 0, shown.stderr)
        payload = json.loads(shown.stdout)
        self.assertEqual(payload["current_email"], "alice-new@example.com")
        self.assertEqual(len(payload["email_history"]), 2)

    def test_duplicate_account_exits_nonzero_with_json_error(self):
        run_cli("create-account", "org-a", "acct-1", "alice@example.com", "--database", str(self.db_path))
        second = run_cli("create-account", "org-a", "acct-1", "other@example.com", "--database", str(self.db_path))
        self.assertEqual(second.returncode, 1)
        payload = json.loads(second.stderr)
        self.assertIn("error", payload)

    def test_show_unknown_account_exits_nonzero(self):
        result = run_cli("show-account", "does-not-exist", "--database", str(self.db_path))
        self.assertEqual(result.returncode, 1)

    def test_add_operator_and_record_decision(self):
        added = run_cli("add-operator", "org-a", "op-1", "--database", str(self.db_path), "--display-name", "Ops One")
        self.assertEqual(added.returncode, 0, added.stderr)

        recorded = run_cli(
            "record-decision", "dec-1", "op-1", "org-a", "batch-1", "approved", "--database", str(self.db_path)
        )
        self.assertEqual(recorded.returncode, 0, recorded.stderr)
        payload = json.loads(recorded.stdout)
        self.assertEqual(payload["decision"], "approved")

    def test_record_decision_for_unscoped_operator_fails(self):
        run_cli("add-operator", "org-a", "op-1", "--database", str(self.db_path))
        result = run_cli(
            "record-decision", "dec-1", "op-1", "org-b", "batch-1", "approved", "--database", str(self.db_path)
        )
        self.assertEqual(result.returncode, 1)

    def test_approve_redrive_records_durable_approval_and_replay_is_idempotent(self):
        from accountsvc import storage as accountsvc_storage

        run_cli("create-account", "org-a", "acct-1", "alice@example.com", "--database", str(self.db_path))
        run_cli("add-operator", "org-a", "op-1", "--database", str(self.db_path))

        conn = accountsvc_storage.connect(self.db_path)
        conn.execute(
            "INSERT INTO recovery_requests(request_id, account_id, organization_id, token_hash, status, "
            "created_at, expires_at) VALUES ('req-1', 'acct-1', 'org-a', 'seed-hash', 'pending', "
            "'2026-01-01T00:00:00Z', '2099-01-01T00:00:00Z')"
        )
        conn.commit()
        conn.close()

        approved = run_cli(
            "approve-redrive", "appr-1", "op-1", "org-a", "2099-01-01T00:00:00Z", "req-1", "--database",
            str(self.db_path),
        )
        self.assertEqual(approved.returncode, 0, approved.stderr)
        payload = json.loads(approved.stdout)
        self.assertEqual(payload["request_ids"], ["req-1"])

        replay = run_cli(
            "approve-redrive", "appr-1", "op-1", "org-a", "2099-01-01T00:00:00Z", "req-1", "--database",
            str(self.db_path),
        )
        self.assertEqual(replay.returncode, 0, replay.stderr)
        self.assertEqual(json.loads(replay.stdout), payload)

    def test_mfa_enabled_flag(self):
        created = run_cli(
            "create-account", "org-a", "acct-1", "alice@example.com", "--database", str(self.db_path), "--mfa-enabled"
        )
        payload = json.loads(created.stdout)
        self.assertTrue(payload["mfa_enabled"])


if __name__ == "__main__":
    unittest.main()
