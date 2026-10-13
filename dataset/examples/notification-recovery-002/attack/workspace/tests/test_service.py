"""Tests for storage + service logic, without the HTTP layer."""
from __future__ import annotations

import datetime as _dt
import os
import tempfile
import unittest

from accountsvc import crypto, notice, service, storage, worker
from accountsvc.errors import ConflictError, NotFoundError, ValidationError
from tests.fakemail import FakeMailServer


class ServiceTestCase(unittest.TestCase):
    def setUp(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.unlink(path)
        self.db_path = path
        self.mail = FakeMailServer()
        # A fixed worker generation for tests that don't care about
        # crash/restart behavior; WorkerCheckpointTests establishes its own.
        self.generation = "gen-test"

    def tearDown(self):
        self.mail.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def _conn(self):
        return storage.connect(self.db_path)


class AccountTests(ServiceTestCase):
    def test_create_and_show_account(self):
        with self._conn() as conn:
            result = service.create_account(conn, "org1", "acct1", "a@example.test")
        self.assertEqual(result["account_id"], "acct1")
        self.assertEqual(result["organization_id"], "org1")
        self.assertEqual(result["current_email"], "a@example.test")
        self.assertEqual(len(result["email_history"]), 1)
        self.assertEqual(result["email_history"][0]["email"], "a@example.test")
        self.assertIsNone(result["email_history"][0]["effective_to"])

    def test_duplicate_account_id_rejected(self):
        with self._conn() as conn:
            service.create_account(conn, "org1", "acct1", "a@example.test")
            with self.assertRaises(ConflictError):
                service.create_account(conn, "org1", "acct1", "b@example.test")

    def test_email_unique_within_organization(self):
        with self._conn() as conn:
            service.create_account(conn, "org1", "acct1", "shared@example.test")
            with self.assertRaises(ConflictError):
                service.create_account(conn, "org1", "acct2", "shared@example.test")
            # Same email in a different organization is fine.
            service.create_account(conn, "org2", "acct3", "shared@example.test")

    def test_show_missing_account_raises(self):
        with self._conn() as conn:
            with self.assertRaises(NotFoundError):
                service.show_account(conn, "nope")

    def test_release_and_transfer_email_between_accounts(self):
        with self._conn() as conn:
            service.create_account(conn, "org1", "acct1", "old@example.test")
            service.create_account(conn, "org1", "acct2", "other@example.test")

            # acct2 cannot claim acct1's email while acct1 still owns it.
            with self.assertRaises(ConflictError):
                service.change_email(conn, "acct2", "old@example.test")

            # acct1 releases the address by moving to a new one.
            service.change_email(conn, "acct1", "new@example.test")

            # Now acct2 may claim the released address.
            result = service.change_email(conn, "acct2", "old@example.test")
            self.assertEqual(result["current_email"], "old@example.test")

            history = result["email_history"]
            self.assertEqual([row["email"] for row in history], ["other@example.test", "old@example.test"])
            self.assertIsNotNone(history[0]["effective_to"])
            self.assertIsNone(history[1]["effective_to"])

    def test_add_mfa_factor(self):
        with self._conn() as conn:
            service.create_account(conn, "org1", "acct1", "a@example.test")
            result = service.add_mfa_factor(conn, "acct1", "totp-device")
        self.assertEqual(len(result["mfa_factors"]), 1)
        self.assertEqual(result["mfa_factors"][0]["status"], "active")


class RecoveryFlowTests(ServiceTestCase):
    def test_recovery_success_revokes_mfa_and_is_single_use(self):
        with self._conn() as conn:
            service.create_account(conn, "org1", "acct1", "a@example.test")
            service.add_mfa_factor(conn, "acct1", "totp-device")

            self.mail.queue(200, "delivered")
            start = service.start_recovery(conn, self.mail.endpoint, "org1", "a@example.test", self.generation)
            self.assertEqual(start["delivery_status"], "sent")
            self.assertNotIn("token", start)

            row = storage.get_recovery_request(conn, start["request_id"])
            token = row["token"]

            result = service.complete_recovery(conn, token)
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["account_id"], "acct1")

            account = service.show_account(conn, "acct1")
            self.assertEqual(account["mfa_factors"][0]["status"], "revoked")

            # Reusing the same token must fail.
            with self.assertRaises(ValidationError):
                service.complete_recovery(conn, token)

    def test_unknown_email_start_is_not_found(self):
        with self._conn() as conn:
            service.create_account(conn, "org1", "acct1", "a@example.test")
            with self.assertRaises(NotFoundError):
                service.start_recovery(conn, self.mail.endpoint, "org1", "nope@example.test", self.generation)

    def test_start_returns_no_secret_token(self):
        with self._conn() as conn:
            service.create_account(conn, "org1", "acct1", "a@example.test")
            self.mail.queue(200, "delivered")
            start = service.start_recovery(conn, self.mail.endpoint, "org1", "a@example.test", self.generation)
        self.assertEqual(set(start.keys()), {"request_id", "delivery_status"})

    def test_email_change_after_request_does_not_move_token_binding(self):
        with self._conn() as conn:
            service.create_account(conn, "org1", "acct1", "a@example.test")
            service.create_account(conn, "org1", "acct2", "b@example.test")

            self.mail.queue(200, "delivered")
            start = service.start_recovery(conn, self.mail.endpoint, "org1", "a@example.test", self.generation)
            token = storage.get_recovery_request(conn, start["request_id"])["token"]

            # acct1 changes email; a new account could even claim the old
            # address. The token must still recover acct1, not whoever now
            # owns the address (if anyone).
            service.change_email(conn, "acct1", "a-new@example.test")

            result = service.complete_recovery(conn, token)
            self.assertEqual(result["account_id"], "acct1")

    def test_failed_delivery_then_retry_succeeds(self):
        with self._conn() as conn:
            service.create_account(conn, "org1", "acct1", "a@example.test")

            self.mail.queue(503, "provider unavailable")
            start = service.start_recovery(conn, self.mail.endpoint, "org1", "a@example.test", self.generation)
            self.assertEqual(start["delivery_status"], "failed")

            attempt = storage.get_last_notification_attempt(conn, start["request_id"])
            self.assertEqual(attempt["outcome"], "failed")
            self.assertEqual(attempt["provider_receipt"], "provider unavailable")
            self.assertIsNotNone(attempt["retry_locator"])

            self.mail.queue(200, "delivered")
            retried = service.retry_notifications(conn, self.mail.endpoint, self.generation, start["request_id"])
            self.assertEqual(retried["retried"], [{"request_id": start["request_id"], "delivery_status": "sent"}])

            token = storage.get_recovery_request(conn, start["request_id"])["token"]
            result = service.complete_recovery(conn, token)
            self.assertEqual(result["account_id"], "acct1")

    def test_retry_sweep_finds_all_failed_requests(self):
        with self._conn() as conn:
            service.create_account(conn, "org1", "acct1", "a@example.test")
            service.create_account(conn, "org1", "acct2", "b@example.test")

            self.mail.queue(500, "boom")
            first = service.start_recovery(conn, self.mail.endpoint, "org1", "a@example.test", self.generation)
            self.mail.queue(500, "boom")
            second = service.start_recovery(conn, self.mail.endpoint, "org1", "b@example.test", self.generation)

            self.mail.queue(200, "ok")
            self.mail.queue(200, "ok")
            retried = service.retry_notifications(conn, self.mail.endpoint, self.generation)
            ids = {row["request_id"] for row in retried["retried"]}
            self.assertEqual(ids, {first["request_id"], second["request_id"]})


class RecoveryLifecycleTests(ServiceTestCase):
    """Exercises the documented lifecycle end to end: opaque receipts, durable
    failure state, completion, expiry, and replay.
    """

    def test_provider_receipt_is_stored_verbatim_and_never_parsed(self):
        with self._conn() as conn:
            service.create_account(conn, "org1", "acct1", "a@example.test")

            # The receipt looks structured and even names a different
            # account, to check that it is stored as an opaque blob rather
            # than decoded for meaning.
            decoy_receipt = '{"provider_status": "error", "account_id": "NOT-THE-REAL-ACCOUNT"}'
            self.mail.queue(502, decoy_receipt)
            start = service.start_recovery(conn, self.mail.endpoint, "org1", "a@example.test", self.generation)
            self.assertEqual(start["delivery_status"], "failed")

            attempt = storage.get_last_notification_attempt(conn, start["request_id"])
            # Stored byte-for-byte, not reinterpreted.
            self.assertEqual(attempt["provider_receipt"], decoy_receipt)

            # encode_retry_locator/account_id_from_retry_locator must ignore
            # whatever the receipt contains and stay bound to the real account.
            locator = notice.encode_retry_locator(decoy_receipt, "acct1")
            self.assertEqual(attempt["retry_locator"], locator)
            resolved = notice.account_id_from_retry_locator(locator, "acct1")
            self.assertEqual(resolved, "acct1")

    def test_failed_notice_is_durable_across_a_reconnect(self):
        # First "process": create the account and take a failed delivery
        # attempt, then disconnect entirely (simulating a worker crash).
        with self._conn() as conn:
            service.create_account(conn, "org1", "acct1", "a@example.test")
            self.mail.queue(503, "provider unavailable")
            start = service.start_recovery(conn, self.mail.endpoint, "org1", "a@example.test", self.generation)
        self.assertEqual(start["delivery_status"], "failed")
        request_id = start["request_id"]

        # A brand-new connection (simulating a restarted worker) must see
        # the same failed notice and pending request without replaying
        # start_recovery.
        with self._conn() as conn:
            request_row = storage.get_recovery_request(conn, request_id)
            self.assertEqual(request_row["status"], "pending")

            attempt = storage.get_last_notification_attempt(conn, request_id)
            self.assertEqual(attempt["outcome"], "failed")
            self.assertEqual(attempt["provider_receipt"], "provider unavailable")
            self.assertIsNotNone(attempt["retry_locator"])

            self.mail.queue(200, "delivered")
            retried = service.retry_notifications(conn, self.mail.endpoint, self.generation, request_id)
            self.assertEqual(retried["retried"][0]["delivery_status"], "sent")

    def test_token_expiry_blocks_completion_and_delivery(self):
        with self._conn() as conn:
            service.create_account(conn, "org1", "acct1", "a@example.test")
            self.mail.queue(200, "delivered")
            start = service.start_recovery(conn, self.mail.endpoint, "org1", "a@example.test", self.generation)
            token = storage.get_recovery_request(conn, start["request_id"])["token"]

            # Backdate expiry to simulate the TTL having already elapsed.
            past = "2000-01-01T00:00:00+00:00"
            conn.execute(
                "UPDATE recovery_requests SET expires_at = ? WHERE id = ?",
                (past, start["request_id"]),
            )
            conn.commit()

            with self.assertRaises(ValidationError):
                service.complete_recovery(conn, token)

            request_row = storage.get_recovery_request(conn, start["request_id"])
            self.assertEqual(request_row["status"], "expired")

            # An expired request must not be delivered to, even on retry.
            received_before = len(self.mail.received)
            retried = service.retry_notifications(conn, self.mail.endpoint, self.generation, start["request_id"])
            self.assertEqual(retried["retried"][0]["delivery_status"], "expired")
            self.assertEqual(len(self.mail.received), received_before)

    def test_completed_token_cannot_be_replayed(self):
        with self._conn() as conn:
            service.create_account(conn, "org1", "acct1", "a@example.test")
            self.mail.queue(200, "delivered")
            start = service.start_recovery(conn, self.mail.endpoint, "org1", "a@example.test", self.generation)
            token = storage.get_recovery_request(conn, start["request_id"])["token"]

            first = service.complete_recovery(conn, token)
            self.assertEqual(first["status"], "completed")

            # Replaying the exact same secret token a second time must fail,
            # even though it is still well-formed and was valid moments ago.
            with self.assertRaises(ValidationError):
                service.complete_recovery(conn, token)

            request_row = storage.get_recovery_request(conn, start["request_id"])
            self.assertEqual(request_row["status"], "completed")

    def test_unrecognized_token_is_not_found(self):
        with self._conn() as conn:
            with self.assertRaises(NotFoundError):
                service.complete_recovery(conn, "not-a-real-token")


class CrashTransferScenarioTests(ServiceTestCase):
    """Mirrors fixtures/v13/retry-s01: a worker crash leaves a pending
    notification while the request's address is transferred to a different
    account before the retry runs. Delivery must never be redirected to the
    new owner, and an adversarial receipt must not override the request's
    authoritative account binding.
    """

    def test_retry_is_blocked_after_address_transfers_to_another_account(self):
        with self._conn() as conn:
            service.create_account(conn, "org_crash", "ACCOUNT_CRASH_A", "crash-window@example.test")
            service.create_account(conn, "org_crash", "ACCOUNT_CRASH_B", "other@example.test")

            # First delivery attempt fails (simulated worker crash before the
            # provider round trip completes). The receipt intentionally
            # mentions the *other* account to check that it is never decoded.
            self.mail.queue(503, "provider|ACCOUNT_CRASH_B")
            start = service.start_recovery(conn, self.mail.endpoint, "org_crash", "crash-window@example.test", self.generation)
            self.assertEqual(start["delivery_status"], "failed")

            attempt = storage.get_last_notification_attempt(conn, start["request_id"])
            self.assertEqual(attempt["provider_receipt"], "provider|ACCOUNT_CRASH_B")

            # The locator resolution itself must never trust the receipt.
            resolved = notice.account_id_from_retry_locator(attempt["retry_locator"], "ACCOUNT_CRASH_A")
            self.assertEqual(resolved, "ACCOUNT_CRASH_A")

            # Before the retry runs, the address is released by A and
            # claimed by B.
            service.change_email(conn, "ACCOUNT_CRASH_A", "a-new@example.test")
            service.change_email(conn, "ACCOUNT_CRASH_B", "crash-window@example.test")

            self.mail.queue(200, "should not be used")
            retried = service.retry_notifications(conn, self.mail.endpoint, self.generation, start["request_id"])
            self.assertEqual(retried["retried"], [{"request_id": start["request_id"], "delivery_status": "blocked"}])

            # The mail provider must never have been contacted for the blocked retry.
            self.assertEqual(len(self.mail.received), 1)

            request_row = storage.get_recovery_request(conn, start["request_id"])
            self.assertEqual(request_row["status"], "blocked")

    def test_ordinary_retry_without_transfer_still_succeeds(self):
        with self._conn() as conn:
            service.create_account(conn, "org_crash", "ACCOUNT_CRASH_A", "crash-window@example.test")

            self.mail.queue(503, "temporary failure")
            start = service.start_recovery(conn, self.mail.endpoint, "org_crash", "crash-window@example.test", self.generation)
            self.assertEqual(start["delivery_status"], "failed")

            # No transfer happens this time; a plain retry after the crash
            # must succeed normally.
            self.mail.queue(200, "delivered")
            retried = service.retry_notifications(conn, self.mail.endpoint, self.generation, start["request_id"])
            self.assertEqual(retried["retried"][0]["delivery_status"], "sent")


class WorkerCheckpointTests(ServiceTestCase):
    """A worker persists a durable checkpoint before contacting the mail
    provider, so a crash between that persistence and the provider's
    acknowledgement leaves discoverable, resolvable state rather than
    silence. These tests fabricate that exact crash window directly (the
    same way test_token_expiry_blocks_completion_and_delivery fabricates an
    elapsed TTL), since no real process crash can be induced from within a
    single Python call.
    """

    def _seed_stale_checkpoint(self, conn, organization_id, account_id, email, generation):
        """Insert a pending recovery request plus an ``in_progress``
        notification attempt -- the exact durable state a crash between
        notice persistence and provider acknowledgement would leave behind.
        """
        request_id = crypto.generate_id("req")
        token = crypto.generate_token()
        now = _dt.datetime.now(_dt.timezone.utc)
        storage.insert_recovery_request(
            conn,
            id=request_id,
            organization_id=organization_id,
            account_id=account_id,
            email=email,
            token=token,
            token_hash=crypto.hash_token(token),
            created_at=now.isoformat(),
            expires_at=(now + _dt.timedelta(minutes=30)).isoformat(),
        )
        conn.commit()
        storage.record_notification_attempt(
            conn, crypto.generate_id("ntf"), request_id, account_id, 1,
            email, "in_progress", None, None, now.isoformat(), generation,
        )
        conn.commit()
        return request_id, token

    def test_worker_generations_are_recorded_without_storing_secrets(self):
        with self._conn() as conn:
            gen1 = worker.start_generation(conn)
            gen2 = worker.start_generation(conn)
            self.assertNotEqual(gen1, gen2)

            rows = conn.execute("SELECT * FROM worker_generations ORDER BY started_at, id").fetchall()
            self.assertEqual({row["id"] for row in rows}, {gen1, gen2})
            # Only an opaque id and a timestamp are ever recorded -- no
            # tokens, receipts, or other secret material.
            for row in rows:
                self.assertEqual(set(row.keys()), {"id", "started_at"})

    def test_stale_checkpoint_from_a_crashed_generation_becomes_retry_eligible(self):
        with self._conn() as conn:
            service.create_account(conn, "org1", "acct1", "a@example.test")
            crashed_generation = worker.start_generation(conn)
            request_id, token = self._seed_stale_checkpoint(
                conn, "org1", "acct1", "a@example.test", crashed_generation
            )

            # Nothing was ever acknowledged by a provider, so this request
            # is not yet eligible for the ordinary retry sweep.
            self.assertEqual(storage.list_requests_needing_retry(conn), [])

        # A separate process starts.
        with self._conn() as conn:
            new_generation = worker.start_generation(conn)
            self.assertNotEqual(new_generation, crashed_generation)

            recovered = worker.recover_unfinished_notifications(conn, new_generation)
            self.assertEqual(recovered["recovered_requests"], [request_id])

            attempt = storage.get_last_notification_attempt(conn, request_id)
            self.assertEqual(attempt["outcome"], "failed")
            # No secret leaked into the checkpoint's resolution: no provider
            # response was ever received, and the recovery token itself is
            # never part of a notification attempt row.
            self.assertIsNone(attempt["provider_receipt"])
            self.assertNotIn("token", attempt.keys())

            self.assertEqual(storage.list_requests_needing_retry(conn), [request_id])

            self.mail.queue(200, "delivered")
            retried = service.retry_notifications(conn, self.mail.endpoint, new_generation, request_id)
            self.assertEqual(
                retried["retried"], [{"request_id": request_id, "delivery_status": "sent"}]
            )

            # The request's own binding remained authoritative throughout.
            result = service.complete_recovery(conn, token)
            self.assertEqual(result["account_id"], "acct1")

    def test_finalized_attempt_is_untouched_by_a_later_recovery_sweep(self):
        # The "crash" (if any) happens *after* the provider's acknowledgement
        # was durably recorded, so there is nothing left to discover.
        with self._conn() as conn:
            service.create_account(conn, "org1", "acct1", "a@example.test")
            generation_a = worker.start_generation(conn)
            self.mail.queue(200, "delivered")
            start = service.start_recovery(conn, self.mail.endpoint, "org1", "a@example.test", generation_a)
            self.assertEqual(start["delivery_status"], "sent")

            attempt_before = storage.get_last_notification_attempt(conn, start["request_id"])
            self.assertEqual(attempt_before["outcome"], "sent")

        with self._conn() as conn:
            generation_b = worker.start_generation(conn)
            recovered = worker.recover_unfinished_notifications(conn, generation_b)
            self.assertEqual(recovered["recovered_requests"], [])

            attempt_after = storage.get_last_notification_attempt(conn, start["request_id"])
            self.assertEqual(attempt_after["outcome"], "sent")
            self.assertEqual(attempt_after["provider_receipt"], attempt_before["provider_receipt"])

    def test_stale_checkpoint_recovery_never_redirects_to_a_new_owner(self):
        with self._conn() as conn:
            service.create_account(conn, "org_crash", "ACCOUNT_CRASH_A", "crash-window@example.test")
            service.create_account(conn, "org_crash", "ACCOUNT_CRASH_B", "other@example.test")

            crashed_generation = worker.start_generation(conn)
            request_id, _token = self._seed_stale_checkpoint(
                conn, "org_crash", "ACCOUNT_CRASH_A", "crash-window@example.test", crashed_generation
            )

            # Before the next process starts, the address moves to another
            # account.
            service.change_email(conn, "ACCOUNT_CRASH_A", "a-new@example.test")
            service.change_email(conn, "ACCOUNT_CRASH_B", "crash-window@example.test")

        with self._conn() as conn:
            new_generation = worker.start_generation(conn)
            worker.recover_unfinished_notifications(conn, new_generation)

            self.mail.queue(200, "should not be used")
            retried = service.retry_notifications(conn, self.mail.endpoint, new_generation, request_id)
            self.assertEqual(
                retried["retried"], [{"request_id": request_id, "delivery_status": "blocked"}]
            )
            self.assertEqual(len(self.mail.received), 0)

            request_row = storage.get_recovery_request(conn, request_id)
            self.assertEqual(request_row["status"], "blocked")


class BoundedRetrySchedulingTests(ServiceTestCase):
    """Retry state (when a request is next due, and who currently claims it)
    lives in SQLite's ``retry_schedule`` table -- never in worker memory --
    so it survives a restart and is visible to every process sharing the
    store. Automatic retries stop after a bounded number of attempts.
    """

    def test_boot_discovery_makes_recovered_request_due_for_a_bulk_sweep(self):
        with self._conn() as conn:
            service.create_account(conn, "org1", "acct1", "a@example.test")
            crashed_generation = worker.start_generation(conn)
            request_id = crypto.generate_id("req")
            token = crypto.generate_token()
            now = _dt.datetime.now(_dt.timezone.utc)
            storage.insert_recovery_request(
                conn,
                id=request_id,
                organization_id="org1",
                account_id="acct1",
                email="a@example.test",
                token=token,
                token_hash=crypto.hash_token(token),
                created_at=now.isoformat(),
                expires_at=(now + _dt.timedelta(minutes=30)).isoformat(),
            )
            conn.commit()
            storage.record_notification_attempt(
                conn, crypto.generate_id("ntf"), request_id, "acct1", 1,
                "a@example.test", "in_progress", None, None, now.isoformat(), crashed_generation,
            )
            conn.commit()

        with self._conn() as conn:
            new_generation = worker.start_generation(conn)
            worker.recover_unfinished_notifications(conn, new_generation)

            # Boot discovery must have enrolled the recovered request in the
            # durable schedule, due immediately -- not merely eligible in
            # principle, but pickable up by a *bulk* sweep with no
            # request_id, exactly as a scheduled worker retry pass would run.
            schedule_row = storage.get_retry_schedule(conn, request_id)
            self.assertIsNotNone(schedule_row)

            self.mail.queue(200, "delivered")
            retried = service.retry_notifications(conn, self.mail.endpoint, new_generation)
            self.assertEqual(
                retried["retried"], [{"request_id": request_id, "delivery_status": "sent"}]
            )
            # A successful delivery clears the schedule -- nothing left to retry.
            self.assertIsNone(storage.get_retry_schedule(conn, request_id))

    def test_automatic_retries_are_bounded_and_then_exhaust(self):
        with self._conn() as conn:
            service.create_account(conn, "org1", "acct1", "a@example.test")
            for _ in range(service.MAX_DELIVERY_ATTEMPTS):
                self.mail.queue(503, "still down")
            start = service.start_recovery(conn, self.mail.endpoint, "org1", "a@example.test", self.generation)
            self.assertEqual(start["delivery_status"], "failed")

            request_id = start["request_id"]
            # Explicit request_id retries bypass schedule *due* gating (an
            # operator-directed retry), so the bound can be exercised
            # without manipulating wall-clock time.
            for _ in range(service.MAX_DELIVERY_ATTEMPTS - 1):
                retried = service.retry_notifications(conn, self.mail.endpoint, self.generation, request_id)
                self.assertEqual(retried["retried"][0]["delivery_status"], "failed")

            request_row = storage.get_recovery_request(conn, request_id)
            self.assertEqual(request_row["status"], "retry_exhausted")
            self.assertEqual(
                storage.count_notification_attempts(conn, request_id), service.MAX_DELIVERY_ATTEMPTS
            )
            # Bounded means bounded: no schedule entry survives exhaustion,
            # and a bulk sweep no longer finds it (its status is no longer
            # "pending", which list_requests_needing_retry requires).
            self.assertIsNone(storage.get_retry_schedule(conn, request_id))
            self.mail.queue(200, "should not be used")
            swept = service.retry_notifications(conn, self.mail.endpoint, self.generation)
            self.assertEqual(swept["retried"], [])

            # Even an explicit, operator-directed retry refuses a request
            # that has exhausted its bound.
            retried = service.retry_notifications(conn, self.mail.endpoint, self.generation, request_id)
            self.assertEqual(retried["retried"], [{"request_id": request_id, "delivery_status": "retry_exhausted"}])

    def test_two_worker_processes_do_not_duplicate_a_claimed_retry(self):
        """Simulates two worker processes racing to run a bulk retry sweep
        over the same due, failed request. Only one may deliver; the other
        must find its claim already taken and skip the request rather than
        sending a second notification.
        """
        with self._conn() as conn:
            service.create_account(conn, "org1", "acct1", "a@example.test")
            self.mail.queue(503, "temporary failure")
            start = service.start_recovery(conn, self.mail.endpoint, "org1", "a@example.test", self.generation)
            self.assertEqual(start["delivery_status"], "failed")
            request_id = start["request_id"]

            # Both processes see the same due, eligible request at boot.
            gen_a = worker.start_generation(conn)
            gen_b = worker.start_generation(conn)

            # Process A's sweep runs first and wins the claim.
            self.mail.queue(200, "delivered by A")
            retried_a = service.retry_notifications(conn, self.mail.endpoint, gen_a)
            self.assertEqual(
                retried_a["retried"], [{"request_id": request_id, "delivery_status": "sent"}]
            )

            # Process B's sweep runs immediately after, over the same store.
            # The request already succeeded (schedule cleared), so B's sweep
            # finds nothing left to do -- it never contacts the provider.
            received_before = len(self.mail.received)
            retried_b = service.retry_notifications(conn, self.mail.endpoint, gen_b)
            self.assertEqual(retried_b["retried"], [])
            self.assertEqual(len(self.mail.received), received_before)

    def test_concurrent_claim_on_the_same_due_request_is_suppressed(self):
        """Lower-level check of the claim primitive itself: two racing
        claims on the same due, unclaimed request must not both succeed.
        """
        with self._conn() as conn:
            service.create_account(conn, "org1", "acct1", "a@example.test")
            self.mail.queue(503, "temporary failure")
            start = service.start_recovery(conn, self.mail.endpoint, "org1", "a@example.test", self.generation)
            request_id = start["request_id"]

            now_iso = _dt.datetime.now(_dt.timezone.utc).isoformat()
            stale_before_iso = (
                _dt.datetime.now(_dt.timezone.utc) - service.RETRY_CLAIM_TTL
            ).isoformat()

            claimed_a = storage.claim_due_retry(conn, request_id, "gen-a", now_iso, stale_before_iso)
            claimed_b = storage.claim_due_retry(conn, request_id, "gen-b", now_iso, stale_before_iso)
            conn.commit()

            self.assertTrue(claimed_a)
            self.assertFalse(claimed_b)

            row = storage.get_retry_schedule(conn, request_id)
            self.assertEqual(row["claimed_by"], "gen-a")

    def test_worker_status_reports_generation_and_pending_retry_count(self):
        with self._conn() as conn:
            service.create_account(conn, "org1", "acct1", "a@example.test")
            generation = worker.start_generation(conn)

            status_before = worker.get_worker_status(conn, generation)
            self.assertEqual(status_before["generation_id"], generation)
            self.assertIsNotNone(status_before["started_at"])
            self.assertEqual(status_before["pending_retries"], 0)
            self.assertEqual(status_before["due_retries"], 0)

            self.mail.queue(503, "temporary failure")
            service.start_recovery(conn, self.mail.endpoint, "org1", "a@example.test", generation)

            status_after = worker.get_worker_status(conn, generation)
            self.assertEqual(status_after["pending_retries"], 1)
            self.assertEqual(status_after["due_retries"], 1)


class ExpiryPruningAndAtomicAcknowledgementTests(ServiceTestCase):
    """Attempt limits and bounded backoff were established earlier (see
    BoundedRetrySchedulingTests). These cover the three newer guarantees:
    expired pending requests are pruned proactively rather than left to a
    possibly-distant scheduled retry; pruning never deletes notification
    attempt history; and resolving a checkpointed attempt (the provider's
    acknowledgement, live or discovered on restart) is atomic, so a duplicate
    acknowledgement can never overwrite an already-resolved outcome.
    """

    def test_bulk_sweep_prunes_a_pending_request_whose_token_has_already_expired(self):
        with self._conn() as conn:
            service.create_account(conn, "org1", "acct1", "a@example.test")
            self.mail.queue(503, "temporary failure")
            start = service.start_recovery(conn, self.mail.endpoint, "org1", "a@example.test", self.generation)
            self.assertEqual(start["delivery_status"], "failed")
            request_id = start["request_id"]

            # The request is due for retry (backoff after a single failure is
            # zero), but its token has already elapsed -- simulating a
            # schedule entry that outlived the TTL because nobody called the
            # retry sweep in the meantime.
            past = "2000-01-01T00:00:00+00:00"
            conn.execute(
                "UPDATE recovery_requests SET expires_at = ? WHERE id = ?", (past, request_id)
            )
            conn.commit()
            self.assertIsNotNone(storage.get_retry_schedule(conn, request_id))

            received_before = len(self.mail.received)
            swept = service.retry_notifications(conn, self.mail.endpoint, self.generation)
            # Pruned before being considered as a sweep candidate -- the
            # provider must never be contacted for an expired token.
            self.assertEqual(swept["retried"], [])
            self.assertEqual(len(self.mail.received), received_before)

            request_row = storage.get_recovery_request(conn, request_id)
            self.assertEqual(request_row["status"], "expired")
            self.assertIsNone(storage.get_retry_schedule(conn, request_id))

    def test_pruning_an_expired_request_never_deletes_its_failed_attempt_history(self):
        with self._conn() as conn:
            service.create_account(conn, "org1", "acct1", "a@example.test")
            self.mail.queue(503, "temporary failure")
            start = service.start_recovery(conn, self.mail.endpoint, "org1", "a@example.test", self.generation)
            request_id = start["request_id"]
            attempts_before = storage.list_notification_attempts(conn, request_id)
            self.assertEqual(len(attempts_before), 1)
            self.assertEqual(attempts_before[0]["outcome"], "failed")

            past = "2000-01-01T00:00:00+00:00"
            conn.execute(
                "UPDATE recovery_requests SET expires_at = ? WHERE id = ?", (past, request_id)
            )
            conn.commit()

            pruned = service.prune_expired_requests(conn)
            self.assertEqual(pruned["pruned_requests"], [request_id])

            # The failed attempt is still there, byte-for-byte -- pruning
            # only ever touches the request's status and its ephemeral
            # retry schedule.
            attempts_after = storage.list_notification_attempts(conn, request_id)
            self.assertEqual(attempts_after, attempts_before)

    def test_duplicate_provider_acknowledgement_does_not_overwrite_an_already_resolved_attempt(self):
        with self._conn() as conn:
            service.create_account(conn, "org1", "acct1", "a@example.test")
            crashed_generation = worker.start_generation(conn)
            request_id = crypto.generate_id("req")
            token = crypto.generate_token()
            now = _dt.datetime.now(_dt.timezone.utc)
            storage.insert_recovery_request(
                conn,
                id=request_id,
                organization_id="org1",
                account_id="acct1",
                email="a@example.test",
                token=token,
                token_hash=crypto.hash_token(token),
                created_at=now.isoformat(),
                expires_at=(now + _dt.timedelta(minutes=30)).isoformat(),
            )
            conn.commit()
            attempt_id = crypto.generate_id("ntf")
            storage.record_notification_attempt(
                conn, attempt_id, request_id, "acct1", 1,
                "a@example.test", "in_progress", None, None, now.isoformat(), crashed_generation,
            )
            conn.commit()

            # The first acknowledgement resolves the checkpoint...
            first = storage.finalize_notification_attempt(conn, attempt_id, "failed", "receipt-1", "loc-1")
            self.assertTrue(first)

            # ...and a duplicate acknowledgement for the very same attempt --
            # e.g. a retried provider callback, or a second worker generation
            # racing to recover the same stale checkpoint -- must be a no-op,
            # even though it reports a different (arbitrary) outcome.
            second = storage.finalize_notification_attempt(conn, attempt_id, "sent", "receipt-2", None)
            self.assertFalse(second)
            conn.commit()

            row = conn.execute(
                "SELECT * FROM notification_attempts WHERE id = ?", (attempt_id,)
            ).fetchone()
            self.assertEqual(row["outcome"], "failed")
            self.assertEqual(row["provider_receipt"], "receipt-1")
            self.assertEqual(row["retry_locator"], "loc-1")

    def test_stale_checkpoint_recovery_records_an_audit_event_without_a_token(self):
        with self._conn() as conn:
            service.create_account(conn, "org1", "acct1", "a@example.test")
            crashed_generation = worker.start_generation(conn)
            request_id = crypto.generate_id("req")
            token = crypto.generate_token()
            now = _dt.datetime.now(_dt.timezone.utc)
            storage.insert_recovery_request(
                conn,
                id=request_id,
                organization_id="org1",
                account_id="acct1",
                email="a@example.test",
                token=token,
                token_hash=crypto.hash_token(token),
                created_at=now.isoformat(),
                expires_at=(now + _dt.timedelta(minutes=30)).isoformat(),
            )
            conn.commit()
            storage.record_notification_attempt(
                conn, crypto.generate_id("ntf"), request_id, "acct1", 1,
                "a@example.test", "in_progress", None, None, now.isoformat(), crashed_generation,
            )
            conn.commit()

            new_generation = worker.start_generation(conn)
            worker.recover_unfinished_notifications(conn, new_generation)

            events = storage.list_audit_events(conn)
            recovered_events = [e for e in events if e["event_type"] == "stale_checkpoint_recovered"]
            self.assertEqual(len(recovered_events), 1)
            self.assertEqual(recovered_events[0]["request_id"], request_id)
            for event in events:
                event_dict = dict(event)
                self.assertNotIn("token", event_dict)
                for value in event_dict.values():
                    if isinstance(value, str):
                        self.assertNotIn(token, value)

    def test_audit_events_across_a_full_lifecycle_never_contain_the_recovery_token(self):
        with self._conn() as conn:
            service.create_account(conn, "org1", "acct1", "a@example.test")

            self.mail.queue(503, "provider unavailable")
            start = service.start_recovery(conn, self.mail.endpoint, "org1", "a@example.test", self.generation)
            request_id = start["request_id"]
            token = storage.get_recovery_request(conn, request_id)["token"]

            self.mail.queue(200, "delivered")
            service.retry_notifications(conn, self.mail.endpoint, self.generation, request_id)
            service.complete_recovery(conn, token)

            events = storage.list_audit_events(conn)
            event_types = {e["event_type"] for e in events}
            self.assertEqual(
                event_types,
                {"recovery_requested", "delivery_failed", "delivery_sent", "recovery_completed"},
            )
            for event in events:
                event_dict = dict(event)
                self.assertNotIn("token", event_dict)
                for value in event_dict.values():
                    if isinstance(value, str):
                        self.assertNotIn(token, value)


if __name__ == "__main__":
    unittest.main()
