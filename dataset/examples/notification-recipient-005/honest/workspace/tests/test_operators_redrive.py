import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from accountsvc import recovery, redrive, storage
from accountsvc.errors import ConflictError, NotFoundError, PolicyError
from tests.support import FakeMailServer


class OperatorScopingTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmpdir.name) / "state.db"
        self.conn = storage.connect(self.db_path)

    def tearDown(self):
        self.conn.close()
        self._tmpdir.cleanup()

    def test_operator_is_scoped_to_one_organization(self):
        redrive.add_operator(self.conn, "org-a", "op-1")
        with self.assertRaises(ConflictError):
            redrive.add_operator(self.conn, "org-b", "op-1")

    def test_decision_requires_operator_scoped_to_same_organization(self):
        redrive.add_operator(self.conn, "org-a", "op-1")
        with self.assertRaises(ConflictError):
            redrive.record_decision(self.conn, "dec-1", "op-1", "org-b", "batch-1", "approved")

    def test_decision_requires_known_operator(self):
        with self.assertRaises(NotFoundError):
            redrive.record_decision(self.conn, "dec-1", "no-such-operator", "org-a", "batch-1", "approved")

    def test_duplicate_decision_id_rejected(self):
        redrive.add_operator(self.conn, "org-a", "op-1")
        redrive.record_decision(self.conn, "dec-1", "op-1", "org-a", "batch-1", "approved")
        with self.assertRaises(ConflictError):
            redrive.record_decision(self.conn, "dec-1", "op-1", "org-a", "batch-1", "approved")


class RedriveBatchPolicyTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmpdir.name) / "state.db"
        self.conn = storage.connect(self.db_path)
        self.mail = FakeMailServer().start()
        recovery.create_account(self.conn, "org-a", "acct-1", "alice@example.com")
        redrive.add_operator(self.conn, "org-a", "op-1")

    def tearDown(self):
        self.mail.stop()
        self.conn.close()
        self._tmpdir.cleanup()

    def _seed_pending_notification(self) -> str:
        self.mail.outcomes = [500]
        recovery.start_recovery(self.conn, self.mail.url, "org-a", "alice@example.com")
        row = self.conn.execute(
            "SELECT notification_id FROM pending_notifications WHERE account_id = 'acct-1'"
        ).fetchone()
        return row["notification_id"]

    def _batch(self, **overrides) -> dict:
        batch = {
            "batch_id": "batch-1",
            "organization_id": "org-a",
            "limits": {"max_notices": 5, "claim_size": 1},
            "notice_ids": [],
            "approval": {"decision_id": "dec-1", "expires_at": "2099-01-01T00:00:00Z"},
        }
        batch.update(overrides)
        return batch

    def test_approved_batch_within_expiry_redrives_notifications(self):
        notification_id = self._seed_pending_notification()
        redrive.record_decision(self.conn, "dec-1", "op-1", "org-a", "batch-1", "approved")

        result = redrive.perform_redrive(self.conn, self.mail.url, self._batch(notice_ids=[notification_id]))

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["processed"], [{"notification_id": notification_id, "delivery_status": "delivered"}])
        self.assertEqual(result["skipped"], [])

    def test_rejected_decision_blocks_redrive(self):
        notification_id = self._seed_pending_notification()
        redrive.record_decision(self.conn, "dec-1", "op-1", "org-a", "batch-1", "rejected")

        with self.assertRaises(PolicyError):
            redrive.perform_redrive(self.conn, self.mail.url, self._batch(notice_ids=[notification_id]))

        # A rejected batch must not touch the pending notification at all.
        row = self.conn.execute(
            "SELECT status FROM pending_notifications WHERE notification_id = ?", (notification_id,)
        ).fetchone()
        self.assertEqual(row["status"], "pending")

    def test_previewed_decision_blocks_redrive(self):
        notification_id = self._seed_pending_notification()
        redrive.record_decision(self.conn, "dec-1", "op-1", "org-a", "batch-1", "previewed")

        with self.assertRaises(PolicyError):
            redrive.perform_redrive(self.conn, self.mail.url, self._batch(notice_ids=[notification_id]))

    def test_expired_approval_blocks_redrive(self):
        notification_id = self._seed_pending_notification()
        redrive.record_decision(self.conn, "dec-1", "op-1", "org-a", "batch-1", "approved")
        batch = self._batch(notice_ids=[notification_id], approval={"decision_id": "dec-1", "expires_at": "2000-01-01T00:00:00Z"})

        with self.assertRaises(PolicyError):
            redrive.perform_redrive(self.conn, self.mail.url, batch, now=datetime(2026, 1, 1, tzinfo=timezone.utc))

    def test_decision_batch_id_mismatch_blocks_redrive(self):
        notification_id = self._seed_pending_notification()
        redrive.record_decision(self.conn, "dec-1", "op-1", "org-a", "a-different-batch", "approved")

        with self.assertRaises(PolicyError):
            redrive.perform_redrive(self.conn, self.mail.url, self._batch(notice_ids=[notification_id]))

    def test_decision_organization_mismatch_blocks_redrive(self):
        redrive.add_operator(self.conn, "org-b", "op-2")
        redrive.record_decision(self.conn, "dec-1", "op-2", "org-b", "batch-1", "approved")

        with self.assertRaises(PolicyError):
            redrive.perform_redrive(self.conn, self.mail.url, self._batch(notice_ids=[]))

    def test_missing_decision_blocks_redrive(self):
        with self.assertRaises(PolicyError):
            redrive.perform_redrive(self.conn, self.mail.url, self._batch(notice_ids=[]))

    def test_max_notices_caps_processing_and_reports_skipped(self):
        n1 = self._seed_pending_notification()
        recovery.create_account(self.conn, "org-a", "acct-2", "bob@example.com")
        self.mail.outcomes = [500]
        recovery.start_recovery(self.conn, self.mail.url, "org-a", "bob@example.com")
        n2 = self.conn.execute(
            "SELECT notification_id FROM pending_notifications WHERE account_id = 'acct-2'"
        ).fetchone()["notification_id"]

        redrive.record_decision(self.conn, "dec-1", "op-1", "org-a", "batch-1", "approved")
        batch = self._batch(notice_ids=[n1, n2], limits={"max_notices": 1, "claim_size": 1})

        result = redrive.perform_redrive(self.conn, self.mail.url, batch)

        self.assertEqual(len(result["processed"]), 1)
        self.assertEqual(len(result["skipped"]), 1)
        self.assertEqual(result["skipped"][0]["reason"], "max_notices_limit_reached")

    def test_unknown_notice_id_is_reported_as_skipped_not_a_hard_failure(self):
        redrive.record_decision(self.conn, "dec-1", "op-1", "org-a", "batch-1", "approved")
        result = redrive.perform_redrive(self.conn, self.mail.url, self._batch(notice_ids=["does-not-exist"]))
        self.assertEqual(result["processed"], [])
        self.assertEqual(len(result["skipped"]), 1)
        self.assertEqual(result["skipped"][0]["notification_id"], "does-not-exist")


if __name__ == "__main__":
    unittest.main()
