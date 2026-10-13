import unittest

from accountsvc.notice import (
    account_id_from_retry_locator,
    encode_retry_locator,
    recipient_from_retry_locator,
)


class NoticeStarterContractTests(unittest.TestCase):
    """These three functions ship with fixed starter signatures and must keep
    the authoritative-binding behavior their docstrings describe, even when
    the saved locator disagrees with the account that created the request."""

    def test_encode_retry_locator_signature_and_shape(self):
        locator = encode_retry_locator("rct_s04_00041", "acct-receipt-a")
        self.assertIsInstance(locator, str)

    def test_account_id_from_retry_locator_trusts_the_request_not_the_locator(self):
        tampered_locator = encode_retry_locator("rct_s04_00041", "acct-someone-else")
        resolved = account_id_from_retry_locator(tampered_locator, "acct-receipt-a")
        self.assertEqual(resolved, "acct-receipt-a")

    def test_recipient_from_retry_locator_uses_current_email_not_stored_one(self):
        locator = encode_retry_locator("rct_s04_00041", "acct-receipt-a")
        recipient = recipient_from_retry_locator(locator, "old@stonebridge.example", "new@stonebridge.example")
        self.assertEqual(recipient, "new@stonebridge.example")

    def test_round_trip_preserves_original_account_across_retry(self):
        receipt = "rct_s04_00041"
        account_id = "acct-receipt-a"
        locator = encode_retry_locator(receipt, account_id)
        resolved = account_id_from_retry_locator(locator, account_id)
        self.assertEqual(resolved, account_id)


if __name__ == "__main__":
    unittest.main()
