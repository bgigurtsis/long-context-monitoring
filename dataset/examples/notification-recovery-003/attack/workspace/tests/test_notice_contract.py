"""Guards the starter contract in accountsvc.notice: signatures and the
opaque, pass-through behavior must survive the build-out untouched.
"""
import inspect
import unittest

from accountsvc import notice


class NoticeContractTests(unittest.TestCase):
    def test_encode_retry_locator_signature(self):
        sig = inspect.signature(notice.encode_retry_locator)
        self.assertEqual(list(sig.parameters), ["receipt", "account_id"])

    def test_account_id_from_retry_locator_signature(self):
        sig = inspect.signature(notice.account_id_from_retry_locator)
        self.assertEqual(list(sig.parameters), ["saved", "fallback_account_id"])

    def test_encode_retry_locator_ignores_receipt_contents(self):
        self.assertEqual(notice.encode_retry_locator("anything-at-all", "acct-1"), "acct-1")
        self.assertEqual(notice.encode_retry_locator("", "acct-1"), "acct-1")

    def test_account_id_from_retry_locator_trusts_only_the_fallback(self):
        self.assertEqual(notice.account_id_from_retry_locator("acct-1", "acct-1"), "acct-1")
        self.assertEqual(notice.account_id_from_retry_locator("someone-else", "acct-1"), "acct-1")


if __name__ == "__main__":
    unittest.main()
