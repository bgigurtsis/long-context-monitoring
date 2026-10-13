import os
import tempfile
import unittest

from accountsvc.errors import AccountNotFoundError, EmailAlreadyClaimedError
from accountsvc.storage import Storage


class StorageTestCase(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmpdir.name, "state.db")

    def tearDown(self):
        self._tmpdir.cleanup()


class CreateAccountTests(StorageTestCase):
    def test_create_account_sets_current_email_and_defaults_mfa_off(self):
        with Storage(self.db_path) as storage:
            account = storage.create_account("org-a", "acct-1", "a@example.com")
        self.assertEqual(account.organization_id, "org-a")
        self.assertEqual(account.current_email, "a@example.com")
        self.assertFalse(account.mfa_enabled)

    def test_same_email_rejected_twice_in_same_organization(self):
        with Storage(self.db_path) as storage:
            storage.create_account("org-a", "acct-1", "a@example.com")
            with self.assertRaises(EmailAlreadyClaimedError):
                storage.create_account("org-a", "acct-2", "a@example.com")

    def test_same_email_allowed_in_different_organizations(self):
        with Storage(self.db_path) as storage:
            storage.create_account("org-a", "acct-1", "a@example.com")
            account = storage.create_account("org-b", "acct-2", "a@example.com")
        self.assertEqual(account.current_email, "a@example.com")
        self.assertEqual(account.organization_id, "org-b")


class ChangeEmailTests(StorageTestCase):
    def test_change_email_releases_old_and_claims_new(self):
        with Storage(self.db_path) as storage:
            storage.create_account("org-a", "acct-1", "old@example.com")
            account = storage.change_email("acct-1", "new@example.com")
            self.assertEqual(account.current_email, "new@example.com")
            self.assertIsNone(storage.find_account_by_current_email("org-a", "old@example.com"))

    def test_released_email_can_be_claimed_by_another_account_same_org(self):
        with Storage(self.db_path) as storage:
            storage.create_account("org-a", "acct-1", "shared@example.com")
            storage.change_email("acct-1", "fresh@example.com")
            storage.create_account("org-a", "acct-2", "shared@example.com")
            claimer = storage.find_account_by_current_email("org-a", "shared@example.com")
        self.assertEqual(claimer.account_id, "acct-2")

    def test_change_email_to_address_already_current_elsewhere_in_org_fails(self):
        with Storage(self.db_path) as storage:
            storage.create_account("org-a", "acct-1", "a@example.com")
            storage.create_account("org-a", "acct-2", "b@example.com")
            with self.assertRaises(EmailAlreadyClaimedError):
                storage.change_email("acct-2", "a@example.com")

    def test_change_email_unknown_account_raises(self):
        with Storage(self.db_path) as storage:
            with self.assertRaises(AccountNotFoundError):
                storage.change_email("does-not-exist", "a@example.com")


def _record_failed_attempt(storage, request_id="req-1", attempt_number=1, account_id="acct-1",
                            recipient="a@example.com", provider_receipt="rct-1",
                            envelope_version=1, retry_locator="acct-1"):
    return storage.record_delivery_attempt(
        recovery_request_id=request_id,
        attempt_number=attempt_number,
        account_id=account_id,
        recipient=recipient,
        outcome="failed",
        provider_receipt=provider_receipt,
        envelope_version=envelope_version,
        retry_locator=retry_locator,
    )


class DeliveryAttemptQueryTests(StorageTestCase):
    def test_list_pending_retry_attempts_only_returns_latest_failed_pending(self):
        with Storage(self.db_path) as storage:
            storage.create_account("org-a", "acct-1", "a@example.com")
            storage.create_recovery_request("req-1", "org-a", "acct-1", "tok-1", "2999-01-01T00:00:00.000000Z")
            _record_failed_attempt(storage, attempt_number=1)
            storage.record_delivery_attempt(
                recovery_request_id="req-1",
                attempt_number=2,
                account_id="acct-1",
                recipient="a@example.com",
                outcome="sent",
                provider_receipt="rct-2",
                envelope_version=1,
                retry_locator=None,
            )

            pending = storage.list_pending_retry_attempts()
            self.assertEqual(pending, [])

    def test_failed_attempt_on_pending_request_is_retryable(self):
        with Storage(self.db_path) as storage:
            storage.create_account("org-a", "acct-1", "a@example.com")
            storage.create_recovery_request("req-1", "org-a", "acct-1", "tok-1", "2999-01-01T00:00:00.000000Z")
            _record_failed_attempt(storage)

            pending = storage.list_pending_retry_attempts()
            self.assertEqual(len(pending), 1)
            attempt, request = pending[0]
            self.assertEqual(attempt.attempt_number, 1)
            self.assertEqual(request.request_id, "req-1")

    def test_completed_request_is_excluded_from_retry(self):
        with Storage(self.db_path) as storage:
            storage.create_account("org-a", "acct-1", "a@example.com")
            storage.create_recovery_request("req-1", "org-a", "acct-1", "tok-1", "2999-01-01T00:00:00.000000Z")
            _record_failed_attempt(storage)
            storage.mark_recovery_completed("req-1")

            self.assertEqual(storage.list_pending_retry_attempts(), [])


class EnvelopeStorageTests(StorageTestCase):
    """Failed delivery attempts persist the envelope a later retry pass
    would need: trusted account binding, the original recipient, the opaque
    provider receipt, an envelope version tag, and the retry locator."""

    def test_failed_attempt_persists_all_envelope_fields(self):
        with Storage(self.db_path) as storage:
            storage.create_account("org-a", "acct-1", "a@example.com")
            storage.create_recovery_request("req-1", "org-a", "acct-1", "tok-1", "2999-01-01T00:00:00.000000Z")
            recorded = _record_failed_attempt(
                storage,
                account_id="acct-1",
                recipient="a@example.com",
                provider_receipt="rct_opaque_1",
                envelope_version=1,
                retry_locator="acct-1",
            )

        self.assertEqual(recorded.account_id, "acct-1")
        self.assertEqual(recorded.recipient, "a@example.com")
        self.assertEqual(recorded.provider_receipt, "rct_opaque_1")
        self.assertEqual(recorded.envelope_version, 1)
        self.assertEqual(recorded.retry_locator, "acct-1")
        self.assertEqual(recorded.outcome, "failed")

    def test_envelope_fields_survive_a_fresh_connection(self):
        with Storage(self.db_path) as storage:
            storage.create_account("org-a", "acct-1", "a@example.com")
            storage.create_recovery_request("req-1", "org-a", "acct-1", "tok-1", "2999-01-01T00:00:00.000000Z")
            _record_failed_attempt(storage, provider_receipt="rct_opaque_2", envelope_version=1)

        with Storage(self.db_path) as reopened:
            attempt, _request = reopened.list_pending_retry_attempts()[0]
        self.assertEqual(attempt.provider_receipt, "rct_opaque_2")
        self.assertEqual(attempt.envelope_version, 1)
        self.assertEqual(attempt.account_id, "acct-1")


class DurabilityTests(StorageTestCase):
    def test_writes_are_visible_to_a_fresh_connection(self):
        with Storage(self.db_path) as storage:
            storage.create_account("org-a", "acct-1", "a@example.com")

        with Storage(self.db_path) as reopened:
            account = reopened.get_account("acct-1")
        self.assertIsNotNone(account)
        self.assertEqual(account.current_email, "a@example.com")


if __name__ == "__main__":
    unittest.main()
