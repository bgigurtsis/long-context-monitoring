import time
import unittest
from typing import List

from accountsvc import db, notice
from accountsvc.errors import (
    AuthorizationError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)
from accountsvc.mailer import MailResult
from accountsvc.recovery import RecoveryService
from accountsvc.repository import Repository


class FakeMailClient:
    """Records every call and replays a scripted sequence of results."""

    def __init__(self, results: List[MailResult]):
        self._results = list(results)
        self.calls: List[tuple[str, str]] = []

    def send_recovery_notification(self, recipient: str, recovery_token: str) -> MailResult:
        self.calls.append((recipient, recovery_token))
        if len(self._results) > 1:
            return self._results.pop(0)
        return self._results[0]


class RecoveryServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = db.connect(":memory:")
        self.repo = Repository(self.conn)
        self.repo.create_organization("ORG_A")
        self.repo.create_account("ORG_A", "ACC_1", "person@example.test")

    def tearDown(self) -> None:
        self.conn.close()

    def test_start_unknown_email_raises(self) -> None:
        mailer = FakeMailClient([MailResult(True, "receipt-1")])
        service = RecoveryService(self.repo, mailer)
        with self.assertRaises(NotFoundError):
            service.start("ORG_A", "nobody@example.test")

    def test_start_success_records_delivery(self) -> None:
        mailer = FakeMailClient([MailResult(True, "receipt-1")])
        service = RecoveryService(self.repo, mailer)
        result = service.start("ORG_A", "person@example.test")
        self.assertEqual(result["delivery_status"], "sent")
        self.assertNotIn("token", result)
        self.assertNotIn("recovery_token", result)

        attempts = self.repo.list_notification_attempts(result["request_id"])
        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts[0]["outcome"], "success")

    def test_start_failure_queues_retry(self) -> None:
        mailer = FakeMailClient([MailResult(False, "provider-down", error="timeout")])
        service = RecoveryService(self.repo, mailer)
        result = service.start("ORG_A", "person@example.test")
        self.assertEqual(result["delivery_status"], "queued_for_retry")

        pending = self.repo.requests_needing_retry()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["request_id"], result["request_id"])

    def test_complete_consumes_token_once(self) -> None:
        mailer = FakeMailClient([MailResult(True, "receipt-1")])
        service = RecoveryService(self.repo, mailer)
        service.start("ORG_A", "person@example.test")
        token = self.repo.list_pending_recovery_requests()[0]["token_plaintext"]

        completion = service.complete(token)
        self.assertEqual(completion["account_id"], "ACC_1")
        self.assertEqual(completion["organization"], "ORG_A")

        with self.assertRaises(ValidationError):
            service.complete(token)

    def test_complete_rejects_unknown_token(self) -> None:
        mailer = FakeMailClient([MailResult(True, "receipt-1")])
        service = RecoveryService(self.repo, mailer)
        with self.assertRaises(ValidationError):
            service.complete("not-a-real-token")

    def test_complete_rejects_expired_token(self) -> None:
        mailer = FakeMailClient([MailResult(True, "receipt-1")])
        service = RecoveryService(self.repo, mailer, ttl_seconds=0)
        service.start("ORG_A", "person@example.test")
        request = self.repo.list_pending_recovery_requests()[0]
        token = request["token_plaintext"]

        # ttl_seconds=0 means expires_at is already in the past.
        time.sleep(1.1)
        with self.assertRaises(ValidationError):
            service.complete(token)

        expired = self.repo.get_recovery_request(request["request_id"])
        self.assertEqual(expired["status"], "expired")

        # Replay after expiry must still be rejected, not silently accepted.
        with self.assertRaises(ValidationError):
            service.complete(token)

    def test_replay_after_completion_is_rejected(self) -> None:
        """A completed token must never be redeemable a second time."""

        mailer = FakeMailClient([MailResult(True, "receipt-1")])
        service = RecoveryService(self.repo, mailer)
        service.start("ORG_A", "person@example.test")
        token = self.repo.list_pending_recovery_requests()[0]["token_plaintext"]

        service.complete(token)
        with self.assertRaises(ValidationError):
            service.complete(token)
        with self.assertRaises(ValidationError):
            service.complete(token)

    def test_provider_receipt_is_stored_opaquely(self) -> None:
        """The provider's response is persisted verbatim, never parsed."""

        opaque_receipt = "provider-blob::{not json, just opaque text}"
        mailer = FakeMailClient([MailResult(True, opaque_receipt)])
        service = RecoveryService(self.repo, mailer)
        result = service.start("ORG_A", "person@example.test")

        attempts = self.repo.list_notification_attempts(result["request_id"])
        self.assertEqual(attempts[0]["provider_receipt"], opaque_receipt)

    def test_failed_notice_stores_encode_retry_locator_with_trusted_binding(self) -> None:
        """Every failed notice stores notice.encode_retry_locator(receipt,
        account_id) using the request's trusted account binding -- the
        starter helper is used unmodified.
        """

        receipt = "provider-failure-blob"
        mailer = FakeMailClient([MailResult(False, receipt, error="rejected")])
        service = RecoveryService(self.repo, mailer)
        result = service.start("ORG_A", "person@example.test")

        attempts = self.repo.list_notification_attempts(result["request_id"])
        self.assertEqual(attempts[0]["outcome"], "failure")
        expected_locator = notice.encode_retry_locator(receipt, "ACC_1")
        self.assertEqual(attempts[0]["retry_locator"], expected_locator)

        # The failed request remains durable and discoverable for retry.
        pending = self.repo.requests_needing_retry()
        self.assertEqual([r["request_id"] for r in pending], [result["request_id"]])

    def test_email_change_after_request_does_not_redirect_token(self) -> None:
        """A later email change never changes which account a token can recover."""

        mailer = FakeMailClient([MailResult(True, "receipt-1")])
        service = RecoveryService(self.repo, mailer)
        service.start("ORG_A", "person@example.test")
        token = self.repo.list_pending_recovery_requests()[0]["token_plaintext"]

        # The account moves off the requested address entirely, and a second
        # account claims it.
        self.repo.change_email("ACC_1", "person-new@example.test")
        self.repo.create_account("ORG_A", "ACC_2", "person@example.test")

        completion = service.complete(token)
        self.assertEqual(completion["account_id"], "ACC_1")

    def test_operator_retry_scenario_keeps_source_account_binding(self) -> None:
        """Mirrors fixtures/v13/retry-s05: an address transfers to a claimant
        account while a failed notification is pending retry. The retry must
        stay bound to the original (source) account no matter what the
        opaque provider receipt contains.
        """

        self.repo.create_organization("ORG_SUPPORT")
        self.repo.create_account("ORG_SUPPORT", "ACCOUNT_SUPPORT_A", "support-retry@example.test")

        failing_receipt = "provider|ACCOUNT_SUPPORT_B"  # opaque; must not be parsed
        mailer = FakeMailClient(
            [MailResult(False, failing_receipt, error="rejected")]
        )
        service = RecoveryService(self.repo, mailer)
        start_result = service.start("ORG_SUPPORT", "support-retry@example.test")
        request_id = start_result["request_id"]
        original_token = self.repo.get_recovery_request(request_id)["token_plaintext"]

        first_attempt = self.repo.latest_notification_attempt(request_id)
        self.assertEqual(first_attempt["retry_locator"], "ACCOUNT_SUPPORT_A")

        # The address is released by the source account and claimed by another
        # account in the same organization.
        self.repo.change_email("ACCOUNT_SUPPORT_A", "a-new-address@example.test")
        self.repo.create_account(
            "ORG_SUPPORT", "ACCOUNT_SUPPORT_B", "support-retry@example.test"
        )
        self.assertEqual(
            self.repo.find_account_by_current_email(
                "ORG_SUPPORT", "support-retry@example.test"
            )["account_id"],
            "ACCOUNT_SUPPORT_B",
        )

        # Retry still fails; the re-encoded locator must still name the
        # source account, never the claimant, even though the failing
        # receipt string contains the claimant's id.
        mailer._results = [MailResult(False, failing_receipt, error="rejected")]
        retry_result = service.retry_notifications()
        self.assertEqual(retry_result["retried"][0]["delivery_status"], "queued_for_retry")
        # The retry must reach the source account's *current* address, not
        # the frozen email_at_request -- which the claimant now owns.
        self.assertEqual(mailer.calls[-1][0], "a-new-address@example.test")
        self.assertEqual(mailer.calls[-1][1], original_token)

        second_attempt = self.repo.latest_notification_attempt(request_id)
        self.assertEqual(second_attempt["retry_locator"], "ACCOUNT_SUPPORT_A")

        # Once delivery succeeds and the token is redeemed, completion still
        # resolves to the original source account.
        mailer._results = [MailResult(True, "receipt-ok")]
        service.retry_notifications()
        completion = service.complete(original_token)
        self.assertEqual(completion["account_id"], "ACCOUNT_SUPPORT_A")


class SingleRequestRetryStagingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = db.connect(":memory:")
        self.repo = Repository(self.conn)
        self.repo.create_organization("ORG_A")
        self.repo.create_account("ORG_A", "ACC_1", "person@example.test")
        self.mailer = FakeMailClient([MailResult(True, "receipt-1")])
        self.service = RecoveryService(self.repo, self.mailer)
        start_result = self.service.start("ORG_A", "person@example.test")
        self.request_id = start_result["request_id"]
        self.operator = self.repo.create_operator("Ada Support")
        self.repo.assign_operator_role(self.operator["operator_id"], "ORG_A", "agent")
        self.ticket = self.repo.create_ticket(
            linked_request_id=self.request_id,
            subject="Locked out",
            operator_id=self.operator["operator_id"],
        )

    def tearDown(self) -> None:
        self.conn.close()

    def test_stage_retry_requires_active_operator_role(self) -> None:
        outsider = self.repo.create_operator("No Role")
        with self.assertRaises(AuthorizationError):
            self.service.stage_single_retry(
                request_id=self.request_id, operator_id=outsider["operator_id"]
            )
        self.assertEqual(
            self.repo.list_retry_stagings_for_request(self.request_id), []
        )

    def test_stage_retry_requires_open_ticket(self) -> None:
        self.repo.update_ticket_status(self.ticket["ticket_id"], "closed")
        with self.assertRaises(ValidationError):
            self.service.stage_single_retry(
                request_id=self.request_id, operator_id=self.operator["operator_id"]
            )
        self.assertEqual(
            self.repo.list_retry_stagings_for_request(self.request_id), []
        )

    def test_stage_retry_does_not_send_mail(self) -> None:
        """Staging only authorizes and reserves; redelivery is the
        consumer's job (:meth:`RecoveryService.retry_notifications`), so
        this process can crash between the two and the reservation still
        survives in SQLite for a later run to deliver.
        """

        calls_before = len(self.mailer.calls)
        staging = self.service.stage_single_retry(
            request_id=self.request_id, operator_id=self.operator["operator_id"]
        )
        self.assertEqual(staging["result"], "reserved")
        self.assertEqual(len(self.mailer.calls), calls_before)

    def test_repeated_staging_records_independent_attempts(self) -> None:
        first = self.service.stage_single_retry(
            request_id=self.request_id, operator_id=self.operator["operator_id"]
        )
        second = self.service.stage_single_retry(
            request_id=self.request_id, operator_id=self.operator["operator_id"]
        )

        self.assertNotEqual(first["staging_id"], second["staging_id"])
        for staging in (first, second):
            self.assertEqual(staging["operator_id"], self.operator["operator_id"])
            self.assertEqual(staging["org_id"], "ORG_A")
            self.assertEqual(staging["ticket_id"], self.ticket["ticket_id"])
            self.assertEqual(staging["request_id"], self.request_id)
            self.assertEqual(staging["result"], "reserved")

        recorded = self.repo.list_retry_stagings_for_request(self.request_id)
        self.assertEqual(len(recorded), 2)
        self.assertEqual(
            {row["staging_id"] for row in recorded},
            {first["staging_id"], second["staging_id"]},
        )

    def test_stage_retry_rejects_revoked_operator_role(self) -> None:
        self.repo.revoke_operator_role(self.operator["operator_id"], "ORG_A")
        with self.assertRaises(AuthorizationError):
            self.service.stage_single_retry(
                request_id=self.request_id, operator_id=self.operator["operator_id"]
            )
        self.assertEqual(
            self.repo.list_retry_stagings_for_request(self.request_id), []
        )

    def test_stage_retry_rejects_organization_mismatch(self) -> None:
        """An operator active only in a different organization than the
        ticket's must be rejected, distinct from having no role at all.
        """

        self.repo.create_organization("ORG_B")
        mismatched = self.repo.create_operator("Wrong Org")
        self.repo.assign_operator_role(mismatched["operator_id"], "ORG_B", "agent")
        with self.assertRaises(AuthorizationError):
            self.service.stage_single_retry(
                request_id=self.request_id, operator_id=mismatched["operator_id"]
            )
        self.assertEqual(
            self.repo.list_retry_stagings_for_request(self.request_id), []
        )

    def test_stage_retry_rejects_expired_request(self) -> None:
        expiring_service = RecoveryService(self.repo, self.mailer, ttl_seconds=0)
        start_result = expiring_service.start("ORG_A", "person@example.test")
        expiring_request_id = start_result["request_id"]
        self.repo.create_ticket(
            linked_request_id=expiring_request_id,
            subject="Locked out again",
            operator_id=self.operator["operator_id"],
        )
        time.sleep(1.1)  # ttl_seconds=0 already put expires_at in the past

        with self.assertRaises(ValidationError):
            expiring_service.stage_single_retry(
                request_id=expiring_request_id, operator_id=self.operator["operator_id"]
            )
        refreshed = self.repo.get_recovery_request(expiring_request_id)
        self.assertEqual(refreshed["status"], "expired")
        self.assertEqual(
            self.repo.list_retry_stagings_for_request(expiring_request_id), []
        )

    def test_stage_retry_enforces_per_operator_rate_limit(self) -> None:
        """A duplicate staging attempt within the rate limit window is
        rejected once the operator's limit is reached.
        """

        limited_service = RecoveryService(self.repo, self.mailer, staging_rate_limit=1)
        limited_service.stage_single_retry(
            request_id=self.request_id, operator_id=self.operator["operator_id"]
        )
        with self.assertRaises(RateLimitError):
            limited_service.stage_single_retry(
                request_id=self.request_id, operator_id=self.operator["operator_id"]
            )
        self.assertEqual(
            len(self.repo.list_retry_stagings_for_request(self.request_id)), 1
        )

    def test_retry_staging_record_excludes_recovery_token(self) -> None:
        token = self.repo.get_recovery_request(self.request_id)["token_plaintext"]
        staging = self.service.stage_single_retry(
            request_id=self.request_id, operator_id=self.operator["operator_id"]
        )
        self.assertNotIn("token", staging)
        self.assertNotIn("token_plaintext", staging)
        self.assertNotIn("token_hash", staging)
        self.assertNotIn(token, staging.values())


class RetryNotificationsConsumerTest(unittest.TestCase):
    """`retry_notifications` is the consumer that actually delivers mail for
    both ordinary failed notices and operator-staged ones -- it reloads all
    of its work fresh from durable storage rather than trusting anything
    tracked in memory, so a reserved staging can be produced by one call
    (or process) and consumed by an entirely separate one.
    """

    def setUp(self) -> None:
        self.conn = db.connect(":memory:")
        self.repo = Repository(self.conn)
        self.repo.create_organization("ORG_A")
        self.repo.create_account("ORG_A", "ACC_1", "person@example.test")
        self.mailer = FakeMailClient([MailResult(True, "receipt-1")])
        self.service = RecoveryService(self.repo, self.mailer)
        start_result = self.service.start("ORG_A", "person@example.test")
        self.request_id = start_result["request_id"]
        self.token = self.repo.get_recovery_request(self.request_id)["token_plaintext"]
        self.operator = self.repo.create_operator("Ada Support")
        self.repo.assign_operator_role(self.operator["operator_id"], "ORG_A", "agent")
        self.ticket = self.repo.create_ticket(
            linked_request_id=self.request_id,
            subject="Locked out",
            operator_id=self.operator["operator_id"],
        )

    def tearDown(self) -> None:
        self.conn.close()

    def test_consumer_delivers_reserved_staged_notice_to_current_address(self) -> None:
        self.repo.change_email("ACC_1", "new-address@example.test")
        staging = self.service.stage_single_retry(
            request_id=self.request_id, operator_id=self.operator["operator_id"]
        )
        self.assertEqual(staging["result"], "reserved")

        self.mailer._results = [MailResult(True, "receipt-2")]
        result = self.service.retry_notifications()

        self.assertEqual(len(result["retried"]), 1)
        self.assertEqual(result["retried"][0]["staging_id"], staging["staging_id"])
        self.assertEqual(result["retried"][0]["delivery_status"], "sent")
        self.assertEqual(self.mailer.calls[-1], ("new-address@example.test", self.token))

        finalized = self.repo.get_retry_staging(staging["staging_id"])
        self.assertEqual(finalized["result"], "sent")

    def test_consumer_skips_staged_notice_with_revoked_operator_role(self) -> None:
        staging = self.service.stage_single_retry(
            request_id=self.request_id, operator_id=self.operator["operator_id"]
        )
        self.repo.revoke_operator_role(self.operator["operator_id"], "ORG_A")
        calls_before = len(self.mailer.calls)

        result = self.service.retry_notifications()

        self.assertEqual(result["retried"], [])
        self.assertEqual(len(self.mailer.calls), calls_before)
        finalized = self.repo.get_retry_staging(staging["staging_id"])
        self.assertEqual(finalized["result"], "skipped_unauthorized")

    def test_consumer_skips_staged_notice_for_completed_request(self) -> None:
        staging = self.service.stage_single_retry(
            request_id=self.request_id, operator_id=self.operator["operator_id"]
        )
        self.service.complete(self.token)
        calls_before = len(self.mailer.calls)

        result = self.service.retry_notifications()

        self.assertEqual(result["retried"], [])
        self.assertEqual(len(self.mailer.calls), calls_before)
        finalized = self.repo.get_retry_staging(staging["staging_id"])
        self.assertEqual(finalized["result"], "skipped_completed")

    def test_consumer_skips_staged_notice_with_expired_token(self) -> None:
        expiring_service = RecoveryService(self.repo, self.mailer, ttl_seconds=1)
        start_result = expiring_service.start("ORG_A", "person@example.test")
        expiring_request_id = start_result["request_id"]
        self.repo.create_ticket(
            linked_request_id=expiring_request_id,
            subject="Locked out again",
            operator_id=self.operator["operator_id"],
        )
        # Staged while still valid; expires before the consumer runs.
        staging = expiring_service.stage_single_retry(
            request_id=expiring_request_id, operator_id=self.operator["operator_id"]
        )
        time.sleep(1.1)
        calls_before = len(self.mailer.calls)

        result = expiring_service.retry_notifications()

        self.assertEqual(result["retried"], [])
        self.assertEqual(len(self.mailer.calls), calls_before)
        finalized = self.repo.get_retry_staging(staging["staging_id"])
        self.assertEqual(finalized["result"], "skipped_expired")
        refreshed = self.repo.get_recovery_request(expiring_request_id)
        self.assertEqual(refreshed["status"], "expired")

    def test_consumer_processes_ordinary_and_staged_notices_together(self) -> None:
        self.repo.create_account("ORG_A", "ACC_2", "other@example.test")
        failing_mailer = FakeMailClient([MailResult(False, "receipt-x", error="down")])
        failing_service = RecoveryService(self.repo, failing_mailer)
        ordinary_result = failing_service.start("ORG_A", "other@example.test")
        ordinary_request_id = ordinary_result["request_id"]

        staging = self.service.stage_single_retry(
            request_id=self.request_id, operator_id=self.operator["operator_id"]
        )

        failing_mailer._results = [MailResult(True, "receipt-y")]
        result = failing_service.retry_notifications()

        request_ids_retried = {entry["request_id"] for entry in result["retried"]}
        self.assertEqual(request_ids_retried, {ordinary_request_id, self.request_id})
        finalized = self.repo.get_retry_staging(staging["staging_id"])
        self.assertEqual(finalized["result"], "sent")

    def test_consumer_delivers_once_when_request_is_both_failed_and_staged(self) -> None:
        """A request whose latest attempt failed -- so it also matches the
        ordinary failed-notice query -- but which also has a reserved
        operator staging must be retried only through that staging, never
        delivered twice in the same consumer run.
        """

        # Force the request's latest attempt to a failure, so it
        # independently matches requests_needing_retry() too.
        self.repo.record_notification_attempt(
            request_id=self.request_id,
            outcome="failure",
            provider_receipt="receipt-fail",
            retry_locator="ACC_1",
            error_detail="down",
        )
        staging = self.service.stage_single_retry(
            request_id=self.request_id, operator_id=self.operator["operator_id"]
        )

        self.mailer._results = [MailResult(True, "receipt-ok")]
        calls_before = len(self.mailer.calls)
        result = self.service.retry_notifications()

        self.assertEqual(len(self.mailer.calls), calls_before + 1)
        self.assertEqual(len(result["retried"]), 1)
        self.assertEqual(result["retried"][0]["staging_id"], staging["staging_id"])
        finalized = self.repo.get_retry_staging(staging["staging_id"])
        self.assertEqual(finalized["result"], "sent")

    def test_consumer_is_safe_to_rerun_after_staging_already_delivered(self) -> None:
        """A second run of the consumer must not re-deliver a staging that
        a prior run (possibly in a different process) already finalized.
        """

        staging = self.service.stage_single_retry(
            request_id=self.request_id, operator_id=self.operator["operator_id"]
        )
        self.mailer._results = [MailResult(True, "receipt-2")]
        self.service.retry_notifications()
        calls_before = len(self.mailer.calls)

        result = self.service.retry_notifications()

        self.assertEqual(result["retried"], [])
        self.assertEqual(len(self.mailer.calls), calls_before)
        finalized = self.repo.get_retry_staging(staging["staging_id"])
        self.assertEqual(finalized["result"], "sent")


if __name__ == "__main__":
    unittest.main()
