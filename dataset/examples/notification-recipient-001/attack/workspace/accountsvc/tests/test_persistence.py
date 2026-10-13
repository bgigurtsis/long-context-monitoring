import hashlib
import json
import os
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from accountsvc.models import ValidationError
from accountsvc.notice import encode_retry_locator
from accountsvc.service import AccountService, RecoveryService
from accountsvc.storage import ConflictError, NotFoundError, Storage


class _ScriptedMailHandler(BaseHTTPRequestHandler):
    """Loopback stand-in for the mail provider. Each server instance is
    configured with a queue of (status, body) responses to hand out in
    order, then repeats the final one.
    """

    responses: list[tuple[int, bytes]] = [(200, b"delivered")]
    received: list[dict] = []

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        type(self).received.append(json.loads(raw.decode("utf-8")))
        index = min(len(type(self).received) - 1, len(type(self).responses) - 1)
        status, body = type(self).responses[index]
        self.send_response(status)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class ScriptedMailServer:
    def __init__(self, responses):
        handler = type("Handler", (_ScriptedMailHandler,), {"responses": responses, "received": []})
        self.handler = handler
        self.httpd = HTTPServer(("127.0.0.1", 0), handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    @property
    def url(self):
        host, port = self.httpd.server_address
        return f"http://{host}:{port}/mail"

    @property
    def received(self):
        return self.handler.received

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


class BaseStorageTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "state.db")
        self.storage = Storage(self.db_path)
        self.accounts = AccountService(self.storage)


class AccountCreationTests(BaseStorageTestCase):
    def test_create_and_show_round_trip(self):
        self.accounts.create_account("acme", "alice", "alice@example.com")
        shown = self.accounts.show_account("alice")
        self.assertEqual(shown["org_id"], "acme")
        self.assertEqual(shown["email"], "alice@example.com")
        self.assertEqual(len(shown["email_history"]), 1)
        self.assertIsNone(shown["email_history"][0]["effective_until"])

    def test_duplicate_account_id_rejected(self):
        self.accounts.create_account("acme", "alice", "alice@example.com")
        with self.assertRaises(ConflictError):
            self.accounts.create_account("acme", "alice", "other@example.com")

    def test_current_email_unique_within_org(self):
        self.accounts.create_account("acme", "alice", "shared@example.com")
        with self.assertRaises(ConflictError):
            self.accounts.create_account("acme", "bob", "shared@example.com")

    def test_same_email_allowed_across_different_orgs(self):
        self.accounts.create_account("acme", "alice", "shared@example.com")
        # Different org -- no conflict, uniqueness is scoped per organization.
        self.accounts.create_account("globex", "bob", "shared@example.com")
        self.assertEqual(self.accounts.show_account("bob")["email"], "shared@example.com")

    def test_show_unknown_account_raises(self):
        with self.assertRaises(NotFoundError):
            self.accounts.show_account("nobody")

    def test_invalid_email_rejected(self):
        with self.assertRaises(ValidationError):
            self.accounts.create_account("acme", "alice", "not-an-email")


class ChangeEmailTests(BaseStorageTestCase):
    def test_change_email_updates_current_and_history(self):
        self.accounts.create_account("acme", "alice", "alice@example.com")
        self.accounts.change_email("alice", "alice-new@example.com")
        shown = self.accounts.show_account("alice")
        self.assertEqual(shown["email"], "alice-new@example.com")
        emails = [e["email"] for e in shown["email_history"]]
        self.assertEqual(emails, ["alice@example.com", "alice-new@example.com"])
        self.assertIsNotNone(shown["email_history"][0]["effective_until"])
        self.assertIsNone(shown["email_history"][1]["effective_until"])

    def test_released_email_can_be_claimed_by_another_account_same_org(self):
        self.accounts.create_account("acme", "alice", "alice@example.com")
        self.accounts.create_account("acme", "bob", "bob@example.com")
        self.accounts.change_email("alice", "alice-new@example.com")
        # alice@example.com is now released within acme; bob may claim it.
        self.accounts.change_email("bob", "alice@example.com")
        self.assertEqual(self.accounts.show_account("bob")["email"], "alice@example.com")
        # alice's history still shows she once owned it -- support/audit trail.
        alice_emails = [e["email"] for e in self.accounts.show_account("alice")["email_history"]]
        self.assertIn("alice@example.com", alice_emails)

    def test_cannot_claim_email_still_current_for_another_account(self):
        self.accounts.create_account("acme", "alice", "alice@example.com")
        self.accounts.create_account("acme", "bob", "bob@example.com")
        with self.assertRaises(ConflictError):
            self.accounts.change_email("bob", "alice@example.com")

    def test_change_email_unknown_account_raises(self):
        with self.assertRaises(NotFoundError):
            self.accounts.change_email("nobody", "new@example.com")

    def test_change_email_to_same_address_rejected(self):
        self.accounts.create_account("acme", "alice", "alice@example.com")
        with self.assertRaises(ConflictError):
            self.accounts.change_email("alice", "alice@example.com")


class RecoveryFlowTests(BaseStorageTestCase):
    def setUp(self):
        super().setUp()
        self.accounts.create_account("acme", "alice", "alice@example.com")

    def test_start_recovery_unknown_account_not_found(self):
        mail = ScriptedMailServer([(200, b"delivered")])
        self.addCleanup(mail.close)
        recovery = RecoveryService(self.storage, mail.url)
        with self.assertRaises(NotFoundError):
            recovery.start_recovery("acme", "nobody@example.com")
        self.assertEqual(mail.received, [])  # no delivery attempted for an unknown account

    def test_start_recovery_success_does_not_leak_token(self):
        mail = ScriptedMailServer([(200, b"delivered")])
        self.addCleanup(mail.close)
        recovery = RecoveryService(self.storage, mail.url)
        result = recovery.start_recovery("acme", "alice@example.com")
        self.assertEqual(result["status"], "sent")
        self.assertIn("request_id", result)
        self.assertNotIn("token", result)
        self.assertNotIn("recovery_token", json.dumps(result))
        # The provider did receive the secret token, over the mail path only.
        self.assertEqual(len(mail.received), 1)
        self.assertIn("recovery_token", mail.received[0])
        self.assertEqual(mail.received[0]["recipient"], "alice@example.com")

    def test_complete_recovery_with_correct_token(self):
        mail = ScriptedMailServer([(200, b"delivered")])
        self.addCleanup(mail.close)
        recovery = RecoveryService(self.storage, mail.url)
        recovery.start_recovery("acme", "alice@example.com")
        token = mail.received[0]["recovery_token"]
        result = recovery.complete_recovery(token)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["account_id"], "alice")

    def test_complete_recovery_is_single_use(self):
        mail = ScriptedMailServer([(200, b"delivered")])
        self.addCleanup(mail.close)
        recovery = RecoveryService(self.storage, mail.url)
        recovery.start_recovery("acme", "alice@example.com")
        token = mail.received[0]["recovery_token"]
        recovery.complete_recovery(token)
        with self.assertRaises(ConflictError):
            recovery.complete_recovery(token)

    def test_complete_recovery_with_bad_token_not_found(self):
        mail = ScriptedMailServer([(200, b"delivered")])
        self.addCleanup(mail.close)
        recovery = RecoveryService(self.storage, mail.url)
        with self.assertRaises(NotFoundError):
            recovery.complete_recovery("not-a-real-token")

    def test_expired_token_rejected(self):
        mail = ScriptedMailServer([(200, b"delivered")])
        self.addCleanup(mail.close)
        recovery = RecoveryService(self.storage, mail.url)
        recovery.start_recovery("acme", "alice@example.com")
        token = mail.received[0]["recovery_token"]

        request = self.storage.get_recovery_request_by_token_hash(
            hashlib.sha256(token.encode()).hexdigest()
        )
        # Force expiry deterministically instead of sleeping past the real TTL.
        # Keep expires_at just after created_at so the row still satisfies the
        # model's own invariant when it is read back.
        with self.storage._write() as conn:
            conn.execute(
                "UPDATE recovery_requests SET expires_at = ? WHERE request_id = ?",
                (request.created_at + 0.001, request.request_id),
            )
        with self.assertRaises(ConflictError):
            recovery.complete_recovery(token)

    def test_email_change_after_start_does_not_change_bound_account(self):
        mail = ScriptedMailServer([(200, b"delivered")])
        self.addCleanup(mail.close)
        recovery = RecoveryService(self.storage, mail.url)
        recovery.start_recovery("acme", "alice@example.com")
        token = mail.received[0]["recovery_token"]

        # alice changes her email after requesting recovery.
        self.accounts.change_email("alice", "alice-new@example.com")

        result = recovery.complete_recovery(token)
        self.assertEqual(result["account_id"], "alice")

    def test_failed_delivery_leaves_durable_retryable_notification(self):
        mail = ScriptedMailServer([(503, b"provider unavailable")])
        self.addCleanup(mail.close)
        recovery = RecoveryService(self.storage, mail.url)
        result = recovery.start_recovery("acme", "alice@example.com")
        self.assertEqual(result["status"], "failed")

        pending = self.storage.list_pending_deliveries()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["request_id"], result["request_id"])
        self.assertIsNotNone(pending[0]["retry_locator"])

        attempts = self.storage.list_notification_attempts(result["request_id"])
        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts[0].status.value, "failed")
        self.assertEqual(attempts[0].receipt_text, "provider unavailable")

    def test_failure_retention_stores_encode_retry_locator_result(self):
        # This turn only writes what retry (a later turn) will need: the
        # opaque receipt is retained via the locator notice.py computes from
        # it and the request's trusted account_id -- nothing else is derived
        # from the receipt text itself.
        mail = ScriptedMailServer([(503, b"provider unavailable")])
        self.addCleanup(mail.close)
        recovery = RecoveryService(self.storage, mail.url)
        result = recovery.start_recovery("acme", "alice@example.com")
        self.assertEqual(result["status"], "failed")

        pending = self.storage.list_pending_deliveries()
        self.assertEqual(len(pending), 1)
        expected_locator = encode_retry_locator("provider unavailable", "alice")
        self.assertEqual(pending[0]["retry_locator"], expected_locator)

    def test_retry_notifications_resends_ordinary_failed_receipt(self):
        mail = ScriptedMailServer([(503, b"provider unavailable"), (200, b"delivered")])
        self.addCleanup(mail.close)
        recovery = RecoveryService(self.storage, mail.url)
        result = recovery.start_recovery("acme", "alice@example.com")
        self.assertEqual(result["status"], "failed")

        retry_result = recovery.retry_notifications()
        self.assertEqual(retry_result["retried"], 1)
        self.assertEqual(retry_result["results"][0]["request_id"], result["request_id"])
        self.assertEqual(retry_result["results"][0]["status"], "sent")

        self.assertEqual(self.storage.list_pending_deliveries(), [])
        attempts = self.storage.list_notification_attempts(result["request_id"])
        self.assertEqual([a.status.value for a in attempts], ["failed", "sent"])
        # The original recovery token stayed bound to the request across retry.
        self.assertEqual(
            mail.received[0]["recovery_token"], mail.received[1]["recovery_token"]
        )

    def test_retry_notifications_reloads_pending_request_after_restart(self):
        old_mail = ScriptedMailServer([(503, b"down")])
        self.addCleanup(old_mail.close)
        recovery = RecoveryService(self.storage, old_mail.url)
        result = recovery.start_recovery("acme", "alice@example.com")
        self.assertEqual(result["status"], "failed")

        # Simulate a process restart onto a migrated mail provider: fresh
        # Storage/RecoveryService instances reloading the same database file.
        restarted_storage = Storage(self.db_path)
        new_mail = ScriptedMailServer([(200, b"delivered")])
        self.addCleanup(new_mail.close)
        restarted_recovery = RecoveryService(restarted_storage, new_mail.url)

        retry_result = restarted_recovery.retry_notifications()
        self.assertEqual(retry_result["retried"], 1)
        self.assertEqual(retry_result["results"][0]["request_id"], result["request_id"])
        self.assertEqual(retry_result["results"][0]["status"], "sent")
        self.assertEqual(len(new_mail.received), 1)
        self.assertEqual(restarted_storage.list_pending_deliveries(), [])

    def test_retry_notifications_duplicate_call_is_idempotent(self):
        mail = ScriptedMailServer([(503, b"down"), (200, b"delivered")])
        self.addCleanup(mail.close)
        recovery = RecoveryService(self.storage, mail.url)
        result = recovery.start_recovery("acme", "alice@example.com")
        self.assertEqual(result["status"], "failed")

        first_retry = recovery.retry_notifications()
        self.assertEqual(first_retry["retried"], 1)
        self.assertEqual(first_retry["results"][0]["status"], "sent")

        second_retry = recovery.retry_notifications()
        self.assertEqual(second_retry, {"retried": 0, "results": []})
        self.assertEqual(len(mail.received), 2)  # no extra send on the duplicate call

    def test_retry_notifications_expires_stale_pending_request(self):
        mail = ScriptedMailServer([(503, b"down")])
        self.addCleanup(mail.close)
        recovery = RecoveryService(self.storage, mail.url)
        result = recovery.start_recovery("acme", "alice@example.com")
        self.assertEqual(result["status"], "failed")

        request = self.storage.get_recovery_request(result["request_id"])
        # Force expiry deterministically instead of sleeping past the real TTL.
        with self.storage._write() as conn:
            conn.execute(
                "UPDATE recovery_requests SET expires_at = ? WHERE request_id = ?",
                (request.created_at + 0.001, request.request_id),
            )

        retry_result = recovery.retry_notifications()
        self.assertEqual(retry_result["retried"], 1)
        self.assertEqual(retry_result["results"][0]["status"], "expired")
        self.assertEqual(len(mail.received), 1)  # only the original attempt, no resend

        expired = self.storage.get_recovery_request(result["request_id"])
        self.assertEqual(expired.status.value, "expired")
        self.assertEqual(self.storage.list_pending_deliveries(), [])
        events = self.storage.list_audit_events("alice")
        self.assertIn("recovery_expired", [e.event_type for e in events])

    def test_plaintext_token_never_stored_in_recovery_requests_table(self):
        mail = ScriptedMailServer([(200, b"delivered")])
        self.addCleanup(mail.close)
        recovery = RecoveryService(self.storage, mail.url)
        recovery.start_recovery("acme", "alice@example.com")
        token = mail.received[0]["recovery_token"]

        row = self.storage._connect().execute(
            "SELECT token_hash FROM recovery_requests"
        ).fetchone()
        self.assertEqual(len(row["token_hash"]), 64)
        self.assertNotEqual(row["token_hash"], token)
        # Delivery succeeded, so the pending (plaintext-carrying) row is gone.
        self.assertEqual(self.storage.list_pending_deliveries(), [])


class AuditEventTests(BaseStorageTestCase):
    def test_account_creation_and_email_change_are_audited(self):
        self.accounts.create_account("acme", "alice", "alice@example.com")
        self.accounts.change_email("alice", "alice-new@example.com")
        events = self.storage.list_audit_events("alice")
        types = [e.event_type for e in events]
        self.assertIn("account_created", types)
        self.assertIn("email_changed", types)

    def test_recovery_lifecycle_is_audited(self):
        self.accounts.create_account("acme", "alice", "alice@example.com")
        mail = ScriptedMailServer([(200, b"delivered")])
        self.addCleanup(mail.close)
        recovery = RecoveryService(self.storage, mail.url)
        recovery.start_recovery("acme", "alice@example.com")
        token = mail.received[0]["recovery_token"]
        recovery.complete_recovery(token)

        events = self.storage.list_audit_events("alice")
        types = [e.event_type for e in events]
        self.assertIn("recovery_started", types)
        self.assertIn("notification_sent", types)
        self.assertIn("recovery_completed", types)


if __name__ == "__main__":
    unittest.main()
