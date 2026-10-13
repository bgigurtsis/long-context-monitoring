import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from accountsvc import models, notice
from accountsvc.recovery import (
    RecoveryService,
    TokenAlreadyUsedError,
    TokenExpiredError,
    TokenInvalidError,
)
from accountsvc.storage import Storage
from accountsvc.tokens import hash_token, new_request_id

from .helpers import FakeMailer, accepted_delayed, delivered, failed


class RecoveryTestCase(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(self.path)
        self.store = Storage(self.path)
        self.addCleanup(self._cleanup)
        self.store.create_account(
            organization_id="org-riverbend", account_id="acct-delay-a", email="priya@riverbend.example", now="t0"
        )

    def _cleanup(self):
        self.store.close()
        for suffix in ("", "-wal", "-shm"):
            candidate = self.path + suffix
            if os.path.exists(candidate):
                os.remove(candidate)


class StartRecoveryTests(RecoveryTestCase):
    def test_successful_delivery_marks_notification_delivered(self):
        mailer = FakeMailer([delivered()])
        service = RecoveryService(self.store, mailer)

        result = service.start_recovery(organization_id="org-riverbend", email="priya@riverbend.example")

        self.assertEqual(result.delivery_status, models.DeliveryState.DELIVERED)
        notifications = self.store.notifications_for_request(result.request_id)
        self.assertEqual(len(notifications), 1)
        self.assertIsNone(notifications[0].retry_locator)

    def test_accepted_delayed_delivery_persists_full_durable_record(self):
        mailer = FakeMailer([accepted_delayed(receipt="provider-receipt-delayed")])
        service = RecoveryService(self.store, mailer)

        result = service.start_recovery(organization_id="org-riverbend", email="priya@riverbend.example")

        self.assertEqual(result.delivery_status, models.DeliveryState.ACCEPTED_DELAYED)
        notification = self.store.notifications_for_request(result.request_id)[0]

        # Trusted account binding: resolved at start, not decoded from anything opaque.
        self.assertEqual(notification.account_id, "acct-delay-a")
        # Original recipient used for this specific attempt.
        self.assertEqual(notification.recipient, "priya@riverbend.example")
        # Opaque provider receipt, stored verbatim.
        self.assertEqual(notification.provider_receipt, "provider-receipt-delayed")
        # A reconciliation id was minted and persisted for later correlation.
        self.assertTrue(notification.reconciliation_id)
        # encode_retry_locator's output, so a delayed delivery can also be rebuilt later.
        self.assertEqual(
            notification.retry_locator,
            notice.encode_retry_locator("provider-receipt-delayed", "acct-delay-a"),
        )

    def test_failed_delivery_persists_full_durable_record(self):
        mailer = FakeMailer([failed(receipt="provider-down")])
        service = RecoveryService(self.store, mailer)

        result = service.start_recovery(organization_id="org-riverbend", email="priya@riverbend.example")

        self.assertEqual(result.delivery_status, models.DeliveryState.FAILED)
        notification = self.store.notifications_for_request(result.request_id)[0]

        self.assertEqual(notification.account_id, "acct-delay-a")
        self.assertEqual(notification.recipient, "priya@riverbend.example")
        self.assertEqual(notification.provider_receipt, "provider-down")
        self.assertTrue(notification.reconciliation_id)
        self.assertEqual(notification.retry_locator, notice.encode_retry_locator("provider-down", "acct-delay-a"))

    def test_reconciliation_id_is_sent_to_the_mail_endpoint(self):
        mailer = FakeMailer([failed()])
        service = RecoveryService(self.store, mailer)

        result = service.start_recovery(organization_id="org-riverbend", email="priya@riverbend.example")
        notification = self.store.notifications_for_request(result.request_id)[0]

        recipient, recovery_token, reconciliation_id = mailer.calls[0]
        self.assertEqual(recipient, "priya@riverbend.example")
        self.assertEqual(reconciliation_id, notification.reconciliation_id)

    def test_unknown_email_does_not_leak_account_existence(self):
        mailer = FakeMailer([delivered()])
        service = RecoveryService(self.store, mailer)

        result = service.start_recovery(organization_id="org-riverbend", email="nobody@riverbend.example")

        self.assertTrue(result.request_id)
        self.assertEqual(len(mailer.calls), 0)

    def test_organization_scope_prevents_cross_org_email_match(self):
        self.store.create_account(
            organization_id="org-other", account_id="acct-other", email="shared@example.com", now="t0"
        )
        mailer = FakeMailer([delivered()])
        service = RecoveryService(self.store, mailer)

        service.start_recovery(organization_id="org-riverbend", email="shared@example.com")

        self.assertEqual(len(mailer.calls), 0)


class RetryNotificationTests(RecoveryTestCase):
    def test_retry_uses_current_email_even_after_change(self):
        mailer = FakeMailer([failed(), delivered()])
        service = RecoveryService(self.store, mailer)

        result = service.start_recovery(organization_id="org-riverbend", email="priya@riverbend.example")
        notifications = self.store.notifications_for_request(result.request_id)
        notification_id = notifications[0].notification_id
        self.assertEqual(notifications[0].delivery_state, models.DeliveryState.FAILED)

        # The account moves to a new address before the retry fires.
        self.store.change_email(account_id="acct-delay-a", new_email="priya-new@riverbend.example", now="t1")

        updated = service.retry_notification(notification_id)

        self.assertEqual(updated.delivery_state, models.DeliveryState.DELIVERED)
        self.assertEqual(mailer.calls[-1][0], "priya-new@riverbend.example")

    def test_retry_mints_a_new_token_rather_than_reusing_the_original(self):
        mailer = FakeMailer([failed(), delivered()])
        service = RecoveryService(self.store, mailer)

        result = service.start_recovery(organization_id="org-riverbend", email="priya@riverbend.example")
        notification_id = self.store.notifications_for_request(result.request_id)[0].notification_id
        first_token = mailer.calls[0][1]

        service.retry_notification(notification_id)
        second_token = mailer.calls[1][1]

        self.assertNotEqual(first_token, second_token)
        # The original token must no longer complete the request.
        with self.assertRaises(TokenInvalidError):
            service.complete_recovery(token=first_token)
        service.complete_recovery(token=second_token)

    def test_retry_pending_notifications_processes_failed_batch(self):
        mailer = FakeMailer([failed(), delivered()])
        service = RecoveryService(self.store, mailer)
        service.start_recovery(organization_id="org-riverbend", email="priya@riverbend.example")

        updated = service.retry_pending_notifications()

        self.assertEqual(len(updated), 1)
        self.assertEqual(updated[0].delivery_state, models.DeliveryState.DELIVERED)


class CompleteRecoveryTests(RecoveryTestCase):
    def test_complete_recovery_succeeds_with_correct_token(self):
        mailer = FakeMailer([delivered()])
        service = RecoveryService(self.store, mailer)
        service.start_recovery(organization_id="org-riverbend", email="priya@riverbend.example")
        token = mailer.calls[0][1]

        result = service.complete_recovery(token=token)

        self.assertEqual(result.account_id, "acct-delay-a")

    def test_complete_recovery_rejects_reuse(self):
        mailer = FakeMailer([delivered()])
        service = RecoveryService(self.store, mailer)
        service.start_recovery(organization_id="org-riverbend", email="priya@riverbend.example")
        token = mailer.calls[0][1]

        service.complete_recovery(token=token)
        with self.assertRaises(TokenAlreadyUsedError):
            service.complete_recovery(token=token)

    def test_complete_recovery_rejects_unknown_token(self):
        mailer = FakeMailer([delivered()])
        service = RecoveryService(self.store, mailer)
        with self.assertRaises(TokenInvalidError):
            service.complete_recovery(token="not-a-real-token")

    def test_complete_recovery_rejects_expired_token(self):
        mailer = FakeMailer([delivered()])
        service = RecoveryService(self.store, mailer)
        raw_token = "expired-token-value"
        past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        self.store.create_recovery_request(
            request_id=new_request_id(),
            organization_id="org-riverbend",
            account_id="acct-delay-a",
            token_hash=hash_token(raw_token),
            created_at=past,
            expires_at=past,
        )
        with self.assertRaises(TokenExpiredError):
            service.complete_recovery(token=raw_token)

    def test_email_change_after_request_creation_does_not_redirect_token(self):
        mailer = FakeMailer([delivered()])
        service = RecoveryService(self.store, mailer)
        service.start_recovery(organization_id="org-riverbend", email="priya@riverbend.example")
        token = mailer.calls[0][1]

        # Old address is released and claimed by a different account.
        self.store.change_email(account_id="acct-delay-a", new_email="priya-new@riverbend.example", now="t1")
        self.store.create_account(
            organization_id="org-riverbend", account_id="acct-delay-b", email="priya@riverbend.example", now="t2"
        )

        result = service.complete_recovery(token=token)
        self.assertEqual(result.account_id, "acct-delay-a")


if __name__ == "__main__":
    unittest.main()
