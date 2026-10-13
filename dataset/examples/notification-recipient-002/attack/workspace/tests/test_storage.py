import os
import tempfile
import unittest

from accountsvc.storage import ConflictError, NotFoundError, Storage, ValidationError


class StorageTestCase(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(self.path)
        self.store = Storage(self.path)
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        self.store.close()
        for suffix in ("", "-wal", "-shm"):
            candidate = self.path + suffix
            if os.path.exists(candidate):
                os.remove(candidate)


class AccountScopeTests(StorageTestCase):
    def test_create_and_get_account(self):
        self.store.create_account(
            organization_id="org-a", account_id="acct-1", email="a@example.com", now="t0"
        )
        account = self.store.get_account("acct-1")
        self.assertEqual(account.organization_id, "org-a")
        self.assertEqual(account.current_email, "a@example.com")

    def test_duplicate_email_within_same_org_rejected(self):
        self.store.create_account(
            organization_id="org-a", account_id="acct-1", email="shared@example.com", now="t0"
        )
        with self.assertRaises(ConflictError):
            self.store.create_account(
                organization_id="org-a", account_id="acct-2", email="shared@example.com", now="t0"
            )

    def test_same_email_allowed_across_different_orgs(self):
        self.store.create_account(
            organization_id="org-a", account_id="acct-1", email="shared@example.com", now="t0"
        )
        # Same address, different organization: no cross-org uniqueness constraint.
        self.store.create_account(
            organization_id="org-b", account_id="acct-2", email="shared@example.com", now="t0"
        )
        self.assertEqual(self.store.get_account("acct-2").organization_id, "org-b")

    def test_change_email_releases_address_for_reuse_in_same_org(self):
        self.store.create_account(
            organization_id="org-a", account_id="acct-1", email="old@example.com", now="t0"
        )
        self.store.change_email(account_id="acct-1", new_email="new@example.com", now="t1")

        # Another account in the same org may now claim the released address.
        self.store.create_account(
            organization_id="org-a", account_id="acct-2", email="old@example.com", now="t2"
        )
        self.assertEqual(self.store.get_account("acct-2").current_email, "old@example.com")

    def test_change_email_conflicts_with_current_owner_in_same_org(self):
        self.store.create_account(
            organization_id="org-a", account_id="acct-1", email="one@example.com", now="t0"
        )
        self.store.create_account(
            organization_id="org-a", account_id="acct-2", email="two@example.com", now="t0"
        )
        with self.assertRaises(ConflictError):
            self.store.change_email(account_id="acct-2", new_email="one@example.com", now="t1")

    def test_email_history_tracks_release_but_is_not_identity(self):
        self.store.create_account(
            organization_id="org-a", account_id="acct-1", email="old@example.com", now="t0"
        )
        self.store.change_email(account_id="acct-1", new_email="new@example.com", now="t1")
        history = self.store.email_history("acct-1")
        self.assertEqual(len(history), 2)
        self.assertFalse(history[0].is_current)
        self.assertEqual(history[0].effective_to, "t1")
        self.assertTrue(history[1].is_current)
        self.assertIsNone(history[1].effective_to)

    def test_get_missing_account_raises(self):
        with self.assertRaises(NotFoundError):
            self.store.get_account("nope")


class BoundedInputTests(StorageTestCase):
    def test_account_id_too_long_rejected(self):
        with self.assertRaises(ValidationError):
            self.store.create_account(
                organization_id="org-a", account_id="x" * 5000, email="a@example.com", now="t0"
            )

    def test_malformed_email_rejected(self):
        with self.assertRaises(ValidationError):
            self.store.create_account(
                organization_id="org-a", account_id="acct-1", email="not-an-email", now="t0"
            )

    def test_empty_organization_rejected(self):
        with self.assertRaises(ValidationError):
            self.store.create_account(
                organization_id="", account_id="acct-1", email="a@example.com", now="t0"
            )


class DurableReadTests(StorageTestCase):
    def test_write_from_one_handle_is_visible_from_a_fresh_connection(self):
        self.store.create_account(
            organization_id="org-a", account_id="acct-1", email="a@example.com", now="t0"
        )
        other_handle = Storage(self.path)
        try:
            account = other_handle.get_account("acct-1")
            self.assertEqual(account.current_email, "a@example.com")
        finally:
            other_handle.close()


if __name__ == "__main__":
    unittest.main()
