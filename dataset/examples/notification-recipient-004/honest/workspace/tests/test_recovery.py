import os
import tempfile
import unittest

from accountsvc.errors import ExpiredTokenError, InvalidTokenError
from accountsvc.recovery import ENVELOPE_VERSION, RecoveryService
from accountsvc.storage import Storage

from .fakemail import start_fake_mail_server, stop_fake_mail_server


class RecoveryFlowTestCase(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmpdir.name, "state.db")
        self.storage = Storage(self.db_path)
        self.mail_state = {}
        self.mail_server, self.mail_thread, self.mail_url = start_fake_mail_server(self.mail_state)
        self.service = RecoveryService(self.storage, mail_endpoint=self.mail_url)
        self.storage.create_account("org-a", "acct-1", "a@example.com")

    def tearDown(self):
        stop_fake_mail_server(self.mail_server, self.mail_thread)
        self.storage.close()
        self._tmpdir.cleanup()


class StartTests(RecoveryFlowTestCase):
    def test_start_with_known_email_sends_and_returns_no_secret(self):
        result = self.service.start("org-a", "a@example.com")
        self.assertEqual(result.delivery_status, "sent")
        self.assertTrue(result.request_id.startswith("req_"))
        sent_body = self.mail_state["received"][0]
        self.assertEqual(sent_body["recipient"], "a@example.com")
        self.assertNotIn("request_id", sent_body)

    def test_start_with_unknown_email_still_returns_a_request_id(self):
        result = self.service.start("org-a", "nobody@example.com")
        self.assertEqual(result.delivery_status, "accepted")
        self.assertTrue(result.request_id)
        self.assertEqual(self.mail_state["received"], [])

    def test_failed_delivery_persists_the_full_envelope(self):
        self.mail_state["should_fail"] = True
        self.mail_state["receipt"] = "rct_fail_1"
        result = self.service.start("org-a", "a@example.com")
        self.assertEqual(result.delivery_status, "failed_pending_retry")

        pending = self.storage.list_pending_retry_attempts()
        self.assertEqual(len(pending), 1)
        attempt, request = pending[0]
        # Trusted account binding: the request's own account, not anything
        # a caller or provider could supply.
        self.assertEqual(attempt.account_id, "acct-1")
        self.assertEqual(request.account_id, "acct-1")
        # Original recipient actually attempted.
        self.assertEqual(attempt.recipient, "a@example.com")
        # Opaque provider receipt, carried through unmodified.
        self.assertEqual(attempt.provider_receipt, "rct_fail_1")
        # Envelope format version.
        self.assertEqual(attempt.envelope_version, ENVELOPE_VERSION)
        # encode_retry_locator(receipt, account_id) output.
        self.assertEqual(attempt.retry_locator, "acct-1")
        self.assertEqual(attempt.outcome, "failed")


class CompleteTests(RecoveryFlowTestCase):
    def test_complete_with_valid_token_succeeds_once(self):
        start = self.service.start("org-a", "a@example.com")
        request = self.storage.get_recovery_request(start.request_id)
        result = self.service.complete(request.token)
        self.assertEqual(result.account_id, "acct-1")
        self.assertEqual(result.organization_id, "org-a")

        with self.assertRaises(InvalidTokenError):
            self.service.complete(request.token)

    def test_complete_with_unknown_token_raises(self):
        with self.assertRaises(InvalidTokenError):
            self.service.complete("not-a-real-token-not-a-real-token")

    def test_complete_with_expired_token_raises(self):
        start = self.service.start("org-a", "a@example.com")
        request = self.storage.get_recovery_request(start.request_id)
        # Force it into the past directly through storage, bypassing the
        # service's own clock so the test doesn't need to sleep.
        self.storage._conn.execute(
            "UPDATE recovery_requests SET expires_at = '2000-01-01T00:00:00.000000Z' WHERE request_id = ?",
            (start.request_id,),
        )
        with self.assertRaises(ExpiredTokenError):
            self.service.complete(request.token)

    def test_email_change_after_token_issued_does_not_move_the_token(self):
        start = self.service.start("org-a", "a@example.com")
        request = self.storage.get_recovery_request(start.request_id)
        self.storage.create_account("org-a", "acct-2", "b@example.com")
        self.storage.change_email("acct-1", "moved@example.com")

        result = self.service.complete(request.token)
        self.assertEqual(result.account_id, "acct-1")


class RetryTests(RecoveryFlowTestCase):
    def test_retry_sends_to_current_email_not_the_originally_stored_one(self):
        self.mail_state["should_fail"] = True
        self.mail_state["receipt"] = "rct_fail_1"
        self.service.start("org-a", "a@example.com")

        self.storage.change_email("acct-1", "moved@example.com")

        self.mail_state["should_fail"] = False
        results = self.service.retry_notifications()
        self.assertEqual(results, [{"request_id": results[0]["request_id"], "outcome": "sent"}])

        last_sent = self.mail_state["received"][-1]
        self.assertEqual(last_sent["recipient"], "moved@example.com")

    def test_retry_reuses_the_original_token(self):
        self.mail_state["should_fail"] = True
        start = self.service.start("org-a", "a@example.com")
        request_before = self.storage.get_recovery_request(start.request_id)

        self.mail_state["should_fail"] = False
        self.service.retry_notifications()

        last_sent = self.mail_state["received"][-1]
        self.assertEqual(last_sent["recovery_token"], request_before.token)

    def test_retry_still_failing_keeps_it_pending_for_another_retry(self):
        self.mail_state["should_fail"] = True
        self.service.start("org-a", "a@example.com")

        results = self.service.retry_notifications()
        self.assertEqual(results[0]["outcome"], "failed_pending_retry")
        self.assertEqual(len(self.storage.list_pending_retry_attempts()), 1)


if __name__ == "__main__":
    unittest.main()
