import tempfile
import unittest
from pathlib import Path

from accountsvc import notice, recovery, storage
from accountsvc.errors import ConflictError, NotFoundError, ValidationError
from accountsvc.tokens import hash_token
from tests.support import FakeMailServer


class RecoveryFlowTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmpdir.name) / "state.db"
        self.conn = storage.connect(self.db_path)
        self.mail = FakeMailServer().start()
        recovery.create_account(self.conn, "org-a", "acct-1", "alice@example.com")

    def tearDown(self):
        self.mail.stop()
        self.conn.close()
        self._tmpdir.cleanup()

    def test_start_and_complete_recovery_happy_path(self):
        started = recovery.start_recovery(self.conn, self.mail.url, "org-a", "alice@example.com")
        self.assertEqual(started["delivery_status"], "delivered")
        self.assertNotIn("token", started)
        self.assertNotIn("recovery_token", started)

        self.assertEqual(len(self.mail.received), 1)
        self.assertEqual(self.mail.received[0]["recipient"], "alice@example.com")
        token = self.mail.received[0]["recovery_token"]

        completed = recovery.complete_recovery(self.conn, token)
        self.assertEqual(completed, {"account_id": "acct-1", "status": "completed"})

    def test_token_is_single_use(self):
        recovery.start_recovery(self.conn, self.mail.url, "org-a", "alice@example.com")
        token = self.mail.received[0]["recovery_token"]
        recovery.complete_recovery(self.conn, token)
        with self.assertRaises(ValidationError):
            recovery.complete_recovery(self.conn, token)

    def test_expired_token_rejected(self):
        recovery.start_recovery(self.conn, self.mail.url, "org-a", "alice@example.com")
        token = self.mail.received[0]["recovery_token"]
        with self.conn:
            self.conn.execute(
                "UPDATE recovery_requests SET expires_at = '2000-01-01T00:00:00Z' WHERE token_hash = ?",
                (hash_token(token),),
            )
        with self.assertRaises(ValidationError):
            recovery.complete_recovery(self.conn, token)

    def test_unknown_organization_or_email_does_not_error_or_leak(self):
        result = recovery.start_recovery(self.conn, self.mail.url, "org-a", "nobody@example.com")
        self.assertEqual(result["delivery_status"], "accepted")
        self.assertEqual(self.mail.received, [])  # no delivery attempted for an unknown address

    def test_failed_delivery_is_durably_queued_and_can_be_retried(self):
        self.mail.outcomes = [500]
        started = recovery.start_recovery(self.conn, self.mail.url, "org-a", "alice@example.com")
        self.assertEqual(started["delivery_status"], "queued_for_retry")

        shown = recovery.show_account(self.conn, "acct-1")
        self.assertEqual(shown["pending_notifications"], 1)

        notification = self.conn.execute(
            "SELECT notification_id FROM pending_notifications WHERE account_id = ?", ("acct-1",)
        ).fetchone()
        retried = recovery.retry_notification(self.conn, self.mail.url, notification["notification_id"])
        self.assertEqual(retried["delivery_status"], "delivered")
        self.assertEqual(recovery.show_account(self.conn, "acct-1")["pending_notifications"], 0)

    def test_retry_delivers_to_current_email_not_the_original_recipient(self):
        self.mail.outcomes = [500]
        recovery.start_recovery(self.conn, self.mail.url, "org-a", "alice@example.com")
        notification = self.conn.execute(
            "SELECT notification_id FROM pending_notifications WHERE account_id = ?", ("acct-1",)
        ).fetchone()

        recovery.change_email(self.conn, "acct-1", "alice-new@example.com")
        recovery.retry_notification(self.conn, self.mail.url, notification["notification_id"])

        self.assertEqual(self.mail.received[-1]["recipient"], "alice-new@example.com")

    def test_email_change_after_start_does_not_change_recoverable_account(self):
        recovery.start_recovery(self.conn, self.mail.url, "org-a", "alice@example.com")
        token = self.mail.received[0]["recovery_token"]

        recovery.create_account(self.conn, "org-a", "acct-2", "someone-else@example.com")
        recovery.change_email(self.conn, "acct-1", "alice-new@example.com")
        recovery.change_email(self.conn, "acct-2", "alice@example.com")  # acct-2 now owns the old address

        completed = recovery.complete_recovery(self.conn, token)
        self.assertEqual(completed["account_id"], "acct-1")  # still the original account, not acct-2

    def test_retry_unknown_notification_raises_not_found(self):
        with self.assertRaises(NotFoundError):
            recovery.retry_notification(self.conn, self.mail.url, "does-not-exist")

    def test_retry_already_delivered_notification_raises_conflict(self):
        self.mail.outcomes = [500]
        recovery.start_recovery(self.conn, self.mail.url, "org-a", "alice@example.com")
        notification = self.conn.execute(
            "SELECT notification_id FROM pending_notifications WHERE account_id = ?", ("acct-1",)
        ).fetchone()
        recovery.retry_notification(self.conn, self.mail.url, notification["notification_id"])
        with self.assertRaises(ConflictError):
            recovery.retry_notification(self.conn, self.mail.url, notification["notification_id"])

    def test_failed_attempt_persists_full_redrive_record(self):
        # A failed provider attempt must leave everything a later redrive
        # needs: the trusted (not caller-supplied) account binding, the
        # exact recipient that was attempted, the provider's receipt kept
        # opaque, a distinct attempt id, and the retry locator produced by
        # the one blessed helper for building it.
        self.mail.outcomes = [503]
        recovery.start_recovery(self.conn, self.mail.url, "org-a", "alice@example.com")

        attempt = self.conn.execute(
            "SELECT * FROM delivery_attempts ORDER BY attempted_at DESC LIMIT 1"
        ).fetchone()
        self.assertTrue(attempt["attempt_id"])
        self.assertEqual(attempt["outcome"], "failure")
        self.assertEqual(attempt["recipient"], "alice@example.com")
        receipt = attempt["provider_receipt"]
        self.assertIsInstance(receipt, str)
        self.assertTrue(receipt)

        pending = self.conn.execute(
            "SELECT * FROM pending_notifications WHERE request_id = ?", (attempt["request_id"],)
        ).fetchone()
        self.assertEqual(pending["account_id"], "acct-1")  # the trusted binding, not attacker input
        self.assertEqual(pending["organization_id"], "org-a")
        self.assertEqual(pending["recipient"], "alice@example.com")
        self.assertEqual(pending["status"], "pending")
        self.assertEqual(pending["attempt_count"], 1)
        # The persisted locator is exactly what the starter helper produces
        # for this receipt and account -- nothing else derives it.
        self.assertEqual(pending["retry_locator"], notice.encode_retry_locator(receipt, "acct-1"))

    def test_provider_receipt_is_stored_opaquely(self):
        self.mail.outcomes = [500]
        recovery.start_recovery(self.conn, self.mail.url, "org-a", "alice@example.com")
        attempt = self.conn.execute(
            "SELECT provider_receipt, outcome FROM delivery_attempts ORDER BY attempted_at DESC LIMIT 1"
        ).fetchone()
        self.assertEqual(attempt["outcome"], "failure")
        self.assertIsInstance(attempt["provider_receipt"], str)
        self.assertTrue(attempt["provider_receipt"])


if __name__ == "__main__":
    unittest.main()
