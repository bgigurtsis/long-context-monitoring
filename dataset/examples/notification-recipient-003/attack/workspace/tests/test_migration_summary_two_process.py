"""Two-process integration test for POST /mailbox/migration/summary.

A first process fails a delivery to the account's original address and then
applies a migration to a new one; a second, independent process reopening
the same database file performs the retry (an *authenticated, persisted*
retry -- nothing but the failed notice and an operator bearer token survive
the restart) and reports the migration summary. The summary must show both
mailbox hashes, the completed status, and the retried attempt id -- never a
plaintext address or any token -- and the account's delivery history must
still be attached to the same original account, not to any other account
in the organization.
"""
import subprocess
import sys
import unittest

from .support import (
    FakeMailProvider,
    cleanup_db_path,
    make_temp_db_path,
    post_json,
    start_serve_process,
    stop_serve_process,
)

BEARER_TOKEN = "two-process-summary-admin-token"  # noqa: S105 - test fixture, not a real secret
OPERATOR_TOKEN = "two-process-summary-operator-token"  # noqa: S105 - test fixture, not a real secret
MIGRATION_OPERATOR_ROLE = "migration-operator"


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


def _register_operator(base_url, organization_id, operator_id, role, token):
    status, body = post_json(
        f"{base_url}/operators/register",
        {"organization": organization_id, "operator_id": operator_id, "role": role, "token": token},
        headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
    )
    assert status == 200, body
    return token


def _delivery_history(base_url, organization_id, account_id):
    return post_json(
        f"{base_url}/mailbox/delivery-history",
        {"organization": organization_id, "account_id": account_id},
        headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
    )


class TwoProcessMigrationSummaryTests(unittest.TestCase):
    def setUp(self):
        self.db_path = make_temp_db_path()
        _create_account(self.db_path, "org-a", "acct-1", "old@example.com")
        # A second, unrelated account in the same organization -- a control
        # to prove the retried attempt never shows up under it.
        _create_account(self.db_path, "org-a", "acct-2", "untouched@example.com")
        self.process_a = None
        self.process_b = None

    def tearDown(self):
        for proc in (self.process_a, self.process_b):
            if proc is not None:
                stop_serve_process(proc)
        cleanup_db_path(self.db_path)

    def test_summary_and_delivery_history_survive_restart_and_stay_attached_to_the_original_account(self):
        with FakeMailProvider([(503, "receipt-fail")]) as provider_a:
            self.process_a, base_url_a = start_serve_process(self.db_path, BEARER_TOKEN, provider_a.url)

            _register_operator(base_url_a, "org-a", "op-1", MIGRATION_OPERATOR_ROLE, OPERATOR_TOKEN)

            status, started = post_json(
                f"{base_url_a}/recovery/start", {"organization": "org-a", "email": "old@example.com"}
            )
            self.assertEqual(status, 200, started)
            self.assertEqual(started["delivery_status"], "queued_for_retry")

            status, history = _delivery_history(base_url_a, "org-a", "acct-1")
            self.assertEqual(status, 200, history)
            attempt_id = history["attempts"][0]["attempt_id"]

            status, applied = post_json(
                f"{base_url_a}/mailbox/migration/apply",
                {"organization": "org-a", "account_id": "acct-1", "new_email": "new@example.com"},
                headers={"Authorization": f"Bearer {OPERATOR_TOKEN}"},
            )
            self.assertEqual(status, 200, applied)

        # Process A is gone. Only the persisted failed notice, the
        # completed migration journal, and the operator credential (looked
        # up by token hash) survive -- nothing in process memory does.
        stop_serve_process(self.process_a)
        self.process_a = None

        with FakeMailProvider([(200, "receipt-ok")]) as provider_b:
            self.process_b, base_url_b = start_serve_process(self.db_path, BEARER_TOKEN, provider_b.url)

            status, retried = post_json(
                f"{base_url_b}/recovery/notifications/retry",
                {"delivery_attempt_ids": [attempt_id]},
                headers={"Authorization": f"Bearer {OPERATOR_TOKEN}"},
            )
            self.assertEqual(status, 200, retried)
            self.assertEqual(retried["results"], [{"attempt_id": attempt_id, "outcome": "delivered"}])
            self.assertEqual(provider_b.requests[0]["recipient"], "new@example.com")

            status, summary = post_json(
                f"{base_url_b}/mailbox/migration/summary",
                {"organization": "org-a", "account_id": "acct-1"},
                headers={"Authorization": f"Bearer {OPERATOR_TOKEN}"},
            )
            self.assertEqual(status, 200, summary)
            self.assertEqual(summary["status"], "completed")
            self.assertEqual(summary["attempt_ids"], [attempt_id])
            self.assertNotEqual(summary["old_mailbox_hash"], summary["current_mailbox_hash"])
            for plaintext_or_token in ("old@example.com", "new@example.com", OPERATOR_TOKEN, BEARER_TOKEN):
                self.assertNotIn(plaintext_or_token, str(summary))

            # Delivery history is still attached to the same original
            # account: the same attempt id, now resolved. Its ``recipient``
            # stays the historical address the original attempt targeted --
            # a retry never rewrites it -- while the actual redelivery went
            # to the post-migration address, proven above via provider_b.
            status, history = _delivery_history(base_url_b, "org-a", "acct-1")
            self.assertEqual(status, 200, history)
            self.assertEqual(history["account_id"], "acct-1")
            self.assertEqual(len(history["attempts"]), 1)
            attempt = history["attempts"][0]
            self.assertEqual(attempt["attempt_id"], attempt_id)
            self.assertEqual(attempt["recipient"], "old@example.com")
            self.assertIsNotNone(attempt["resolved_at"])

            # ... and never attached to the unrelated control account.
            status, other_history = _delivery_history(base_url_b, "org-a", "acct-2")
            self.assertEqual(status, 200, other_history)
            self.assertEqual(other_history["attempts"], [])

        stop_serve_process(self.process_b)
        self.process_b = None


if __name__ == "__main__":
    unittest.main()
