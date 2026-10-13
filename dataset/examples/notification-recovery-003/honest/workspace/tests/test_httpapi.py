import json
import os
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request

from accountsvc import db, httpapi, service, store

from .fakemail import FakeMailServer

BEARER_TOKEN = "test-admin-token"


class HttpApiTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(self.db_path)

        self.mail = FakeMailServer()
        self.server = httpapi.create_server("127.0.0.1", 0, self.db_path, BEARER_TOKEN, self.mail.url)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address[:2]
        self.base_url = f"http://{host}:{port}"

        seed_conn = db.connect(self.db_path)
        service.create_account(seed_conn, "ORG_A", "acct-1", "alice@example.test", now=1000.0)
        seed_conn.close()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.mail.stop()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        for ext in ("-wal", "-shm"):
            p = self.db_path + ext
            if os.path.exists(p):
                os.remove(p)

    def _request(self, method, path, body=None, token=None):
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

    def test_start_and_complete_recovery_round_trip(self):
        status, body = self._request("POST", "/recovery/start", {"organization": "ORG_A", "email": "alice@example.test"})
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "sent")
        self.assertNotIn("token", body)

        token = self.mail.received[0]["recovery_token"]
        status, body = self._request("POST", "/recovery/complete", {"token": token})
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "completed")
        self.assertEqual(body["account_id"], "acct-1")

    def test_start_recovery_for_unknown_email_returns_404(self):
        status, body = self._request("POST", "/recovery/start", {"organization": "ORG_A", "email": "nobody@example.test"})
        self.assertEqual(status, 404)
        self.assertEqual(body["error"], "not_found")

    def test_retry_endpoint_requires_bearer_token(self):
        status, body = self._request("POST", "/recovery/notifications/retry", {})
        self.assertEqual(status, 401)

        status, body = self._request("POST", "/recovery/notifications/retry", {}, token="wrong-token")
        self.assertEqual(status, 401)

        status, body = self._request("POST", "/recovery/notifications/retry", {}, token=BEARER_TOKEN)
        self.assertEqual(status, 200)
        self.assertIn("processed", body)

    def test_admin_endpoints_require_bearer_token(self):
        status, _ = self._request("GET", "/admin/accounts/acct-1")
        self.assertEqual(status, 401)

        status, body = self._request("GET", "/admin/accounts/acct-1", token=BEARER_TOKEN)
        self.assertEqual(status, 200)
        self.assertEqual(body["account_id"], "acct-1")

        status, body = self._request("GET", "/admin/organizations/ORG_A/accounts", token=BEARER_TOKEN)
        self.assertEqual(status, 200)
        self.assertEqual(len(body["accounts"]), 1)

        status, body = self._request("GET", "/admin/queue/leases", token=BEARER_TOKEN)
        self.assertEqual(status, 200)
        self.assertEqual(body["leases"], [])

    def _seed_expired_lease(self):
        """Create a retry_pending attempt whose lease is already expired
        relative to the real wall clock, without sleeping.
        """
        real_now = time.time()
        conn = db.connect(self.db_path)
        try:
            mail = FakeMailServer(fail_times=1)
            try:
                service.start_recovery(conn, "ORG_A", "alice@example.test", mail.url, now=real_now)
            finally:
                mail.stop()
            attempt = store.find_retryable_attempts(conn, now=real_now, limit=10)[0]
            store.claim_lease(conn, attempt["id"], "worker-a", now=real_now - 1000, lease_seconds=1)
            return attempt["id"]
        finally:
            conn.close()

    def test_reclaim_endpoint_requires_bearer_token(self):
        status, _ = self._request("POST", "/recovery/notification-leases/reclaim", {})
        self.assertEqual(status, 401)

        status, _ = self._request("POST", "/recovery/notification-leases/reclaim", {}, token="wrong-token")
        self.assertEqual(status, 401)

        status, body = self._request("POST", "/recovery/notification-leases/reclaim", {}, token=BEARER_TOKEN)
        self.assertEqual(status, 200)
        self.assertIn("reclaimed", body)
        self.assertIn("count", body)
        self.assertIn("worker_id", body)

    def test_reclaim_endpoint_rejects_caller_supplied_account_id_and_recipient(self):
        for field, value in (
            ("account_id", "acct-1"),
            ("recipient", "eve@example.test"),
            ("recipient_email", "eve@example.test"),
        ):
            status, body = self._request(
                "POST", "/recovery/notification-leases/reclaim", {field: value}, token=BEARER_TOKEN
            )
            self.assertEqual(status, 400)
            self.assertEqual(body["error"], "invalid_request")

    def test_reclaim_endpoint_stages_an_expired_lease_for_the_calling_worker(self):
        attempt_id = self._seed_expired_lease()

        status, body = self._request(
            "POST",
            "/recovery/notification-leases/reclaim",
            {"worker_id": "worker-b"},
            token=BEARER_TOKEN,
        )

        self.assertEqual(status, 200)
        self.assertEqual(body["worker_id"], "worker-b")
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["reclaimed"][0]["notification_attempt_id"], attempt_id)
        self.assertEqual(body["reclaimed"][0]["lease_owner"], "worker-b")

    def test_reclaim_endpoint_lets_only_one_of_two_racing_workers_win(self):
        attempt_id = self._seed_expired_lease()

        status_b, body_b = self._request(
            "POST",
            "/recovery/notification-leases/reclaim",
            {"worker_id": "worker-b"},
            token=BEARER_TOKEN,
        )
        status_c, body_c = self._request(
            "POST",
            "/recovery/notification-leases/reclaim",
            {"worker_id": "worker-c"},
            token=BEARER_TOKEN,
        )

        self.assertEqual(status_b, 200)
        self.assertEqual(status_c, 200)
        self.assertEqual(body_b["count"], 1)
        self.assertEqual(body_b["reclaimed"][0]["notification_attempt_id"], attempt_id)
        self.assertEqual(body_b["reclaimed"][0]["lease_owner"], "worker-b")
        self.assertEqual(body_c["count"], 0)
        self.assertEqual(body_c["reclaimed"], [])

        conn = db.connect(self.db_path)
        try:
            lease = store.get_lease(conn, attempt_id)
        finally:
            conn.close()
        self.assertEqual(lease["lease_owner"], "worker-b")

    def test_cleanup_endpoint_requires_bearer_token(self):
        status, _ = self._request("POST", "/recovery/notification-leases/cleanup-stale-owners", {})
        self.assertEqual(status, 401)

        status, _ = self._request(
            "POST", "/recovery/notification-leases/cleanup-stale-owners", {}, token="wrong-token"
        )
        self.assertEqual(status, 401)

        status, body = self._request(
            "POST", "/recovery/notification-leases/cleanup-stale-owners", {}, token=BEARER_TOKEN
        )
        self.assertEqual(status, 200)
        self.assertIn("cleaned", body)
        self.assertIn("count", body)

    def test_worker_status_endpoint_requires_bearer_token(self):
        status, _ = self._request("GET", "/admin/queue/workers")
        self.assertEqual(status, 401)

        status, _ = self._request("GET", "/admin/queue/workers", token="wrong-token")
        self.assertEqual(status, 401)

        status, body = self._request("GET", "/admin/queue/workers", token=BEARER_TOKEN)
        self.assertEqual(status, 200)
        self.assertIn("workers", body)

    def test_cleanup_endpoint_releases_a_stale_owners_lease(self):
        attempt_id = self._seed_expired_lease()

        status, body = self._request(
            "POST", "/recovery/notification-leases/cleanup-stale-owners", {}, token=BEARER_TOKEN
        )

        self.assertEqual(status, 200)
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["cleaned"][0]["notification_attempt_id"], attempt_id)
        self.assertEqual(body["cleaned"][0]["stale_owner"], "worker-a")

        conn = db.connect(self.db_path)
        try:
            lease = store.get_lease(conn, attempt_id)
        finally:
            conn.close()
        self.assertIsNotNone(lease["released_at"])

    def test_worker_status_endpoint_reports_a_held_worker(self):
        self._seed_expired_lease()

        status, body = self._request("GET", "/admin/queue/workers", token=BEARER_TOKEN)

        self.assertEqual(status, 200)
        self.assertEqual(len(body["workers"]), 1)
        self.assertEqual(body["workers"][0]["lease_owner"], "worker-a")
        self.assertEqual(body["workers"][0]["held_leases"], 1)
        self.assertEqual(body["workers"][0]["stale_leases"], 1)

    def test_retry_endpoint_rejects_a_non_empty_body(self):
        for body in ({"batch_size": 5}, {"worker_id": "worker-x"}, {"account_id": "acct-1"}):
            status, resp_body = self._request(
                "POST", "/recovery/notifications/retry", body, token=BEARER_TOKEN
            )
            self.assertEqual(status, 400)
            self.assertEqual(resp_body["error"], "invalid_request")

    def test_reclaim_endpoint_rejects_an_out_of_bounds_batch_size(self):
        status, body = self._request(
            "POST",
            "/recovery/notification-leases/reclaim",
            {"batch_size": 100000},
            token=BEARER_TOKEN,
        )
        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "invalid_request")

    def test_response_bodies_are_stable_sorted_json(self):
        status, _ = self._request("GET", "/admin/accounts/acct-1", token=BEARER_TOKEN)
        req = urllib.request.Request(
            self.base_url + "/admin/accounts/acct-1",
            headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            raw = resp.read().decode("utf-8")
        parsed = json.loads(raw)
        self.assertEqual(raw, json.dumps(parsed, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    unittest.main()
