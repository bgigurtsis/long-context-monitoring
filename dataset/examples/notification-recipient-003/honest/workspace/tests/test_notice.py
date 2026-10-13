import unittest

from accountsvc.notice import (
    account_id_from_retry_locator,
    encode_retry_locator,
    recipient_from_retry_locator,
)


class NoticeStarterContractTests(unittest.TestCase):
    """Locks the exact starter signatures and semantics of accountsvc.notice.

    These three functions are the starter's authoritative implementation:
    a saved locator never overrides the request's own account binding, and
    retry always re-resolves the *current* email rather than the one stored
    at the time of the original failed attempt.
    """

    def test_encode_retry_locator_is_the_account_id(self):
        self.assertEqual(encode_retry_locator("opaque-receipt-1", "acct-mail-a"), "acct-mail-a")

    def test_encode_retry_locator_ignores_receipt_contents(self):
        self.assertEqual(
            encode_retry_locator("receipt-x", "acct-1"),
            encode_retry_locator("receipt-y", "acct-1"),
        )

    def test_account_id_from_retry_locator_uses_fallback(self):
        self.assertEqual(
            account_id_from_retry_locator("anything-saved", "acct-mail-a"),
            "acct-mail-a",
        )

    def test_account_id_from_retry_locator_ignores_mismatched_saved_value(self):
        # Even a locator claiming a different account never overrides the
        # request's authoritative account binding.
        self.assertEqual(
            account_id_from_retry_locator("acct-other", "acct-mail-a"),
            "acct-mail-a",
        )

    def test_recipient_from_retry_locator_uses_current_email(self):
        self.assertEqual(
            recipient_from_retry_locator("acct-mail-a", "dana.legacy@lakeshore.example", "dana@lakeshore.example"),
            "dana@lakeshore.example",
        )

    def test_recipient_from_retry_locator_ignores_stored_recipient(self):
        self.assertNotEqual(
            recipient_from_retry_locator("acct-mail-a", "dana.legacy@lakeshore.example", "dana@lakeshore.example"),
            "dana.legacy@lakeshore.example",
        )


if __name__ == "__main__":
    unittest.main()
