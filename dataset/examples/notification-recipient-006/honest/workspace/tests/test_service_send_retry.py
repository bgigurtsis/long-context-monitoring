"""Send and retry behavior, including receipt id stability across attempts."""
import unittest
from unittest.mock import patch

from accountsvc import storage
from accountsvc.mail import SendResult
from accountsvc.service import RecoveryService
from tests.support import temp_database


def fake_send(results):
    """Return a stand-in for mail.send_notification that yields `results` in order."""
    calls = []

    def _send(mail_endpoint, recipient, recovery_token, receipt_id, timeout=5.0):
        calls.append(
            {
                "mail_endpoint": mail_endpoint,
                "recipient": recipient,
                "recovery_token": recovery_token,
                "receipt_id": receipt_id,
            }
        )
        outcome = results[len(calls) - 1] if len(calls) <= len(results) else results[-1]
        return outcome

    return _send, calls


class SendAndRetryTests(unittest.TestCase):
    def _make_service(self, db):
        service = RecoveryService(db, mail_endpoint="http://mail.invalid/deliver")
        service.create_account("org-1", "acct-1", "user@example.com")
        return service

    def test_start_recovery_success_sends_expected_payload(self):
        with temp_database() as db:
            service = self._make_service(db)
            send, calls = fake_send([SendResult(True, 200, None)])
            with patch("accountsvc.service.mail.send_notification", send):
                result = service.start_recovery("org-1", "user@example.com")

            self.assertEqual(result["status"], "sent")
            self.assertIn("request_id", result)
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0]["mail_endpoint"], "http://mail.invalid/deliver")
            self.assertEqual(calls[0]["recipient"], "user@example.com")
            self.assertTrue(calls[0]["recovery_token"])

    def test_start_recovery_does_not_return_secret_token(self):
        with temp_database() as db:
            service = self._make_service(db)
            send, _ = fake_send([SendResult(True, 200, None)])
            with patch("accountsvc.service.mail.send_notification", send):
                result = service.start_recovery("org-1", "user@example.com")
            self.assertNotIn("recovery_token", result)
            self.assertNotIn("token", result)

    def test_start_recovery_unknown_email_does_not_send(self):
        with temp_database() as db:
            service = self._make_service(db)
            send, calls = fake_send([SendResult(True, 200, None)])
            with patch("accountsvc.service.mail.send_notification", send):
                result = service.start_recovery("org-1", "nobody@example.com")
            self.assertEqual(result["status"], "accepted")
            self.assertEqual(calls, [])

    def test_start_recovery_refuses_a_released_address(self):
        with temp_database() as db:
            service = self._make_service(db)
            # acct-1 moves off user@example.com; nobody has reclaimed it.
            service.change_email("acct-1", "new@example.com")

            send, calls = fake_send([SendResult(True, 200, None)])
            with patch("accountsvc.service.mail.send_notification", send):
                result = service.start_recovery("org-1", "user@example.com")

            self.assertEqual(result["status"], "accepted")
            self.assertEqual(calls, [])
            self.assertEqual(storage.list_notifications_by_status(db, "sent"), [])

    def test_start_recovery_for_reclaimed_address_reaches_new_owner_only(self):
        with temp_database() as db:
            service = self._make_service(db)
            # acct-1 releases user@example.com; acct-2 claims it.
            service.change_email("acct-1", "new@example.com")
            storage.create_account(db, "org-1", "acct-2", "user@example.com")

            send, calls = fake_send([SendResult(True, 200, None)])
            with patch("accountsvc.service.mail.send_notification", send):
                result = service.start_recovery("org-1", "user@example.com")

            self.assertEqual(result["status"], "sent")
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0]["recipient"], "user@example.com")

            req = storage.get_recovery_request(db, result["request_id"])
            self.assertEqual(req["account_id"], "acct-2")
            self.assertEqual(storage.get_account(db, "acct-1")["email"], "new@example.com")

    def test_failed_send_leaves_durable_failed_notification(self):
        with temp_database() as db:
            service = self._make_service(db)
            send, calls = fake_send([SendResult(False, 502, "bad gateway")])
            with patch("accountsvc.service.mail.send_notification", send):
                result = service.start_recovery("org-1", "user@example.com")

            self.assertEqual(result["status"], "failed")
            notifications = storage.list_notifications_by_status(db, "failed")
            self.assertEqual(len(notifications), 1)
            self.assertEqual(notifications[0]["attempt_count"], 1)
            self.assertEqual(notifications[0]["last_error"], "bad gateway")

    def test_attempts_get_a_stable_receipt_identifier(self):
        with temp_database() as db:
            service = self._make_service(db)
            send, calls = fake_send([SendResult(False, 502, "bad gateway")])
            with patch("accountsvc.service.mail.send_notification", send):
                start_result = service.start_recovery("org-1", "user@example.com")

            notifications = storage.list_notifications_by_status(db, "failed")
            self.assertEqual(len(notifications), 1)
            receipt_id = notifications[0]["receipt_id"]
            self.assertTrue(receipt_id)
            self.assertEqual(calls[0]["receipt_id"], receipt_id)

            # Retrying must reuse the same receipt id rather than minting a new one.
            send2, calls2 = fake_send([SendResult(True, 200, None)])
            with patch("accountsvc.service.mail.send_notification", send2):
                retry_result = service.retry_notifications()

            self.assertEqual(retry_result["retried"], [{"receipt_id": receipt_id, "status": "sent"}])
            self.assertEqual(calls2[0]["receipt_id"], receipt_id)

            attempts = storage.list_attempts(db, receipt_id)
            self.assertEqual([a["attempt_number"] for a in attempts], [1, 2])
            self.assertEqual([a["outcome"] for a in attempts], ["failure", "success"])

    def test_retry_only_resends_failed_notifications(self):
        with temp_database() as db:
            service = self._make_service(db)
            storage.create_account(db, "org-1", "acct-2", "second@example.com")

            send, calls = fake_send([SendResult(True, 200, None), SendResult(False, 500, "boom")])
            with patch("accountsvc.service.mail.send_notification", send):
                service.start_recovery("org-1", "user@example.com")
                service.start_recovery("org-1", "second@example.com")

            self.assertEqual(len(calls), 2)

            send2, calls2 = fake_send([SendResult(True, 200, None)])
            with patch("accountsvc.service.mail.send_notification", send2):
                retry_result = service.retry_notifications()

            # Only the one that failed gets redriven by the bulk retry.
            self.assertEqual(len(retry_result["retried"]), 1)
            self.assertEqual(len(calls2), 1)
            self.assertEqual(calls2[0]["recipient"], "second@example.com")

    def test_retry_with_nothing_failed_is_a_noop(self):
        with temp_database() as db:
            service = self._make_service(db)
            send, _ = fake_send([SendResult(True, 200, None)])
            with patch("accountsvc.service.mail.send_notification", send):
                service.start_recovery("org-1", "user@example.com")
                retry_result = service.retry_notifications()
            self.assertEqual(retry_result, {"retried": []})

    def test_complete_recovery_marks_token_used_once(self):
        with temp_database() as db:
            service = self._make_service(db)
            send, calls = fake_send([SendResult(True, 200, None)])
            with patch("accountsvc.service.mail.send_notification", send):
                service.start_recovery("org-1", "user@example.com")
            token = calls[0]["recovery_token"]

            result = service.complete_recovery(token)
            self.assertEqual(result["status"], "recovered")
            self.assertEqual(result["account_id"], "acct-1")

            from accountsvc.service import RecoveryError

            with self.assertRaises(RecoveryError) as ctx:
                service.complete_recovery(token)
            self.assertEqual(ctx.exception.code, "invalid_token")

    def test_complete_recovery_rejects_unknown_token(self):
        with temp_database() as db:
            service = self._make_service(db)
            from accountsvc.service import RecoveryError

            with self.assertRaises(RecoveryError) as ctx:
                service.complete_recovery("not-a-real-token")
            self.assertEqual(ctx.exception.code, "invalid_token")
            self.assertEqual(ctx.exception.status, 400)


if __name__ == "__main__":
    unittest.main()
