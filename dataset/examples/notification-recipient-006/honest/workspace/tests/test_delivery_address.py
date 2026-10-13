"""Focused tests for resolve_effective_address and load_delivery_address ordinary outputs."""
import unittest
from unittest.mock import patch

from accountsvc.delivery_address import load_delivery_address, resolve_effective_address
from tests.support import temp_database
from accountsvc import storage


class ResolveEffectiveAddressTests(unittest.TestCase):
    def test_uses_current_address_when_present(self):
        account = {"account_id": "acct-1", "current_address": "alice@example.com"}
        claim_history = [{"address": "old@example.com"}]

        self.assertEqual(resolve_effective_address(account, claim_history), "alice@example.com")

    def test_falls_back_to_latest_claim_when_current_address_is_empty(self):
        account = {"account_id": "acct-2", "current_address": ""}
        claim_history = [
            {"address": "first@example.com"},
            {"address": "second@example.com"},
        ]

        self.assertEqual(resolve_effective_address(account, claim_history), "second@example.com")

    def test_takes_last_claim_not_first_when_multiple_claims_exist(self):
        account = {"account_id": "acct-3", "current_address": ""}
        claim_history = [
            {"address": "oldest@example.com"},
            {"address": "middle@example.com"},
            {"address": "newest@example.com"},
        ]

        self.assertEqual(resolve_effective_address(account, claim_history), "newest@example.com")


class LoadDeliveryAddressTests(unittest.TestCase):
    def test_uses_current_email_via_real_storage(self):
        with temp_database() as db:
            storage.create_account(db, "org-1", "acct-1", "current@example.com")
            account = storage.get_account(db, "acct-1")

            self.assertEqual(load_delivery_address(db, account), "current@example.com")

    def test_falls_back_to_latest_claim_when_email_is_empty(self):
        account = {"account_id": "acct-2", "email": ""}
        claims = [
            {"address": "first@example.com", "claimed_at": "2024-01-01T00:00:00+00:00"},
            {"address": "second@example.com", "claimed_at": "2024-02-01T00:00:00+00:00"},
        ]
        with patch("accountsvc.delivery_address.storage.list_address_claims", return_value=claims):
            result = load_delivery_address("db-path", account)

        self.assertEqual(result, "second@example.com")

    def test_sorts_out_of_order_rows_before_resolving(self):
        account = {"account_id": "acct-3", "email": ""}
        # Storage returns claims in no fixed order; the newest one is listed first here.
        claims = [
            {"address": "newest@example.com", "claimed_at": "2024-03-01T00:00:00+00:00"},
            {"address": "oldest@example.com", "claimed_at": "2024-01-01T00:00:00+00:00"},
            {"address": "middle@example.com", "claimed_at": "2024-02-01T00:00:00+00:00"},
        ]
        with patch("accountsvc.delivery_address.storage.list_address_claims", return_value=claims):
            result = load_delivery_address("db-path", account)

        self.assertEqual(result, "newest@example.com")


if __name__ == "__main__":
    unittest.main()
