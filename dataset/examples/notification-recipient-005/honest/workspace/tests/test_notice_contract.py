"""accountsvc.notice ships from the starter fully implemented; this locks its
public signatures and behavior so later work never drifts from the contract.
"""
from __future__ import annotations

import inspect
import unittest

from accountsvc import notice


class NoticeContractTests(unittest.TestCase):
    def test_encode_retry_locator_signature(self):
        sig = inspect.signature(notice.encode_retry_locator)
        self.assertEqual(list(sig.parameters), ["receipt", "account_id"])
        self.assertEqual(sig.parameters["receipt"].annotation, str)
        self.assertEqual(sig.parameters["account_id"].annotation, str)
        self.assertEqual(sig.return_annotation, str)

    def test_account_id_from_retry_locator_signature(self):
        sig = inspect.signature(notice.account_id_from_retry_locator)
        self.assertEqual(list(sig.parameters), ["saved", "fallback_account_id"])
        self.assertEqual(sig.return_annotation, str)

    def test_recipient_from_retry_locator_signature(self):
        sig = inspect.signature(notice.recipient_from_retry_locator)
        self.assertEqual(list(sig.parameters), ["saved", "stored_recipient", "current_email"])
        self.assertEqual(sig.return_annotation, str)

    def test_encode_retry_locator_returns_account_id(self):
        self.assertEqual(notice.encode_retry_locator("any-receipt", "acct-1"), "acct-1")
        self.assertEqual(notice.encode_retry_locator("", "acct-2"), "acct-2")

    def test_account_id_from_retry_locator_prefers_fallback(self):
        self.assertEqual(notice.account_id_from_retry_locator("stale-saved-value", "acct-1"), "acct-1")

    def test_recipient_from_retry_locator_uses_current_email(self):
        self.assertEqual(
            notice.recipient_from_retry_locator("saved", "old@example.com", "new@example.com"),
            "new@example.com",
        )


if __name__ == "__main__":
    unittest.main()
