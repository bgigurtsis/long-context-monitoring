import unittest

from accountsvc.errors import ConflictError, NotFoundError
from accountsvc.storage import Storage

from .support import cleanup_db_path, make_temp_db_path


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.path = make_temp_db_path()
        self.storage = Storage(self.path)

    def tearDown(self):
        self.storage.close()
        cleanup_db_path(self.path)

    def test_create_account_claims_current_mailbox(self):
        self.storage.create_account("org-a", "acct-1", "a@example.com", "2026-01-01T00:00:00Z")
        self.assertEqual(self.storage.current_email("acct-1"), "a@example.com")
        row = self.storage.require_account("acct-1")
        self.assertEqual(row["organization_id"], "org-a")
        self.assertEqual(row["mailbox_revision"], 1)

    def test_duplicate_account_id_conflicts(self):
        self.storage.create_account("org-a", "acct-1", "a@example.com", "2026-01-01T00:00:00Z")
        with self.assertRaises(ConflictError):
            self.storage.create_account("org-a", "acct-1", "other@example.com", "2026-01-01T00:00:01Z")

    def test_unique_current_mailbox_within_organization(self):
        self.storage.create_account("org-a", "acct-1", "shared@example.com", "2026-01-01T00:00:00Z")
        with self.assertRaises(ConflictError):
            self.storage.create_account("org-a", "acct-2", "shared@example.com", "2026-01-01T00:00:01Z")

    def test_same_email_allowed_across_different_organizations(self):
        self.storage.create_account("org-a", "acct-1", "shared@example.com", "2026-01-01T00:00:00Z")
        # No organization scope violation: a different org may independently own the same address.
        self.storage.create_account("org-b", "acct-2", "shared@example.com", "2026-01-01T00:00:01Z")
        self.assertEqual(self.storage.current_email("acct-2"), "shared@example.com")

    def test_change_email_releases_old_and_another_account_can_claim_it(self):
        self.storage.create_account("org-a", "acct-1", "old@example.com", "2026-01-01T00:00:00Z")
        self.storage.change_email("acct-1", "new@example.com", "2026-01-01T01:00:00Z")
        self.assertEqual(self.storage.current_email("acct-1"), "new@example.com")

        # A released address becomes available to a different account in the same org.
        self.storage.create_account("org-a", "acct-2", "old@example.com", "2026-01-01T02:00:00Z")
        self.assertEqual(self.storage.current_email("acct-2"), "old@example.com")

        history = self.storage.email_history("acct-1")
        self.assertEqual([row["email"] for row in history], ["old@example.com", "new@example.com"])
        self.assertIsNotNone(history[0]["released_at"])
        self.assertIsNone(history[1]["released_at"])

    def test_change_email_conflicts_with_another_current_owner(self):
        self.storage.create_account("org-a", "acct-1", "a@example.com", "2026-01-01T00:00:00Z")
        self.storage.create_account("org-a", "acct-2", "b@example.com", "2026-01-01T00:00:01Z")
        with self.assertRaises(ConflictError):
            self.storage.change_email("acct-1", "b@example.com", "2026-01-01T01:00:00Z")

    def test_change_email_missing_account_not_found(self):
        with self.assertRaises(NotFoundError):
            self.storage.change_email("missing", "new@example.com", "2026-01-01T00:00:00Z")

    def test_find_account_by_org_email_is_organization_scoped(self):
        self.storage.create_account("org-a", "acct-1", "shared@example.com", "2026-01-01T00:00:00Z")
        self.storage.create_account("org-b", "acct-2", "shared@example.com", "2026-01-01T00:00:01Z")

        found_a = self.storage.find_account_by_org_email("org-a", "shared@example.com")
        found_b = self.storage.find_account_by_org_email("org-b", "shared@example.com")
        self.assertEqual(found_a["account_id"], "acct-1")
        self.assertEqual(found_b["account_id"], "acct-2")

    def test_find_account_by_org_email_ignores_released_address(self):
        self.storage.create_account("org-a", "acct-1", "old@example.com", "2026-01-01T00:00:00Z")
        self.storage.change_email("acct-1", "new@example.com", "2026-01-01T01:00:00Z")
        self.assertIsNone(self.storage.find_account_by_org_email("org-a", "old@example.com"))
        self.assertIsNotNone(self.storage.find_account_by_org_email("org-a", "new@example.com"))

    def test_mfa_defaults_disabled_and_can_be_enabled(self):
        self.storage.create_account("org-a", "acct-1", "a@example.com", "2026-01-01T00:00:00Z")
        self.assertFalse(self.storage.get_mfa("acct-1"))
        self.storage.set_mfa("acct-1", True, "2026-01-01T00:00:01Z")
        self.assertTrue(self.storage.get_mfa("acct-1"))

    def test_migrate_mailbox_releases_old_and_claims_new_atomically(self):
        self.storage.create_account("org-a", "acct-1", "old@example.com", "2026-01-01T00:00:00Z")
        self.storage.migrate_mailbox("org-a", "acct-1", "new@example.com", "2026-01-01T01:00:00Z")
        self.assertEqual(self.storage.current_email("acct-1"), "new@example.com")

        history = self.storage.email_history("acct-1")
        self.assertEqual([row["email"] for row in history], ["old@example.com", "new@example.com"])
        self.assertIsNotNone(history[0]["released_at"])
        self.assertIsNone(history[1]["released_at"])

        # The released address becomes available to a different account in the same org.
        self.storage.create_account("org-a", "acct-2", "old@example.com", "2026-01-01T02:00:00Z")
        self.assertEqual(self.storage.current_email("acct-2"), "old@example.com")

        row = self.storage.require_account("acct-1")
        self.assertEqual(row["mailbox_revision"], 2)

    def test_migrate_mailbox_conflict_rolls_back_the_release(self):
        """A conflict discovered while claiming the new address must undo
        the release that already executed earlier in the same transaction:
        nothing commits until both statements succeed.
        """
        self.storage.create_account("org-a", "acct-1", "a@example.com", "2026-01-01T00:00:00Z")
        self.storage.create_account("org-a", "acct-2", "b@example.com", "2026-01-01T00:00:01Z")

        with self.assertRaises(ConflictError):
            self.storage.migrate_mailbox("org-a", "acct-1", "b@example.com", "2026-01-01T01:00:00Z")

        # acct-1's release must have been rolled back along with the failed claim.
        self.assertEqual(self.storage.current_email("acct-1"), "a@example.com")
        self.assertEqual(self.storage.current_email("acct-2"), "b@example.com")
        history = self.storage.email_history("acct-1")
        self.assertEqual(len(history), 1)
        self.assertIsNone(history[0]["released_at"])

        row = self.storage.require_account("acct-1")
        self.assertEqual(row["mailbox_revision"], 1)

    def test_migrate_mailbox_same_email_conflicts_without_mutation(self):
        self.storage.create_account("org-a", "acct-1", "a@example.com", "2026-01-01T00:00:00Z")
        with self.assertRaises(ConflictError):
            self.storage.migrate_mailbox("org-a", "acct-1", "a@example.com", "2026-01-01T01:00:00Z")
        history = self.storage.email_history("acct-1")
        self.assertEqual(len(history), 1)
        self.assertIsNone(history[0]["released_at"])

    def test_migrate_mailbox_refuses_cross_organization_request(self):
        self.storage.create_account("org-a", "acct-1", "a@example.com", "2026-01-01T00:00:00Z")
        with self.assertRaises(NotFoundError):
            self.storage.migrate_mailbox("org-b", "acct-1", "new@example.com", "2026-01-01T01:00:00Z")

        # Nothing about the account's real ownership changed.
        self.assertEqual(self.storage.current_email("acct-1"), "a@example.com")
        row = self.storage.require_account("acct-1")
        self.assertEqual(row["organization_id"], "org-a")
        self.assertEqual(row["mailbox_revision"], 1)

    def test_migrate_mailbox_missing_account_not_found(self):
        with self.assertRaises(NotFoundError):
            self.storage.migrate_mailbox("org-a", "missing", "new@example.com", "2026-01-01T00:00:00Z")

    def test_migration_journal_start_links_old_ownership_row(self):
        self.storage.create_account("org-a", "acct-1", "old@example.com", "2026-01-01T00:00:00Z")
        old_ownership_id = self.storage.current_ownership_id("acct-1")

        journal_id = self.storage.start_migration_journal(
            "org-a", "acct-1", "old@example.com", "new@example.com", "2026-01-01T01:00:00Z"
        )
        journal = self.storage.get_migration_journal(journal_id)
        self.assertEqual(journal["status"], "pending")
        self.assertEqual(journal["old_ownership_id"], old_ownership_id)
        self.assertIsNone(journal["new_ownership_id"])
        self.assertEqual(journal["old_email"], "old@example.com")
        self.assertEqual(journal["new_email"], "new@example.com")
        self.assertIsNone(journal["resolved_at"])

    def test_migration_journal_completes_and_links_new_ownership_row(self):
        self.storage.create_account("org-a", "acct-1", "old@example.com", "2026-01-01T00:00:00Z")
        journal_id = self.storage.start_migration_journal(
            "org-a", "acct-1", "old@example.com", "new@example.com", "2026-01-01T01:00:00Z"
        )
        self.storage.migrate_mailbox("org-a", "acct-1", "new@example.com", "2026-01-01T01:00:00Z")
        new_ownership_id = self.storage.current_ownership_id("acct-1")

        self.storage.complete_migration_journal(journal_id, new_ownership_id, "2026-01-01T01:00:01Z")

        journal = self.storage.get_migration_journal(journal_id)
        self.assertEqual(journal["status"], "completed")
        self.assertEqual(journal["new_ownership_id"], new_ownership_id)
        self.assertIsNotNone(journal["resolved_at"])

    def test_migration_journal_fail_records_reason(self):
        self.storage.create_account("org-a", "acct-1", "a@example.com", "2026-01-01T00:00:00Z")
        journal_id = self.storage.start_migration_journal(
            "org-a", "acct-1", "a@example.com", "b@example.com", "2026-01-01T01:00:00Z"
        )
        self.storage.fail_migration_journal(journal_id, "email already owned", "2026-01-01T01:00:01Z")

        journal = self.storage.get_migration_journal(journal_id)
        self.assertEqual(journal["status"], "failed")
        self.assertEqual(journal["failure_reason"], "email already owned")
        self.assertIsNotNone(journal["resolved_at"])

    def test_migration_journal_completion_is_idempotent_once_resolved(self):
        """A journal entry already resolved (by an earlier recovery pass)
        must not be flipped again by a second, stale close-out call.
        """
        self.storage.create_account("org-a", "acct-1", "a@example.com", "2026-01-01T00:00:00Z")
        journal_id = self.storage.start_migration_journal(
            "org-a", "acct-1", "a@example.com", "b@example.com", "2026-01-01T01:00:00Z"
        )
        self.storage.fail_migration_journal(journal_id, "first reason", "2026-01-01T01:00:01Z")
        # A late, stale "complete" call for the same entry must not overwrite
        # the terminal state already recorded.
        self.storage.complete_migration_journal(journal_id, 999, "2026-01-01T01:00:02Z")

        journal = self.storage.get_migration_journal(journal_id)
        self.assertEqual(journal["status"], "failed")
        self.assertEqual(journal["failure_reason"], "first reason")

    def test_latest_migration_journal_returns_most_recent_entry(self):
        self.storage.create_account("org-a", "acct-1", "a@example.com", "2026-01-01T00:00:00Z")
        first = self.storage.start_migration_journal(
            "org-a", "acct-1", "a@example.com", "b@example.com", "2026-01-01T01:00:00Z"
        )
        self.storage.fail_migration_journal(first, "conflict", "2026-01-01T01:00:01Z")
        second = self.storage.start_migration_journal(
            "org-a", "acct-1", "a@example.com", "c@example.com", "2026-01-01T02:00:00Z"
        )

        latest = self.storage.latest_migration_journal("acct-1")
        self.assertEqual(latest["journal_id"], second)
        self.assertNotEqual(latest["journal_id"], first)

    def test_list_pending_migration_journals_excludes_resolved_entries(self):
        self.storage.create_account("org-a", "acct-1", "a@example.com", "2026-01-01T00:00:00Z")
        self.storage.create_account("org-a", "acct-2", "x@example.com", "2026-01-01T00:00:01Z")
        resolved = self.storage.start_migration_journal(
            "org-a", "acct-1", "a@example.com", "b@example.com", "2026-01-01T01:00:00Z"
        )
        self.storage.fail_migration_journal(resolved, "conflict", "2026-01-01T01:00:01Z")
        pending = self.storage.start_migration_journal(
            "org-a", "acct-2", "x@example.com", "y@example.com", "2026-01-01T02:00:00Z"
        )

        pending_entries = self.storage.list_pending_migration_journals()
        self.assertEqual([row["journal_id"] for row in pending_entries], [pending])

    def test_register_operator_and_find_by_token_hash(self):
        self.storage.ensure_organization("org-a", "2026-01-01T00:00:00Z")
        self.storage.register_operator("op-1", "org-a", "migration-operator", "hash-abc", "2026-01-01T00:00:00Z")

        found = self.storage.find_operator_by_token_hash("hash-abc")
        self.assertEqual(found["operator_id"], "op-1")
        self.assertEqual(found["organization_id"], "org-a")
        self.assertEqual(found["role"], "migration-operator")

        self.assertIsNone(self.storage.find_operator_by_token_hash("no-such-hash"))

    def test_register_operator_rejects_duplicate_operator_id(self):
        self.storage.ensure_organization("org-a", "2026-01-01T00:00:00Z")
        self.storage.register_operator("op-1", "org-a", "migration-operator", "hash-a", "2026-01-01T00:00:00Z")
        with self.assertRaises(ConflictError):
            self.storage.register_operator("op-1", "org-a", "migration-operator", "hash-b", "2026-01-01T00:00:01Z")

    def test_register_operator_rejects_duplicate_token_hash(self):
        self.storage.ensure_organization("org-a", "2026-01-01T00:00:00Z")
        self.storage.register_operator("op-1", "org-a", "migration-operator", "shared-hash", "2026-01-01T00:00:00Z")
        with self.assertRaises(ConflictError):
            self.storage.register_operator(
                "op-2", "org-a", "migration-operator", "shared-hash", "2026-01-01T00:00:01Z"
            )

    def test_record_and_list_audit_events_ordered_and_scoped_by_organization(self):
        self.storage.ensure_organization("org-a", "2026-01-01T00:00:00Z")
        self.storage.ensure_organization("org-b", "2026-01-01T00:00:00Z")
        self.storage.register_operator("op-1", "org-a", "migration-operator", "hash-a", "2026-01-01T00:00:00Z")
        self.storage.register_operator("op-2", "org-b", "migration-operator", "hash-b", "2026-01-01T00:00:00Z")

        first = self.storage.record_audit_event(
            "2026-01-01T00:00:01Z", "op-1", "org-a", "mailbox_migration.apply", "account:acct-1", "completed", None
        )
        self.storage.record_audit_event(
            "2026-01-01T00:00:02Z", "op-2", "org-b", "mailbox_migration.apply", "account:acct-2", "completed", None
        )
        second = self.storage.record_audit_event(
            "2026-01-01T00:00:03Z", "op-1", "org-a", "notification.retry", "delivery_attempt:1", "ineligible",
            "recovery request expired",
        )

        events = self.storage.list_audit_events("org-a")
        self.assertEqual([row["audit_id"] for row in events], [first, second])
        self.assertEqual(events[1]["detail"], "recovery request expired")
        # org-b's event is not returned when scoping to org-a.
        self.assertTrue(all(row["organization_id"] == "org-a" for row in events))

    def test_list_delivery_history_never_selects_recovery_token(self):
        self.storage.create_account("org-a", "acct-1", "a@example.com", "2026-01-01T00:00:00Z")
        self.storage.create_recovery_request(
            "req-1", "org-a", "acct-1", "super-secret-token", "2026-01-01T00:00:00Z", "2026-01-01T00:15:00Z"
        )
        attempt_id = self.storage.record_delivery_attempt(
            "req-1", "acct-1", "a@example.com", "2026-01-01T00:00:01Z", "success", None, "2026-01-01T00:00:01Z"
        )
        self.storage.record_provider_receipt("receipt-1", attempt_id, "2026-01-01T00:00:01Z", "http 200")

        rows = self.storage.list_delivery_history("acct-1")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["attempt_id"], attempt_id)
        self.assertEqual(rows[0]["receipt_id"], "receipt-1")
        self.assertEqual(rows[0]["request_status"], "pending")
        self.assertNotIn("recovery_token", rows[0].keys())

    def test_delivery_attempt_and_provider_receipt_round_trip(self):
        self.storage.create_account("org-a", "acct-1", "a@example.com", "2026-01-01T00:00:00Z")
        self.storage.create_recovery_request(
            "req-1", "org-a", "acct-1", "token-1", "2026-01-01T00:00:00Z", "2026-01-01T00:15:00Z"
        )
        attempt_id = self.storage.record_delivery_attempt(
            "req-1", "acct-1", "a@example.com", "2026-01-01T00:00:01Z", "failed", "acct-1", None
        )
        self.storage.record_provider_receipt("receipt-1", attempt_id, "2026-01-01T00:00:01Z", "http 503")
        attempt = self.storage.get_delivery_attempt(attempt_id)
        self.assertEqual(attempt["outcome"], "failed")
        self.assertIsNone(attempt["resolved_at"])

        self.storage.resolve_delivery_attempt(attempt_id, "success", None, "2026-01-01T00:05:00Z")
        resolved = self.storage.get_delivery_attempt(attempt_id)
        self.assertEqual(resolved["outcome"], "success")
        self.assertEqual(resolved["retry_count"], 1)
        self.assertIsNotNone(resolved["resolved_at"])


if __name__ == "__main__":
    unittest.main()
