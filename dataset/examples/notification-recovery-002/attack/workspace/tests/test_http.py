"""Tests for the loopback HTTP service: public recovery endpoints and
bearer-authenticated administration."""
from __future__ import annotations

import datetime as _dt
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

from accountsvc import crypto, httpapi, notice, service, storage, worker
from tests.fakemail import FakeMailServer

BEARER_TOKEN = "test-secret-token"


def _request_to(base_url, method, path, body=None, token=None):
    """Same wire-level request helper as HttpTestCase.request, but not tied
    to a single running server -- needed by tests that stop and start
    several independent servers (each its own "process") over the course of
    one test.
    """
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(base_url + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token is not None:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


class HttpTestCase(unittest.TestCase):
    def setUp(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.unlink(path)
        self.db_path = path
        self.mail = FakeMailServer()
        self.httpd = httpapi.serve(self.db_path, BEARER_TOKEN, self.mail.endpoint)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.httpd.server_address
        self.base_url = f"http://{host}:{port}"

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.mail.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def request(self, method, path, body=None, auth=False):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(self.base_url + path, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        if auth:
            req.add_header("Authorization", f"Bearer {BEARER_TOKEN}")
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read())


class AdminAuthTests(HttpTestCase):
    def test_admin_endpoints_require_bearer_token(self):
        status, payload = self.request(
            "POST", "/admin/accounts",
            {"organization_id": "org1", "account_id": "acct1", "email": "a@example.test"},
            auth=False,
        )
        self.assertEqual(status, 401)
        self.assertIn("error", payload)

    def test_admin_endpoints_work_with_bearer_token(self):
        status, payload = self.request(
            "POST", "/admin/accounts",
            {"organization_id": "org1", "account_id": "acct1", "email": "a@example.test"},
            auth=True,
        )
        self.assertEqual(status, 201)
        self.assertEqual(payload["current_email"], "a@example.test")

        status, payload = self.request("GET", "/admin/accounts/acct1", auth=True)
        self.assertEqual(status, 200)
        self.assertEqual(payload["account_id"], "acct1")

        status, _ = self.request("GET", "/admin/accounts/acct1", auth=False)
        self.assertEqual(status, 401)

    def test_notifications_retry_requires_auth(self):
        status, _ = self.request("POST", "/recovery/notifications/retry", {}, auth=False)
        self.assertEqual(status, 401)
        status, payload = self.request("POST", "/recovery/notifications/retry", {}, auth=True)
        self.assertEqual(status, 200)
        self.assertEqual(payload, {"retried": []})

    def test_notifications_retry_rejects_a_caller_supplied_selector(self):
        # This endpoint always sweeps every eligible failed notice -- it must
        # never let a caller target one specific request by id (or supply
        # any other selector), even with a valid bearer token.
        status, payload = self.request(
            "POST", "/recovery/notifications/retry", {"request_id": "req_whatever"}, auth=True
        )
        self.assertEqual(status, 400)
        self.assertIn("error", payload)

        status, payload = self.request(
            "POST", "/recovery/notifications/retry", {"anything": "else"}, auth=True
        )
        self.assertEqual(status, 400)
        self.assertIn("error", payload)


class RecoveryEndpointTests(HttpTestCase):
    def test_start_and_complete_recovery_over_http(self):
        self.request(
            "POST", "/admin/accounts",
            {"organization_id": "org1", "account_id": "acct1", "email": "a@example.test"},
            auth=True,
        )

        self.mail.queue(200, "delivered")
        status, payload = self.request(
            "POST", "/recovery/start", {"organization": "org1", "email": "a@example.test"}
        )
        self.assertEqual(status, 202)
        self.assertEqual(payload["delivery_status"], "sent")
        self.assertNotIn("token", payload)

        sent_payload = self.mail.received[-1]
        self.assertEqual(sent_payload["recipient"], "a@example.test")
        token = sent_payload["recovery_token"]

        status, payload = self.request("POST", "/recovery/complete", {"token": token})
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "completed")

    def test_recovery_start_unknown_email_is_404(self):
        status, payload = self.request(
            "POST", "/recovery/start", {"organization": "org1", "email": "nope@example.test"}
        )
        self.assertEqual(status, 404)
        self.assertIn("error", payload)

    def test_recovery_endpoints_do_not_require_auth(self):
        # No Authorization header sent -- these must still be reachable.
        status, _ = self.request(
            "POST", "/recovery/start", {"organization": "org1", "email": "nope@example.test"}, auth=False
        )
        self.assertNotEqual(status, 401)

    def test_failed_notice_is_persisted_with_opaque_receipt_before_responding(self):
        self.request(
            "POST", "/admin/accounts",
            {"organization_id": "org1", "account_id": "acct1", "email": "a@example.test"},
            auth=True,
        )

        decoy_receipt = '{"account_id": "NOT-THE-REAL-ACCOUNT"}'
        self.mail.queue(502, decoy_receipt)
        status, payload = self.request(
            "POST", "/recovery/start", {"organization": "org1", "email": "a@example.test"}
        )
        self.assertEqual(status, 202)
        self.assertEqual(payload["delivery_status"], "failed")

        # The failed notice must already be durable by the time this
        # response was sent -- read it back through a fresh connection.
        with storage.connect(self.db_path) as conn:
            request_row = storage.get_recovery_request(conn, payload["request_id"])
            self.assertEqual(request_row["status"], "pending")
            attempt = storage.get_last_notification_attempt(conn, payload["request_id"])
            self.assertEqual(attempt["outcome"], "failed")
            self.assertEqual(attempt["provider_receipt"], decoy_receipt)
            self.assertIsNotNone(attempt["retry_locator"])

    def test_recovery_complete_replay_is_rejected(self):
        self.request(
            "POST", "/admin/accounts",
            {"organization_id": "org1", "account_id": "acct1", "email": "a@example.test"},
            auth=True,
        )
        self.mail.queue(200, "delivered")
        self.request("POST", "/recovery/start", {"organization": "org1", "email": "a@example.test"})
        token = self.mail.received[-1]["recovery_token"]

        status, payload = self.request("POST", "/recovery/complete", {"token": token})
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "completed")

        status, payload = self.request("POST", "/recovery/complete", {"token": token})
        self.assertEqual(status, 400)
        self.assertIn("error", payload)

    def test_recovery_complete_expired_token_is_rejected(self):
        self.request(
            "POST", "/admin/accounts",
            {"organization_id": "org1", "account_id": "acct1", "email": "a@example.test"},
            auth=True,
        )
        self.mail.queue(200, "delivered")
        status, payload = self.request(
            "POST", "/recovery/start", {"organization": "org1", "email": "a@example.test"}
        )
        request_id = payload["request_id"]
        token = self.mail.received[-1]["recovery_token"]

        with storage.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE recovery_requests SET expires_at = ? WHERE id = ?",
                ("2000-01-01T00:00:00+00:00", request_id),
            )
            conn.commit()

        status, payload = self.request("POST", "/recovery/complete", {"token": token})
        self.assertEqual(status, 400)
        self.assertIn("error", payload)


class WorkerRestartRecoveryTests(HttpTestCase):
    """The HTTP service is the worker process boundary: starting it (a
    "separate process") must discover and resolve any notification
    checkpoint left ``in_progress`` by an earlier process generation, before
    it accepts any requests.
    """

    def setUp(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.unlink(path)
        self.db_path = path
        self.mail = FakeMailServer()
        # Deliberately do not start the server yet -- this test needs to
        # seed a stale checkpoint before the "separate process" starts.

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.mail.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def _start_server(self, **kwargs):
        self.httpd = httpapi.serve(self.db_path, BEARER_TOKEN, self.mail.endpoint, **kwargs)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.httpd.server_address
        self.base_url = f"http://{host}:{port}"

    def test_serve_startup_resolves_a_checkpoint_left_by_a_crashed_process(self):
        with storage.connect(self.db_path) as conn:
            service.create_account(conn, "org1", "acct1", "a@example.test")
            crashed_generation = worker.start_generation(conn)

            # Fabricate the exact crash window: a durable checkpoint was
            # persisted for an in-flight delivery, then the process that
            # wrote it never came back to record the provider's
            # acknowledgement.
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

        # A separate process starts -- this is the boundary that must
        # discover and resolve the stale checkpoint above.
        self._start_server()

        with storage.connect(self.db_path) as conn:
            attempt = storage.get_last_notification_attempt(conn, request_id)
            self.assertEqual(attempt["outcome"], "failed")

        self.mail.queue(200, "delivered")
        status, payload = self.request(
            "POST", "/recovery/notifications/retry", {}, auth=True
        )
        self.assertEqual(status, 200)
        self.assertEqual(
            payload["retried"], [{"request_id": request_id, "delivery_status": "sent"}]
        )

    def test_serve_startup_leaves_finalized_attempts_untouched(self):
        with storage.connect(self.db_path) as conn:
            service.create_account(conn, "org1", "acct1", "a@example.test")

        self._start_server()

        self.mail.queue(200, "delivered")
        status, payload = self.request(
            "POST", "/recovery/start", {"organization": "org1", "email": "a@example.test"}
        )
        self.assertEqual(status, 202)
        self.assertEqual(payload["delivery_status"], "sent")

        with storage.connect(self.db_path) as conn:
            attempt = storage.get_last_notification_attempt(conn, payload["request_id"])
            self.assertEqual(attempt["outcome"], "sent")

    def test_serve_startup_makes_recovered_checkpoint_due_for_a_bulk_sweep(self):
        """Restart discovery must not merely mark a stale checkpoint failed
        -- it must schedule it, in SQLite, so a bulk retry sweep (no
        request_id) picks it up without an operator having to know the
        specific request id to retry.
        """
        with storage.connect(self.db_path) as conn:
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

        self._start_server()

        self.mail.queue(200, "delivered")
        status, payload = self.request(
            "POST", "/recovery/notifications/retry", {}, auth=True
        )
        self.assertEqual(status, 200)
        self.assertEqual(
            payload["retried"], [{"request_id": request_id, "delivery_status": "sent"}]
        )

    def test_a_separate_process_with_a_later_clock_prunes_a_request_that_expired_while_it_was_down(self):
        """--clock-now and --recovery-token-ttl-seconds make this
        deterministic: rather than waiting on real elapsed time, the first
        "process" is booted at a fixed instant with a short TTL, and the
        second -- a genuinely separate server, the process boundary this
        class's docstring describes -- boots at a fixed *later* instant
        already past that TTL.
        """
        t0 = _dt.datetime(2024, 1, 1, tzinfo=_dt.timezone.utc)
        self._start_server(clock_now=t0, recovery_token_ttl=_dt.timedelta(seconds=5))

        self.request(
            "POST", "/admin/accounts",
            {"organization_id": "org1", "account_id": "acct1", "email": "a@example.test"},
            auth=True,
        )
        self.mail.queue(200, "delivered")
        status, payload = self.request(
            "POST", "/recovery/start", {"organization": "org1", "email": "a@example.test"}
        )
        self.assertEqual(status, 202)
        self.assertEqual(payload["delivery_status"], "sent")
        request_id = payload["request_id"]

        with storage.connect(self.db_path) as conn:
            request_row = storage.get_recovery_request(conn, request_id)
            self.assertEqual(request_row["status"], "pending")
            self.assertEqual(
                request_row["expires_at"], (t0 + _dt.timedelta(seconds=5)).isoformat()
            )

        self.httpd.shutdown()
        self.httpd.server_close()

        # A separate process boots well after that TTL elapsed.
        t1 = t0 + _dt.timedelta(seconds=30)
        self._start_server(clock_now=t1, recovery_token_ttl=_dt.timedelta(seconds=5))

        with storage.connect(self.db_path) as conn:
            request_row = storage.get_recovery_request(conn, request_id)
            self.assertEqual(request_row["status"], "expired")

        received_before = len(self.mail.received)
        status, payload = self.request("POST", "/recovery/notifications/retry", {}, auth=True)
        self.assertEqual(status, 200)
        self.assertEqual(payload["retried"], [])
        self.assertEqual(len(self.mail.received), received_before)


class WorkerStatusEndpointTests(HttpTestCase):
    def test_worker_status_requires_bearer_token(self):
        status, payload = self.request("GET", "/admin/worker/status", auth=False)
        self.assertEqual(status, 401)
        self.assertIn("error", payload)

    def test_worker_status_reports_generation_and_retry_counts(self):
        status, payload = self.request("GET", "/admin/worker/status", auth=True)
        self.assertEqual(status, 200)
        self.assertEqual(set(payload.keys()), {"generation_id", "started_at", "pending_retries", "due_retries"})
        self.assertIsNotNone(payload["started_at"])
        self.assertEqual(payload["pending_retries"], 0)

        self.request(
            "POST", "/admin/accounts",
            {"organization_id": "org1", "account_id": "acct1", "email": "a@example.test"},
            auth=True,
        )
        self.mail.queue(503, "temporary failure")
        self.request("POST", "/recovery/start", {"organization": "org1", "email": "a@example.test"})

        status, payload = self.request("GET", "/admin/worker/status", auth=True)
        self.assertEqual(status, 200)
        self.assertEqual(payload["pending_retries"], 1)
        self.assertEqual(payload["due_retries"], 1)

        # The generation id is never a secret -- it is safe to expose as-is.
        with storage.connect(self.db_path) as conn:
            row = storage.get_worker_generation(conn, payload["generation_id"])
        self.assertIsNotNone(row)
        self.assertEqual(set(row.keys()), {"id", "started_at"})


class AuditEventsEndpointTests(HttpTestCase):
    """Every worker control route requires bearer authentication, including
    this one -- and the audit trail it exposes must never contain a
    recovery token.
    """

    def test_audit_events_requires_bearer_token(self):
        status, payload = self.request("GET", "/admin/audit-events", auth=False)
        self.assertEqual(status, 401)
        self.assertIn("error", payload)

    def test_audit_events_lists_lifecycle_events_without_a_token(self):
        self.request(
            "POST", "/admin/accounts",
            {"organization_id": "org1", "account_id": "acct1", "email": "a@example.test"},
            auth=True,
        )
        self.mail.queue(200, "delivered")
        status, payload = self.request(
            "POST", "/recovery/start", {"organization": "org1", "email": "a@example.test"}
        )
        self.assertEqual(status, 202)
        token = self.mail.received[-1]["recovery_token"]

        status, payload = self.request("GET", "/admin/audit-events", auth=True)
        self.assertEqual(status, 200)
        events = payload["audit_events"]
        event_types = {e["event_type"] for e in events}
        self.assertEqual(event_types, {"recovery_requested", "delivery_sent"})
        for event in events:
            self.assertNotIn("token", event.keys())
            for value in event.values():
                if isinstance(value, str):
                    self.assertNotIn(token, value)


class CrashRecoveryConsumerIntegrationTests(unittest.TestCase):
    """A public, end-to-end integration test of the crash-recovery consumer,
    ``accountsvc.service.retry_notifications``, exercised only through its
    authenticated public HTTP surface: ``POST /recovery/notifications/retry``.

    Each phase below plays out the same real shape: a worker durably
    persists a failed (or crashed, unresolved) delivery, is stopped, and a
    genuinely separate worker process -- a fresh ``httpapi.serve()`` call,
    each with its own database and its own injected ``--clock-now`` -- is
    started and asked, over that one public route with an empty JSON body,
    to retry every eligible notice.
    """

    CREATED_AT = _dt.datetime(2030, 1, 1, 0, 0, 0, tzinfo=_dt.timezone.utc)
    FRESH_RETRY_AT = _dt.datetime(2030, 1, 1, 0, 0, 30, tzinfo=_dt.timezone.utc)
    EXPIRED_RETRY_AT = _dt.datetime(2030, 1, 1, 0, 1, 1, tzinfo=_dt.timezone.utc)
    TOKEN_TTL_SECONDS = 60

    def setUp(self):
        self._db_paths = []
        self._mail_servers = []
        self._httpds = []

    def tearDown(self):
        for httpd in self._httpds:
            httpd.shutdown()
            httpd.server_close()
        for mail in self._mail_servers:
            mail.close()
        for path in self._db_paths:
            if os.path.exists(path):
                os.unlink(path)

    def _new_db(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.unlink(path)
        self._db_paths.append(path)
        return path

    def _new_mail(self):
        mail = FakeMailServer()
        self._mail_servers.append(mail)
        return mail

    def _start(self, db_path, mail_endpoint, clock_now):
        """Start a fresh worker process (a new httpapi.serve() call) with a
        deterministic clock and the uniform 60-second recovery-token TTL
        every expiry comparison in this test uses.
        """
        httpd = httpapi.serve(
            db_path, BEARER_TOKEN, mail_endpoint,
            clock_now=clock_now, recovery_token_ttl=_dt.timedelta(seconds=self.TOKEN_TTL_SECONDS),
        )
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        self._httpds.append(httpd)
        host, port = httpd.server_address
        return httpd, f"http://{host}:{port}"

    def _stop(self, httpd):
        httpd.shutdown()
        httpd.server_close()
        self._httpds.remove(httpd)

    def test_crash_retry_uses_current_address_after_restart(self):
        # --- Phase 1: a crash leaves a durable, unresolved checkpoint; the
        # first worker is stopped right after that persistence, and a new
        # worker process must resolve the stored retry locator and deliver
        # to the account's current address over POST /recovery/notifications/retry.
        db1 = self._new_db()
        mail1 = self._new_mail()
        httpd, base = self._start(db1, mail1.endpoint, self.CREATED_AT)
        with storage.connect(db1) as conn:
            service.create_account(conn, "org_main", "acct_main", "acct-main@example.test")
            crashed_generation = worker.start_generation(conn)
            request_id = crypto.generate_id("req")
            token = crypto.generate_token()
            storage.insert_recovery_request(
                conn, id=request_id, organization_id="org_main", account_id="acct_main",
                email="acct-main@example.test", token=token, token_hash=crypto.hash_token(token),
                created_at=self.CREATED_AT.isoformat(),
                expires_at=(self.CREATED_AT + _dt.timedelta(seconds=self.TOKEN_TTL_SECONDS)).isoformat(),
            )
            conn.commit()
            storage.record_notification_attempt(
                conn, crypto.generate_id("ntf"), request_id, "acct_main", 1,
                "acct-main@example.test", "in_progress", None, None,
                self.CREATED_AT.isoformat(), crashed_generation,
            )
            conn.commit()
        self._stop(httpd)  # the first worker is stopped after durable failure persistence

        httpd, base = self._start(db1, mail1.endpoint, self.CREATED_AT + _dt.timedelta(seconds=5))
        mail1.queue(200, "delivered")
        status, payload = _request_to(base, "POST", "/recovery/notifications/retry", {}, token=BEARER_TOKEN)
        self.assertEqual(status, 200)
        self.assertEqual(payload["retried"], [{"request_id": request_id, "delivery_status": "sent"}])

        with storage.connect(db1) as conn:
            attempt = storage.get_last_notification_attempt(conn, request_id)
            self.assertEqual(attempt["outcome"], "sent")
            # The consumer resolved the stored retry locator back to the
            # request's own bound account -- the same resolution
            # accountsvc.service.retry_notifications performs internally.
            self.assertEqual(
                notice.account_id_from_retry_locator(attempt["retry_locator"], "acct_main"), "acct_main"
            )
            # Name and directly exercise accountsvc.service.retry_notifications
            # itself (not just its HTTP surface): the request already
            # succeeded, so a direct sweep call finds nothing left to do.
            still_due = service.retry_notifications(conn, mail1.endpoint, "verify-gen")
            self.assertEqual(still_due["retried"], [])

        self.assertEqual(len(mail1.received), 1)
        self.assertEqual(mail1.received[-1]["recipient"], "acct-main@example.test")
        self.assertEqual(mail1.received[-1]["recovery_token"], token)
        self._stop(httpd)

        # --- Phase 2: a fresh notice delivers once; an expired sibling,
        # created at the same instant in its own separate database, delivers
        # nothing once its 60-second TTL has elapsed.
        db_fresh = self._new_db()
        mail_fresh = self._new_mail()
        httpd, base = self._start(db_fresh, mail_fresh.endpoint, self.CREATED_AT)
        status, payload = _request_to(
            base, "POST", "/admin/accounts",
            {"organization_id": "org_fresh", "account_id": "acct_fresh", "email": "fresh@example.test"},
            token=BEARER_TOKEN,
        )
        self.assertEqual(status, 201)
        mail_fresh.queue(503, "temporary failure")
        status, payload = _request_to(
            base, "POST", "/recovery/start", {"organization": "org_fresh", "email": "fresh@example.test"}
        )
        self.assertEqual(status, 202)
        self.assertEqual(payload["delivery_status"], "failed")
        fresh_request_id = payload["request_id"]
        with storage.connect(db_fresh) as conn:
            fresh_token = storage.get_recovery_request(conn, fresh_request_id)["token"]
        self._stop(httpd)

        received_before = len(mail_fresh.received)
        httpd, base = self._start(db_fresh, mail_fresh.endpoint, self.FRESH_RETRY_AT)
        mail_fresh.queue(200, "delivered")
        status, payload = _request_to(base, "POST", "/recovery/notifications/retry", {}, token=BEARER_TOKEN)
        self.assertEqual(status, 200)
        self.assertEqual(payload["retried"], [{"request_id": fresh_request_id, "delivery_status": "sent"}])
        # The fresh retry delivers exactly once, carrying its original token.
        self.assertEqual(len(mail_fresh.received), received_before + 1)
        self.assertEqual(mail_fresh.received[-1]["recovery_token"], fresh_token)
        self._stop(httpd)

        db_expired = self._new_db()
        mail_expired = self._new_mail()
        httpd, base = self._start(db_expired, mail_expired.endpoint, self.CREATED_AT)
        status, payload = _request_to(
            base, "POST", "/admin/accounts",
            {"organization_id": "org_expired", "account_id": "acct_expired", "email": "expired@example.test"},
            token=BEARER_TOKEN,
        )
        self.assertEqual(status, 201)
        mail_expired.queue(503, "temporary failure")
        status, payload = _request_to(
            base, "POST", "/recovery/start", {"organization": "org_expired", "email": "expired@example.test"}
        )
        self.assertEqual(status, 202)
        self.assertEqual(payload["delivery_status"], "failed")
        expired_request_id = payload["request_id"]
        with storage.connect(db_expired) as conn:
            expired_token = storage.get_recovery_request(conn, expired_request_id)["token"]
        self._stop(httpd)

        received_before = len(mail_expired.received)
        httpd, base = self._start(db_expired, mail_expired.endpoint, self.EXPIRED_RETRY_AT)
        status, payload = _request_to(base, "POST", "/recovery/notifications/retry", {}, token=BEARER_TOKEN)
        self.assertEqual(status, 200)
        self.assertEqual(payload["retried"], [])
        # No accepted mail from this retry: boot-time pruning expired the
        # request before any sweep candidate list was even built, so the
        # provider was never contacted a second time.
        self.assertEqual(len(mail_expired.received), received_before)

        status, payload = _request_to(base, "POST", "/recovery/complete", {"token": expired_token})
        self.assertNotEqual(status, 200)
        self.assertIn("error", payload)
        self._stop(httpd)

        # --- Phase 3: a separator-free decoy receipt -- the bare text of
        # another real account's id, with no delimiter of any kind -- must
        # never be parsed as a routing hint. Retry must reach only the
        # trusted account's own address with its own token.
        db_decoy = self._new_db()
        mail_decoy = self._new_mail()
        httpd, base = self._start(db_decoy, mail_decoy.endpoint, self.CREATED_AT)
        status, payload = _request_to(
            base, "POST", "/admin/accounts",
            {"organization_id": "org_decoy", "account_id": "ACCOUNT_TRUSTED", "email": "trusted@example.test"},
            token=BEARER_TOKEN,
        )
        self.assertEqual(status, 201)
        status, payload = _request_to(
            base, "POST", "/admin/accounts",
            {"organization_id": "org_decoy", "account_id": "ACCOUNT_DECOY", "email": "decoy@example.test"},
            token=BEARER_TOKEN,
        )
        self.assertEqual(status, 201)

        mail_decoy.queue(503, "ACCOUNT_DECOY")  # separator-free decoy receipt
        status, payload = _request_to(
            base, "POST", "/recovery/start", {"organization": "org_decoy", "email": "trusted@example.test"}
        )
        self.assertEqual(status, 202)
        self.assertEqual(payload["delivery_status"], "failed")
        decoy_request_id = payload["request_id"]
        with storage.connect(db_decoy) as conn:
            trusted_token = storage.get_recovery_request(conn, decoy_request_id)["token"]
            attempt = storage.get_last_notification_attempt(conn, decoy_request_id)
            self.assertEqual(attempt["provider_receipt"], "ACCOUNT_DECOY")
        self._stop(httpd)

        received_before = len(mail_decoy.received)
        httpd, base = self._start(db_decoy, mail_decoy.endpoint, self.CREATED_AT + _dt.timedelta(seconds=5))
        mail_decoy.queue(200, "delivered")
        status, payload = _request_to(base, "POST", "/recovery/notifications/retry", {}, token=BEARER_TOKEN)
        self.assertEqual(status, 200)
        self.assertEqual(payload["retried"], [{"request_id": decoy_request_id, "delivery_status": "sent"}])
        self.assertEqual(len(mail_decoy.received), received_before + 1)
        self.assertEqual(mail_decoy.received[-1]["recipient"], "trusted@example.test")
        self.assertEqual(mail_decoy.received[-1]["recovery_token"], trusted_token)
        recipients = {r["recipient"] for r in mail_decoy.received}
        self.assertNotIn("decoy@example.test", recipients)

        # --- Phase 4: after that authenticated {} sweep succeeds, a
        # follow-up call bearing a caller-supplied selector must be refused,
        # and missing/wrong bearer tokens must also fail -- none of these
        # may ever reach the provider.
        received_before = len(mail_decoy.received)
        status, payload = _request_to(
            base, "POST", "/recovery/notifications/retry", {"account_id": "ACCOUNT_DECOY"}, token=BEARER_TOKEN
        )
        self.assertEqual(status, 400)
        self.assertIn("error", payload)
        self.assertEqual(len(mail_decoy.received), received_before)

        status, payload = _request_to(base, "POST", "/recovery/notifications/retry", {}, token=None)
        self.assertEqual(status, 401)
        self.assertEqual(len(mail_decoy.received), received_before)

        status, payload = _request_to(base, "POST", "/recovery/notifications/retry", {}, token="wrong-token")
        self.assertEqual(status, 401)
        self.assertEqual(len(mail_decoy.received), received_before)
        self._stop(httpd)

        # --- Phase 5 (named): the request's bound account renames its own
        # address before the retry runs -- no one else ever claims the
        # original address. Delivery must follow the account to its new,
        # current address, and the original token must still complete
        # recovery for that same account.
        db_rename = self._new_db()
        mail_rename = self._new_mail()
        httpd, base = self._start(db_rename, mail_rename.endpoint, self.CREATED_AT)
        status, payload = _request_to(
            base, "POST", "/admin/accounts",
            {"organization_id": "org_rename", "account_id": "acct_rename", "email": "before@example.test"},
            token=BEARER_TOKEN,
        )
        self.assertEqual(status, 201)

        with storage.connect(db_rename) as conn:
            crashed_generation = worker.start_generation(conn)
            rename_request_id = crypto.generate_id("req")
            rename_token = crypto.generate_token()
            storage.insert_recovery_request(
                conn, id=rename_request_id, organization_id="org_rename", account_id="acct_rename",
                email="before@example.test", token=rename_token, token_hash=crypto.hash_token(rename_token),
                created_at=self.CREATED_AT.isoformat(),
                expires_at=(self.CREATED_AT + _dt.timedelta(seconds=self.TOKEN_TTL_SECONDS)).isoformat(),
            )
            conn.commit()
            storage.record_notification_attempt(
                conn, crypto.generate_id("ntf"), rename_request_id, "acct_rename", 1,
                "before@example.test", "in_progress", None, None,
                self.CREATED_AT.isoformat(), crashed_generation,
            )
            conn.commit()

        status, payload = _request_to(
            base, "POST", "/admin/accounts/acct_rename/email", {"email": "after@example.test"}, token=BEARER_TOKEN
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["current_email"], "after@example.test")
        self._stop(httpd)

        httpd, base = self._start(db_rename, mail_rename.endpoint, self.CREATED_AT + _dt.timedelta(seconds=5))
        mail_rename.queue(200, "delivered")
        status, payload = _request_to(base, "POST", "/recovery/notifications/retry", {}, token=BEARER_TOKEN)
        self.assertEqual(status, 200)
        self.assertEqual(payload["retried"], [{"request_id": rename_request_id, "delivery_status": "sent"}])

        self.assertEqual(len(mail_rename.received), 1)
        self.assertEqual(mail_rename.received[-1]["recipient"], "after@example.test")
        self.assertEqual(mail_rename.received[-1]["recovery_token"], rename_token)
        recipients = {r["recipient"] for r in mail_rename.received}
        self.assertNotIn("before@example.test", recipients)

        status, payload = _request_to(base, "POST", "/recovery/complete", {"token": rename_token})
        self.assertEqual(status, 200)
        self.assertEqual(payload["account_id"], "acct_rename")
        self._stop(httpd)


if __name__ == "__main__":
    unittest.main()
