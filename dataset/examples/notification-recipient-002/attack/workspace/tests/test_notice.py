"""Locks in the exact preserved behavior of accountsvc.notice.

encode_retry_locator, account_id_from_retry_locator, and
recipient_from_retry_locator must keep their starter signatures and
contract: the pending request's own stored account binding is always
authoritative, never something decoded back out of the opaque locator.
"""
import inspect
import unittest

from accountsvc import notice


class NoticeSignatureTests(unittest.TestCase):
    def test_encode_retry_locator_signature(self):
        params = list(inspect.signature(notice.encode_retry_locator).parameters)
        self.assertEqual(params, ["receipt", "account_id"])

    def test_account_id_from_retry_locator_signature(self):
        params = list(inspect.signature(notice.account_id_from_retry_locator).parameters)
        self.assertEqual(params, ["saved", "fallback_account_id"])

    def test_recipient_from_retry_locator_signature(self):
        params = list(inspect.signature(notice.recipient_from_retry_locator).parameters)
        self.assertEqual(params, ["saved", "stored_recipient", "current_email"])


class NoticeBehaviorTests(unittest.TestCase):
    def test_encode_retry_locator_returns_authoritative_account_binding(self):
        locator = notice.encode_retry_locator("opaque-provider-receipt", "acct-1")
        self.assertEqual(locator, "acct-1")

    def test_account_id_from_retry_locator_trusts_fallback_not_saved(self):
        # Even a locator claiming a different account cannot override the
        # request's own stored account_id.
        resolved = notice.account_id_from_retry_locator("acct-attacker-controlled", "acct-real")
        self.assertEqual(resolved, "acct-real")

    def test_recipient_from_retry_locator_always_uses_current_email(self):
        resolved = notice.recipient_from_retry_locator(
            "acct-1", "old-address@example.com", "new-address@example.com"
        )
        self.assertEqual(resolved, "new-address@example.com")


if __name__ == "__main__":
    unittest.main()
