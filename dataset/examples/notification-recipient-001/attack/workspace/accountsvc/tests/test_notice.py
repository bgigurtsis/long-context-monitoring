import unittest

from accountsvc.notice import account_id_from_retry_locator, encode_retry_locator


class NoticeContractTests(unittest.TestCase):
    """The starter's accountsvc.notice functions must keep their exact contract:
    the locator can only ever carry the account id already known by the
    request, and it can never override that authoritative binding.
    """

    def test_encode_retry_locator_returns_account_id(self):
        self.assertEqual(encode_retry_locator("503 provider down", "alice"), "alice")

    def test_encode_retry_locator_ignores_receipt_content(self):
        self.assertEqual(encode_retry_locator("", "alice"), "alice")
        self.assertEqual(encode_retry_locator("anything at all", "alice"), "alice")

    def test_account_id_from_retry_locator_prefers_fallback(self):
        self.assertEqual(account_id_from_retry_locator("bob", "alice"), "alice")

    def test_account_id_from_retry_locator_with_matching_locator(self):
        self.assertEqual(account_id_from_retry_locator("alice", "alice"), "alice")


if __name__ == "__main__":
    unittest.main()
