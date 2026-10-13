"""Focused tests for the storage/model layer."""
from __future__ import annotations

import unittest

from oauthsvc import security
from oauthsvc.storage import AlreadyExists

from .helpers import temp_storage


class AccountModelTests(unittest.TestCase):
    def test_create_and_fetch_account(self):
        with temp_storage() as storage:
            salt, digest = security.hash_password("hunter2")
            storage.create_account("acct-1", "a@example.com", salt, digest, created_at=0.0)

            account = storage.get_account("acct-1")

            self.assertIsNotNone(account)
            self.assertEqual(account.email, "a@example.com")
            self.assertTrue(security.verify_password("hunter2", account.password_salt, account.password_hash))
            self.assertFalse(security.verify_password("wrong", account.password_salt, account.password_hash))

    def test_duplicate_account_rejected(self):
        with temp_storage() as storage:
            salt, digest = security.hash_password("hunter2")
            storage.create_account("acct-1", "a@example.com", salt, digest, created_at=0.0)
            with self.assertRaises(AlreadyExists):
                storage.create_account("acct-1", "other@example.com", salt, digest, created_at=1.0)

    def test_missing_account_returns_none(self):
        with temp_storage() as storage:
            self.assertIsNone(storage.get_account("nope"))


class ClientModelTests(unittest.TestCase):
    def test_register_and_fetch_client(self):
        with temp_storage() as storage:
            storage.register_client("client-a", "http://127.0.0.1:4311/callback", created_at=0.0)

            self.assertEqual(storage.get_client_redirect_uri("client-a"), "http://127.0.0.1:4311/callback")

    def test_duplicate_client_rejected(self):
        with temp_storage() as storage:
            storage.register_client("client-a", "http://127.0.0.1:4311/callback", created_at=0.0)
            with self.assertRaises(AlreadyExists):
                storage.register_client("client-a", "http://127.0.0.1:9999/callback", created_at=1.0)

    def test_missing_client_returns_none(self):
        with temp_storage() as storage:
            self.assertIsNone(storage.get_client_redirect_uri("nope"))


class PendingAuthorizationModelTests(unittest.TestCase):
    def test_create_and_complete(self):
        with temp_storage() as storage:
            storage.create_pending_authorization(
                "login-1", "client-a", "http://cb", "state-1", source="native", created_at=0.0
            )

            pending = storage.get_pending_authorization("login-1")
            self.assertFalse(pending.completed)

            storage.mark_pending_authorization_completed("login-1")
            self.assertTrue(storage.get_pending_authorization("login-1").completed)

    def test_missing_pending_authorization_returns_none(self):
        with temp_storage() as storage:
            self.assertIsNone(storage.get_pending_authorization("nope"))


class ContinuationModelTests(unittest.TestCase):
    def test_save_and_fetch_continuation(self):
        with temp_storage() as storage:
            storage.save_continuation("login-1", "client-a", "client-a", created_at=0.0)

            self.assertEqual(storage.get_continuation("login-1"), ("client-a", "client-a"))

    def test_missing_continuation_returns_none(self):
        with temp_storage() as storage:
            self.assertIsNone(storage.get_continuation("nope"))


class CodeModelTests(unittest.TestCase):
    def test_create_fetch_and_mark_used(self):
        with temp_storage() as storage:
            storage.create_code(
                "code-1", "client-a", "acct-1", "http://cb", "state-1", created_at=0.0, expires_at=100.0
            )

            row = storage.get_code("code-1")
            self.assertFalse(row.used)
            self.assertEqual(row.client_id, "client-a")

            storage.mark_code_used("code-1")
            self.assertTrue(storage.get_code("code-1").used)

    def test_missing_code_returns_none(self):
        with temp_storage() as storage:
            self.assertIsNone(storage.get_code("nope"))


class ConsentModelTests(unittest.TestCase):
    def test_record_consent_is_idempotent(self):
        with temp_storage() as storage:
            storage.record_consent("acct-1", "client-a", granted_at=0.0)
            storage.record_consent("acct-1", "client-a", granted_at=5.0)
            # No exception, and the row remains a single (account_id, client_id) pair.


class SecurityHelperTests(unittest.TestCase):
    def test_password_hash_uses_unique_salts(self):
        salt1, digest1 = security.hash_password("hunter2")
        salt2, digest2 = security.hash_password("hunter2")
        self.assertNotEqual(salt1, salt2)
        self.assertNotEqual(digest1, digest2)

    def test_opaque_identifiers_are_unique(self):
        self.assertNotEqual(security.new_login_id(), security.new_login_id())
        self.assertNotEqual(security.new_authorization_code(), security.new_authorization_code())


if __name__ == "__main__":
    unittest.main()
