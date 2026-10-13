"""Drives recovery start/completion through the real loopback HTTP service
(not direct service-layer calls) and checks the properties that must hold
regardless of transport: token binding, expiry, single use, and durable,
opaque notice persistence ahead of any retry queue activity.

Provider receipts and retry locators are intentionally never returned by any
HTTP response (README: recovery start "returns a request id and delivery
status, not the secret recovery token"; receipts stay opaque). Those
properties are therefore checked by reading the same SQLite file the server
writes to, not by asserting on API responses.
"""
from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

from accountsvc import db, httpapi, notice, security, service, store

from .fakemail import FakeMailServer

BEARER_TOKEN = "http-lifecycle-token"


class _HttpFixture:
    """A real RecoveryServer bound to loopback, plus a FakeMailServer."""

    def __init__(self, fail_times: int = 0, token_ttl_seconds: float = security.TOKEN_TTL_SECONDS):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(self.db_path)

        self.mail = FakeMailServer(fail_times=fail_times)
        self.server = httpapi.create_server(
            "127.0.0.1", 0, self.db_path, BEARER_TOKEN, self.mail.url, token_ttl_seconds
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address[:2]
        self.base_url = f"http://{host}:{port}"

    def seed_account(self, organization_id: str, account_id: str, email: str) -> None:
        conn = db.connect(self.db_path)
        try:
            service.create_account(conn, organization_id, account_id, email, now=1000.0)
        finally:
            conn.close()

    def request(self, method: str, path: str, body: dict | None = None, token: str | None = None):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Content-Type": "application/json"}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(self.base_url + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            try:
                return exc.code, json.loads(exc.read())
            finally:
                exc.close()

    def store_conn(self) -> sqlite3.Connection:
        return db.connect(self.db_path)

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.mail.stop()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        for ext in ("-wal", "-shm"):
            p = self.db_path + ext
            if os.path.exists(p):
                os.remove(p)


class RecoveryHttpLifecycleTests(unittest.TestCase):
    def test_start_binds_the_token_to_one_account_and_organization(self):
        fx = _HttpFixture()
        try:
            fx.seed_account("ORG_A", "acct-1", "alice@example.test")
            status, body = fx.request(
                "POST", "/recovery/start", {"organization": "ORG_A", "email": "alice@example.test"}
            )
            self.assertEqual(status, 200)
            self.assertEqual(body["status"], "sent")
            self.assertNotIn("token", body)

            conn = fx.store_conn()
            try:
                request_row = store.get_recovery_request(conn, body["request_id"])
            finally:
                conn.close()
            self.assertEqual(request_row["account_id"], "acct-1")
            self.assertEqual(request_row["organization_id"], "ORG_A")
        finally:
            fx.close()

    def test_opaque_receipt_is_persisted_but_never_returned_over_http(self):
        fx = _HttpFixture(fail_times=1)
        try:
            fx.seed_account("ORG_A", "acct-1", "alice@example.test")
            status, body = fx.request(
                "POST", "/recovery/start", {"organization": "ORG_A", "email": "alice@example.test"}
            )
            self.assertEqual(status, 200)
            self.assertEqual(body["status"], "queued_retry")
            # The opaque provider receipt must never surface through the API.
            self.assertNotIn("receipt", json.dumps(body))

            conn = fx.store_conn()
            try:
                attempts = store.find_retryable_attempts(conn, now=time.time(), limit=10)
            finally:
                conn.close()
            self.assertEqual(len(attempts), 1)
            attempt = attempts[0]
            self.assertEqual(attempt["provider_receipt"], "provider|attempt-1")
            self.assertEqual(attempt["account_id"], "acct-1")
            self.assertEqual(
                attempt["retry_locator"], notice.encode_retry_locator(attempt["provider_receipt"], "acct-1")
            )
        finally:
            fx.close()

    def test_failed_notice_and_trusted_account_are_durable_before_any_retry_call(self):
        fx = _HttpFixture(fail_times=1)
        try:
            fx.seed_account("ORG_A", "acct-1", "alice@example.test")
            status, body = fx.request(
                "POST", "/recovery/start", {"organization": "ORG_A", "email": "alice@example.test"}
            )
            self.assertEqual(status, 200)
            self.assertEqual(body["status"], "queued_retry")

            # Read back durable state before /recovery/notifications/retry is ever called.
            conn = fx.store_conn()
            try:
                attempts = store.find_retryable_attempts(conn, now=time.time(), limit=10)
            finally:
                conn.close()
            self.assertEqual(len(attempts), 1)
            self.assertEqual(attempts[0]["status"], "retry_pending")
            self.assertEqual(attempts[0]["account_id"], "acct-1")
            self.assertIsNotNone(attempts[0]["retry_locator"])
        finally:
            fx.close()

    def test_complete_recovery_over_http(self):
        fx = _HttpFixture()
        try:
            fx.seed_account("ORG_A", "acct-1", "alice@example.test")
            fx.request("POST", "/recovery/start", {"organization": "ORG_A", "email": "alice@example.test"})
            token = fx.mail.received[0]["recovery_token"]

            status, body = fx.request("POST", "/recovery/complete", {"token": token})
            self.assertEqual(status, 200)
            self.assertEqual(body["status"], "completed")
            self.assertEqual(body["account_id"], "acct-1")
            self.assertEqual(body["organization_id"], "ORG_A")
        finally:
            fx.close()

    def test_expired_token_is_rejected_over_http(self):
        fx = _HttpFixture(token_ttl_seconds=1)
        try:
            fx.seed_account("ORG_A", "acct-1", "alice@example.test")
            fx.request("POST", "/recovery/start", {"organization": "ORG_A", "email": "alice@example.test"})
            token = fx.mail.received[0]["recovery_token"]

            time.sleep(1.5)

            status, body = fx.request("POST", "/recovery/complete", {"token": token})
            self.assertEqual(status, 410)
            self.assertEqual(body["error"], "invalid_or_expired_token")
        finally:
            fx.close()

    def test_replaying_a_completed_token_is_rejected_over_http(self):
        fx = _HttpFixture()
        try:
            fx.seed_account("ORG_A", "acct-1", "alice@example.test")
            fx.request("POST", "/recovery/start", {"organization": "ORG_A", "email": "alice@example.test"})
            token = fx.mail.received[0]["recovery_token"]

            first_status, first_body = fx.request("POST", "/recovery/complete", {"token": token})
            self.assertEqual(first_status, 200)
            self.assertEqual(first_body["status"], "completed")

            replay_status, replay_body = fx.request("POST", "/recovery/complete", {"token": token})
            self.assertEqual(replay_status, 410)
            self.assertEqual(replay_body["error"], "invalid_or_expired_token")
        finally:
            fx.close()

    def test_retry_endpoint_delivers_the_durable_failed_notice(self):
        fx = _HttpFixture(fail_times=1)
        try:
            fx.seed_account("ORG_A", "acct-1", "alice@example.test")
            fx.request("POST", "/recovery/start", {"organization": "ORG_A", "email": "alice@example.test"})

            status, body = fx.request("POST", "/recovery/notifications/retry", {}, token=BEARER_TOKEN)
            self.assertEqual(status, 200)
            self.assertEqual(body["processed"], 1)
            self.assertEqual(body["results"][0]["outcome"], "sent")

            conn = fx.store_conn()
            try:
                attempts = store.find_retryable_attempts(conn, now=time.time(), limit=10)
            finally:
                conn.close()
            self.assertEqual(attempts, [])
        finally:
            fx.close()


if __name__ == "__main__":
    unittest.main()
