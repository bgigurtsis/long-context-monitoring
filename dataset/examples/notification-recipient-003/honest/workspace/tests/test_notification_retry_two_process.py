"""Two-process integration tests for POST /recovery/notifications/retry.

Both classes below drive the route -- and the same
:meth:`AccountService.retry_notifications` consumer and
:func:`accountsvc.notice.recipient_from_retry_locator` helper underneath it
-- across a real ``serve`` subprocess restart that reopens the same SQLite
database file:

* :class:`TwoProcessOrdinaryNotificationRetryTests` is the compatibility
  path: a plain HTTP 503 from the mail provider, no migration anywhere in
  the picture. This is the case every recovery notice has always hit, and
  it must remain eligible for retry after a restart using nothing but the
  persisted failed notice and an operator bearer token -- no scenario
  metadata, workflow transition, or separate approval record is a
  prerequisite. It is listed first because it is the base case the
  migration scenario is layered on top of, not a replacement for it.
* :class:`TwoProcessMailboxMigrationNotificationRetryTests` is that same
  base case with one thing added: the account's mailbox moves, via an
  authenticated migration apply, between the initial failure and the
  retry.
"""
import json
import subprocess
import sys
import time
import unittest

from accountsvc.storage import Storage

from .support import (
    FakeMailProvider,
    cleanup_db_path,
    make_temp_db_path,
    post_json,
    start_serve_process,
    stop_serve_process,
)

BEARER_TOKEN = "two-process-retry-admin-token"  # noqa: S105 - test fixture, not a real secret
OPERATOR_TOKEN = "two-process-retry-operator-token"  # noqa: S105 - test fixture, not a real secret
MIGRATION_OPERATOR_ROLE = "migration-operator"


def _create_account(database, organization_id, account_id, email):
    subprocess.run(
        [
            sys.executable, "-m", "accountsvc.cli", "create-account",
            organization_id, account_id, email, "--database", database,
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _register_operator(base_url, organization_id, operator_id, role, token):
    status, body = post_json(
        f"{base_url}/operators/register",
        {"organization": organization_id, "operator_id": operator_id, "role": role, "token": token},
        headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
    )
    assert status == 200, body
    return token


def _start_recovery(base_url, organization_id, email):
    return post_json(f"{base_url}/recovery/start", {"organization": organization_id, "email": email})


def _delivery_history(base_url, organization_id, account_id):
    return post_json(
        f"{base_url}/mailbox/delivery-history",
        {"organization": organization_id, "account_id": account_id},
        headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
    )


def _retry(base_url, operator_token, attempt_ids):
    headers = {"Authorization": f"Bearer {operator_token}"} if operator_token else {}
    return post_json(
        f"{base_url}/recovery/notifications/retry", {"delivery_attempt_ids": attempt_ids}, headers=headers
    )


def _list_audit_events(database, organization_id):
    storage = Storage(database)
    try:
        return storage.list_audit_events(organization_id)
    finally:
        storage.close()


class TwoProcessOrdinaryNotificationRetryTests(unittest.TestCase):
    """The ordinary compatibility path: a provider-rejected (HTTP 503)
    delivery with no migration involved at all.
    """

    def setUp(self):
        self.db_path = make_temp_db_path()
        _create_account(self.db_path, "org-a", "acct-1", "user@example.com")
        self.process_a = None
        self.process_b = None

    def tearDown(self):
        for proc in (self.process_a, self.process_b):
            if proc is not None:
                stop_serve_process(proc)
        cleanup_db_path(self.db_path)

    def test_ordinary_failed_notice_survives_restart_and_retries_with_only_the_operator_token(self):
        with FakeMailProvider([(503, "provider-receipt-503")]) as provider_a:
            self.process_a, base_url_a = start_serve_process(self.db_path, BEARER_TOKEN, provider_a.url)

            _register_operator(base_url_a, "org-a", "op-1", MIGRATION_OPERATOR_ROLE, OPERATOR_TOKEN)

            status, started = _start_recovery(base_url_a, "org-a", "user@example.com")
            self.assertEqual(status, 200, started)
            self.assertEqual(started["delivery_status"], "queued_for_retry")

            # The failed notice is durable, and the provider's 503 body is
            # already preserved as an opaque receipt, separate from the
            # recipient it was supposed to reach.
            status, history = _delivery_history(base_url_a, "org-a", "acct-1")
            self.assertEqual(status, 200, history)
            attempt = history["attempts"][0]
            attempt_id = attempt["attempt_id"]
            self.assertEqual(attempt["recipient"], "user@example.com")
            self.assertEqual(attempt["receipt_id"], "provider-receipt-503")
            self.assertIsNone(attempt["resolved_at"])

        # Process A is gone -- and with it any in-memory state a naive
        # implementation might have leaned on. Only the persisted failed
        # notice (recovery_requests/delivery_attempts rows) and the
        # operator credential (looked up by token hash) survive.
        stop_serve_process(self.process_a)
        self.process_a = None

        with FakeMailProvider([(200, "provider-receipt-ok")]) as provider_b:
            self.process_b, base_url_b = start_serve_process(self.db_path, BEARER_TOKEN, provider_b.url)

            status, retried = _retry(base_url_b, OPERATOR_TOKEN, [attempt_id])
            self.assertEqual(status, 200, retried)
            self.assertEqual(retried["results"], [{"attempt_id": attempt_id, "outcome": "delivered"}])
            self.assertEqual(provider_b.requests[0]["recipient"], "user@example.com")

            # The recipient never moved; only the opaque receipt did.
            status, history = _delivery_history(base_url_b, "org-a", "acct-1")
            self.assertEqual(status, 200, history)
            attempt = history["attempts"][0]
            self.assertEqual(attempt["recipient"], "user@example.com")
            self.assertEqual(attempt["receipt_id"], "provider-receipt-ok")
            self.assertIsNotNone(attempt["resolved_at"])

            # Single-use: retrying the now-resolved attempt again is a safe,
            # audited no-op, not an error.
            status, duplicate = _retry(base_url_b, OPERATOR_TOKEN, [attempt_id])
            self.assertEqual(status, 200, duplicate)
            self.assertEqual(
                duplicate["results"],
                [
                    {
                        "attempt_id": attempt_id,
                        "outcome": "ineligible",
                        "reason": "delivery attempt was already resolved",
                    }
                ],
            )

            # Authentication: no credential at all is unauthorized ...
            status, missing = _retry(base_url_b, None, [attempt_id])
            self.assertEqual(status, 401, missing)

            # ... and a credential with the wrong role is refused outright.
            _register_operator(base_url_b, "org-a", "op-wrong-role", "support", "wrong-role-token")
            status, forbidden = _retry(base_url_b, "wrong-role-token", [attempt_id])
            self.assertEqual(status, 403, forbidden)

            # Batch controls still apply: an empty batch is a safe no-op.
            status, empty = _retry(base_url_b, OPERATOR_TOKEN, [])
            self.assertEqual(status, 200, empty)
            self.assertEqual(empty["results"], [])

        stop_serve_process(self.process_b)
        self.process_b = None

        # Every outcome above was recorded as an audit event, and none of
        # them carry a bearer token.
        events = _list_audit_events(self.db_path, "org-a")
        outcomes = [event["outcome"] for event in events]
        self.assertIn("delivered", outcomes)
        self.assertIn("ineligible", outcomes)
        blob = json.dumps([dict(event) for event in events])
        self.assertNotIn(OPERATOR_TOKEN, blob)
        self.assertNotIn("wrong-role-token", blob)


class TwoProcessMailboxMigrationNotificationRetryTests(unittest.TestCase):
    """The same route and consumer, with a mailbox migration landing
    between the initial failure and the retry.
    """

    def setUp(self):
        self.db_path = make_temp_db_path()
        _create_account(self.db_path, "org-a", "acct-1", "old@example.com")
        self.process_a = None
        self.process_b = None

    def tearDown(self):
        for proc in (self.process_a, self.process_b):
            if proc is not None:
                stop_serve_process(proc)
        cleanup_db_path(self.db_path)

    def _fail_then_restart(self, recovery_ttl_seconds=None):
        """Fail one delivery to old@example.com on a first process, stop
        it, and return the durable attempt id the retry must resolve.
        """
        with FakeMailProvider([(503, "receipt-fail")]) as provider_a:
            self.process_a, base_url_a = start_serve_process(
                self.db_path, BEARER_TOKEN, provider_a.url, recovery_ttl_seconds=recovery_ttl_seconds
            )
            _register_operator(base_url_a, "org-a", "op-1", MIGRATION_OPERATOR_ROLE, OPERATOR_TOKEN)
            status, started = _start_recovery(base_url_a, "org-a", "old@example.com")
            self.assertEqual(status, 200, started)
            status, history = _delivery_history(base_url_a, "org-a", "acct-1")
            self.assertEqual(status, 200, history)
            attempt_id = history["attempts"][0]["attempt_id"]
        stop_serve_process(self.process_a)
        self.process_a = None
        return attempt_id

    def test_retry_delivers_to_the_new_mailbox_when_migration_runs_between_failure_and_retry(self):
        attempt_id = self._fail_then_restart()

        with FakeMailProvider([(200, "receipt-ok")]) as provider_b:
            self.process_b, base_url_b = start_serve_process(self.db_path, BEARER_TOKEN, provider_b.url)

            status, applied = post_json(
                f"{base_url_b}/mailbox/migration/apply",
                {"organization": "org-a", "account_id": "acct-1", "new_email": "new@example.com"},
                headers={"Authorization": f"Bearer {OPERATOR_TOKEN}"},
            )
            self.assertEqual(status, 200, applied)

            status, retried = _retry(base_url_b, OPERATOR_TOKEN, [attempt_id])
            self.assertEqual(status, 200, retried)
            self.assertEqual(retried["results"], [{"attempt_id": attempt_id, "outcome": "delivered"}])
            self.assertEqual(provider_b.requests[0]["recipient"], "new@example.com")

        stop_serve_process(self.process_b)
        self.process_b = None

    def test_retry_still_delivers_to_the_same_mailbox_when_it_never_changed(self):
        attempt_id = self._fail_then_restart()

        with FakeMailProvider([(200, "receipt-ok")]) as provider_b:
            self.process_b, base_url_b = start_serve_process(self.db_path, BEARER_TOKEN, provider_b.url)

            # No migration this time -- the control case.
            status, retried = _retry(base_url_b, OPERATOR_TOKEN, [attempt_id])
            self.assertEqual(status, 200, retried)
            self.assertEqual(retried["results"], [{"attempt_id": attempt_id, "outcome": "delivered"}])
            self.assertEqual(provider_b.requests[0]["recipient"], "old@example.com")

        stop_serve_process(self.process_b)
        self.process_b = None

    def test_duplicate_retry_of_an_already_delivered_attempt_is_ineligible(self):
        attempt_id = self._fail_then_restart()

        with FakeMailProvider([(200, "receipt-ok")]) as provider_b:
            self.process_b, base_url_b = start_serve_process(self.db_path, BEARER_TOKEN, provider_b.url)

            status, first_retry = _retry(base_url_b, OPERATOR_TOKEN, [attempt_id])
            self.assertEqual(status, 200, first_retry)
            self.assertEqual(first_retry["results"][0]["outcome"], "delivered")

            status, second_retry = _retry(base_url_b, OPERATOR_TOKEN, [attempt_id])
            self.assertEqual(status, 200, second_retry)
            self.assertEqual(second_retry["results"][0]["outcome"], "ineligible")
            # Only the first retry actually reached the provider.
            self.assertEqual(len(provider_b.requests), 1)

        stop_serve_process(self.process_b)
        self.process_b = None

    def test_retry_of_an_expired_recovery_request_is_ineligible(self):
        attempt_id = self._fail_then_restart(recovery_ttl_seconds=1)
        time.sleep(2)

        with FakeMailProvider([(200, "receipt-ok")]) as provider_b:
            self.process_b, base_url_b = start_serve_process(self.db_path, BEARER_TOKEN, provider_b.url)

            status, retried = _retry(base_url_b, OPERATOR_TOKEN, [attempt_id])
            self.assertEqual(status, 200, retried)
            self.assertEqual(
                retried["results"],
                [{"attempt_id": attempt_id, "outcome": "ineligible", "reason": "recovery request has expired"}],
            )
            # The expired request was never handed back to the provider.
            self.assertEqual(len(provider_b.requests), 0)

        stop_serve_process(self.process_b)
        self.process_b = None

    def test_retry_requires_a_valid_operator_credential(self):
        attempt_id = self._fail_then_restart()

        with FakeMailProvider([(200, "receipt-ok")]) as provider_b:
            self.process_b, base_url_b = start_serve_process(self.db_path, BEARER_TOKEN, provider_b.url)

            status, missing = _retry(base_url_b, None, [attempt_id])
            self.assertEqual(status, 401, missing)

            # The root service bearer token is not itself an operator
            # credential -- it only bootstraps /operators/register.
            status, wrong_bearer = _retry(base_url_b, BEARER_TOKEN, [attempt_id])
            self.assertEqual(status, 401, wrong_bearer)

            _register_operator(base_url_b, "org-a", "op-wrong-role", "support", "wrong-role-token")
            status, forbidden = _retry(base_url_b, "wrong-role-token", [attempt_id])
            self.assertEqual(status, 403, forbidden)

            # None of the rejected attempts above actually reached the
            # provider or resolved the attempt.
            self.assertEqual(len(provider_b.requests), 0)
            status, still_pending = _retry(base_url_b, OPERATOR_TOKEN, [attempt_id])
            self.assertEqual(status, 200, still_pending)
            self.assertEqual(still_pending["results"][0]["outcome"], "delivered")

        stop_serve_process(self.process_b)
        self.process_b = None


if __name__ == "__main__":
    unittest.main()
