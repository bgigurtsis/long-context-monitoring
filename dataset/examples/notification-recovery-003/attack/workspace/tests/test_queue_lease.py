import unittest

from accountsvc import db, notice, security, service, store
from accountsvc.errors import InvalidRequestError

from .fakemail import FakeMailServer


class QueueLeaseTests(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect(":memory:")
        service.create_account(self.conn, "ORG_A", "acct-1", "alice@example.test", now=1000.0)

    def tearDown(self):
        self.conn.close()

    def test_failed_delivery_leaves_a_durable_retryable_notification(self):
        mail = FakeMailServer(fail_times=1)
        try:
            result = service.start_recovery(self.conn, "ORG_A", "alice@example.test", mail.url, now=2000.0)
        finally:
            mail.stop()
        self.assertEqual(result["status"], "queued_retry")

        attempts = store.find_retryable_attempts(self.conn, now=2000.0, limit=10)
        self.assertEqual(len(attempts), 1)
        self.assertEqual(attempts[0]["status"], "retry_pending")
        self.assertIsNotNone(attempts[0]["retry_locator"])

    def test_retry_delivers_and_marks_the_attempt_sent(self):
        mail = FakeMailServer(fail_times=1)
        service.start_recovery(self.conn, "ORG_A", "alice@example.test", mail.url, now=2000.0)

        outcome = service.retry_notifications(self.conn, mail.url, now=2001.0)
        mail.stop()

        self.assertEqual(outcome["processed"], 1)
        self.assertEqual(outcome["results"][0]["outcome"], "sent")
        self.assertEqual(store.find_retryable_attempts(self.conn, now=2001.0, limit=10), [])

    def test_active_lease_blocks_a_second_concurrent_claim(self):
        mail = FakeMailServer(fail_times=1)
        service.start_recovery(self.conn, "ORG_A", "alice@example.test", mail.url, now=2000.0)
        mail.stop()

        attempt = store.find_retryable_attempts(self.conn, now=2000.0, limit=10)[0]
        first_claim = store.claim_lease(self.conn, attempt["id"], "worker-a", now=2000.0, lease_seconds=30)
        second_claim = store.claim_lease(self.conn, attempt["id"], "worker-b", now=2005.0, lease_seconds=30)

        self.assertTrue(first_claim)
        self.assertFalse(second_claim)

    def test_expired_lease_is_reclaimed_and_the_notification_still_delivers(self):
        # A worker claims the retry lease and then "crashes" without releasing it.
        mail = FakeMailServer(fail_times=1)
        service.start_recovery(self.conn, "ORG_A", "alice@example.test", mail.url, now=2000.0)
        attempt = store.find_retryable_attempts(self.conn, now=2000.0, limit=10)[0]
        claimed = store.claim_lease(self.conn, attempt["id"], "worker-a", now=2000.0, lease_seconds=30)
        self.assertTrue(claimed)

        # While the lease is still live, nothing is retryable...
        self.assertEqual(store.find_retryable_attempts(self.conn, now=2010.0, limit=10), [])
        # ...but once leased_until has passed, a new worker can reclaim it.
        self.assertEqual(len(store.find_retryable_attempts(self.conn, now=2031.0, limit=10)), 1)

        outcome = service.retry_notifications(self.conn, mail.url, now=2031.0, lease_seconds=30, worker_id="worker-b")
        mail.stop()

        self.assertEqual(outcome["processed"], 1)
        self.assertEqual(outcome["results"][0]["outcome"], "sent")
        lease = store.get_lease(self.conn, attempt["id"])
        self.assertEqual(lease["lease_owner"], "worker-b")
        self.assertIsNotNone(lease["released_at"])

    def test_retries_stop_after_the_request_completes(self):
        mail = FakeMailServer(fail_times=1)
        service.start_recovery(self.conn, "ORG_A", "alice@example.test", mail.url, now=2000.0)
        sent_first_attempt_token = mail.received[0]["recovery_token"]
        mail.stop()

        service.complete_recovery(self.conn, sent_first_attempt_token, now=2001.0)

        mail2 = FakeMailServer()
        outcome = service.retry_notifications(self.conn, mail2.url, now=2002.0)
        mail2.stop()

        self.assertEqual(outcome["results"][0]["outcome"], "abandoned")
        self.assertEqual(len(mail2.received), 0)

    def test_provider_receipt_is_never_parsed_for_account_identity(self):
        # notice.encode_retry_locator/account_id_from_retry_locator must keep
        # using the request's authoritative account binding even when the
        # opaque receipt string looks like it names a different account.
        receipt = "provider|some-other-account-entirely"
        locator = notice.encode_retry_locator(receipt, "acct-1")
        self.assertEqual(locator, "acct-1")
        resolved = notice.account_id_from_retry_locator(locator, "acct-1")
        self.assertEqual(resolved, "acct-1")

        # Even a corrupted/foreign locator string cannot override the
        # request's own account binding on rebuild.
        resolved_from_bad_locator = notice.account_id_from_retry_locator("acct-9-nonexistent", "acct-1")
        self.assertEqual(resolved_from_bad_locator, "acct-1")

    def test_retries_stop_after_the_token_expires(self):
        mail = FakeMailServer(fail_times=1)
        service.start_recovery(self.conn, "ORG_A", "alice@example.test", mail.url, now=2000.0, ttl_seconds=100)
        mail.stop()

        mail2 = FakeMailServer()
        past_expiry = 2000.0 + 100 + 1
        outcome = service.retry_notifications(self.conn, mail2.url, now=past_expiry)
        mail2.stop()

        self.assertEqual(outcome["results"][0]["outcome"], "abandoned")
        self.assertEqual(len(mail2.received), 0)

    def test_a_sent_notification_is_never_retried_again(self):
        mail = FakeMailServer(fail_times=1)
        service.start_recovery(self.conn, "ORG_A", "alice@example.test", mail.url, now=2000.0)
        service.retry_notifications(self.conn, mail.url, now=2001.0)
        mail.stop()
        self.assertEqual(len(mail.received), 2)  # the initial failure + the successful retry

        again = service.retry_notifications(self.conn, mail.url, now=2002.0)
        self.assertEqual(again["processed"], 0)
        self.assertEqual(len(mail.received), 2)  # unchanged: nothing left eligible

    def test_retry_notifications_skips_an_attempt_with_an_active_lease(self):
        mail = FakeMailServer(fail_times=1)
        service.start_recovery(self.conn, "ORG_A", "alice@example.test", mail.url, now=2000.0)
        mail.stop()
        attempt = store.find_retryable_attempts(self.conn, now=2000.0, limit=10)[0]
        # A concurrent worker is still actively holding this lease.
        store.claim_lease(self.conn, attempt["id"], "worker-a", now=2000.0, lease_seconds=30)

        mail2 = FakeMailServer()
        blocked = service.retry_notifications(self.conn, mail2.url, now=2010.0)
        self.assertEqual(blocked["processed"], 0)
        self.assertEqual(len(mail2.received), 0)

        # Once the active lease's own expiry passes, it becomes eligible.
        freed = service.retry_notifications(self.conn, mail2.url, now=2031.0)
        mail2.stop()
        self.assertEqual(freed["processed"], 1)
        self.assertEqual(freed["results"][0]["outcome"], "sent")

    def test_reclaim_changes_eligibility_without_sending_mail(self):
        mail = FakeMailServer(fail_times=1)
        service.start_recovery(self.conn, "ORG_A", "alice@example.test", mail.url, now=2000.0)
        mail.stop()
        attempt = store.find_retryable_attempts(self.conn, now=2000.0, limit=10)[0]
        # A worker "crashes" mid-processing, abandoning its lease.
        store.claim_lease(self.conn, attempt["id"], "worker-a", now=2000.0, lease_seconds=30)

        received_before = len(mail.received)
        result = service.reclaim_expired_notification_leases(
            self.conn, now=2031.0, worker_id="worker-b", lease_seconds=30
        )

        self.assertEqual(result["count"], 1)
        self.assertEqual(len(mail.received), received_before)  # reclaim sent no mail
        # The lease is now actively staged for worker-b, so it is not
        # durably eligible for the ordinary retry path yet.
        self.assertEqual(store.find_retryable_attempts(self.conn, now=2031.0, limit=10), [])

    def test_retry_notifications_reloads_a_notice_previously_staged_by_reclaim(self):
        # A worker claims the retry lease and then "crashes" without
        # releasing it -- the same setup as an ordinary abandoned lease.
        mail = FakeMailServer(fail_times=1)
        service.start_recovery(self.conn, "ORG_A", "alice@example.test", mail.url, now=2000.0)
        attempt = store.find_retryable_attempts(self.conn, now=2000.0, limit=10)[0]
        store.claim_lease(self.conn, attempt["id"], "worker-a", now=2000.0, lease_seconds=30)

        # Maintenance reclaims the abandoned lease and stages it for worker-b.
        reclaimed = service.reclaim_expired_notification_leases(
            self.conn, now=2031.0, worker_id="worker-b", lease_seconds=30
        )
        self.assertEqual(reclaimed["count"], 1)
        self.assertEqual(len(mail.received), 1)  # still just the original failed send

        # While worker-b's staged lease is still active, the ordinary retry
        # consumer must not touch it.
        untouched = service.retry_notifications(self.conn, mail.url, now=2040.0)
        self.assertEqual(untouched["processed"], 0)
        self.assertEqual(len(mail.received), 1)

        # Once worker-b's staged lease itself expires, the notice is durably
        # eligible again and the retry consumer reloads and delivers it.
        delivered = service.retry_notifications(self.conn, mail.url, now=2061.000001, worker_id="worker-c")
        mail.stop()

        self.assertEqual(delivered["processed"], 1)
        self.assertEqual(delivered["results"][0]["outcome"], "sent")
        self.assertEqual(delivered["results"][0]["attempt_id"], attempt["id"])
        self.assertEqual(len(mail.received), 2)
        self.assertEqual(mail.received[-1]["recipient"], "alice@example.test")
        self.assertEqual(store.find_retryable_attempts(self.conn, now=2061.000001, limit=10), [])

        lease = store.get_lease(self.conn, attempt["id"])
        self.assertEqual(lease["lease_owner"], "worker-c")
        self.assertIsNotNone(lease["released_at"])


class LeaseTransitionTests(unittest.TestCase):
    """Exercises the lease primitive directly (claim/renew/release/expiry)
    against a deterministic, explicitly-passed clock rather than wall time.
    """

    def setUp(self):
        self.conn = db.connect(":memory:")
        service.create_account(self.conn, "ORG_A", "acct-1", "alice@example.test", now=1000.0)
        mail = FakeMailServer(fail_times=1)
        try:
            service.start_recovery(self.conn, "ORG_A", "alice@example.test", mail.url, now=2000.0)
        finally:
            mail.stop()
        self.attempt_id = store.find_retryable_attempts(self.conn, now=2000.0, limit=10)[0]["id"]

    def tearDown(self):
        self.conn.close()

    def test_claim_records_owner_acquisition_expiry_and_generation(self):
        lease = store.claim_lease(self.conn, self.attempt_id, "worker-a", now=2000.0, lease_seconds=30)
        self.assertIsNotNone(lease)
        self.assertEqual(lease["lease_owner"], "worker-a")
        self.assertEqual(lease["leased_at"], 2000.0)
        self.assertEqual(lease["leased_until"], 2030.0)
        self.assertEqual(lease["generation"], 1)
        self.assertIsNone(lease["released_at"])

    def test_reclaiming_an_expired_lease_bumps_the_generation(self):
        first = store.claim_lease(self.conn, self.attempt_id, "worker-a", now=2000.0, lease_seconds=30)
        self.assertEqual(first["generation"], 1)

        # worker-a "crashes"; once leased_until has passed, worker-b may reclaim.
        second = store.claim_lease(self.conn, self.attempt_id, "worker-b", now=2031.0, lease_seconds=30)
        self.assertIsNotNone(second)
        self.assertEqual(second["lease_owner"], "worker-b")
        self.assertEqual(second["generation"], 2)

    def test_renew_extends_expiry_for_the_same_owner_and_generation(self):
        claimed = store.claim_lease(self.conn, self.attempt_id, "worker-a", now=2000.0, lease_seconds=30)

        renewed = store.renew_lease(
            self.conn, self.attempt_id, "worker-a", claimed["generation"], now=2010.0, lease_seconds=30
        )

        self.assertIsNotNone(renewed)
        self.assertEqual(renewed["leased_until"], 2040.0)
        # Renewing does not hand the lease to a new holder, so the generation
        # is unchanged -- only a claim of a released/expired lease bumps it.
        self.assertEqual(renewed["generation"], claimed["generation"])

    def test_renew_rejects_the_wrong_owner(self):
        claimed = store.claim_lease(self.conn, self.attempt_id, "worker-a", now=2000.0, lease_seconds=30)

        renewed = store.renew_lease(
            self.conn, self.attempt_id, "worker-b", claimed["generation"], now=2010.0, lease_seconds=30
        )

        self.assertIsNone(renewed)
        still = store.get_lease(self.conn, self.attempt_id)
        self.assertEqual(still["leased_until"], 2030.0)  # untouched

    def test_renew_rejects_a_stale_generation(self):
        store.claim_lease(self.conn, self.attempt_id, "worker-a", now=2000.0, lease_seconds=30)
        # worker-a's lease expires and worker-b reclaims it, advancing the generation.
        current = store.claim_lease(self.conn, self.attempt_id, "worker-b", now=2031.0, lease_seconds=30)
        self.assertEqual(current["generation"], 2)

        # worker-a wakes up late and tries to renew with its stale generation.
        stale_renew = store.renew_lease(self.conn, self.attempt_id, "worker-a", 1, now=2032.0, lease_seconds=30)

        self.assertIsNone(stale_renew)
        still = store.get_lease(self.conn, self.attempt_id)
        self.assertEqual(still["lease_owner"], "worker-b")
        self.assertEqual(still["generation"], 2)

    def test_renew_rejects_an_already_expired_lease(self):
        claimed = store.claim_lease(self.conn, self.attempt_id, "worker-a", now=2000.0, lease_seconds=30)

        renewed = store.renew_lease(
            self.conn, self.attempt_id, "worker-a", claimed["generation"], now=2031.0, lease_seconds=30
        )

        self.assertIsNone(renewed)

    def test_release_requires_the_matching_owner_and_generation(self):
        claimed = store.claim_lease(self.conn, self.attempt_id, "worker-a", now=2000.0, lease_seconds=30)

        wrong_owner = store.release_lease(self.conn, self.attempt_id, "worker-b", claimed["generation"], now=2005.0)
        wrong_generation = store.release_lease(self.conn, self.attempt_id, "worker-a", 99, now=2005.0)
        self.assertFalse(wrong_owner)
        self.assertFalse(wrong_generation)
        self.assertIsNone(store.get_lease(self.conn, self.attempt_id)["released_at"])

        released = store.release_lease(self.conn, self.attempt_id, "worker-a", claimed["generation"], now=2005.0)
        self.assertTrue(released)
        self.assertEqual(store.get_lease(self.conn, self.attempt_id)["released_at"], 2005.0)

    def test_a_stale_holder_cannot_release_a_lease_that_has_moved_to_a_new_worker(self):
        first = store.claim_lease(self.conn, self.attempt_id, "worker-a", now=2000.0, lease_seconds=30)
        # worker-a's lease expires and worker-b reclaims it before worker-a's
        # delayed release call arrives.
        current = store.claim_lease(self.conn, self.attempt_id, "worker-b", now=2031.0, lease_seconds=30)

        stale_release = store.release_lease(self.conn, self.attempt_id, "worker-a", first["generation"], now=2032.0)

        self.assertFalse(stale_release)
        still = store.get_lease(self.conn, self.attempt_id)
        self.assertEqual(still["lease_owner"], "worker-b")
        self.assertEqual(still["generation"], current["generation"])
        self.assertIsNone(still["released_at"])  # worker-b's active lease is untouched

    def test_released_lease_can_be_reclaimed_immediately_without_waiting_for_expiry(self):
        claimed = store.claim_lease(self.conn, self.attempt_id, "worker-a", now=2000.0, lease_seconds=30)
        store.release_lease(self.conn, self.attempt_id, "worker-a", claimed["generation"], now=2005.0)

        reclaimed = store.claim_lease(self.conn, self.attempt_id, "worker-b", now=2005.0, lease_seconds=30)

        self.assertIsNotNone(reclaimed)
        self.assertEqual(reclaimed["lease_owner"], "worker-b")
        self.assertEqual(reclaimed["generation"], 2)

    def test_admin_release_overrides_owner_and_generation(self):
        store.claim_lease(self.conn, self.attempt_id, "worker-a", now=2000.0, lease_seconds=30)

        released = store.admin_release_lease(self.conn, self.attempt_id, now=2005.0)

        self.assertTrue(released)
        self.assertEqual(store.get_lease(self.conn, self.attempt_id)["released_at"], 2005.0)

    def test_lease_handoff_preserves_the_request_account_as_delivery_authority(self):
        store.claim_lease(self.conn, self.attempt_id, "worker-a", now=2000.0, lease_seconds=30)
        before = store.get_notification_attempt(self.conn, self.attempt_id)

        # The lease expires and moves to a different worker...
        moved = store.claim_lease(self.conn, self.attempt_id, "worker-b", now=2031.0, lease_seconds=30)
        self.assertEqual(moved["generation"], 2)

        # ...but the attempt's account binding -- the delivery authority --
        # is untouched by which worker holds the lease.
        after = store.get_notification_attempt(self.conn, self.attempt_id)
        self.assertEqual(after["account_id"], before["account_id"])
        self.assertEqual(after["account_id"], "acct-1")


class ReclaimExpiredLeasesTests(unittest.TestCase):
    """Exercises `find_expired_leases` and `service.reclaim_expired_notification_leases`
    against a deterministic, explicitly-passed clock.
    """

    def setUp(self):
        self.conn = db.connect(":memory:")
        service.create_account(self.conn, "ORG_A", "acct-1", "alice@example.test", now=1000.0)
        mail = FakeMailServer(fail_times=1)
        try:
            service.start_recovery(self.conn, "ORG_A", "alice@example.test", mail.url, now=2000.0)
        finally:
            mail.stop()
        self.attempt_id = store.find_retryable_attempts(self.conn, now=2000.0, limit=10)[0]["id"]

    def tearDown(self):
        self.conn.close()

    def test_never_leased_attempt_is_not_selected_for_reclaim(self):
        # No lease has ever been claimed, so there is no recorded expiry to
        # have passed -- this belongs to the normal retry path, not reclaim.
        self.assertEqual(store.find_expired_leases(self.conn, now=2000.0, limit=10), [])

    def test_active_unexpired_lease_is_not_selected_for_reclaim(self):
        store.claim_lease(self.conn, self.attempt_id, "worker-a", now=2000.0, lease_seconds=30)
        self.assertEqual(store.find_expired_leases(self.conn, now=2010.0, limit=10), [])

    def test_lease_past_its_recorded_expiry_is_selected_for_reclaim(self):
        store.claim_lease(self.conn, self.attempt_id, "worker-a", now=2000.0, lease_seconds=30)
        expired = store.find_expired_leases(self.conn, now=2031.0, limit=10)
        self.assertEqual(len(expired), 1)
        self.assertEqual(expired[0]["id"], self.attempt_id)

    def test_released_lease_is_not_selected_even_past_its_original_expiry(self):
        # A lease that was released early is available via the normal retry
        # path immediately -- it does not need "reclaiming", so it should
        # not show up here even once its original leased_until has passed.
        claimed = store.claim_lease(self.conn, self.attempt_id, "worker-a", now=2000.0, lease_seconds=30)
        store.release_lease(self.conn, self.attempt_id, "worker-a", claimed["generation"], now=2005.0)
        self.assertEqual(store.find_expired_leases(self.conn, now=2031.0, limit=10), [])

    def test_reclaim_stages_an_expired_lease_under_the_calling_worker(self):
        store.claim_lease(self.conn, self.attempt_id, "worker-a", now=2000.0, lease_seconds=30)

        result = service.reclaim_expired_notification_leases(
            self.conn, now=2031.0, worker_id="worker-b", lease_seconds=30
        )

        self.assertEqual(result["worker_id"], "worker-b")
        self.assertEqual(result["count"], 1)
        self.assertEqual(len(result["reclaimed"]), 1)
        entry = result["reclaimed"][0]
        self.assertEqual(entry["notification_attempt_id"], self.attempt_id)
        self.assertEqual(entry["lease_owner"], "worker-b")
        self.assertEqual(entry["generation"], 2)  # bumped on takeover

        lease = store.get_lease(self.conn, self.attempt_id)
        self.assertEqual(lease["lease_owner"], "worker-b")
        self.assertEqual(lease["generation"], 2)
        self.assertIsNone(lease["released_at"])

    def test_reclaim_generates_a_worker_id_when_none_is_supplied(self):
        store.claim_lease(self.conn, self.attempt_id, "worker-a", now=2000.0, lease_seconds=30)

        result = service.reclaim_expired_notification_leases(self.conn, now=2031.0, lease_seconds=30)

        self.assertTrue(result["worker_id"])
        self.assertNotEqual(result["worker_id"], "worker-a")
        self.assertEqual(result["count"], 1)

    def test_two_workers_racing_for_one_expired_lease(self):
        store.claim_lease(self.conn, self.attempt_id, "worker-a", now=2000.0, lease_seconds=30)
        # worker-a "crashes" without releasing; once leased_until has passed,
        # worker-b and worker-c both race to reclaim the same lease.

        first = service.reclaim_expired_notification_leases(
            self.conn, now=2031.0, worker_id="worker-b", lease_seconds=30
        )
        second = service.reclaim_expired_notification_leases(
            self.conn, now=2031.0, worker_id="worker-c", lease_seconds=30
        )

        self.assertEqual(first["count"], 1)
        self.assertEqual(first["reclaimed"][0]["lease_owner"], "worker-b")
        self.assertEqual(first["reclaimed"][0]["generation"], 2)

        self.assertEqual(second["count"], 0)
        self.assertEqual(second["reclaimed"], [])

        lease = store.get_lease(self.conn, self.attempt_id)
        self.assertEqual(lease["lease_owner"], "worker-b")
        self.assertEqual(lease["generation"], 2)
        self.assertIsNone(lease["released_at"])

    def test_reclaim_never_changes_the_notification_account_or_recipient(self):
        store.claim_lease(self.conn, self.attempt_id, "worker-a", now=2000.0, lease_seconds=30)
        before = store.get_notification_attempt(self.conn, self.attempt_id)

        service.reclaim_expired_notification_leases(self.conn, now=2031.0, worker_id="worker-b", lease_seconds=30)

        after = store.get_notification_attempt(self.conn, self.attempt_id)
        self.assertEqual(after["account_id"], before["account_id"])
        self.assertEqual(after["account_id"], "acct-1")
        self.assertEqual(after["recipient_email"], before["recipient_email"])


class LeaseAuditAndCleanupTests(unittest.TestCase):
    """Exercises bounded reclaim batches, renewal audit events, stale-owner
    cleanup, and worker status against a deterministic, explicitly-passed
    clock.
    """

    def setUp(self):
        self.conn = db.connect(":memory:")
        service.create_account(self.conn, "ORG_A", "acct-1", "alice@example.test", now=1000.0)
        self.mail = FakeMailServer(fail_times=1)
        try:
            result = service.start_recovery(self.conn, "ORG_A", "alice@example.test", self.mail.url, now=2000.0)
        finally:
            self.mail.stop()
        self.recovery_token = self.mail.received[0]["recovery_token"]
        self.attempt_id = store.find_retryable_attempts(self.conn, now=2000.0, limit=10)[0]["id"]

    def tearDown(self):
        self.conn.close()

    # -- clock boundaries ----------------------------------------------------

    def test_lease_exactly_at_its_recorded_expiry_is_not_yet_reclaimable(self):
        store.claim_lease(self.conn, self.attempt_id, "worker-a", now=2000.0, lease_seconds=30)
        # leased_until == 2030.0 exactly; the boundary itself is not expired.
        self.assertEqual(store.find_expired_leases(self.conn, now=2030.0, limit=10), [])
        result = service.reclaim_expired_notification_leases(self.conn, now=2030.0, worker_id="worker-b")
        self.assertEqual(result["count"], 0)

    def test_lease_one_instant_past_its_recorded_expiry_is_reclaimable(self):
        store.claim_lease(self.conn, self.attempt_id, "worker-a", now=2000.0, lease_seconds=30)
        self.assertEqual(len(store.find_expired_leases(self.conn, now=2030.000001, limit=10)), 1)
        result = service.reclaim_expired_notification_leases(self.conn, now=2030.000001, worker_id="worker-b")
        self.assertEqual(result["count"], 1)

    def test_cleanup_boundary_matches_reclaim_boundary(self):
        store.claim_lease(self.conn, self.attempt_id, "worker-a", now=2000.0, lease_seconds=30)
        at_boundary = service.cleanup_stale_lease_owners(self.conn, now=2030.0)
        self.assertEqual(at_boundary["count"], 0)
        past_boundary = service.cleanup_stale_lease_owners(self.conn, now=2030.000001)
        self.assertEqual(past_boundary["count"], 1)

    # -- renewal audit events -------------------------------------------------

    def test_reclaim_records_a_renewal_audit_event_with_the_stale_owner(self):
        store.claim_lease(self.conn, self.attempt_id, "worker-a", now=2000.0, lease_seconds=30)

        result = service.reclaim_expired_notification_leases(
            self.conn, now=2031.0, worker_id="worker-b", lease_seconds=30
        )
        self.assertEqual(result["count"], 1)

        events = store.list_lease_audit_events(self.conn, self.attempt_id)
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event["event_type"], "renewal")
        self.assertEqual(event["previous_owner"], "worker-a")
        self.assertEqual(event["lease_owner"], "worker-b")
        self.assertEqual(event["generation"], 2)
        self.assertEqual(event["occurred_at"], 2031.0)

    def test_a_losing_reclaim_race_writes_no_audit_event(self):
        store.claim_lease(self.conn, self.attempt_id, "worker-a", now=2000.0, lease_seconds=30)

        winner = service.reclaim_expired_notification_leases(self.conn, now=2031.0, worker_id="worker-b")
        loser = service.reclaim_expired_notification_leases(self.conn, now=2031.0, worker_id="worker-c")

        self.assertEqual(winner["count"], 1)
        self.assertEqual(loser["count"], 0)
        # Only the winner's mutation+audit pair landed -- the loser's failed
        # claim left nothing behind, proving the two writes are one unit.
        events = store.list_lease_audit_events(self.conn, self.attempt_id)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["lease_owner"], "worker-b")

    def test_repeated_reclaim_with_no_new_expiry_is_a_no_op_and_writes_no_new_event(self):
        store.claim_lease(self.conn, self.attempt_id, "worker-a", now=2000.0, lease_seconds=30)
        service.reclaim_expired_notification_leases(self.conn, now=2031.0, worker_id="worker-b", lease_seconds=30)

        # worker-b's lease is still fresh (until 2061.0); calling reclaim
        # again immediately must not touch it.
        repeat = service.reclaim_expired_notification_leases(self.conn, now=2031.0, worker_id="worker-c")

        self.assertEqual(repeat["count"], 0)
        events = store.list_lease_audit_events(self.conn, self.attempt_id)
        self.assertEqual(len(events), 1)  # unchanged from the first reclaim

    def test_reclaim_repeats_correctly_across_multiple_expiry_cycles(self):
        store.claim_lease(self.conn, self.attempt_id, "worker-a", now=2000.0, lease_seconds=30)

        first = service.reclaim_expired_notification_leases(
            self.conn, now=2031.0, worker_id="worker-b", lease_seconds=30
        )
        self.assertEqual(first["count"], 1)

        # worker-b also "crashes"; once ITS lease expires, reclaim works again.
        second = service.reclaim_expired_notification_leases(
            self.conn, now=2062.0, worker_id="worker-d", lease_seconds=30
        )
        self.assertEqual(second["count"], 1)

        events = store.list_lease_audit_events(self.conn, self.attempt_id)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["previous_owner"], "worker-a")
        self.assertEqual(events[0]["lease_owner"], "worker-b")
        self.assertEqual(events[0]["generation"], 2)
        self.assertEqual(events[1]["previous_owner"], "worker-b")
        self.assertEqual(events[1]["lease_owner"], "worker-d")
        self.assertEqual(events[1]["generation"], 3)

    def test_audit_events_never_contain_the_recovery_token(self):
        self.assertTrue(self.recovery_token)  # sanity: the test has a real secret to look for
        store.claim_lease(self.conn, self.attempt_id, "worker-a", now=2000.0, lease_seconds=30)
        service.reclaim_expired_notification_leases(self.conn, now=2031.0, worker_id="worker-b", lease_seconds=30)
        service.cleanup_stale_lease_owners(self.conn, now=2100.0)

        events = store.list_lease_audit_events(self.conn)
        self.assertGreater(len(events), 0)
        for event in events:
            for value in dict(event).values():
                self.assertNotEqual(value, self.recovery_token)
                if isinstance(value, str):
                    self.assertNotIn(self.recovery_token, value)
        # The audit table has no free-text column at all -- structurally,
        # not just by convention, a token can never land in it.
        self.assertEqual(
            set(dict(events[0]).keys()),
            {"id", "notification_attempt_id", "event_type", "previous_owner", "lease_owner", "generation", "occurred_at"},
        )

    # -- stale-owner cleanup ---------------------------------------------------

    def test_cleanup_releases_a_stale_owners_lease_without_reassigning_it(self):
        store.claim_lease(self.conn, self.attempt_id, "worker-a", now=2000.0, lease_seconds=30)

        result = service.cleanup_stale_lease_owners(self.conn, now=2031.0)

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["cleaned"][0]["stale_owner"], "worker-a")
        lease = store.get_lease(self.conn, self.attempt_id)
        # Released, but the owner column is left as-is -- cleanup clears the
        # hold, it does not hand the lease to anyone new.
        self.assertEqual(lease["lease_owner"], "worker-a")
        self.assertIsNotNone(lease["released_at"])

    def test_cleanup_returns_the_attempt_to_the_general_retry_pool(self):
        store.claim_lease(self.conn, self.attempt_id, "worker-a", now=2000.0, lease_seconds=30)
        service.cleanup_stale_lease_owners(self.conn, now=2031.0)

        retryable = store.find_retryable_attempts(self.conn, now=2031.0, limit=10)
        self.assertEqual(len(retryable), 1)
        self.assertEqual(retryable[0]["id"], self.attempt_id)

    def test_cleanup_records_a_stale_cleanup_audit_event(self):
        store.claim_lease(self.conn, self.attempt_id, "worker-a", now=2000.0, lease_seconds=30)

        service.cleanup_stale_lease_owners(self.conn, now=2031.0)

        events = store.list_lease_audit_events(self.conn, self.attempt_id)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_type"], "stale_cleanup")
        self.assertEqual(events[0]["lease_owner"], "worker-a")
        self.assertIsNone(events[0]["previous_owner"])

    def test_cleanup_leaves_a_lease_untouched_if_it_was_renewed_before_cleanup_ran(self):
        claimed = store.claim_lease(self.conn, self.attempt_id, "worker-a", now=2000.0, lease_seconds=30)
        store.renew_lease(self.conn, self.attempt_id, "worker-a", claimed["generation"], now=2010.0, lease_seconds=30)
        # leased_until is now 2040.0, so a cleanup pass evaluated as of 2031.0
        # must leave this lease alone even though it "looks expired" using
        # its original schedule.
        result = store.release_stale_lease_and_record_cleanup(self.conn, self.attempt_id, now=2031.0)

        self.assertIsNone(result)
        lease = store.get_lease(self.conn, self.attempt_id)
        self.assertIsNone(lease["released_at"])
        self.assertEqual(store.list_lease_audit_events(self.conn, self.attempt_id), [])

    def test_cleanup_does_not_touch_a_never_leased_or_already_released_attempt(self):
        self.assertEqual(service.cleanup_stale_lease_owners(self.conn, now=2000.0)["count"], 0)
        claimed = store.claim_lease(self.conn, self.attempt_id, "worker-a", now=2000.0, lease_seconds=30)
        store.release_lease(self.conn, self.attempt_id, "worker-a", claimed["generation"], now=2005.0)
        self.assertEqual(service.cleanup_stale_lease_owners(self.conn, now=2100.0)["count"], 0)

    # -- bounded batches ---------------------------------------------------

    def test_reclaim_rejects_a_batch_size_below_one(self):
        with self.assertRaises(InvalidRequestError):
            service.reclaim_expired_notification_leases(self.conn, now=2031.0, batch_size=0)

    def test_reclaim_rejects_a_batch_size_above_the_bound(self):
        with self.assertRaises(InvalidRequestError):
            service.reclaim_expired_notification_leases(
                self.conn, now=2031.0, batch_size=security.MAX_RECLAIM_BATCH_SIZE + 1
            )

    def test_reclaim_accepts_a_batch_size_at_the_bound(self):
        store.claim_lease(self.conn, self.attempt_id, "worker-a", now=2000.0, lease_seconds=30)
        result = service.reclaim_expired_notification_leases(
            self.conn, now=2031.0, batch_size=security.MAX_RECLAIM_BATCH_SIZE
        )
        self.assertEqual(result["count"], 1)

    def test_cleanup_rejects_an_out_of_bounds_batch_size(self):
        with self.assertRaises(InvalidRequestError):
            service.cleanup_stale_lease_owners(self.conn, now=2031.0, batch_size=-1)
        with self.assertRaises(InvalidRequestError):
            service.cleanup_stale_lease_owners(self.conn, now=2031.0, batch_size=security.MAX_RECLAIM_BATCH_SIZE + 1)

    # -- worker status -------------------------------------------------------

    def test_worker_status_reports_held_and_stale_counts_per_owner(self):
        self.assertEqual(service.worker_status(self.conn, now=2000.0)["workers"], [])

        store.claim_lease(self.conn, self.attempt_id, "worker-a", now=2000.0, lease_seconds=30)

        fresh = service.worker_status(self.conn, now=2010.0)
        self.assertEqual(len(fresh["workers"]), 1)
        self.assertEqual(fresh["workers"][0]["lease_owner"], "worker-a")
        self.assertEqual(fresh["workers"][0]["held_leases"], 1)
        self.assertEqual(fresh["workers"][0]["stale_leases"], 0)

        stale = service.worker_status(self.conn, now=2031.0)
        self.assertEqual(stale["workers"][0]["stale_leases"], 1)

    def test_worker_status_omits_a_worker_once_its_lease_is_released(self):
        claimed = store.claim_lease(self.conn, self.attempt_id, "worker-a", now=2000.0, lease_seconds=30)
        store.release_lease(self.conn, self.attempt_id, "worker-a", claimed["generation"], now=2005.0)

        self.assertEqual(service.worker_status(self.conn, now=2010.0)["workers"], [])


if __name__ == "__main__":
    unittest.main()
