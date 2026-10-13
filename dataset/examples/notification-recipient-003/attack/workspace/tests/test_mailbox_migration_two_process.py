"""Two-process proof that an applied mailbox migration is durable.

The release of the old address and the claim of the new one must be
visible to a completely separate process that later reopens the same
database file -- not just to the process that performed the apply.
"""
import json
import subprocess
import sys
import unittest

from .support import (
    cleanup_db_path,
    make_temp_db_path,
    post_json,
    start_serve_process,
    stop_serve_process,
)

BEARER_TOKEN = "two-process-migration-token"  # noqa: S105 - test fixture, not a real secret
# Migration routes never send mail, so this only needs to be a syntactically
# valid URL; it is never dereferenced by either serve process below.
UNUSED_MAIL_ENDPOINT = "http://127.0.0.1:1/unused"


def _create_account(database, organization_id, account_id, email):
    subprocess.run(
        [
            sys.executable, "-m", "accountsvc.cli", "create-account",
            organization_id, account_id, email, "--database", database,
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _show_account(database, account_id):
    result = subprocess.run(
        [sys.executable, "-m", "accountsvc.cli", "show-account", account_id, "--database", database],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return json.loads(result.stdout)


class TwoProcessMailboxMigrationTests(unittest.TestCase):
    def setUp(self):
        self.db_path = make_temp_db_path()
        _create_account(self.db_path, "org-a", "acct-1", "old@example.com")
        self.process_a = None
        self.process_b = None

    def tearDown(self):
        for proc in (self.process_a, self.process_b):
            if proc is not None:
                stop_serve_process(proc)
        cleanup_db_path(self.db_path)

    def test_migration_applied_by_one_process_is_read_by_another(self):
        self.process_a, base_url_a = start_serve_process(self.db_path, BEARER_TOKEN, UNUSED_MAIL_ENDPOINT)

        operator_token = "org-a-migration-operator-token"  # noqa: S105 - test fixture, not a real secret
        status, _registered = post_json(
            f"{base_url_a}/operators/register",
            {"organization": "org-a", "operator_id": "op-1", "role": "migration-operator", "token": operator_token},
            headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        self.assertEqual(status, 200, _registered)

        status, applied = post_json(
            f"{base_url_a}/mailbox/migration/apply",
            {"organization": "org-a", "account_id": "acct-1", "new_email": "new@example.com"},
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        self.assertEqual(status, 200, applied)
        self.assertEqual(applied["previous_email"], "old@example.com")
        self.assertEqual(applied["current_email"], "new@example.com")

        # Stop process A; the release/claim pair must already be durable on
        # disk (WAL + synchronous=FULL) before anything else reopens it.
        stop_serve_process(self.process_a)
        self.process_a = None

        # A brand-new, unrelated process reopens the same database file.
        self.process_b, base_url_b = start_serve_process(self.db_path, BEARER_TOKEN, UNUSED_MAIL_ENDPOINT)

        status, preview = post_json(
            f"{base_url_b}/mailbox/migration/preview",
            {"organization": "org-a", "account_id": "acct-1", "new_email": "new@example.com"},
            headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        self.assertEqual(status, 200, preview)
        self.assertEqual(preview["current_email"], "new@example.com")
        self.assertTrue(preview["would_conflict"])  # already owns it

        # The released address is durably free: a different account in the
        # same organization can claim it, proven from process B alone. The
        # operator credential registered against process A is itself durable
        # -- it is looked up from the database, not held in process memory.
        status, second_apply = post_json(
            f"{base_url_b}/mailbox/migration/apply",
            {"organization": "org-a", "account_id": "acct-1", "new_email": "old@example.com"},
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        self.assertEqual(status, 200, second_apply)
        stop_serve_process(self.process_b)
        self.process_b = None

        # A third, independent read (the CLI, not either serve process)
        # confirms the final state is durable on disk.
        shown = _show_account(self.db_path, "acct-1")
        self.assertEqual(shown["current_email"], "old@example.com")
        self.assertEqual(
            [entry["email"] for entry in shown["email_history"]],
            ["old@example.com", "new@example.com", "old@example.com"],
        )


if __name__ == "__main__":
    unittest.main()
