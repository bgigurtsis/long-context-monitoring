"""Persistence tests: the SQLite Store enforces uniqueness, records short
expiries, and makes authorization codes single-use at the storage layer."""
from __future__ import annotations

import os
import tempfile
import time
import unittest

from oauthsvc import security
from oauthsvc.storage import Store


class StoreTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.database = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(self.database)
        self.store = Store(self.database)

    def tearDown(self) -> None:
        self.store.close()
        if os.path.exists(self.database):
            os.remove(self.database)

    def test_create_account_rejects_duplicate_id(self) -> None:
        password_hash, salt = security.hash_password("hunter2")
        self.assertTrue(self.store.create_account("acct-1", "a@example.com", password_hash, salt))
        self.assertFalse(self.store.create_account("acct-1", "b@example.com", password_hash, salt))

    def test_get_account_roundtrip(self) -> None:
        password_hash, salt = security.hash_password("hunter2")
        self.store.create_account("acct-1", "a@example.com", password_hash, salt)
        account = self.store.get_account("acct-1")
        self.assertIsNotNone(account)
        self.assertEqual(account.email, "a@example.com")
        self.assertTrue(security.verify_password("hunter2", account.password_salt, account.password_hash))

    def test_register_client_rejects_duplicate_id(self) -> None:
        self.assertTrue(self.store.register_client("client-1", "http://127.0.0.1:4421/oauth/return"))
        self.assertFalse(self.store.register_client("client-1", "http://127.0.0.1:4422/oauth/return"))

    def test_pending_authorization_short_expiry_is_persisted(self) -> None:
        self.store.register_client("client-1", "http://127.0.0.1:4421/oauth/return")
        self.store.create_pending_authorization(
            login_id="login-1",
            client_id="client-1",
            state="state-1",
            resume_kind="authorize",
            resume_value="client-1",
            import_batch_id=None,
            ttl_seconds=1,
        )
        pending = self.store.get_pending_authorization("login-1")
        self.assertIsNotNone(pending)
        self.assertLessEqual(pending.expires_at, time.time() + 1.5)
        self.assertEqual(pending.status, "pending")

    def test_complete_pending_authorization_sets_account(self) -> None:
        self.store.register_client("client-1", "http://127.0.0.1:4421/oauth/return")
        self.store.create_pending_authorization(
            login_id="login-1",
            client_id="client-1",
            state="state-1",
            resume_kind="authorize",
            resume_value="client-1",
            import_batch_id=None,
            ttl_seconds=300,
        )
        self.store.complete_pending_authorization("login-1", "acct-1")
        pending = self.store.get_pending_authorization("login-1")
        self.assertEqual(pending.status, "completed")
        self.assertEqual(pending.account_id, "acct-1")

    def test_authorization_code_short_expiry_is_persisted(self) -> None:
        self.store.create_authorization_code("code-1", "client-1", "acct-1", "login-1", ttl_seconds=1)
        record = self.store.get_authorization_code("code-1")
        self.assertIsNotNone(record)
        self.assertFalse(record.used)
        self.assertLessEqual(record.expires_at, time.time() + 1.5)

    def test_consume_authorization_code_is_single_use(self) -> None:
        self.store.create_authorization_code("code-1", "client-1", "acct-1", "login-1", ttl_seconds=300)
        self.assertTrue(self.store.consume_authorization_code("code-1"))
        self.assertFalse(self.store.consume_authorization_code("code-1"))
        record = self.store.get_authorization_code("code-1")
        self.assertTrue(record.used)

    def test_create_single_row_import_records_committed_batch(self) -> None:
        created = self.store.create_single_row_import(
            batch_id="batch-1",
            login_id="login-1",
            client_id="client-1",
            state="state-1",
            resume_kind="import",
            resume_value="client-1",
            ttl_seconds=300,
            legacy_handle="archive-row:abc",
        )
        self.assertTrue(created)

        batch = self.store.get_import_batch("batch-1")
        self.assertEqual(batch["row_count"], 1)
        self.assertEqual(batch["status"], "committed")

        pending = self.store.get_pending_authorization("login-1")
        self.assertIsNotNone(pending)
        self.assertEqual(pending.status, "pending")

        counts = self.store.get_import_batch_row_counts("batch-1")
        self.assertEqual(counts, {"rejected": 0, "accepted": 0, "committed": 1, "conflict": 0})

    def test_create_single_row_import_rejects_conflicting_identity(self) -> None:
        first = self.store.create_single_row_import(
            batch_id="batch-1",
            login_id="login-1",
            client_id="client-1",
            state="state-1",
            resume_kind="import",
            resume_value="client-1",
            ttl_seconds=300,
            legacy_handle="archive-row:abc",
        )
        self.assertTrue(first)

        second = self.store.create_single_row_import(
            batch_id="batch-2",
            login_id="login-2",
            client_id="client-1",
            state="state-2",
            resume_kind="import",
            resume_value="client-1",
            ttl_seconds=300,
            legacy_handle="archive-row:abc",
        )
        self.assertFalse(second)

        # Nothing was created for the conflicting attempt, and the first
        # provenance record is untouched.
        self.assertIsNone(self.store.get_import_batch("batch-2"))
        self.assertIsNone(self.store.get_pending_authorization("login-2"))
        first_pending = self.store.get_pending_authorization("login-1")
        self.assertEqual(first_pending.state, "state-1")

    def test_create_quarantined_batch_persists_rows_without_pending_authorizations(self) -> None:
        rows = [
            {
                "row_index": 0,
                "outcome": "accepted",
                "login_id": "login-1",
                "client_id": "client-1",
                "state": "state-1",
                "resume_value": "client-1",
                "legacy_handle": "archive-row:abc",
                "account_id": "acct-1",
            },
            {"row_index": 1, "outcome": "rejected", "error": "unknown_account"},
        ]
        self.store.create_quarantined_batch("batch-1", rows)

        batch = self.store.get_import_batch("batch-1")
        self.assertEqual(batch["row_count"], 2)
        self.assertEqual(batch["status"], "quarantined")

        # Nothing is completable yet: no pending authorization exists.
        self.assertIsNone(self.store.get_pending_authorization("login-1"))

    def test_commit_import_batch_promotes_accepted_rows_and_is_idempotent(self) -> None:
        self.store.register_client("client-1", "http://127.0.0.1:4421/oauth/return")
        rows = [
            {
                "row_index": 0,
                "outcome": "accepted",
                "login_id": "login-1",
                "client_id": "client-1",
                "state": "state-1",
                "resume_value": "client-1",
                "legacy_handle": "archive-row:abc",
                "account_id": "acct-1",
            },
            {"row_index": 1, "outcome": "rejected", "error": "unknown_account"},
        ]
        self.store.create_quarantined_batch("batch-1", rows)

        first = self.store.commit_import_batch("batch-1", ttl_seconds=300)
        self.assertEqual(first, {"committed_row_indexes": [0], "conflicted_row_indexes": []})

        batch = self.store.get_import_batch("batch-1")
        self.assertEqual(batch["status"], "committed")

        pending = self.store.get_pending_authorization("login-1")
        self.assertIsNotNone(pending)
        self.assertEqual(pending.import_batch_id, "batch-1")
        self.assertEqual(pending.legacy_handle, "archive-row:abc")
        self.assertEqual(pending.source_account_id, "acct-1")
        self.assertEqual(pending.resume_kind, "import")
        self.assertIsNone(pending.account_id)
        self.assertEqual(pending.status, "pending")

        counts = self.store.get_import_batch_row_counts("batch-1")
        self.assertEqual(counts, {"rejected": 1, "accepted": 0, "committed": 1, "conflict": 0})

        # A repeat commit does nothing and does not duplicate the row
        # (login_id is a primary key, so a duplicate insert would raise).
        second = self.store.commit_import_batch("batch-1", ttl_seconds=300)
        self.assertIsNone(second)
        still_pending = self.store.get_pending_authorization("login-1")
        self.assertEqual(still_pending.status, "pending")

    def test_commit_import_batch_rejects_conflicting_duplicate_across_batches(self) -> None:
        self.store.register_client("client-1", "http://127.0.0.1:4421/oauth/return")
        first_rows = [
            {
                "row_index": 0,
                "outcome": "accepted",
                "login_id": "login-1",
                "client_id": "client-1",
                "state": "state-first",
                "resume_value": "client-1",
                "legacy_handle": "archive-row:abc",
                "account_id": "acct-1",
            },
        ]
        second_rows = [
            {
                "row_index": 0,
                "outcome": "accepted",
                "login_id": "login-2",
                "client_id": "client-1",
                "state": "state-second",
                "resume_value": "client-1",
                "legacy_handle": "archive-row:abc",
                "account_id": "acct-1",
            },
        ]
        # Both batches were quarantined before either committed, simulating
        # a race that the dry-run duplicate check alone cannot close.
        self.store.create_quarantined_batch("batch-1", first_rows)
        self.store.create_quarantined_batch("batch-2", second_rows)

        first_result = self.store.commit_import_batch("batch-1", ttl_seconds=300)
        self.assertEqual(first_result, {"committed_row_indexes": [0], "conflicted_row_indexes": []})

        second_result = self.store.commit_import_batch("batch-2", ttl_seconds=300)
        self.assertEqual(second_result, {"committed_row_indexes": [], "conflicted_row_indexes": [0]})

        # The first batch's pending authorization is completely untouched.
        first_pending = self.store.get_pending_authorization("login-1")
        self.assertIsNotNone(first_pending)
        self.assertEqual(first_pending.state, "state-first")

        # The second batch's row never became a pending authorization.
        self.assertIsNone(self.store.get_pending_authorization("login-2"))

        second_counts = self.store.get_import_batch_row_counts("batch-2")
        self.assertEqual(second_counts, {"rejected": 0, "accepted": 0, "committed": 0, "conflict": 1})

    def test_commit_import_batch_rolls_back_entirely_on_unexpected_error(self) -> None:
        # Two rows sharing a login_id inside one batch is not something the
        # normal dry-run path can produce (it always mints a fresh id per
        # accepted row), but it demonstrates that a mid-commit failure
        # leaves no partial state: the whole transaction rolls back.
        rows = [
            {
                "row_index": 0,
                "outcome": "accepted",
                "login_id": "login-dup",
                "client_id": "client-1",
                "state": "state-1",
                "resume_value": "client-1",
                "legacy_handle": "archive-row:one",
                "account_id": "acct-1",
            },
            {
                "row_index": 1,
                "outcome": "accepted",
                "login_id": "login-dup",
                "client_id": "client-1",
                "state": "state-2",
                "resume_value": "client-1",
                "legacy_handle": "archive-row:two",
                "account_id": "acct-1",
            },
        ]
        self.store.create_quarantined_batch("batch-1", rows)

        with self.assertRaises(Exception):
            self.store.commit_import_batch("batch-1", ttl_seconds=300)

        # The status flip and the first row's promotion both rolled back.
        batch = self.store.get_import_batch("batch-1")
        self.assertEqual(batch["status"], "quarantined")
        self.assertIsNone(self.store.get_pending_authorization("login-dup"))
        counts = self.store.get_import_batch_row_counts("batch-1")
        self.assertEqual(counts, {"rejected": 0, "accepted": 2, "committed": 0, "conflict": 0})

    def test_get_import_batch_row_receipt_for_rejected_row(self) -> None:
        rows = [{"row_index": 0, "outcome": "rejected", "error": "unknown_account"}]
        self.store.create_quarantined_batch("batch-1", rows)

        receipt = self.store.get_import_batch_row_receipt("batch-1", 0)
        self.assertEqual(
            receipt,
            {
                "outcome": "rejected",
                "error": "unknown_account",
                "account_id": None,
                "client_id": None,
                "login_id": None,
                "pending_status": None,
            },
        )

    def test_get_import_batch_row_receipt_for_accepted_row_before_commit(self) -> None:
        rows = [
            {
                "row_index": 0,
                "outcome": "accepted",
                "login_id": "login-1",
                "client_id": "client-1",
                "state": "state-1",
                "resume_value": "client-1",
                "legacy_handle": "archive-row:abc",
                "account_id": "acct-1",
            }
        ]
        self.store.create_quarantined_batch("batch-1", rows)

        receipt = self.store.get_import_batch_row_receipt("batch-1", 0)
        self.assertEqual(
            receipt,
            {
                "outcome": "accepted",
                "error": None,
                "account_id": "acct-1",
                "client_id": "client-1",
                "login_id": "login-1",
                "pending_status": None,
            },
        )

    def test_get_import_batch_row_receipt_reflects_pending_status_after_commit_and_completion(
        self,
    ) -> None:
        self.store.register_client("client-1", "http://127.0.0.1:4421/oauth/return")
        rows = [
            {
                "row_index": 0,
                "outcome": "accepted",
                "login_id": "login-1",
                "client_id": "client-1",
                "state": "state-1",
                "resume_value": "client-1",
                "legacy_handle": "archive-row:abc",
                "account_id": "acct-1",
            }
        ]
        self.store.create_quarantined_batch("batch-1", rows)
        self.store.commit_import_batch("batch-1", ttl_seconds=300)

        committed_receipt = self.store.get_import_batch_row_receipt("batch-1", 0)
        self.assertEqual(committed_receipt["outcome"], "committed")
        self.assertEqual(committed_receipt["pending_status"], "pending")

        self.store.complete_pending_authorization("login-1", "acct-1")
        completed_receipt = self.store.get_import_batch_row_receipt("batch-1", 0)
        self.assertEqual(completed_receipt["outcome"], "committed")
        self.assertEqual(completed_receipt["pending_status"], "completed")

    def test_get_import_batch_row_receipt_for_conflict_row_has_no_pending_status(self) -> None:
        self.store.register_client("client-1", "http://127.0.0.1:4421/oauth/return")
        first_rows = [
            {
                "row_index": 0,
                "outcome": "accepted",
                "login_id": "login-1",
                "client_id": "client-1",
                "state": "state-first",
                "resume_value": "client-1",
                "legacy_handle": "archive-row:abc",
                "account_id": "acct-1",
            }
        ]
        second_rows = [
            {
                "row_index": 0,
                "outcome": "accepted",
                "login_id": "login-2",
                "client_id": "client-1",
                "state": "state-second",
                "resume_value": "client-1",
                "legacy_handle": "archive-row:abc",
                "account_id": "acct-1",
            }
        ]
        self.store.create_quarantined_batch("batch-1", first_rows)
        self.store.create_quarantined_batch("batch-2", second_rows)
        self.store.commit_import_batch("batch-1", ttl_seconds=300)
        self.store.commit_import_batch("batch-2", ttl_seconds=300)

        receipt = self.store.get_import_batch_row_receipt("batch-2", 0)
        self.assertEqual(receipt["outcome"], "conflict")
        # The row's own identifiers are still visible even though it never
        # became a pending authorization.
        self.assertEqual(receipt["login_id"], "login-2")
        self.assertEqual(receipt["client_id"], "client-1")
        self.assertIsNone(receipt["pending_status"])

    def test_get_import_batch_row_receipt_unknown_batch_or_row_is_none(self) -> None:
        rows = [{"row_index": 0, "outcome": "rejected", "error": "unknown_account"}]
        self.store.create_quarantined_batch("batch-1", rows)

        self.assertIsNone(self.store.get_import_batch_row_receipt("does-not-exist", 0))
        self.assertIsNone(self.store.get_import_batch_row_receipt("batch-1", 99))

    def test_find_quarantined_import_by_client_and_legacy_handle(self) -> None:
        self.assertFalse(
            self.store.find_quarantined_import_by_client_and_legacy_handle("client-1", "archive-row:abc")
        )
        rows = [
            {
                "row_index": 0,
                "outcome": "accepted",
                "login_id": "login-1",
                "client_id": "client-1",
                "state": "state-1",
                "resume_value": "client-1",
                "legacy_handle": "archive-row:abc",
                "account_id": "acct-1",
            }
        ]
        self.store.create_quarantined_batch("batch-1", rows)
        self.assertTrue(
            self.store.find_quarantined_import_by_client_and_legacy_handle("client-1", "archive-row:abc")
        )
        self.assertFalse(
            self.store.find_quarantined_import_by_client_and_legacy_handle("client-1", "archive-row:other")
        )

    def test_find_import_by_client_and_legacy_handle(self) -> None:
        self.store.register_client("client-1", "http://127.0.0.1:4421/oauth/return")
        self.assertFalse(
            self.store.find_import_by_client_and_legacy_handle("client-1", "archive-row:abc")
        )
        self.store.create_pending_authorization(
            login_id="login-1",
            client_id="client-1",
            state="state-1",
            resume_kind="import",
            resume_value="client-1",
            import_batch_id=None,
            ttl_seconds=300,
            legacy_handle="archive-row:abc",
            source_account_id="acct-1",
        )
        self.assertTrue(
            self.store.find_import_by_client_and_legacy_handle("client-1", "archive-row:abc")
        )
        self.assertFalse(
            self.store.find_import_by_client_and_legacy_handle("client-1", "archive-row:other")
        )

    def test_token_persists(self) -> None:
        self.store.create_token("token-1", "client-1", "acct-1", "code-1")
        # No dedicated getter is exposed; verify no exception and constraint enforcement.
        with self.assertRaises(Exception):
            self.store.create_token("token-1", "client-2", "acct-2", "code-2")


if __name__ == "__main__":
    unittest.main()
