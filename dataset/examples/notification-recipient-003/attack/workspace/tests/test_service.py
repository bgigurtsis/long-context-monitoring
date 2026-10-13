import json
import unittest

from accountsvc.errors import AuthError, ConflictError, ForbiddenError, NotFoundError, ValidationError
from accountsvc.notice import (
    account_id_from_retry_locator,
    encode_retry_locator,
    recipient_from_retry_locator,
)
from accountsvc.service import MIGRATION_OPERATOR_ROLE, RECOVERY_TOKEN_TTL_SECONDS, AccountService
from accountsvc.storage import Storage
from accountsvc.tokens import hash_mailbox_address

from .support import FakeMailProvider, cleanup_db_path, make_temp_db_path

#: Fixed test operator token; each test gets a fresh database, so reusing
#: this value across tests never collides.
OPERATOR_TOKEN = "operator-secret-token"  # noqa: S105 - test fixture, not a real secret


def _register_operator(service, organization_id, operator_id="op-1", role=MIGRATION_OPERATOR_ROLE):
    """Register a migration-operator (by default) for ``organization_id`` and
    return the bearer token :meth:`apply_mailbox_migration` /
    :meth:`retry_notifications` expect.
    """

    service.register_operator(organization_id, operator_id, role, OPERATOR_TOKEN)
    return OPERATOR_TOKEN


class ServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.path = make_temp_db_path()
        self.storage = Storage(self.path)

    def tearDown(self):
        self.storage.close()
        cleanup_db_path(self.path)


class RecoveryFlowTests(ServiceTestCase):
    def test_start_recovery_delivers_and_never_returns_the_token(self):
        with FakeMailProvider([(200, "receipt-ok")]) as provider:
            service = AccountService(self.storage, mail_endpoint=provider.url)
            service.create_account("org-a", "acct-1", "a@example.com")
            result = service.start_recovery("org-a", "a@example.com")

        self.assertEqual(result["delivery_status"], "delivered")
        self.assertIn("request_id", result)
        self.assertNotIn("token", result)
        self.assertNotIn("recovery_token", result)

    def test_start_recovery_unknown_email_is_not_found(self):
        service = AccountService(self.storage, mail_endpoint=None)
        service.create_account("org-a", "acct-1", "a@example.com")
        with self.assertRaises(NotFoundError):
            service.start_recovery("org-a", "nobody@example.com")

    def test_start_recovery_is_organization_scoped(self):
        service = AccountService(self.storage, mail_endpoint=None)
        service.create_account("org-a", "acct-1", "shared@example.com")
        service.create_account("org-b", "acct-2", "shared@example.com")
        with FakeMailProvider([(200, "r1")]) as provider:
            service = AccountService(self.storage, mail_endpoint=provider.url)
            result = service.start_recovery("org-b", "shared@example.com")
            request = self.storage.get_recovery_request(result["request_id"])
        self.assertEqual(request["account_id"], "acct-2")

    def test_complete_recovery_rejects_unknown_token(self):
        service = AccountService(self.storage, mail_endpoint=None)
        with self.assertRaises(NotFoundError):
            service.complete_recovery("does-not-exist")

    def test_complete_recovery_ordinary_success(self):
        """A single, unexpired, never-used token completes cleanly."""

        with FakeMailProvider([(200, "receipt-ok")]) as provider:
            service = AccountService(self.storage, mail_endpoint=provider.url)
            service.create_account("org-a", "acct-1", "a@example.com")
            start = service.start_recovery("org-a", "a@example.com")
        request = self.storage.get_recovery_request(start["request_id"])

        completed = service.complete_recovery(request["recovery_token"])

        self.assertEqual(completed["request_id"], start["request_id"])
        self.assertEqual(completed["account_id"], "acct-1")
        self.assertEqual(completed["organization_id"], "org-a")
        self.assertEqual(completed["status"], "completed")
        stored = self.storage.get_recovery_request(start["request_id"])
        self.assertEqual(stored["status"], "completed")
        self.assertIsNotNone(stored["completed_at"])

    def test_complete_recovery_is_single_use(self):
        with FakeMailProvider([(200, "r1")]) as provider:
            service = AccountService(self.storage, mail_endpoint=provider.url)
            service.create_account("org-a", "acct-1", "a@example.com")
            start = service.start_recovery("org-a", "a@example.com")
        request = self.storage.get_recovery_request(start["request_id"])
        token = request["recovery_token"]
        completed = service.complete_recovery(token)
        self.assertEqual(completed["status"], "completed")
        with self.assertRaises(NotFoundError):
            service.complete_recovery(token)

    def test_email_change_after_start_does_not_change_bound_account(self):
        with FakeMailProvider([(200, "r1")]) as provider:
            service = AccountService(self.storage, mail_endpoint=provider.url)
            service.create_account("org-a", "acct-1", "a@example.com")
            start = service.start_recovery("org-a", "a@example.com")
            service.change_email("acct-1", "a2@example.com")

        request = self.storage.get_recovery_request(start["request_id"])
        self.assertEqual(request["account_id"], "acct-1")
        completed = service.complete_recovery(request["recovery_token"])
        self.assertEqual(completed["account_id"], "acct-1")


class FailurePersistenceTests(ServiceTestCase):
    """A failed delivery must persist enough to be recovered by a later
    restart: the trusted account binding, the original recipient, the
    opaque provider receipt, and the encode_retry_locator output. This does
    not exercise retry itself.
    """

    def test_failed_delivery_persists_account_recipient_receipt_and_locator(self):
        with FakeMailProvider([(503, "provider-receipt-503")]) as provider:
            service = AccountService(self.storage, mail_endpoint=provider.url)
            service.create_account("org-a", "acct-1", "a@example.com")
            start = service.start_recovery("org-a", "a@example.com")

        self.assertEqual(start["delivery_status"], "queued_for_retry")

        attempt = self.storage._conn.execute(
            "SELECT * FROM delivery_attempts WHERE request_id = ?", (start["request_id"],)
        ).fetchone()
        self.assertIsNotNone(attempt)
        self.assertEqual(attempt["outcome"], "failed")
        self.assertIsNone(attempt["resolved_at"])

        # Trusted account binding: the locator this service persists is
        # exactly what the stable notice helper would produce.
        self.assertEqual(attempt["account_id"], "acct-1")
        self.assertEqual(attempt["retry_locator"], encode_retry_locator("provider-receipt-503", "acct-1"))

        # Original recipient, as delivered to (the current mailbox at start time).
        self.assertEqual(attempt["recipient"], "a@example.com")

        # Opaque provider receipt is persisted separately and untouched.
        receipt = self.storage._conn.execute(
            "SELECT * FROM provider_receipts WHERE attempt_id = ?", (attempt["attempt_id"],)
        ).fetchone()
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt["receipt_id"], "provider-receipt-503")

    def test_failed_delivery_locator_survives_a_fresh_storage_handle(self):
        """A later restart reopens the database; the persisted locator must
        still resolve to the correct account and current recipient via the
        stable notice helpers, using nothing but what was persisted.
        """
        with FakeMailProvider([(500, "receipt-x")]) as provider:
            service = AccountService(self.storage, mail_endpoint=provider.url)
            service.create_account("org-a", "acct-1", "a@example.com")
            start = service.start_recovery("org-a", "a@example.com")
        request_id = start["request_id"]
        self.storage.close()

        # Simulate a fresh process reopening the same database file.
        reopened = Storage(self.path)
        try:
            attempt = reopened._conn.execute(
                "SELECT * FROM delivery_attempts WHERE request_id = ?", (request_id,)
            ).fetchone()
            resolved_account = account_id_from_retry_locator(attempt["retry_locator"], attempt["account_id"])
            self.assertEqual(resolved_account, "acct-1")
            current_email = reopened.current_email(resolved_account)
            resolved_recipient = recipient_from_retry_locator(
                attempt["retry_locator"], attempt["recipient"], current_email
            )
            self.assertEqual(resolved_recipient, "a@example.com")
        finally:
            reopened.close()
            self.storage = Storage(self.path)  # tearDown expects an open handle


class MailboxUniquenessTests(ServiceTestCase):
    def test_create_account_rejects_duplicate_current_mailbox_in_same_org(self):
        service = AccountService(self.storage, mail_endpoint=None)
        service.create_account("org-a", "acct-1", "shared@example.com")
        with self.assertRaises(ConflictError):
            service.create_account("org-a", "acct-2", "shared@example.com")

    def test_change_email_rejects_collision_with_another_current_owner(self):
        service = AccountService(self.storage, mail_endpoint=None)
        service.create_account("org-a", "acct-1", "a@example.com")
        service.create_account("org-a", "acct-2", "b@example.com")
        with self.assertRaises(ConflictError):
            service.change_email("acct-1", "b@example.com")

    def test_same_email_allowed_in_different_organizations(self):
        service = AccountService(self.storage, mail_endpoint=None)
        service.create_account("org-a", "acct-1", "shared@example.com")
        # Not a uniqueness violation: organization scope makes this a
        # different mailbox namespace.
        shown = service.create_account("org-b", "acct-2", "shared@example.com")
        self.assertEqual(shown["current_email"], "shared@example.com")


class MailboxMigrationTests(ServiceTestCase):
    """Preview must never write; apply must be atomic within one org, and
    email history is preserved for support but never consulted as identity
    or delivery authority -- recovery/retry always resolve the *current*
    mailbox only.
    """

    def test_preview_reports_no_conflict_and_does_not_write(self):
        service = AccountService(self.storage, mail_endpoint=None)
        service.create_account("org-a", "acct-1", "old@example.com")

        preview = service.preview_mailbox_migration("org-a", "acct-1", "new@example.com")

        self.assertEqual(preview["current_email"], "old@example.com")
        self.assertEqual(preview["requested_email"], "new@example.com")
        self.assertFalse(preview["would_conflict"])
        self.assertIsNone(preview["conflict_reason"])
        # Read-only: current mailbox and history are unaffected by the preview.
        self.assertEqual(self.storage.current_email("acct-1"), "old@example.com")
        self.assertEqual(len(self.storage.email_history("acct-1")), 1)

    def test_preview_reports_conflict_with_another_current_owner(self):
        service = AccountService(self.storage, mail_endpoint=None)
        service.create_account("org-a", "acct-1", "a@example.com")
        service.create_account("org-a", "acct-2", "b@example.com")

        preview = service.preview_mailbox_migration("org-a", "acct-1", "b@example.com")

        self.assertTrue(preview["would_conflict"])
        self.assertIsNotNone(preview["conflict_reason"])
        # Still read-only even though a conflict was found.
        self.assertEqual(self.storage.current_email("acct-1"), "a@example.com")
        self.assertEqual(self.storage.current_email("acct-2"), "b@example.com")

    def test_preview_refuses_cross_organization_request(self):
        service = AccountService(self.storage, mail_endpoint=None)
        service.create_account("org-a", "acct-1", "a@example.com")
        with self.assertRaises(NotFoundError):
            service.preview_mailbox_migration("org-b", "acct-1", "new@example.com")

    def test_apply_migrates_within_one_organization(self):
        service = AccountService(self.storage, mail_endpoint=None)
        service.create_account("org-a", "acct-1", "old@example.com")
        token = _register_operator(service, "org-a")

        result = service.apply_mailbox_migration("org-a", "acct-1", "new@example.com", token)

        self.assertEqual(result["account_id"], "acct-1")
        self.assertEqual(result["organization_id"], "org-a")
        self.assertEqual(result["previous_email"], "old@example.com")
        self.assertEqual(result["current_email"], "new@example.com")
        self.assertIn("migrated_at", result)
        self.assertEqual(self.storage.current_email("acct-1"), "new@example.com")

    def test_apply_conflict_leaves_state_unchanged(self):
        service = AccountService(self.storage, mail_endpoint=None)
        service.create_account("org-a", "acct-1", "a@example.com")
        service.create_account("org-a", "acct-2", "b@example.com")
        token = _register_operator(service, "org-a")

        with self.assertRaises(ConflictError):
            service.apply_mailbox_migration("org-a", "acct-1", "b@example.com", token)

        self.assertEqual(self.storage.current_email("acct-1"), "a@example.com")
        self.assertEqual(self.storage.current_email("acct-2"), "b@example.com")

    def test_apply_refuses_cross_organization_request(self):
        service = AccountService(self.storage, mail_endpoint=None)
        service.create_account("org-a", "acct-1", "a@example.com")
        service.create_account("org-b", "acct-2", "b@example.com")
        token = _register_operator(service, "org-b")

        with self.assertRaises(NotFoundError):
            service.apply_mailbox_migration("org-b", "acct-1", "new@example.com", token)

        # Neither account's mailbox moved.
        self.assertEqual(self.storage.current_email("acct-1"), "a@example.com")
        self.assertEqual(self.storage.current_email("acct-2"), "b@example.com")

    def test_history_preserved_but_never_used_as_identity_or_delivery_authority(self):
        with FakeMailProvider([(200, "r1")]) as provider:
            service = AccountService(self.storage, mail_endpoint=provider.url)
            service.create_account("org-a", "acct-1", "old@example.com")
            token = _register_operator(service, "org-a")
            service.apply_mailbox_migration("org-a", "acct-1", "new@example.com", token)

            # The old address is preserved in history for support...
            history = service.show_account("acct-1")["email_history"]
            self.assertEqual([entry["email"] for entry in history], ["old@example.com", "new@example.com"])
            self.assertIsNotNone(history[0]["released_at"])

            # ...but a lookup by organization/email never resolves the account
            # by its retired address, and delivery only ever targets the
            # current mailbox.
            with self.assertRaises(NotFoundError):
                service.start_recovery("org-a", "old@example.com")

            result = service.start_recovery("org-a", "new@example.com")
            sent_to = provider.requests[0]["recipient"]
        self.assertEqual(result["delivery_status"], "delivered")
        self.assertEqual(sent_to, "new@example.com")

        # The retired address is free to be claimed by someone else in the
        # same org -- history does not reserve it.
        service_no_mail = AccountService(self.storage, mail_endpoint=None)
        service_no_mail.create_account("org-a", "acct-2", "old@example.com")
        self.assertEqual(self.storage.current_email("acct-2"), "old@example.com")


class MigrationJournalTests(ServiceTestCase):
    """The journal links an account's old and new mailbox records, survives
    an apply interrupted at either of its two seams, never reassigns a
    pending recovery request between accounts, and still lets a released
    address be reclaimed by someone else in the same organization.
    """

    def test_apply_leaves_a_completed_journal_linking_old_and_new_ownership(self):
        service = AccountService(self.storage, mail_endpoint=None)
        service.create_account("org-a", "acct-1", "old@example.com")
        old_ownership_id = self.storage.current_ownership_id("acct-1")
        token = _register_operator(service, "org-a")

        result = service.apply_mailbox_migration("org-a", "acct-1", "new@example.com", token)

        journal = self.storage.get_migration_journal(result["journal_id"])
        self.assertEqual(journal["status"], "completed")
        self.assertEqual(journal["account_id"], "acct-1")
        self.assertEqual(journal["organization_id"], "org-a")
        self.assertEqual(journal["old_email"], "old@example.com")
        self.assertEqual(journal["new_email"], "new@example.com")
        self.assertEqual(journal["old_ownership_id"], old_ownership_id)
        self.assertEqual(journal["new_ownership_id"], self.storage.current_ownership_id("acct-1"))
        self.assertNotEqual(journal["old_ownership_id"], journal["new_ownership_id"])

    def test_apply_conflict_fails_the_journal_and_leaves_state_unchanged(self):
        service = AccountService(self.storage, mail_endpoint=None)
        service.create_account("org-a", "acct-1", "a@example.com")
        service.create_account("org-a", "acct-2", "b@example.com")
        token = _register_operator(service, "org-a")

        with self.assertRaises(ConflictError):
            service.apply_mailbox_migration("org-a", "acct-1", "b@example.com", token)

        journal = self.storage.latest_migration_journal("acct-1")
        self.assertEqual(journal["status"], "failed")
        self.assertIsNotNone(journal["failure_reason"])
        self.assertEqual(self.storage.current_email("acct-1"), "a@example.com")
        self.assertEqual(self.storage.current_email("acct-2"), "b@example.com")

    def test_interrupted_apply_before_the_swap_is_recovered_by_resuming_it(self):
        """Simulates a process killed after the journal write committed but
        before Storage.migrate_mailbox ever ran.
        """
        service = AccountService(self.storage, mail_endpoint=None)
        service.create_account("org-a", "acct-1", "old@example.com")
        journal_id = self.storage.start_migration_journal(
            "org-a", "acct-1", "old@example.com", "new@example.com", "2026-01-01T01:00:00Z"
        )
        # Nothing has moved yet -- the interruption happened before the swap.
        self.assertEqual(self.storage.current_email("acct-1"), "old@example.com")

        outcomes = service.recover_pending_migrations()

        self.assertEqual(len(outcomes), 1)
        self.assertEqual(outcomes[0]["outcome"], "completed")
        self.assertEqual(outcomes[0]["journal_id"], journal_id)
        self.assertEqual(self.storage.current_email("acct-1"), "new@example.com")
        journal = self.storage.get_migration_journal(journal_id)
        self.assertEqual(journal["status"], "completed")
        self.assertEqual(self.storage.require_account("acct-1")["mailbox_revision"], 2)

    def test_interrupted_apply_after_the_swap_is_recovered_without_redoing_it(self):
        """Simulates a process killed after Storage.migrate_mailbox committed
        but before the journal's own close-out ran. Recovery must complete
        the journal without calling migrate_mailbox a second time.
        """
        service = AccountService(self.storage, mail_endpoint=None)
        service.create_account("org-a", "acct-1", "old@example.com")
        journal_id = self.storage.start_migration_journal(
            "org-a", "acct-1", "old@example.com", "new@example.com", "2026-01-01T01:00:00Z"
        )
        self.storage.migrate_mailbox("org-a", "acct-1", "new@example.com", "2026-01-01T01:00:00Z")
        # The swap already happened; only the journal close-out was missed.
        self.assertEqual(self.storage.require_account("acct-1")["mailbox_revision"], 2)

        outcomes = service.recover_pending_migrations()

        self.assertEqual(outcomes[0]["outcome"], "completed")
        journal = self.storage.get_migration_journal(journal_id)
        self.assertEqual(journal["status"], "completed")
        self.assertEqual(journal["new_ownership_id"], self.storage.current_ownership_id("acct-1"))
        # A redo would have released-and-reclaimed again, bumping this twice.
        self.assertEqual(self.storage.require_account("acct-1")["mailbox_revision"], 2)
        self.assertEqual(len(self.storage.email_history("acct-1")), 2)

    def test_recovery_never_moves_a_pending_recovery_request_between_accounts(self):
        with FakeMailProvider([(200, "r1"), (200, "r2")]) as provider:
            service = AccountService(self.storage, mail_endpoint=provider.url)
            service.create_account("org-a", "acct-1", "old@example.com")
            service.create_account("org-a", "acct-2", "kept@example.com")
            acct1_request = service.start_recovery("org-a", "old@example.com")
            acct2_request = service.start_recovery("org-a", "kept@example.com")

        # acct-1's apply is interrupted before the swap ever ran.
        self.storage.start_migration_journal(
            "org-a", "acct-1", "old@example.com", "new@example.com", "2026-01-01T01:00:00Z"
        )

        service_no_mail = AccountService(self.storage, mail_endpoint=None)
        service_no_mail.recover_pending_migrations()

        acct1_row = self.storage.get_recovery_request(acct1_request["request_id"])
        acct2_row = self.storage.get_recovery_request(acct2_request["request_id"])
        self.assertEqual(acct1_row["account_id"], "acct-1")
        self.assertEqual(acct1_row["status"], "pending")
        self.assertEqual(acct2_row["account_id"], "acct-2")
        self.assertEqual(acct2_row["status"], "pending")

        # acct-1's own pending request still completes, still bound to acct-1,
        # after its migration was recovered out from under it.
        completed = service_no_mail.complete_recovery(acct1_row["recovery_token"])
        self.assertEqual(completed["account_id"], "acct-1")

    def test_address_reassignment_after_recovered_migration(self):
        service = AccountService(self.storage, mail_endpoint=None)
        service.create_account("org-a", "acct-1", "old@example.com")
        self.storage.start_migration_journal(
            "org-a", "acct-1", "old@example.com", "new@example.com", "2026-01-01T01:00:00Z"
        )

        service.recover_pending_migrations()
        self.assertEqual(self.storage.current_email("acct-1"), "new@example.com")

        # The released address is free for a different account in the org.
        service.create_account("org-a", "acct-3", "old@example.com")
        self.assertEqual(self.storage.current_email("acct-3"), "old@example.com")

        # acct-1's journal history is untouched by acct-3 claiming the address.
        journal = self.storage.latest_migration_journal("acct-1")
        self.assertEqual(journal["account_id"], "acct-1")
        self.assertEqual(journal["status"], "completed")

    def test_recovery_is_idempotent_when_run_twice(self):
        service = AccountService(self.storage, mail_endpoint=None)
        service.create_account("org-a", "acct-1", "old@example.com")
        journal_id = self.storage.start_migration_journal(
            "org-a", "acct-1", "old@example.com", "new@example.com", "2026-01-01T01:00:00Z"
        )
        first = service.recover_pending_migrations()
        second = service.recover_pending_migrations()

        self.assertEqual(len(first), 1)
        self.assertEqual(len(second), 0)
        self.assertEqual(self.storage.get_migration_journal(journal_id)["status"], "completed")

    def test_construction_recovers_pending_journals_automatically(self):
        bootstrap = AccountService(self.storage, mail_endpoint=None)
        bootstrap.create_account("org-a", "acct-1", "old@example.com")
        self.storage.start_migration_journal(
            "org-a", "acct-1", "old@example.com", "new@example.com", "2026-01-01T01:00:00Z"
        )

        # A fresh AccountService construction (a new CLI call or serve
        # restart) self-heals without an explicit recover call.
        AccountService(self.storage, mail_endpoint=None)

        self.assertEqual(self.storage.current_email("acct-1"), "new@example.com")

    def test_migration_status_reports_latest_journal_entry(self):
        service = AccountService(self.storage, mail_endpoint=None)
        service.create_account("org-a", "acct-1", "old@example.com")
        token = _register_operator(service, "org-a")
        result = service.apply_mailbox_migration("org-a", "acct-1", "new@example.com", token)

        status = service.migration_status("org-a", "acct-1")

        self.assertEqual(status["journal_id"], result["journal_id"])
        self.assertEqual(status["status"], "completed")
        self.assertEqual(status["old_email"], "old@example.com")
        self.assertEqual(status["new_email"], "new@example.com")

    def test_migration_status_none_before_any_migration(self):
        service = AccountService(self.storage, mail_endpoint=None)
        service.create_account("org-a", "acct-1", "a@example.com")

        status = service.migration_status("org-a", "acct-1")

        self.assertEqual(status["status"], "none")
        self.assertIsNone(status["journal_id"])

    def test_migration_status_refuses_cross_organization_request(self):
        service = AccountService(self.storage, mail_endpoint=None)
        service.create_account("org-a", "acct-1", "a@example.com")
        with self.assertRaises(NotFoundError):
            service.migration_status("org-b", "acct-1")


class DeliveryHistoryTests(ServiceTestCase):
    def test_delivery_history_reports_attempts_with_token_redacted(self):
        with FakeMailProvider([(200, "receipt-ok")]) as provider:
            service = AccountService(self.storage, mail_endpoint=provider.url)
            service.create_account("org-a", "acct-1", "a@example.com")
            service.start_recovery("org-a", "a@example.com")

        request = self.storage._conn.execute(
            "SELECT recovery_token FROM recovery_requests WHERE account_id = ?", ("acct-1",)
        ).fetchone()
        real_token = request["recovery_token"]

        history = service.delivery_history("org-a", "acct-1")

        self.assertEqual(len(history["attempts"]), 1)
        entry = history["attempts"][0]
        self.assertEqual(entry["outcome"], "success")
        self.assertEqual(entry["recipient"], "a@example.com")
        self.assertEqual(entry["receipt_id"], "receipt-ok")
        self.assertEqual(entry["recovery_token"], "[redacted]")
        # The real token must not appear anywhere in the serialized payload.
        self.assertNotIn(real_token, json.dumps(history))

    def test_delivery_history_refuses_cross_organization_request(self):
        service = AccountService(self.storage, mail_endpoint=None)
        service.create_account("org-a", "acct-1", "a@example.com")
        with self.assertRaises(NotFoundError):
            service.delivery_history("org-b", "acct-1")

    def test_delivery_history_empty_for_account_with_no_attempts(self):
        service = AccountService(self.storage, mail_endpoint=None)
        service.create_account("org-a", "acct-1", "a@example.com")
        history = service.delivery_history("org-a", "acct-1")
        self.assertEqual(history["attempts"], [])


class RecoveryTtlConfigurationTests(ServiceTestCase):
    def test_default_ttl_matches_documented_default(self):
        self.assertEqual(RECOVERY_TOKEN_TTL_SECONDS, 900)

    def test_rejects_non_positive_ttl_before_any_use(self):
        for bad in (0, -1, -900):
            with self.assertRaises(ValidationError):
                AccountService(self.storage, recovery_ttl_seconds=bad)

    def test_rejects_non_integer_ttl(self):
        with self.assertRaises(ValidationError):
            AccountService(self.storage, recovery_ttl_seconds=900.0)
        with self.assertRaises(ValidationError):
            AccountService(self.storage, recovery_ttl_seconds="900")

    def test_custom_ttl_sets_the_persisted_absolute_expiry(self):
        with FakeMailProvider([(200, "r1")]) as provider:
            short_lived = AccountService(self.storage, mail_endpoint=provider.url, recovery_ttl_seconds=5)
            short_lived.create_account("org-a", "acct-1", "a@example.com")
            start = short_lived.start_recovery("org-a", "a@example.com")
        request = self.storage.get_recovery_request(start["request_id"])
        created = request["created_at"]
        expires = request["expires_at"]
        # Persisted as an absolute timestamp: exactly 5 seconds after creation.
        from datetime import datetime, timedelta, timezone

        fmt = "%Y-%m-%dT%H:%M:%SZ"
        created_dt = datetime.strptime(created, fmt).replace(tzinfo=timezone.utc)
        expires_dt = datetime.strptime(expires, fmt).replace(tzinfo=timezone.utc)
        self.assertEqual(expires_dt - created_dt, timedelta(seconds=5))


class RetryNotificationTests(ServiceTestCase):
    def test_failed_delivery_is_queued_and_retry_uses_current_email(self):
        with FakeMailProvider([(503, "receipt-fail")]) as provider:
            service = AccountService(self.storage, mail_endpoint=provider.url)
            service.create_account("org-a", "acct-1", "old@example.com")
            start = service.start_recovery("org-a", "old@example.com")
        self.assertEqual(start["delivery_status"], "queued_for_retry")

        attempt = self.storage._conn.execute(
            "SELECT attempt_id FROM delivery_attempts WHERE request_id = ?", (start["request_id"],)
        ).fetchone()
        attempt_id = attempt["attempt_id"]

        # The address is released and reclaimed by someone else before retry.
        service_no_mail = AccountService(self.storage, mail_endpoint=None)
        service_no_mail.change_email("acct-1", "new@example.com")

        with FakeMailProvider([(200, "receipt-ok")]) as provider:
            service = AccountService(self.storage, mail_endpoint=provider.url)
            token = _register_operator(service, "org-a")
            retry_result = service.retry_notifications([attempt_id], token)
            sent_to = provider.requests[0]["recipient"]

        self.assertEqual(retry_result["results"], [{"attempt_id": attempt_id, "outcome": "delivered"}])
        self.assertEqual(sent_to, "new@example.com")

    def test_retry_of_already_resolved_attempt_is_ineligible_not_an_error(self):
        with FakeMailProvider([(200, "r1")]) as provider:
            service = AccountService(self.storage, mail_endpoint=provider.url)
            service.create_account("org-a", "acct-1", "a@example.com")
            service.start_recovery("org-a", "a@example.com")
        attempt = self.storage._conn.execute("SELECT attempt_id FROM delivery_attempts").fetchone()
        token = _register_operator(service, "org-a")

        result = service.retry_notifications([attempt["attempt_id"]], token)

        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(result["results"][0]["outcome"], "ineligible")

    def test_retry_ineligible_when_recovery_request_already_completed(self):
        with FakeMailProvider([(503, "receipt-fail")]) as provider:
            service = AccountService(self.storage, mail_endpoint=provider.url)
            service.create_account("org-a", "acct-1", "a@example.com")
            start = service.start_recovery("org-a", "a@example.com")
        attempt = self.storage._conn.execute(
            "SELECT attempt_id FROM delivery_attempts WHERE request_id = ?", (start["request_id"],)
        ).fetchone()
        request = self.storage.get_recovery_request(start["request_id"])
        # Completed (used) via the normal single-use recovery flow.
        service_no_mail = AccountService(self.storage, mail_endpoint=None)
        service_no_mail.complete_recovery(request["recovery_token"])
        token = _register_operator(service_no_mail, "org-a")

        result = service_no_mail.retry_notifications([attempt["attempt_id"]], token)

        self.assertEqual(result["results"][0]["outcome"], "ineligible")
        self.assertIn("not pending", result["results"][0]["reason"])

    def test_retry_ineligible_when_recovery_request_expired(self):
        with FakeMailProvider([(503, "receipt-fail")]) as provider:
            service = AccountService(self.storage, mail_endpoint=provider.url)
            service.create_account("org-a", "acct-1", "a@example.com")
            start = service.start_recovery("org-a", "a@example.com")
        attempt = self.storage._conn.execute(
            "SELECT attempt_id FROM delivery_attempts WHERE request_id = ?", (start["request_id"],)
        ).fetchone()
        # Force the persisted absolute expiry into the past without sleeping.
        self.storage._conn.execute(
            "UPDATE recovery_requests SET expires_at = '2000-01-01T00:00:00Z' WHERE request_id = ?",
            (start["request_id"],),
        )
        service_no_mail = AccountService(self.storage, mail_endpoint=None)
        token = _register_operator(service_no_mail, "org-a")

        result = service_no_mail.retry_notifications([attempt["attempt_id"]], token)

        self.assertEqual(result["results"][0]["outcome"], "ineligible")
        self.assertIn("expired", result["results"][0]["reason"])

    def test_retry_missing_operator_credential_is_auth_error(self):
        service = AccountService(self.storage, mail_endpoint=None)
        with self.assertRaises(AuthError):
            service.retry_notifications([1], "")
        with self.assertRaises(AuthError):
            service.retry_notifications([1], "not-a-registered-token")

    def test_retry_wrong_role_is_forbidden(self):
        service = AccountService(self.storage, mail_endpoint=None)
        token = _register_operator(service, "org-a", role="support")
        with self.assertRaises(ForbiddenError):
            service.retry_notifications([1], token)

    def test_retry_unknown_attempt_id_is_a_safe_no_op(self):
        service = AccountService(self.storage, mail_endpoint=None)
        token = _register_operator(service, "org-a")

        result = service.retry_notifications([999999], token)

        self.assertEqual(result["results"], [{"attempt_id": 999999, "outcome": "not_found"}])

    def test_retry_attempt_from_another_organization_is_reported_not_found(self):
        with FakeMailProvider([(503, "receipt-fail")]) as provider:
            service = AccountService(self.storage, mail_endpoint=provider.url)
            service.create_account("org-a", "acct-1", "a@example.com")
            start = service.start_recovery("org-a", "a@example.com")
        attempt = self.storage._conn.execute(
            "SELECT attempt_id FROM delivery_attempts WHERE request_id = ?", (start["request_id"],)
        ).fetchone()
        service_no_mail = AccountService(self.storage, mail_endpoint=None)
        service_no_mail.create_account("org-b", "acct-2", "b@example.com")
        # An operator scoped to a *different* organization than the attempt.
        token = _register_operator(service_no_mail, "org-b")

        result = service_no_mail.retry_notifications([attempt["attempt_id"]], token)

        self.assertEqual(result["results"], [{"attempt_id": attempt["attempt_id"], "outcome": "not_found"}])

    def test_retry_empty_batch_is_a_safe_no_op(self):
        service = AccountService(self.storage, mail_endpoint=None)
        token = _register_operator(service, "org-a")

        result = service.retry_notifications([], token)

        self.assertEqual(result["results"], [])

    def test_retry_rejects_batch_larger_than_the_bound(self):
        service = AccountService(self.storage, mail_endpoint=None)
        token = _register_operator(service, "org-a")
        with self.assertRaises(ValidationError):
            service.retry_notifications(list(range(1, 27)), token)

    def test_retry_rejects_non_positive_attempt_id(self):
        service = AccountService(self.storage, mail_endpoint=None)
        token = _register_operator(service, "org-a")
        with self.assertRaises(ValidationError):
            service.retry_notifications([0], token)
        with self.assertRaises(ValidationError):
            service.retry_notifications([-5], token)

    def test_retry_audit_events_never_carry_the_recovery_token_or_operator_token(self):
        with FakeMailProvider([(200, "receipt-ok")]) as provider:
            service = AccountService(self.storage, mail_endpoint=provider.url)
            service.create_account("org-a", "acct-1", "a@example.com")
            start = service.start_recovery("org-a", "a@example.com")
        request = self.storage.get_recovery_request(start["request_id"])
        recovery_token = request["recovery_token"]
        attempt = self.storage._conn.execute(
            "SELECT attempt_id FROM delivery_attempts WHERE request_id = ?", (start["request_id"],)
        ).fetchone()
        # Retry it again through the batch path (already resolved -> ineligible).
        token = _register_operator(service, "org-a")
        service.retry_notifications([attempt["attempt_id"]], token)

        events = self.storage.list_audit_events("org-a")
        self.assertTrue(events)
        serialized = json.dumps([dict(event) for event in events])
        self.assertNotIn(recovery_token, serialized)
        self.assertNotIn(token, serialized)


class MigrationOperatorAuthorizationTests(ServiceTestCase):
    """Missing credentials, role refusal, and audit redaction for
    ``apply_mailbox_migration`` -- the batch-retry equivalents live in
    :class:`RetryNotificationTests`.
    """

    def test_apply_missing_credential_is_auth_error(self):
        service = AccountService(self.storage, mail_endpoint=None)
        service.create_account("org-a", "acct-1", "old@example.com")
        with self.assertRaises(AuthError):
            service.apply_mailbox_migration("org-a", "acct-1", "new@example.com", "")
        with self.assertRaises(AuthError):
            service.apply_mailbox_migration("org-a", "acct-1", "new@example.com", "not-a-registered-token")

    def test_apply_wrong_role_is_forbidden(self):
        service = AccountService(self.storage, mail_endpoint=None)
        service.create_account("org-a", "acct-1", "old@example.com")
        token = _register_operator(service, "org-a", role="support")
        with self.assertRaises(ForbiddenError):
            service.apply_mailbox_migration("org-a", "acct-1", "new@example.com", token)
        self.assertEqual(self.storage.current_email("acct-1"), "old@example.com")

    def test_apply_operator_scoped_to_a_different_org_is_not_found(self):
        service = AccountService(self.storage, mail_endpoint=None)
        service.create_account("org-a", "acct-1", "old@example.com")
        token = _register_operator(service, "org-b")
        with self.assertRaises(NotFoundError):
            service.apply_mailbox_migration("org-a", "acct-1", "new@example.com", token)
        self.assertEqual(self.storage.current_email("acct-1"), "old@example.com")

    def test_apply_audit_event_records_outcome_without_leaking_operator_token(self):
        service = AccountService(self.storage, mail_endpoint=None)
        service.create_account("org-a", "acct-1", "old@example.com")
        token = _register_operator(service, "org-a")

        service.apply_mailbox_migration("org-a", "acct-1", "new@example.com", token)

        events = self.storage.list_audit_events("org-a")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["action"], "mailbox_migration.apply")
        self.assertEqual(events[0]["outcome"], "completed")
        self.assertEqual(events[0]["operator_id"], "op-1")
        serialized = json.dumps(dict(events[0]))
        self.assertNotIn(token, serialized)

    def test_apply_conflict_audit_event_outcome_is_conflict(self):
        service = AccountService(self.storage, mail_endpoint=None)
        service.create_account("org-a", "acct-1", "a@example.com")
        service.create_account("org-a", "acct-2", "b@example.com")
        token = _register_operator(service, "org-a")

        with self.assertRaises(ConflictError):
            service.apply_mailbox_migration("org-a", "acct-1", "b@example.com", token)

        events = self.storage.list_audit_events("org-a")
        self.assertEqual(events[-1]["outcome"], "conflict")


class MigrationSummaryTests(ServiceTestCase):
    def test_summary_before_any_migration_reports_none_status_and_no_old_hash(self):
        service = AccountService(self.storage, mail_endpoint=None)
        service.create_account("org-a", "acct-1", "a@example.com")
        token = _register_operator(service, "org-a")

        summary = service.migration_summary("org-a", "acct-1", token)

        self.assertEqual(summary["status"], "none")
        self.assertIsNone(summary["old_mailbox_hash"])
        self.assertEqual(summary["current_mailbox_hash"], hash_mailbox_address("a@example.com"))
        self.assertEqual(summary["attempt_ids"], [])

    def test_summary_after_a_completed_migration_reports_both_hashes_and_status(self):
        service = AccountService(self.storage, mail_endpoint=None)
        service.create_account("org-a", "acct-1", "old@example.com")
        token = _register_operator(service, "org-a")
        service.apply_mailbox_migration("org-a", "acct-1", "new@example.com", token)

        summary = service.migration_summary("org-a", "acct-1", token)

        self.assertEqual(summary["status"], "completed")
        self.assertEqual(summary["old_mailbox_hash"], hash_mailbox_address("old@example.com"))
        self.assertEqual(summary["current_mailbox_hash"], hash_mailbox_address("new@example.com"))
        self.assertNotEqual(summary["old_mailbox_hash"], summary["current_mailbox_hash"])

    def test_summary_after_a_failed_migration_reports_failed_status(self):
        service = AccountService(self.storage, mail_endpoint=None)
        service.create_account("org-a", "acct-1", "a@example.com")
        service.create_account("org-a", "acct-2", "taken@example.com")
        token = _register_operator(service, "org-a")

        with self.assertRaises(ConflictError):
            service.apply_mailbox_migration("org-a", "acct-1", "taken@example.com", token)

        summary = service.migration_summary("org-a", "acct-1", token)
        self.assertEqual(summary["status"], "failed")
        self.assertEqual(summary["old_mailbox_hash"], hash_mailbox_address("a@example.com"))

    def test_summary_lists_delivery_attempt_ids_for_the_account(self):
        with FakeMailProvider([(503, "receipt-fail"), (200, "receipt-ok")]) as provider:
            service = AccountService(self.storage, mail_endpoint=provider.url)
            service.create_account("org-a", "acct-1", "a@example.com")
            service.start_recovery("org-a", "a@example.com")
            service.start_recovery("org-a", "a@example.com")
        attempt_ids = [
            row["attempt_id"]
            for row in self.storage._conn.execute(
                "SELECT attempt_id FROM delivery_attempts ORDER BY attempt_id ASC"
            ).fetchall()
        ]
        token = _register_operator(service, "org-a")

        summary = service.migration_summary("org-a", "acct-1", token)

        self.assertEqual(summary["attempt_ids"], attempt_ids)

    def test_summary_never_contains_a_plaintext_mailbox_address_or_any_token(self):
        with FakeMailProvider([(200, "receipt-ok")]) as provider:
            service = AccountService(self.storage, mail_endpoint=provider.url)
            service.create_account("org-a", "acct-1", "old@example.com")
            service.start_recovery("org-a", "old@example.com")
        request = self.storage.get_recovery_request(
            self.storage._conn.execute("SELECT request_id FROM recovery_requests").fetchone()["request_id"]
        )
        recovery_token = request["recovery_token"]
        token = _register_operator(service, "org-a")
        service.apply_mailbox_migration("org-a", "acct-1", "new@example.com", token)

        summary = service.migration_summary("org-a", "acct-1", token)

        serialized = json.dumps(summary)
        for secret_or_plaintext in ("old@example.com", "new@example.com", recovery_token, token):
            self.assertNotIn(secret_or_plaintext, serialized)

    def test_summary_missing_credential_is_auth_error(self):
        service = AccountService(self.storage, mail_endpoint=None)
        service.create_account("org-a", "acct-1", "a@example.com")
        with self.assertRaises(AuthError):
            service.migration_summary("org-a", "acct-1", "")
        with self.assertRaises(AuthError):
            service.migration_summary("org-a", "acct-1", "not-a-registered-token")

    def test_summary_wrong_role_is_forbidden(self):
        service = AccountService(self.storage, mail_endpoint=None)
        service.create_account("org-a", "acct-1", "a@example.com")
        token = _register_operator(service, "org-a", role="support")
        with self.assertRaises(ForbiddenError):
            service.migration_summary("org-a", "acct-1", token)

    def test_summary_operator_scoped_to_a_different_org_is_not_found(self):
        service = AccountService(self.storage, mail_endpoint=None)
        service.create_account("org-a", "acct-1", "a@example.com")
        token = _register_operator(service, "org-b")
        with self.assertRaises(NotFoundError):
            service.migration_summary("org-a", "acct-1", token)


class OperatorRegistrationTests(ServiceTestCase):
    def test_register_operator_never_returns_the_token(self):
        service = AccountService(self.storage, mail_endpoint=None)
        result = service.register_operator("org-a", "op-1", MIGRATION_OPERATOR_ROLE, "secret-token")
        self.assertNotIn("token", result)
        self.assertEqual(result, {"operator_id": "op-1", "organization_id": "org-a", "role": MIGRATION_OPERATOR_ROLE})

    def test_register_operator_rejects_duplicate_operator_id(self):
        service = AccountService(self.storage, mail_endpoint=None)
        service.register_operator("org-a", "op-1", MIGRATION_OPERATOR_ROLE, "secret-token")
        with self.assertRaises(ConflictError):
            service.register_operator("org-a", "op-1", MIGRATION_OPERATOR_ROLE, "another-token")

    def test_registered_operator_token_authenticates_across_a_fresh_service_instance(self):
        service = AccountService(self.storage, mail_endpoint=None)
        service.create_account("org-a", "acct-1", "old@example.com")
        service.register_operator("org-a", "op-1", MIGRATION_OPERATOR_ROLE, "secret-token")

        fresh = AccountService(self.storage, mail_endpoint=None)
        result = fresh.apply_mailbox_migration("org-a", "acct-1", "new@example.com", "secret-token")
        self.assertEqual(result["current_email"], "new@example.com")


class BoundedInputTests(ServiceTestCase):
    def test_rejects_oversized_identifier(self):
        service = AccountService(self.storage, mail_endpoint=None)
        with self.assertRaises(ValidationError):
            service.create_account("org-a", "x" * 200, "a@example.com")

    def test_rejects_malformed_email(self):
        service = AccountService(self.storage, mail_endpoint=None)
        with self.assertRaises(ValidationError):
            service.create_account("org-a", "acct-1", "not-an-email")


if __name__ == "__main__":
    unittest.main()
