import unittest

from accountsvc import db, service
from accountsvc.errors import ConflictError, NotFoundError


class AccountTests(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect(":memory:")

    def tearDown(self):
        self.conn.close()

    def test_create_and_show_account(self):
        result = service.create_account(self.conn, "ORG_A", "acct-1", "alice@example.test", now=1000.0)
        self.assertEqual(result["account_id"], "acct-1")
        self.assertEqual(result["organization_id"], "ORG_A")
        self.assertEqual(result["current_email"], "alice@example.test")
        self.assertFalse(result["mfa_enrolled"])
        self.assertEqual(len(result["email_history"]), 1)

    def test_duplicate_account_id_conflicts(self):
        service.create_account(self.conn, "ORG_A", "acct-1", "alice@example.test", now=1000.0)
        with self.assertRaises(ConflictError):
            service.create_account(self.conn, "ORG_A", "acct-1", "someone-else@example.test", now=1001.0)

    def test_email_uniqueness_within_organization(self):
        service.create_account(self.conn, "ORG_A", "acct-1", "alice@example.test", now=1000.0)
        with self.assertRaises(ConflictError):
            service.create_account(self.conn, "ORG_A", "acct-2", "alice@example.test", now=1001.0)

    def test_email_uniqueness_is_scoped_per_organization(self):
        service.create_account(self.conn, "ORG_A", "acct-1", "alice@example.test", now=1000.0)
        # Same address, different organization: allowed.
        result = service.create_account(self.conn, "ORG_B", "acct-2", "alice@example.test", now=1001.0)
        self.assertEqual(result["current_email"], "alice@example.test")

    def test_change_email_rejects_address_owned_by_another_account(self):
        service.create_account(self.conn, "ORG_A", "acct-1", "alice@example.test", now=1000.0)
        service.create_account(self.conn, "ORG_A", "acct-2", "bob@example.test", now=1000.0)
        with self.assertRaises(ConflictError):
            service.change_email(self.conn, "acct-2", "alice@example.test", now=1001.0)

    def test_released_address_can_transfer_to_another_account(self):
        service.create_account(self.conn, "ORG_A", "acct-1", "alice@example.test", now=1000.0)
        service.create_account(self.conn, "ORG_A", "acct-2", "bob@example.test", now=1000.0)

        service.change_email(self.conn, "acct-1", "alice-new@example.test", now=1001.0)
        result = service.change_email(self.conn, "acct-2", "alice@example.test", now=1002.0)

        self.assertEqual(result["current_email"], "alice@example.test")
        released_entry = [h for h in result["email_history"] if h["email"] == "bob@example.test"][0]
        self.assertIsNotNone(released_entry["released_at"])

    def test_show_unknown_account_raises_not_found(self):
        with self.assertRaises(NotFoundError):
            service.show_account(self.conn, "does-not-exist")

    def test_change_email_to_current_value_is_a_noop(self):
        service.create_account(self.conn, "ORG_A", "acct-1", "alice@example.test", now=1000.0)
        result = service.change_email(self.conn, "acct-1", "alice@example.test", now=1001.0)
        self.assertEqual(len(result["email_history"]), 1)


if __name__ == "__main__":
    unittest.main()
