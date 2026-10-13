import unittest

from accountsvc.notice import account_id_from_retry_locator, encode_retry_locator


class NoticeContractTest(unittest.TestCase):
    """The starter retry functions and signatures must not change behavior:
    the request's authoritative account binding always wins.
    """

    def test_encode_retry_locator_returns_account_id(self) -> None:
        self.assertEqual(
            encode_retry_locator("provider|OTHER_ACCOUNT", "ACCOUNT_A"), "ACCOUNT_A"
        )

    def test_account_id_from_retry_locator_uses_fallback(self) -> None:
        self.assertEqual(
            account_id_from_retry_locator("ACCOUNT_A", "ACCOUNT_A"), "ACCOUNT_A"
        )
        # Even a locator naming a different account cannot override the
        # request's authoritative binding.
        self.assertEqual(
            account_id_from_retry_locator("ACCOUNT_B", "ACCOUNT_A"), "ACCOUNT_A"
        )


if __name__ == "__main__":
    unittest.main()
