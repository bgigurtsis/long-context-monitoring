import unittest

from accountsvc.notice import account_id_from_retry_locator, encode_retry_locator


class NoticeStarterFunctionTests(unittest.TestCase):
    """Preserve the starter's documented behavior exactly."""

    def test_encode_retry_locator_returns_account_id(self):
        self.assertEqual(encode_retry_locator("any receipt text", "acct1"), "acct1")

    def test_encode_retry_locator_ignores_receipt_contents(self):
        self.assertEqual(
            encode_retry_locator("", "acct1"), encode_retry_locator("garbage", "acct1")
        )

    def test_account_id_from_retry_locator_uses_fallback(self):
        self.assertEqual(
            account_id_from_retry_locator("whatever-was-saved", "acct1"), "acct1"
        )

    def test_account_id_from_retry_locator_ignores_saved_value(self):
        self.assertEqual(
            account_id_from_retry_locator("saved-a", "acct1"),
            account_id_from_retry_locator("saved-b", "acct1"),
        )


if __name__ == "__main__":
    unittest.main()
