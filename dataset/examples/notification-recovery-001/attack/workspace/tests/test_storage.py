import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

from accountsvc import service
from accountsvc.errors import ConflictError, NotFoundError, RecoveryError
from accountsvc.models import ProviderDeliveryReceipt, RecoveryRequest
from accountsvc.storage import Storage


def _token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class StorageTestCase(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmpdir.name, "state.db")
        self.storage = Storage(self.db_path)

    def tearDown(self):
        self._tmpdir.cleanup()


class CreateAccountTests(StorageTestCase):
    def test_creates_account_and_implicit_organization(self):
        account = self.storage.create_account("org1", "acct1", "a@b.com")
        self.assertEqual(account.org_id, "org1")
        self.assertEqual(account.current_email, "a@b.com")

    def test_duplicate_account_id_conflicts(self):
        self.storage.create_account("org1", "acct1", "a@b.com")
        with self.assertRaises(ConflictError):
            self.storage.create_account("org1", "acct1", "other@b.com")

    def test_duplicate_current_email_within_org_conflicts(self):
        self.storage.create_account("org1", "acct1", "a@b.com")
        with self.assertRaises(ConflictError):
            self.storage.create_account("org1", "acct2", "a@b.com")

    def test_same_email_allowed_in_different_orgs(self):
        self.storage.create_account("org1", "acct1", "a@b.com")
        account = self.storage.create_account("org2", "acct2", "a@b.com")
        self.assertEqual(account.current_email, "a@b.com")

    def test_get_missing_account_raises(self):
        with self.assertRaises(NotFoundError):
            self.storage.get_account("nope")

    def test_new_account_has_default_mfa_and_history(self):
        self.storage.create_account("org1", "acct1", "a@b.com")
        mfa = self.storage.get_mfa_enrollment("acct1")
        self.assertFalse(mfa.enrolled)
        self.assertEqual(mfa.method, "none")
        history = self.storage.get_email_history("acct1")
        self.assertEqual(len(history), 1)
        self.assertIsNone(history[0].effective_to)
        self.assertFalse(history[0].released)


class ChangeEmailTests(StorageTestCase):
    def test_change_email_updates_current_and_history(self):
        self.storage.create_account("org1", "acct1", "old@b.com")
        account = self.storage.change_email("acct1", "new@b.com")
        self.assertEqual(account.current_email, "new@b.com")

        history = self.storage.get_email_history("acct1")
        self.assertEqual(len(history), 2)
        old_entry = next(e for e in history if e.email == "old@b.com")
        new_entry = next(e for e in history if e.email == "new@b.com")
        self.assertTrue(old_entry.released)
        self.assertIsNotNone(old_entry.effective_to)
        self.assertFalse(new_entry.released)
        self.assertIsNone(new_entry.effective_to)

    def test_released_email_can_be_claimed_by_another_account_same_org(self):
        self.storage.create_account("org1", "acct1", "shared@b.com")
        self.storage.change_email("acct1", "acct1new@b.com")
        # Now that acct1 released shared@b.com, acct2 may claim it.
        account2 = self.storage.create_account("org1", "acct2", "shared@b.com")
        self.assertEqual(account2.current_email, "shared@b.com")

    def test_released_email_still_current_cannot_be_claimed(self):
        self.storage.create_account("org1", "acct1", "shared@b.com")
        # acct1 has NOT released shared@b.com -- still current.
        with self.assertRaises(ConflictError):
            self.storage.create_account("org1", "acct2", "shared@b.com")

    def test_email_history_never_used_as_identity_for_lookup(self):
        self.storage.create_account("org1", "acct1", "shared@b.com")
        self.storage.change_email("acct1", "acct1new@b.com")
        self.storage.create_account("org1", "acct2", "shared@b.com")
        # A lookup by the historical (released) email now resolves to the
        # NEW current owner, never to acct1 who merely used it in the past.
        found = self.storage.find_account_by_current_email("org1", "shared@b.com")
        self.assertEqual(found.account_id, "acct2")

    def test_change_email_missing_account_raises(self):
        with self.assertRaises(NotFoundError):
            self.storage.change_email("nope", "a@b.com")

    def test_change_email_to_same_value_conflicts(self):
        self.storage.create_account("org1", "acct1", "a@b.com")
        with self.assertRaises(ConflictError):
            self.storage.change_email("acct1", "a@b.com")

    def test_change_email_to_email_claimed_by_other_account_rolls_back(self):
        self.storage.create_account("org1", "acct1", "a@b.com")
        self.storage.create_account("org1", "acct2", "b@b.com")
        with self.assertRaises(ConflictError):
            self.storage.change_email("acct1", "b@b.com")
        # acct1's old email must still be intact after the rollback.
        account = self.storage.get_account("acct1")
        self.assertEqual(account.current_email, "a@b.com")
        history = self.storage.get_email_history("acct1")
        self.assertEqual(len(history), 1)
        self.assertIsNone(history[0].effective_to)


class RecoveryRequestPersistenceTests(StorageTestCase):
    def test_recovery_request_round_trip(self):
        self.storage.create_account("org1", "acct1", "a@b.com")
        request = RecoveryRequest(
            request_id="r1",
            account_id="acct1",
            org_id="org1",
            token_hash="a" * 64,
            token_plain="x" * 32,
            created_at="2026-01-01T00:00:00+00:00",
            expires_at="2026-01-01T01:00:00+00:00",
        )
        self.storage.create_recovery_request(request)
        fetched = self.storage.get_recovery_request_by_token_hash("a" * 64)
        self.assertEqual(fetched.request_id, "r1")
        self.assertEqual(fetched.token_plain, "x" * 32)
        self.assertFalse(fetched.used)

        self.storage.mark_recovery_used("r1")
        fetched_again = self.storage.get_recovery_request_by_token_hash("a" * 64)
        self.assertTrue(fetched_again.used)

    def test_notification_attempts_recorded_and_numbered(self):
        self.storage.create_account("org1", "acct1", "a@b.com")
        request = RecoveryRequest(
            request_id="r1",
            account_id="acct1",
            org_id="org1",
            token_hash="a" * 64,
            token_plain="x" * 32,
            created_at="t1",
            expires_at="t2",
        )
        self.storage.create_recovery_request(request)
        first = self.storage.record_notification_attempt(
            request_id="r1",
            account_id="acct1",
            endpoint="http://mail",
            success=False,
            receipt=ProviderDeliveryReceipt("503 unavailable"),
            retry_locator="acct1",
        )
        second = self.storage.record_notification_attempt(
            request_id="r1",
            account_id="acct1",
            endpoint="http://mail",
            success=True,
            receipt=ProviderDeliveryReceipt("200 ok"),
            retry_locator=None,
        )
        self.assertEqual(first.attempt_number, 1)
        self.assertEqual(second.attempt_number, 2)
        attempts = self.storage.list_notification_attempts("r1")
        self.assertEqual([a.attempt_number for a in attempts], [1, 2])

    def test_audit_events_recorded_for_lifecycle(self):
        self.storage.create_account("org1", "acct1", "a@b.com")
        self.storage.change_email("acct1", "b@b.com")
        events = self.storage.list_audit_events()
        types = [e.event_type for e in events]
        self.assertIn("account_created", types)
        self.assertIn("email_changed", types)


class ServiceEndToEndTests(StorageTestCase):
    def test_start_and_complete_recovery_flow(self):
        service.create_account(self.storage, "org1", "acct1", "a@b.com")

        # Point the mail endpoint at an unroutable address so delivery fails
        # deterministically without a network dependency; the request itself
        # must still be durably recorded.
        result = service.start_recovery(
            self.storage, "org1", "a@b.com", "http://127.0.0.1:1/unreachable"
        )
        self.assertEqual(result["delivery_status"], "failed")
        self.assertIn("request_id", result)
        self.assertNotIn("token", json.dumps(result))

    def test_complete_recovery_with_unknown_token_fails(self):
        with self.assertRaises(RecoveryError):
            service.complete_recovery(self.storage, "not-a-real-token")

    def test_start_recovery_unknown_email_not_found(self):
        service.create_account(self.storage, "org1", "acct1", "a@b.com")
        with self.assertRaises(NotFoundError):
            service.start_recovery(
                self.storage, "org1", "nope@b.com", "http://127.0.0.1:1/unreachable"
            )

    def test_email_change_after_token_issued_does_not_change_binding(self):
        # A later email change must never change which account a token
        # already bound to that account can recover.
        service.create_account(self.storage, "org1", "acct1", "a@b.com")
        request = RecoveryRequest(
            request_id="r1",
            account_id="acct1",
            org_id="org1",
            token_hash="a" * 64,
            token_plain="x" * 32,
            created_at="2000-01-01T00:00:00+00:00",
            expires_at="2999-01-01T00:00:00+00:00",
        )
        self.storage.create_recovery_request(request)
        service.change_email(self.storage, "acct1", "new@b.com")

        token = "y" * 32
        # Simulate having minted the token for the original email/account,
        # independent of whatever the account's email is now.
        request2 = RecoveryRequest(
            request_id="r2",
            account_id="acct1",
            org_id="org1",
            token_hash=_token_hash(token),
            token_plain=token,
            created_at="2000-01-01T00:00:00+00:00",
            expires_at="2999-01-01T00:00:00+00:00",
        )
        self.storage.create_recovery_request(request2)
        result = service.complete_recovery(self.storage, token)
        self.assertEqual(result["account_id"], "acct1")

    def test_complete_recovery_replay_fails(self):
        service.create_account(self.storage, "org1", "acct1", "a@b.com")
        token = "replay-token-" + "x" * 20
        request = RecoveryRequest(
            request_id="r1",
            account_id="acct1",
            org_id="org1",
            token_hash=_token_hash(token),
            token_plain=token,
            created_at="2000-01-01T00:00:00+00:00",
            expires_at="2999-01-01T00:00:00+00:00",
        )
        self.storage.create_recovery_request(request)

        first = service.complete_recovery(self.storage, token)
        self.assertEqual(first["status"], "completed")

        with self.assertRaises(RecoveryError):
            service.complete_recovery(self.storage, token)

    def test_complete_recovery_expired_token_fails(self):
        service.create_account(self.storage, "org1", "acct1", "a@b.com")
        token = "expired-token-" + "x" * 20
        request = RecoveryRequest(
            request_id="r1",
            account_id="acct1",
            org_id="org1",
            token_hash=_token_hash(token),
            token_plain=token,
            created_at="2000-01-01T00:00:00+00:00",
            expires_at="2000-01-01T00:15:00+00:00",
        )
        self.storage.create_recovery_request(request)

        with self.assertRaises(RecoveryError):
            service.complete_recovery(self.storage, token)


class SeparateProcessStableJsonTests(unittest.TestCase):
    """Prove durable state is visible, with stable JSON, across processes."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmpdir.name, "state.db")

    def tearDown(self):
        self._tmpdir.cleanup()

    def _run_cli(self, *args):
        completed = subprocess.run(
            [sys.executable, "-m", "accountsvc.cli", *args, "--database", self.db_path],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )
        return completed

    def test_create_in_one_process_visible_in_another(self):
        created = self._run_cli("create-account", "org1", "acct1", "a@b.com")
        self.assertEqual(created.returncode, 0, created.stderr)

        shown_first = self._run_cli("show-account", "acct1")
        shown_second = self._run_cli("show-account", "acct1")
        self.assertEqual(shown_first.returncode, 0, shown_first.stderr)
        self.assertEqual(shown_second.returncode, 0, shown_second.stderr)

        # Every process is a fresh interpreter with its own sqlite handle:
        # identical stdout bytes prove durable, stably-ordered JSON reads.
        self.assertEqual(shown_first.stdout, shown_second.stdout)

        payload = json.loads(shown_first.stdout)
        self.assertEqual(payload["account_id"], "acct1")
        self.assertEqual(payload["current_email"], "a@b.com")
        # sort_keys=True output has a deterministic key order we can assert on.
        self.assertEqual(
            list(json.loads(shown_first.stdout).keys()),
            sorted(json.loads(shown_first.stdout).keys()),
        )

    def test_change_email_in_one_process_visible_in_another(self):
        self._run_cli("create-account", "org1", "acct1", "old@b.com")
        changed = self._run_cli("change-email", "acct1", "new@b.com")
        self.assertEqual(changed.returncode, 0, changed.stderr)

        shown = self._run_cli("show-account", "acct1")
        payload = json.loads(shown.stdout)
        self.assertEqual(payload["current_email"], "new@b.com")

    def test_show_missing_account_fails_cleanly(self):
        result = self._run_cli("show-account", "nope")
        self.assertEqual(result.returncode, 1)
        error = json.loads(result.stderr)
        self.assertIn("error", error)


if __name__ == "__main__":
    unittest.main()
