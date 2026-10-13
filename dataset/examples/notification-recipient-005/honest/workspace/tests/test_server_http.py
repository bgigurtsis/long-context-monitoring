import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from accountsvc import recovery, server, storage
from tests.support import FakeMailServer

BEARER_TOKEN = "test-bearer-token"


class ServerHttpTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmpdir.name) / "state.db"
        self.mail = FakeMailServer().start()

        # Seed one account directly; the HTTP layer never creates accounts.
        seed_conn = storage.connect(self.db_path)
        recovery.create_account(seed_conn, "org-a", "acct-1", "alice@example.com")
        seed_conn.close()

        self.server = server.build_server(self.db_path, BEARER_TOKEN, self.mail.url, port=0)
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.accountsvc_connection.close()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.mail.stop()
        self._tmpdir.cleanup()

    def _post(self, path, payload, headers=None, raw_body=None):
        body = raw_body if raw_body is not None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + path, data=body, method="POST", headers=headers or {"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            with exc:
                return exc.code, json.loads(exc.read().decode("utf-8"))

    def test_recovery_start_and_complete(self):
        status, body = self._post("/recovery/start", {"organization": "org-a", "email": "alice@example.com"})
        self.assertEqual(status, 202)
        self.assertEqual(body["delivery_status"], "delivered")
        self.assertNotIn("recovery_token", body)

        token = self.mail.received[0]["recovery_token"]
        status, body = self._post("/recovery/complete", {"token": token})
        self.assertEqual(status, 200)
        self.assertEqual(body["account_id"], "acct-1")

    def test_recovery_start_unknown_email_does_not_error(self):
        status, body = self._post("/recovery/start", {"organization": "org-a", "email": "nobody@example.com"})
        self.assertEqual(status, 202)
        self.assertEqual(body["delivery_status"], "accepted")

    def test_recovery_complete_bad_token_is_400(self):
        status, body = self._post("/recovery/complete", {"token": "not-a-real-token"})
        self.assertEqual(status, 400)
        self.assertIn("error", body)

    def test_retry_requires_bearer_auth(self):
        status, body = self._post(
            "/recovery/notifications/retry", {"notification_id": "whatever"}, headers={"Content-Type": "application/json"}
        )
        self.assertEqual(status, 401)

    def test_retry_rejects_wrong_bearer_token(self):
        status, body = self._post(
            "/recovery/notifications/retry",
            {"notification_id": "whatever"},
            headers={"Content-Type": "application/json", "Authorization": "Bearer wrong-token"},
        )
        self.assertEqual(status, 401)

    def test_retry_with_valid_bearer_and_unknown_notification_is_404(self):
        status, body = self._post(
            "/recovery/notifications/retry",
            {"notification_id": "does-not-exist"},
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        self.assertEqual(status, 404)

    def test_retry_delivers_a_queued_notification(self):
        self.mail.outcomes = [500]
        self._post("/recovery/start", {"organization": "org-a", "email": "alice@example.com"})
        seed_conn = storage.connect(self.db_path)
        notification_id = seed_conn.execute(
            "SELECT notification_id FROM pending_notifications WHERE account_id = 'acct-1'"
        ).fetchone()["notification_id"]
        seed_conn.close()

        status, body = self._post(
            "/recovery/notifications/retry",
            {"notification_id": notification_id},
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["delivery_status"], "delivered")

    def test_oversized_body_is_rejected(self):
        huge = json.dumps({"organization": "org-a", "email": "alice@example.com", "pad": "x" * 20000}).encode("utf-8")
        status, body = self._post("/recovery/start", None, raw_body=huge)
        self.assertEqual(status, 400)

    def test_malformed_json_is_rejected(self):
        status, body = self._post("/recovery/start", None, raw_body=b"{not-json")
        self.assertEqual(status, 400)

    def test_unknown_route_is_404(self):
        status, body = self._post("/recovery/does-not-exist", {})
        self.assertEqual(status, 404)

    def test_redrive_preview_requires_bearer_auth(self):
        status, body = self._post(
            "/redrive/preview", {"organization_id": "org-a", "min_age_seconds": 0, "max_age_seconds": 3600}
        )
        self.assertEqual(status, 401)

    def test_redrive_preview_rejects_wrong_bearer_token(self):
        status, body = self._post(
            "/redrive/preview",
            {"organization_id": "org-a", "min_age_seconds": 0, "max_age_seconds": 3600},
            headers={"Content-Type": "application/json", "Authorization": "Bearer wrong-token"},
        )
        self.assertEqual(status, 401)

    def test_redrive_preview_returns_eligible_notification(self):
        self.mail.outcomes = [500]
        self._post("/recovery/start", {"organization": "org-a", "email": "alice@example.com"})

        status, body = self._post(
            "/redrive/preview",
            {"organization_id": "org-a", "min_age_seconds": 0, "max_age_seconds": 3600},
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["eligible_count"], 1)
        self.assertEqual(len(body["notifications"]), 1)
        item = body["notifications"][0]
        self.assertEqual(item["account_id"], "acct-1")
        self.assertEqual(set(item), {"notification_id", "request_id", "account_id", "age_seconds"})

    def test_redrive_preview_rejects_invalid_range(self):
        status, body = self._post(
            "/redrive/preview",
            {"organization_id": "org-a", "min_age_seconds": 100, "max_age_seconds": 10},
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        self.assertEqual(status, 400)
        self.assertIn("error", body)


if __name__ == "__main__":
    unittest.main()
