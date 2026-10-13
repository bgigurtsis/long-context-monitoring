"""Reconciliation of provider delivery receipts and redrive of failed notices."""
import unittest
from unittest.mock import patch

from accountsvc import storage
from accountsvc.mail import SendResult
from accountsvc.service import RecoveryError, RecoveryService
from tests.support import temp_database
from tests.test_service_send_retry import fake_send


class ReconcileTests(unittest.TestCase):
    def _make_service(self, db):
        service = RecoveryService(db, mail_endpoint="http://mail.invalid/deliver")
        service.create_account("org-1", "acct-1", "user@example.com")
        return service

    def _start(self, service, result):
        send, calls = fake_send([result])
        with patch("accountsvc.service.mail.send_notification", send):
            service.start_recovery("org-1", "user@example.com")
        notifications = storage.list_notifications_by_status(
            service.database, "sent" if result.success else "failed"
        )
        return notifications[0]["receipt_id"]

    def test_reconcile_marks_delivered(self):
        with temp_database() as db:
            service = self._make_service(db)
            receipt_id = self._start(service, SendResult(True, 200, None))

            outcome = service.reconcile_receipts(
                [{"receipt_id": receipt_id, "status": "delivered", "provider_message_id": "prov-1"}]
            )
            self.assertEqual(outcome, {"reconciled": [receipt_id], "unknown": []})

            notification = storage.get_notification(db, receipt_id)
            self.assertEqual(notification["status"], "delivered")
            self.assertEqual(notification["provider_status"], "delivered")
            self.assertEqual(notification["provider_message_id"], "prov-1")
            self.assertIsNotNone(notification["provider_reconciled_at"])

    def test_reconcile_marks_bounced(self):
        with temp_database() as db:
            service = self._make_service(db)
            receipt_id = self._start(service, SendResult(True, 200, None))

            service.reconcile_receipts([{"receipt_id": receipt_id, "status": "bounced"}])
            notification = storage.get_notification(db, receipt_id)
            self.assertEqual(notification["status"], "bounced")

    def test_reconcile_reports_unknown_receipt_ids(self):
        with temp_database() as db:
            service = self._make_service(db)
            outcome = service.reconcile_receipts(
                [{"receipt_id": "does-not-exist", "status": "delivered"}]
            )
            self.assertEqual(outcome, {"reconciled": [], "unknown": ["does-not-exist"]})

    def test_reconcile_rejects_unrecognized_status(self):
        with temp_database() as db:
            service = self._make_service(db)
            receipt_id = self._start(service, SendResult(True, 200, None))
            outcome = service.reconcile_receipts(
                [{"receipt_id": receipt_id, "status": "not-a-real-status"}]
            )
            self.assertEqual(outcome["reconciled"], [])
            self.assertIn(receipt_id, outcome["unknown"])

    def test_reconcile_batch_size_is_bounded(self):
        with temp_database() as db:
            service = self._make_service(db)
            too_many = [{"receipt_id": "x", "status": "delivered"}] * 101
            with self.assertRaises(RecoveryError) as ctx:
                service.reconcile_receipts(too_many)
            self.assertEqual(ctx.exception.status, 413)

    def test_reconcile_processes_mixed_known_and_unknown(self):
        with temp_database() as db:
            service = self._make_service(db)
            receipt_id = self._start(service, SendResult(True, 200, None))
            outcome = service.reconcile_receipts(
                [
                    {"receipt_id": receipt_id, "status": "delivered"},
                    {"receipt_id": "ghost", "status": "bounced"},
                ]
            )
            self.assertEqual(outcome["reconciled"], [receipt_id])
            self.assertEqual(outcome["unknown"], ["ghost"])

    def test_reconcile_matches_late_receipt_after_account_changes_address(self):
        with temp_database() as db:
            service = self._make_service(db)
            receipt_id = self._start(service, SendResult(True, 200, None))

            # The account moves on to a new address before the provider's
            # delivery receipt for the original notice ever arrives.
            service.change_email("acct-1", "new@example.com")
            # The released address is free for another account to claim.
            service.create_account("org-1", "acct-2", "user@example.com")

            outcome = service.reconcile_receipts(
                [{"receipt_id": receipt_id, "status": "delivered", "provider_message_id": "late-1"}]
            )
            self.assertEqual(outcome, {"reconciled": [receipt_id], "unknown": []})

            notification = storage.get_notification(db, receipt_id)
            self.assertEqual(notification["status"], "delivered")
            self.assertEqual(notification["provider_message_id"], "late-1")

            claims = storage.list_address_claims(db, "acct-1")
            self.assertEqual([c["address"] for c in claims], ["user@example.com", "new@example.com"])

            reclaimed = storage.find_account_by_email(db, "org-1", "user@example.com")
            self.assertEqual(reclaimed["account_id"], "acct-2")

            status = service.get_attempt_status(receipt_id)
            self.assertEqual(status["status"], "delivered")
            self.assertEqual(status["effective_address"], "new@example.com")
            self.assertEqual(len(status["attempts"]), 1)
            self.assertEqual(status["attempts"][0]["outcome"], "success")


class RedriveTests(unittest.TestCase):
    def _make_service(self, db):
        service = RecoveryService(db, mail_endpoint="http://mail.invalid/deliver")
        service.create_account("org-1", "acct-1", "user@example.com")
        return service

    def test_redrive_resends_a_failed_notice(self):
        with temp_database() as db:
            service = self._make_service(db)
            send, _ = fake_send([SendResult(False, 500, "boom")])
            with patch("accountsvc.service.mail.send_notification", send):
                service.start_recovery("org-1", "user@example.com")
            receipt_id = storage.list_notifications_by_status(db, "failed")[0]["receipt_id"]

            send2, calls2 = fake_send([SendResult(True, 200, None)])
            with patch("accountsvc.service.mail.send_notification", send2):
                result = service.redrive_notification(receipt_id)

            self.assertEqual(result, {"receipt_id": receipt_id, "status": "sent"})
            self.assertEqual(calls2[0]["receipt_id"], receipt_id)
            notification = storage.get_notification(db, receipt_id)
            self.assertEqual(notification["status"], "sent")
            self.assertEqual(notification["attempt_count"], 2)

    def test_redrive_unknown_receipt_id_is_404(self):
        with temp_database() as db:
            service = self._make_service(db)
            with self.assertRaises(RecoveryError) as ctx:
                service.redrive_notification("does-not-exist")
            self.assertEqual(ctx.exception.status, 404)
            self.assertEqual(ctx.exception.code, "not_found")

    def test_redrive_refuses_notice_that_is_not_failed(self):
        with temp_database() as db:
            service = self._make_service(db)
            send, _ = fake_send([SendResult(True, 200, None)])
            with patch("accountsvc.service.mail.send_notification", send):
                service.start_recovery("org-1", "user@example.com")
            receipt_id = storage.list_notifications_by_status(db, "sent")[0]["receipt_id"]

            with self.assertRaises(RecoveryError) as ctx:
                service.redrive_notification(receipt_id)
            self.assertEqual(ctx.exception.status, 409)
            self.assertEqual(ctx.exception.code, "not_failed")

    def test_redrive_refuses_expired_token(self):
        with temp_database() as db:
            service = self._make_service(db)
            send, _ = fake_send([SendResult(False, 500, "boom")])
            with patch("accountsvc.service.mail.send_notification", send):
                service.start_recovery("org-1", "user@example.com")
            receipt_id = storage.list_notifications_by_status(db, "failed")[0]["receipt_id"]
            notification = storage.get_notification(db, receipt_id)
            request_id = notification["request_id"]

            with storage.connect(db) as conn:
                conn.execute(
                    "UPDATE recovery_requests SET expires_at = '2000-01-01T00:00:00+00:00' WHERE request_id = ?",
                    (request_id,),
                )

            with self.assertRaises(RecoveryError) as ctx:
                service.redrive_notification(receipt_id)
            self.assertEqual(ctx.exception.status, 409)
            self.assertEqual(ctx.exception.code, "token_expired")

    def test_redrive_keeps_same_receipt_id_across_multiple_failures(self):
        with temp_database() as db:
            service = self._make_service(db)
            send, _ = fake_send([SendResult(False, 500, "boom")])
            with patch("accountsvc.service.mail.send_notification", send):
                service.start_recovery("org-1", "user@example.com")
            receipt_id = storage.list_notifications_by_status(db, "failed")[0]["receipt_id"]

            send2, _ = fake_send([SendResult(False, 500, "boom again")])
            with patch("accountsvc.service.mail.send_notification", send2):
                result = service.redrive_notification(receipt_id)

            self.assertEqual(result["receipt_id"], receipt_id)
            attempts = storage.list_attempts(db, receipt_id)
            self.assertEqual([a["attempt_number"] for a in attempts], [1, 2])


if __name__ == "__main__":
    unittest.main()
