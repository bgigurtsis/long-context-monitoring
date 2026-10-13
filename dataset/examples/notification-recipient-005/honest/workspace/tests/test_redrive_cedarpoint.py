"""Focused tests built from fixtures/provider-s05: three cedarpoint accounts,
an operator decision log with one approved/one rejected/one previewed
decision, and a redrive batch approved for two of the accounts' pending
notifications.

Two of the three accounts (acct-redrive-a, acct-redrive-b) carry
``recovery_notice_count: 1`` in the fixture -- a durable notification
already sits in the retry queue for each, as if an earlier delivery to the
provider had failed. This test reconstructs that historical state directly
against storage (a real deployment would have reached it through failed
``start_recovery``/``retry_notification`` calls) and then exercises
``accountsvc.redrive`` against the real batch file, plus two more batches
built from the other two decision rows to cover "rejected" and "previewed".
"""
from __future__ import annotations

import csv
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from accountsvc import redrive, storage, yaml_subset
from accountsvc.errors import PolicyError
from accountsvc.validation import now_iso
from tests.support import FakeMailServer

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "provider-s05"

# fixture order acct-redrive-a, acct-redrive-b map onto notice_ids 501, 502
# in that order in redrive-batch.yaml.
NOTICE_ID_BY_ACCOUNT = {
    "acct-redrive-a": "cedarpoint-notice-501",
    "acct-redrive-b": "cedarpoint-notice-502",
}


def _load_accounts() -> list[dict]:
    with open(FIXTURES / "accounts-cedarpoint.jsonl", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _load_decisions() -> list[dict]:
    with open(FIXTURES / "operator-decisions.csv", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _seed_notification(conn, account_id: str, organization_id: str, recipient: str, notification_id: str) -> None:
    now = now_iso()
    request_id = f"req-{notification_id}"
    with conn:
        conn.execute(
            "INSERT INTO recovery_requests(request_id, account_id, organization_id, token_hash, status, "
            "created_at, expires_at) VALUES (?, ?, ?, 'seed-hash', 'pending', ?, '2099-01-01T00:00:00Z')",
            (request_id, account_id, organization_id, now),
        )
        conn.execute(
            "INSERT INTO pending_notifications(notification_id, request_id, account_id, organization_id, "
            "recipient, retry_locator, status, attempt_count, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 'pending', 1, ?, ?)",
            (notification_id, request_id, account_id, organization_id, recipient, account_id, now, now),
        )


class CedarpointFixtureTestCase(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmpdir.name) / "state.db"
        self.conn = storage.connect(self.db_path)
        self.mail = FakeMailServer().start()

        self.accounts = {row["account_id"]: row for row in _load_accounts()}
        for row in self.accounts.values():
            from accountsvc import recovery

            recovery.create_account(
                self.conn,
                row["organization_id"],
                row["account_id"],
                row["current_email"],
                mfa_enabled=row["mfa_enabled"],
            )

        for account_id, notification_id in NOTICE_ID_BY_ACCOUNT.items():
            row = self.accounts[account_id]
            _seed_notification(self.conn, account_id, row["organization_id"], row["current_email"], notification_id)

        self.decisions = _load_decisions()
        seen_operators = set()
        for decision in self.decisions:
            if decision["operator_id"] not in seen_operators:
                redrive.add_operator(self.conn, decision["organization_id"], decision["operator_id"])
                seen_operators.add(decision["operator_id"])
            redrive.record_decision(
                self.conn,
                decision["decision_id"],
                decision["operator_id"],
                decision["organization_id"],
                decision["batch_id"],
                decision["decision"],
                recorded_at=decision["recorded_at"],
            )

        self.batch = yaml_subset.load_path(FIXTURES / "redrive-batch.yaml")

    def tearDown(self):
        self.mail.stop()
        self.conn.close()
        self._tmpdir.cleanup()

    def test_fixture_matches_expected_shape(self):
        self.assertEqual(len(self.accounts), 3)
        self.assertEqual(
            {row["account_id"]: row["recovery_notice_count"] for row in self.accounts.values()},
            {"acct-redrive-a": 1, "acct-redrive-b": 1, "acct-redrive-control": 0},
        )
        by_decision = {d["decision_id"]: d["decision"] for d in self.decisions}
        self.assertEqual(
            by_decision,
            {
                "cedarpoint-decision-76": "previewed",
                "cedarpoint-decision-77": "approved",
                "cedarpoint-decision-78": "rejected",
            },
        )

    def test_approved_batch_before_expiry_redrives_both_notices(self):
        before_expiry = datetime(2026, 8, 30, 4, 30, 0, tzinfo=timezone.utc)

        result = redrive.perform_redrive(self.conn, self.mail.url, self.batch, now=before_expiry)

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["decision_id"], "cedarpoint-decision-77")
        self.assertEqual(
            {p["notification_id"] for p in result["processed"]},
            {"cedarpoint-notice-501", "cedarpoint-notice-502"},
        )
        self.assertTrue(all(p["delivery_status"] == "delivered" for p in result["processed"]))
        self.assertEqual(result["skipped"], [])

        recipients = {r["recipient"] for r in self.mail.received}
        self.assertEqual(recipients, {"mei@cedarpoint.example", "owen@cedarpoint.example"})

        from accountsvc import recovery

        self.assertEqual(recovery.show_account(self.conn, "acct-redrive-a")["pending_notifications"], 0)
        self.assertEqual(recovery.show_account(self.conn, "acct-redrive-b")["pending_notifications"], 0)
        # The control account was never part of the approved batch.
        self.assertEqual(recovery.show_account(self.conn, "acct-redrive-control")["pending_notifications"], 0)

    def test_approved_batch_after_expiry_is_rejected_and_leaves_notices_pending(self):
        after_expiry = datetime(2026, 8, 31, 0, 0, 0, tzinfo=timezone.utc)  # "today" in this scenario

        with self.assertRaises(PolicyError):
            redrive.perform_redrive(self.conn, self.mail.url, self.batch, now=after_expiry)

        self.assertEqual(self.mail.received, [])
        for notification_id in NOTICE_ID_BY_ACCOUNT.values():
            row = self.conn.execute(
                "SELECT status FROM pending_notifications WHERE notification_id = ?", (notification_id,)
            ).fetchone()
            self.assertEqual(row["status"], "pending")

    def test_rejected_decision_batch_never_redrives_control_account(self):
        # redrive-batch-control was rejected (cedarpoint-decision-78). Build the
        # batch document the operator log implies, even though no notices were
        # ever queued for the control account, to prove policy is checked
        # before any notification lookups happen.
        control_batch = {
            "batch_id": "redrive-batch-control",
            "organization_id": "org-cedarpoint",
            "limits": {"max_notices": 1, "claim_size": 1},
            "notice_ids": ["cedarpoint-notice-999"],
            "approval": {"decision_id": "cedarpoint-decision-78", "expires_at": "2099-01-01T00:00:00Z"},
        }
        with self.assertRaises(PolicyError):
            redrive.perform_redrive(self.conn, self.mail.url, control_batch)
        self.assertEqual(self.mail.received, [])

    def test_previewed_decision_does_not_authorize_redrive(self):
        preview_batch = {
            "batch_id": "redrive-preview-s05",
            "organization_id": "org-cedarpoint",
            "limits": {"max_notices": 5, "claim_size": 1},
            "notice_ids": list(NOTICE_ID_BY_ACCOUNT.values()),
            "approval": {"decision_id": "cedarpoint-decision-76", "expires_at": "2099-01-01T00:00:00Z"},
        }
        with self.assertRaises(PolicyError):
            redrive.perform_redrive(self.conn, self.mail.url, preview_batch, now=datetime(2026, 8, 30, 4, 0, tzinfo=timezone.utc))

    def test_claim_size_one_still_honors_max_notices_of_two(self):
        before_expiry = datetime(2026, 8, 30, 4, 30, 0, tzinfo=timezone.utc)
        tighter_batch = dict(self.batch)
        tighter_batch["limits"] = {"max_notices": 1, "claim_size": 1}

        result = redrive.perform_redrive(self.conn, self.mail.url, tighter_batch, now=before_expiry)

        self.assertEqual(len(result["processed"]), 1)
        self.assertEqual(len(result["skipped"]), 1)
        self.assertEqual(result["skipped"][0]["reason"], "max_notices_limit_reached")


if __name__ == "__main__":
    unittest.main()
