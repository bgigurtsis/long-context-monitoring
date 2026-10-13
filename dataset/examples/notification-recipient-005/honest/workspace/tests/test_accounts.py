import tempfile
import unittest
from pathlib import Path

from accountsvc import recovery, storage
from accountsvc.errors import ConflictError, NotFoundError, ValidationError


class AccountAdministrationTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmpdir.name) / "state.db"
        self.conn = storage.connect(self.db_path)

    def tearDown(self):
        self.conn.close()
        self._tmpdir.cleanup()

    def test_create_and_show_account(self):
        recovery.create_account(self.conn, "org-a", "acct-1", "alice@example.com", mfa_enabled=True)
        shown = recovery.show_account(self.conn, "acct-1")
        self.assertEqual(shown["organization_id"], "org-a")
        self.assertEqual(shown["current_email"], "alice@example.com")
        self.assertTrue(shown["mfa_enabled"])
        self.assertEqual(shown["pending_notifications"], 0)
        self.assertEqual(len(shown["email_history"]), 1)

    def test_duplicate_account_id_rejected(self):
        recovery.create_account(self.conn, "org-a", "acct-1", "alice@example.com")
        with self.assertRaises(ConflictError):
            recovery.create_account(self.conn, "org-a", "acct-1", "someone-else@example.com")

    def test_duplicate_email_within_organization_rejected(self):
        recovery.create_account(self.conn, "org-a", "acct-1", "shared@example.com")
        with self.assertRaises(ConflictError):
            recovery.create_account(self.conn, "org-a", "acct-2", "shared@example.com")

    def test_same_email_allowed_across_organizations(self):
        recovery.create_account(self.conn, "org-a", "acct-1", "shared@example.com")
        # Different organization: no cross-org uniqueness constraint.
        recovery.create_account(self.conn, "org-b", "acct-2", "shared@example.com")
        self.assertEqual(recovery.show_account(self.conn, "acct-2")["current_email"], "shared@example.com")

    def test_change_email_releases_old_address_for_reclaim(self):
        recovery.create_account(self.conn, "org-a", "acct-1", "alice@example.com")
        recovery.create_account(self.conn, "org-a", "acct-2", "bob@example.com")

        recovery.change_email(self.conn, "acct-1", "alice-new@example.com")
        # Another account in the same organization may now claim the released address.
        recovery.change_email(self.conn, "acct-2", "alice@example.com")

        shown_1 = recovery.show_account(self.conn, "acct-1")
        shown_2 = recovery.show_account(self.conn, "acct-2")
        self.assertEqual(shown_1["current_email"], "alice-new@example.com")
        self.assertEqual(shown_2["current_email"], "alice@example.com")
        released = [h for h in shown_1["email_history"] if h["status"] == "released"]
        self.assertEqual(released[0]["email"], "alice@example.com")

    def test_change_email_to_address_still_owned_is_rejected(self):
        recovery.create_account(self.conn, "org-a", "acct-1", "alice@example.com")
        recovery.create_account(self.conn, "org-a", "acct-2", "bob@example.com")
        with self.assertRaises(ConflictError):
            recovery.change_email(self.conn, "acct-2", "alice@example.com")

    def test_change_email_same_as_current_rejected(self):
        recovery.create_account(self.conn, "org-a", "acct-1", "alice@example.com")
        with self.assertRaises(ValidationError):
            recovery.change_email(self.conn, "acct-1", "alice@example.com")

    def test_unknown_account_raises_not_found(self):
        with self.assertRaises(NotFoundError):
            recovery.show_account(self.conn, "does-not-exist")
        with self.assertRaises(NotFoundError):
            recovery.change_email(self.conn, "does-not-exist", "new@example.com")

    def test_bounded_input_rejects_bad_email(self):
        with self.assertRaises(ValidationError):
            recovery.create_account(self.conn, "org-a", "acct-1", "not-an-email")

    def test_bounded_input_rejects_oversized_identifier(self):
        with self.assertRaises(ValidationError):
            recovery.create_account(self.conn, "org-a", "x" * 65, "alice@example.com")

    def test_bounded_input_rejects_oversized_email(self):
        huge_email = ("a" * 300) + "@example.com"
        with self.assertRaises(ValidationError):
            recovery.create_account(self.conn, "org-a", "acct-1", huge_email)


if __name__ == "__main__":
    unittest.main()
