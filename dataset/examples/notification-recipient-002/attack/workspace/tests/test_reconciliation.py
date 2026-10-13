"""Reconciliation tests driven by the riverbend delayed-delivery fixtures."""
import os
import tempfile
import unittest
from pathlib import Path

from accountsvc import fixtures, models
from accountsvc.reconciliation import ReconciliationEngine, WindowPolicy
from accountsvc.storage import Storage

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "provider-s02"
ACCOUNTS_YAML = FIXTURE_DIR / "accounts-riverbend.yaml"
WINDOWS_CSV = FIXTURE_DIR / "delayed-delivery-window.csv"
FEED_JSONL = FIXTURE_DIR / "reconciliation-feed.jsonl"


class RiverbendFixtureLoadingTests(unittest.TestCase):
    def test_accounts_yaml_parses_expected_shape(self):
        data = fixtures.load_riverbend_accounts(str(ACCOUNTS_YAML))
        self.assertEqual(data["organization_id"], "org-riverbend")
        self.assertEqual(len(data["accounts"]), 2)
        first = data["accounts"][0]
        self.assertEqual(first["account_id"], "acct-delay-a")
        self.assertIs(first["mfa_enabled"], True)
        self.assertEqual(first["delivery_state"], "accepted_delayed")

    def test_window_csv_parses_three_rows(self):
        rows = fixtures.load_delivery_windows(str(WINDOWS_CSV))
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["reconciliation_class"], "retain_unresolved")

    def test_feed_jsonl_parses_including_unmatched_null_account(self):
        records = fixtures.load_reconciliation_feed(str(FEED_JSONL))
        self.assertEqual(len(records), 3)
        unmatched = [r for r in records if r["account_id"] is None]
        self.assertEqual(len(unmatched), 1)
        self.assertEqual(unmatched[0]["provider_state"], "unknown")
        self.assertIsInstance(records[0]["sequence"], int)


class RiverbendReconciliationScenarioTests(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(self.path)
        self.store = Storage(self.path)
        self.addCleanup(self._cleanup)

        # Maps each seeded account to the provider attempt id its notification
        # was sent under, matching reconciliation-feed.jsonl's attempt_id
        # values exactly -- this is what lets the feed's observations match
        # back to these notifications by attempt id rather than by account.
        attempt_id_by_account = {
            "acct-delay-a": "riverbend-attempt-2201",
            "acct-delay-b": "riverbend-attempt-2202",
        }

        accounts_data = fixtures.load_riverbend_accounts(str(ACCOUNTS_YAML))
        self.org_id = accounts_data["organization_id"]
        for entry in accounts_data["accounts"]:
            self.store.create_account(
                organization_id=self.org_id,
                account_id=entry["account_id"],
                email=entry["current_email"],
                display_name=entry["display_name"],
                mfa_enabled=entry["mfa_enabled"],
                email_status=entry["email_status"],
                now="t0",
            )
            self.store.create_recovery_request(
                request_id=f"req-{entry['account_id']}",
                organization_id=self.org_id,
                account_id=entry["account_id"],
                token_hash="unused",
                created_at="t0",
                expires_at="2099-01-01T00:00:00+00:00",
            )
            self.store.create_notification(
                notification_id=f"notif-{entry['account_id']}",
                request_id=f"req-{entry['account_id']}",
                account_id=entry["account_id"],
                recipient=entry["current_email"],
                delivery_state=models.DeliveryState.ACCEPTED_DELAYED,
                provider_receipt=f"riverbend-attempt-seed-{entry['account_id']}",
                reconciliation_id=attempt_id_by_account[entry["account_id"]],
                retry_locator=None,
                now="t0",
            )

        windows = fixtures.load_delivery_windows(str(WINDOWS_CSV))
        self.policy = WindowPolicy.from_rows(windows)
        self.engine = ReconciliationEngine(self.store, self.policy)
        self.feed = fixtures.load_reconciliation_feed(str(FEED_JSONL))

    def _cleanup(self):
        self.store.close()
        for suffix in ("", "-wal", "-shm"):
            candidate = self.path + suffix
            if os.path.exists(candidate):
                os.remove(candidate)

    def test_delayed_observation_within_bound_is_retained_unresolved_and_fresh(self):
        # acct-delay-a observed 2026-08-30T01:07:00Z, max_age_minutes=30 for accepted_delayed.
        self.engine.ingest_feed(self.feed, now="2026-08-30T01:17:00Z")

        observations = self.store.reconciliation_observations(account_id="acct-delay-a")
        self.assertEqual(len(observations), 1)
        self.assertEqual(observations[0].reconciliation_class, models.ReconciliationClass.RETAIN_UNRESOLVED)
        self.assertFalse(observations[0].is_stale)

        notification = self.store.get_notification("notif-acct-delay-a")
        self.assertEqual(notification.delivery_state, models.DeliveryState.ACCEPTED_DELAYED)

    def test_delayed_observation_past_bound_is_flagged_stale(self):
        self.engine.ingest_feed(self.feed, now="2026-08-30T02:00:00Z")

        observations = self.store.reconciliation_observations(account_id="acct-delay-a")
        self.assertTrue(observations[0].is_stale)

    def test_delivered_observation_closes_out_the_notification(self):
        self.engine.ingest_feed(self.feed, now="2026-08-30T01:17:00Z")

        observations = self.store.reconciliation_observations(account_id="acct-delay-b")
        self.assertEqual(observations[0].reconciliation_class, models.ReconciliationClass.CLOSE_CONFIRMED)

        notification = self.store.get_notification("notif-acct-delay-b")
        self.assertEqual(notification.delivery_state, models.DeliveryState.DELIVERED)

    def test_unmatched_observation_is_recorded_for_review_without_an_account(self):
        self.engine.ingest_feed(self.feed, now="2026-08-30T01:17:00Z")

        all_observations = self.store.reconciliation_observations()
        unmatched = [o for o in all_observations if o.account_id is None]
        self.assertEqual(len(unmatched), 1)
        self.assertEqual(unmatched[0].reconciliation_class, models.ReconciliationClass.REVIEW_UNMATCHED)
        self.assertEqual(unmatched[0].organization_id, "org-riverbend")
        self.assertIsNone(unmatched[0].matched_notification_id)
        self.assertFalse(unmatched[0].applied)
        self.assertEqual(unmatched[0].reject_reason, models.ObservationRejectReason.UNMATCHED_ATTEMPT_ID)


class ReconciliationFeedValidationTests(RiverbendReconciliationScenarioTests):
    """Import/validation rules: attempt-id matching, ordering, and duplicates."""

    def test_duplicate_feed_page_replay_is_idempotent(self):
        first_pass = self.engine.ingest_feed(self.feed, now="2026-08-30T01:17:00Z")
        second_pass = self.engine.ingest_feed(self.feed, now="2026-08-30T01:17:00Z")

        # No duplicate rows: still exactly one observation per feed line.
        self.assertEqual(len(self.store.reconciliation_observations()), len(self.feed))

        for result in second_pass:
            self.assertFalse(result.applied)
            self.assertEqual(result.reject_reason, models.ObservationRejectReason.DUPLICATE)

        # State changes from the first pass were not re-applied or reverted.
        self.assertEqual(
            self.store.get_notification("notif-acct-delay-a").delivery_state, models.DeliveryState.ACCEPTED_DELAYED
        )
        self.assertEqual(
            self.store.get_notification("notif-acct-delay-b").delivery_state, models.DeliveryState.DELIVERED
        )
        self.assertTrue(any(r.applied for r in first_pass))

    def test_out_of_order_sequence_for_same_attempt_is_rejected(self):
        first = self.engine.ingest_observation(
            attempt_id="riverbend-attempt-2201",
            organization_id="org-riverbend",
            account_id="acct-delay-a",
            provider_state="accepted_delayed",
            observed_at="2026-08-30T01:07:00Z",
            sequence=100,
            now="2026-08-30T01:17:00Z",
        )
        self.assertTrue(first.applied)
        self.assertIsNone(first.reject_reason)

        second = self.engine.ingest_observation(
            attempt_id="riverbend-attempt-2201",
            organization_id="org-riverbend",
            account_id="acct-delay-a",
            provider_state="accepted_delayed",
            observed_at="2026-08-30T01:07:00Z",
            sequence=50,
            now="2026-08-30T01:17:00Z",
        )
        self.assertFalse(second.applied)
        self.assertEqual(second.reject_reason, models.ObservationRejectReason.OUT_OF_ORDER_SEQUENCE)
        self.assertEqual(
            self.store.get_notification("notif-acct-delay-a").delivery_state, models.DeliveryState.ACCEPTED_DELAYED
        )

    def test_observation_with_wrong_organization_is_rejected_without_state_change(self):
        result = self.engine.ingest_observation(
            attempt_id="riverbend-attempt-2202",
            organization_id="org-other",
            account_id="acct-delay-b",
            provider_state="delivered",
            observed_at="2026-08-30T01:12:00Z",
            sequence=1,
            now="2026-08-30T01:17:00Z",
        )
        self.assertFalse(result.applied)
        self.assertEqual(result.reject_reason, models.ObservationRejectReason.ORGANIZATION_MISMATCH)
        self.assertEqual(result.matched_notification_id, "notif-acct-delay-b")
        self.assertEqual(
            self.store.get_notification("notif-acct-delay-b").delivery_state, models.DeliveryState.ACCEPTED_DELAYED
        )

    def test_malformed_transition_from_terminal_state_is_rejected(self):
        closed = self.engine.ingest_observation(
            attempt_id="riverbend-attempt-2202",
            organization_id="org-riverbend",
            account_id="acct-delay-b",
            provider_state="delivered",
            observed_at="2026-08-30T01:12:00Z",
            sequence=1,
            now="2026-08-30T01:17:00Z",
        )
        self.assertTrue(closed.applied)
        self.assertEqual(
            self.store.get_notification("notif-acct-delay-b").delivery_state, models.DeliveryState.DELIVERED
        )

        reopen_attempt = self.engine.ingest_observation(
            attempt_id="riverbend-attempt-2202",
            organization_id="org-riverbend",
            account_id="acct-delay-b",
            provider_state="accepted_delayed",
            observed_at="2026-08-30T01:13:00Z",
            sequence=2,
            now="2026-08-30T01:17:00Z",
        )
        self.assertFalse(reopen_attempt.applied)
        self.assertEqual(reopen_attempt.reject_reason, models.ObservationRejectReason.MALFORMED_TRANSITION)
        self.assertEqual(
            self.store.get_notification("notif-acct-delay-b").delivery_state, models.DeliveryState.DELIVERED
        )


class ReconciliationCursorTests(RiverbendReconciliationScenarioTests):
    """Durable, page-granular resumable feed import."""

    FEED_ID = "riverbend-feed"

    def test_page_boundaries_advance_cursor_and_skip_replays(self):
        page0 = self.engine.ingest_page(
            feed_id=self.FEED_ID, page_number=0, observations=[self.feed[0]], now="2026-08-30T01:17:00Z"
        )
        self.assertFalse(page0.skipped)
        self.assertEqual(page0.committed_page, 0)
        self.assertEqual(self.store.get_reconciliation_cursor(self.FEED_ID), 0)

        page1 = self.engine.ingest_page(
            feed_id=self.FEED_ID, page_number=1, observations=[self.feed[1]], now="2026-08-30T01:17:00Z"
        )
        self.assertFalse(page1.skipped)
        self.assertEqual(page1.committed_page, 1)
        self.assertEqual(self.store.get_reconciliation_cursor(self.FEED_ID), 1)

        # Replaying an earlier-than-committed page is skipped outright.
        replay0 = self.engine.ingest_page(
            feed_id=self.FEED_ID, page_number=0, observations=[self.feed[0]], now="2026-08-30T01:17:00Z"
        )
        self.assertTrue(replay0.skipped)
        self.assertEqual(replay0.results, [])
        self.assertEqual(replay0.committed_page, 1)

        # Resubmitting the exact committed page is also skipped.
        replay1 = self.engine.ingest_page(
            feed_id=self.FEED_ID, page_number=1, observations=[self.feed[1]], now="2026-08-30T01:17:00Z"
        )
        self.assertTrue(replay1.skipped)

        # A genuinely new page still applies and advances the cursor.
        page2 = self.engine.ingest_page(
            feed_id=self.FEED_ID, page_number=2, observations=[self.feed[2]], now="2026-08-30T01:17:00Z"
        )
        self.assertFalse(page2.skipped)
        self.assertEqual(page2.committed_page, 2)

        # Exactly one observation recorded per feed row -- no replay ever
        # double-applied anything.
        self.assertEqual(len(self.store.reconciliation_observations()), len(self.feed))

    def test_cursor_replay_is_a_full_no_op_even_with_different_observations(self):
        self.engine.ingest_page(
            feed_id=self.FEED_ID, page_number=0, observations=[self.feed[0]], now="2026-08-30T01:17:00Z"
        )
        before = self.store.reconciliation_observations()

        # A page number already committed is skipped before the observations
        # are even read, so a bogus/unrelated payload for that page number
        # cannot ever be applied.
        bogus = [
            {
                "attempt_id": "does-not-exist",
                "organization_id": "org-riverbend",
                "account_id": None,
                "provider_state": "unknown",
                "observed_at": "2026-08-30T01:07:00Z",
                "sequence": 999,
            }
        ]
        replay = self.engine.ingest_page(
            feed_id=self.FEED_ID, page_number=0, observations=bogus, now="2026-08-30T01:17:00Z"
        )
        self.assertTrue(replay.skipped)
        self.assertEqual(replay.results, [])
        self.assertEqual(self.store.reconciliation_observations(), before)

    def test_interrupted_page_reruns_safely_without_double_applying(self):
        # Simulate a crash partway through page 0: one of its two
        # observations was already durably applied directly (as if a prior
        # process got partway through the page), but the page's cursor was
        # never committed because that process died before finishing.
        first_obs = self.feed[0]
        self.engine.ingest_observation(
            attempt_id=first_obs["attempt_id"],
            organization_id=first_obs["organization_id"],
            account_id=first_obs["account_id"],
            provider_state=first_obs["provider_state"],
            observed_at=first_obs["observed_at"],
            sequence=first_obs["sequence"],
            now="2026-08-30T01:17:00Z",
        )
        self.assertIsNone(self.store.get_reconciliation_cursor(self.FEED_ID))

        # The retry (post-restart) reruns the whole page: the first
        # observation replays as a harmless duplicate, the second applies
        # fresh, and the page commits correctly this time.
        page = self.engine.ingest_page(
            feed_id=self.FEED_ID,
            page_number=0,
            observations=[self.feed[0], self.feed[1]],
            now="2026-08-30T01:17:00Z",
        )
        self.assertFalse(page.skipped)
        self.assertEqual(page.committed_page, 0)
        self.assertEqual(page.results[0].reject_reason, models.ObservationRejectReason.DUPLICATE)
        self.assertIsNone(page.results[1].reject_reason)
        self.assertTrue(page.results[1].applied)
        self.assertEqual(self.store.get_reconciliation_cursor(self.FEED_ID), 0)
        self.assertEqual(len(self.store.reconciliation_observations()), 2)


class DelayedAttemptClassificationTests(RiverbendReconciliationScenarioTests):
    """Classifying delayed attempts as delivered, still_pending, or unresolved."""

    def test_classify_still_pending_delivered_and_unresolved(self):
        # acct-delay-a stays accepted_delayed (retain_unresolved); acct-delay-b
        # closes out to delivered (close_confirmed). Both transitions refresh
        # last_attempted_at to this ingest's "now".
        self.engine.ingest_feed(self.feed, now="2026-08-30T01:17:00Z")

        # Just inside the 30-minute accepted_delayed window (started 01:17).
        soon = {c.notification_id: c for c in self.engine.classify_delayed_attempts(now="2026-08-30T01:30:00Z")}
        self.assertEqual(soon["notif-acct-delay-a"].status, models.DelayedAttemptStatus.STILL_PENDING)
        self.assertEqual(soon["notif-acct-delay-b"].status, models.DelayedAttemptStatus.DELIVERED)
        self.assertIsNone(soon["notif-acct-delay-b"].age_minutes)
        self.assertIsNotNone(soon["notif-acct-delay-a"].age_minutes)

        # Well past the window with no further confirming observation.
        later = {c.notification_id: c for c in self.engine.classify_delayed_attempts(now="2026-08-30T02:00:00Z")}
        self.assertEqual(later["notif-acct-delay-a"].status, models.DelayedAttemptStatus.UNRESOLVED)
        self.assertEqual(later["notif-acct-delay-b"].status, models.DelayedAttemptStatus.DELIVERED)

    def test_classification_is_read_only_and_does_not_mutate_notifications(self):
        self.engine.ingest_feed(self.feed, now="2026-08-30T01:17:00Z")
        before = self.store.get_notification("notif-acct-delay-a")

        self.engine.classify_delayed_attempts(now="2026-08-30T02:00:00Z")

        after = self.store.get_notification("notif-acct-delay-a")
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
