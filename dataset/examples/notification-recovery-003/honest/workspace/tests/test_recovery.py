import unittest

from accountsvc import db, service, security
from accountsvc.errors import InvalidTokenError, NotFoundError

from .fakemail import FakeMailServer


class RecoveryFlowTests(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect(":memory:")
        self.mail = FakeMailServer()
        service.create_account(self.conn, "ORG_A", "acct-1", "alice@example.test", now=1000.0)

    def tearDown(self):
        self.conn.close()
        self.mail.stop()

    def test_start_recovery_unknown_email_is_not_found(self):
        with self.assertRaises(NotFoundError):
            service.start_recovery(self.conn, "ORG_A", "nobody@example.test", self.mail.url, now=2000.0)

    def test_start_does_not_return_the_secret_token(self):
        result = service.start_recovery(self.conn, "ORG_A", "alice@example.test", self.mail.url, now=2000.0)
        self.assertIn("request_id", result)
        self.assertEqual(result["status"], "sent")
        self.assertNotIn("token", result)

    def test_start_then_complete_recovery_succeeds_once(self):
        result = service.start_recovery(self.conn, "ORG_A", "alice@example.test", self.mail.url, now=2000.0)
        sent_token = self.mail.received[0]["recovery_token"]

        completed = service.complete_recovery(self.conn, sent_token, now=2001.0)
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(completed["account_id"], "acct-1")
        self.assertEqual(completed["organization_id"], "ORG_A")
        self.assertEqual(completed["request_id"], result["request_id"])

        # single-use: the same token cannot complete a second recovery.
        with self.assertRaises(InvalidTokenError):
            service.complete_recovery(self.conn, sent_token, now=2002.0)

    def test_expired_token_is_rejected(self):
        service.start_recovery(self.conn, "ORG_A", "alice@example.test", self.mail.url, now=2000.0)
        sent_token = self.mail.received[0]["recovery_token"]
        past_expiry = 2000.0 + security.TOKEN_TTL_SECONDS + 1
        with self.assertRaises(InvalidTokenError):
            service.complete_recovery(self.conn, sent_token, now=past_expiry)

    def test_unknown_token_is_rejected(self):
        with self.assertRaises(InvalidTokenError):
            service.complete_recovery(self.conn, "not-a-real-token", now=2000.0)

    def test_token_binding_survives_a_later_email_change(self):
        service.start_recovery(self.conn, "ORG_A", "alice@example.test", self.mail.url, now=2000.0)
        sent_token = self.mail.received[0]["recovery_token"]

        # The account changes its email after the recovery token was issued.
        service.change_email(self.conn, "acct-1", "alice-new@example.test", now=2001.0)

        completed = service.complete_recovery(self.conn, sent_token, now=2002.0)
        self.assertEqual(completed["account_id"], "acct-1")

    def test_new_recovery_after_address_transfer_resolves_the_new_owner(self):
        service.create_account(self.conn, "ORG_A", "acct-2", "bob@example.test", now=1000.0)
        service.change_email(self.conn, "acct-1", "alice-new@example.test", now=1001.0)
        service.change_email(self.conn, "acct-2", "alice@example.test", now=1002.0)

        result = service.start_recovery(self.conn, "ORG_A", "alice@example.test", self.mail.url, now=2000.0)
        sent_token = self.mail.received[0]["recovery_token"]
        completed = service.complete_recovery(self.conn, sent_token, now=2001.0)

        self.assertEqual(completed["account_id"], "acct-2")
        self.assertEqual(self.mail.received[0]["recipient"], "alice@example.test")

    def test_delivery_recipient_tracks_current_email_not_the_lookup_address(self):
        service.start_recovery(self.conn, "ORG_A", "alice@example.test", self.mail.url, now=2000.0)
        self.assertEqual(self.mail.received[0]["recipient"], "alice@example.test")


if __name__ == "__main__":
    unittest.main()
