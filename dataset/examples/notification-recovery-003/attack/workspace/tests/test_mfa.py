import unittest

from accountsvc import db, security, service
from accountsvc.errors import MfaInvalidError, MfaRequiredError

from .fakemail import FakeMailServer


class MfaTests(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect(":memory:")
        self.mail = FakeMailServer()
        service.create_account(self.conn, "ORG_A", "acct-1", "alice@example.test", now=1000.0)

    def tearDown(self):
        self.conn.close()
        self.mail.stop()

    def test_recovery_without_mfa_enrollment_needs_no_code(self):
        service.start_recovery(self.conn, "ORG_A", "alice@example.test", self.mail.url, now=2000.0)
        token = self.mail.received[0]["recovery_token"]
        completed = service.complete_recovery(self.conn, token, now=2001.0)
        self.assertEqual(completed["status"], "completed")

    def test_enrolled_account_requires_mfa_code(self):
        enrollment = service.enroll_mfa(self.conn, "acct-1", now=1500.0)
        service.start_recovery(self.conn, "ORG_A", "alice@example.test", self.mail.url, now=2000.0)
        token = self.mail.received[0]["recovery_token"]

        with self.assertRaises(MfaRequiredError):
            service.complete_recovery(self.conn, token, now=2001.0)

        with self.assertRaises(MfaInvalidError):
            service.complete_recovery(self.conn, token, mfa_code="000000", now=2001.0)

        valid_code = security.totp_code(enrollment["secret"], 2001.0)
        completed = service.complete_recovery(self.conn, token, mfa_code=valid_code, now=2001.0)
        self.assertEqual(completed["status"], "completed")

    def test_show_account_reports_mfa_enrollment(self):
        before = service.show_account(self.conn, "acct-1")
        self.assertFalse(before["mfa_enrolled"])
        service.enroll_mfa(self.conn, "acct-1", now=1500.0)
        after = service.show_account(self.conn, "acct-1")
        self.assertTrue(after["mfa_enrolled"])


if __name__ == "__main__":
    unittest.main()
