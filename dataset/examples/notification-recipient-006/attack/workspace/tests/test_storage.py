import unittest

from accountsvc import storage
from tests.support import temp_database


class AccountStorageTests(unittest.TestCase):
    def test_create_and_show_account(self):
        with temp_database() as db:
            storage.create_account(db, "org-1", "acct-1", "a@example.com")
            account = storage.get_account(db, "acct-1")
            self.assertEqual(account["org_id"], "org-1")
            self.assertEqual(account["email"], "a@example.com")

    def test_duplicate_account_id_rejected(self):
        with temp_database() as db:
            storage.create_account(db, "org-1", "acct-1", "a@example.com")
            with self.assertRaises(storage.AccountExistsError):
                storage.create_account(db, "org-1", "acct-1", "b@example.com")

    def test_duplicate_email_in_org_rejected(self):
        with temp_database() as db:
            storage.create_account(db, "org-1", "acct-1", "a@example.com")
            with self.assertRaises(storage.EmailInUseError):
                storage.create_account(db, "org-1", "acct-2", "a@example.com")

    def test_same_email_allowed_across_orgs(self):
        with temp_database() as db:
            storage.create_account(db, "org-1", "acct-1", "a@example.com")
            storage.create_account(db, "org-2", "acct-2", "a@example.com")
            self.assertIsNotNone(storage.find_account_by_email(db, "org-2", "a@example.com"))

    def test_change_email_releases_old_address(self):
        with temp_database() as db:
            storage.create_account(db, "org-1", "acct-1", "old@example.com")
            storage.create_account(db, "org-1", "acct-2", "other@example.com")

            storage.change_email(db, "acct-1", "new@example.com")

            self.assertIsNone(storage.find_account_by_email(db, "org-1", "old@example.com"))
            self.assertIsNotNone(storage.find_account_by_email(db, "org-1", "new@example.com"))

            # Another account may now claim the released address.
            storage.change_email(db, "acct-2", "old@example.com")
            reclaimed = storage.find_account_by_email(db, "org-1", "old@example.com")
            self.assertEqual(reclaimed["account_id"], "acct-2")

    def test_change_email_conflict_raises(self):
        with temp_database() as db:
            storage.create_account(db, "org-1", "acct-1", "a@example.com")
            storage.create_account(db, "org-1", "acct-2", "b@example.com")
            with self.assertRaises(storage.EmailInUseError):
                storage.change_email(db, "acct-2", "a@example.com")

    def test_change_email_unknown_account_raises(self):
        with temp_database() as db:
            with self.assertRaises(storage.AccountNotFoundError):
                storage.change_email(db, "missing", "a@example.com")

    def test_create_account_records_initial_address_claim(self):
        with temp_database() as db:
            storage.create_account(db, "org-1", "acct-1", "a@example.com")

            claims = storage.list_address_claims(db, "acct-1")
            self.assertEqual(len(claims), 1)
            self.assertEqual(claims[0]["address"], "a@example.com")
            self.assertTrue(claims[0]["claimed_at"])

    def test_change_email_appends_a_new_claim(self):
        with temp_database() as db:
            storage.create_account(db, "org-1", "acct-1", "old@example.com")
            storage.change_email(db, "acct-1", "new@example.com")

            claims = storage.list_address_claims(db, "acct-1")
            self.assertEqual([c["address"] for c in claims], ["old@example.com", "new@example.com"])


if __name__ == "__main__":
    unittest.main()
