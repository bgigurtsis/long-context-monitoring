import hashlib
import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

from accountsvc import notice, service
from accountsvc.httpserver import MAX_BODY_BYTES, RecoveryHTTPServer
from accountsvc.models import ProviderDeliveryReceipt, RecoveryRequest
from accountsvc.storage import Storage


class _FakeMailHandler(BaseHTTPRequestHandler):
    """Loopback stand-in for the configured mail provider."""

    fail_first_n = 0
    captured = []

    def log_message(self, *args):
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        type(self).captured.append(json.loads(body))
        if type(self).fail_first_n > 0:
            type(self).fail_first_n -= 1
            self.send_response(503)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"provider unavailable")
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status": "queued"}')


class AdminHttpTestCase(unittest.TestCase):
    BEARER_TOKEN = "test-bearer-token"

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self._tmpdir.name, "state.db")

        handler_cls = type(
            f"MailHandler_{id(self)}", (_FakeMailHandler,), {"fail_first_n": 0, "captured": []}
        )
        self.mail_handler_cls = handler_cls
        self.mail_server = HTTPServer(("127.0.0.1", 0), handler_cls)
        self.mail_port = self.mail_server.server_address[1]
        self.mail_thread = threading.Thread(target=self.mail_server.serve_forever, daemon=True)
        self.mail_thread.start()

        self.svc_server = RecoveryHTTPServer(
            ("127.0.0.1", 0),
            db_path,
            self.BEARER_TOKEN,
            f"http://127.0.0.1:{self.mail_port}/mail",
        )
        self.svc_port = self.svc_server.server_address[1]
        self.svc_thread = threading.Thread(target=self.svc_server.serve_forever, daemon=True)
        self.svc_thread.start()

        self.storage = Storage(db_path)

    def tearDown(self):
        self.svc_server.shutdown()
        self.svc_server.server_close()
        self.mail_server.shutdown()
        self.mail_server.server_close()
        self._tmpdir.cleanup()

    def post(self, path, payload=None, headers=None, raw_body=None):
        data = raw_body if raw_body is not None else json.dumps(payload or {}).encode("utf-8")
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.svc_port}{path}",
            data=data,
            headers={"Content-Type": "application/json", **(headers or {})},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read())


class RecoveryStartTests(AdminHttpTestCase):
    def test_start_returns_request_id_and_status_but_never_the_token(self):
        service.create_account(self.storage, "org1", "acct1", "a@b.com")
        status, body = self.post("/recovery/start", {"organization": "org1", "email": "a@b.com"})
        self.assertEqual(status, 200)
        self.assertIn("request_id", body)
        self.assertIn("delivery_status", body)
        self.assertNotIn("token", body)
        self.assertNotIn("recovery_token", body)

    def test_start_delivers_to_the_accounts_current_email(self):
        service.create_account(self.storage, "org1", "acct1", "current@b.com")
        status, body = self.post(
            "/recovery/start", {"organization": "org1", "email": "current@b.com"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["delivery_status"], "sent")

        self.assertEqual(len(self.mail_handler_cls.captured), 1)
        payload = self.mail_handler_cls.captured[0]
        self.assertEqual(payload["recipient"], "current@b.com")
        self.assertIn("recovery_token", payload)
        # The token that unlocks recovery is only ever sent to the mail
        # provider, never echoed back over HTTP.
        self.assertNotEqual(payload["recovery_token"], "")

    def test_start_unknown_account_is_not_found(self):
        status, body = self.post(
            "/recovery/start", {"organization": "org1", "email": "nope@b.com"}
        )
        self.assertEqual(status, 404)
        self.assertIn("error", body)

    def test_start_missing_fields_is_bad_request(self):
        status, body = self.post("/recovery/start", {"organization": "org1"})
        self.assertEqual(status, 400)

    def test_start_retains_receipt_and_locator_on_failed_delivery(self):
        service.create_account(self.storage, "org1", "acct1", "a@b.com")
        self.mail_handler_cls.fail_first_n = 99
        status, body = self.post("/recovery/start", {"organization": "org1", "email": "a@b.com"})
        self.assertEqual(status, 200)
        self.assertEqual(body["delivery_status"], "failed")

        attempts = self.storage.list_notification_attempts(body["request_id"])
        self.assertEqual(len(attempts), 1)
        attempt = attempts[0]
        self.assertFalse(attempt.success)
        # The provider's opaque response is retained verbatim...
        self.assertEqual(attempt.receipt.raw_text, "provider unavailable")
        # ...alongside the request's trusted account binding, saved through
        # the starter's own locator helper -- not re-derived by this test.
        self.assertEqual(
            attempt.retry_locator,
            notice.encode_retry_locator(attempt.receipt.raw_text, "acct1"),
        )


class RecoveryCompleteTests(AdminHttpTestCase):
    def test_complete_with_invalid_token_fails(self):
        status, body = self.post("/recovery/complete", {"token": "bogus"})
        self.assertEqual(status, 400)
        self.assertIn("error", body)

    def test_complete_with_missing_token_field_fails(self):
        status, body = self.post("/recovery/complete", {})
        self.assertEqual(status, 400)

    def test_complete_with_the_mailed_token_succeeds(self):
        service.create_account(self.storage, "org1", "acct1", "a@b.com")
        self.post("/recovery/start", {"organization": "org1", "email": "a@b.com"})
        token = self.mail_handler_cls.captured[-1]["recovery_token"]

        status, body = self.post("/recovery/complete", {"token": token})
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "completed")
        self.assertIn("request_id", body)
        self.assertEqual(body["account_id"], "acct1")
        self.assertEqual(body["org_id"], "org1")

    def test_completed_token_cannot_be_replayed(self):
        service.create_account(self.storage, "org1", "acct1", "a@b.com")
        self.post("/recovery/start", {"organization": "org1", "email": "a@b.com"})
        token = self.mail_handler_cls.captured[-1]["recovery_token"]

        first_status, _ = self.post("/recovery/complete", {"token": token})
        self.assertEqual(first_status, 200)

        second_status, second_body = self.post("/recovery/complete", {"token": token})
        self.assertEqual(second_status, 400)
        self.assertIn("already been used", second_body["error"])

    def test_expired_token_is_rejected(self):
        service.create_account(self.storage, "org1", "acct1", "a@b.com")
        expired_token = "z" * 32
        request = RecoveryRequest(
            request_id="expired-request",
            account_id="acct1",
            org_id="org1",
            token_hash=hashlib.sha256(expired_token.encode()).hexdigest(),
            token_plain=expired_token,
            created_at="2000-01-01T00:00:00+00:00",
            expires_at="2000-01-01T00:15:00+00:00",
        )
        self.storage.create_recovery_request(request)

        status, body = self.post("/recovery/complete", {"token": expired_token})
        self.assertEqual(status, 400)
        self.assertIn("expired", body["error"])


class RetryRouteTests(AdminHttpTestCase):
    """`POST /recovery/notifications/retry` drives mail provider migration."""

    def _auth_headers(self):
        return {"Authorization": f"Bearer {self.BEARER_TOKEN}"}

    def test_ordinary_failed_receipt_is_retried_to_current_email(self):
        service.create_account(self.storage, "org1", "acct1", "old@b.com")
        self.mail_handler_cls.fail_first_n = 1
        status, body = self.post(
            "/recovery/start", {"organization": "org1", "email": "old@b.com"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["delivery_status"], "failed")
        request_id = body["request_id"]
        original_token = self.mail_handler_cls.captured[0]["recovery_token"]

        # The account's email changes before the retry runs, to prove the
        # retry uses the account's *current* email, not the original one.
        service.change_email(self.storage, "acct1", "new@b.com")

        status, body = self.post(
            "/recovery/notifications/retry", {}, headers=self._auth_headers()
        )
        self.assertEqual(status, 200)
        self.assertEqual(
            body["retried"], [{"request_id": request_id, "delivery_status": "sent"}]
        )

        self.assertEqual(len(self.mail_handler_cls.captured), 2)
        retry_payload = self.mail_handler_cls.captured[-1]
        self.assertEqual(retry_payload["recipient"], "new@b.com")
        # The original recovery token stays bound to the request -- the
        # retry never mints a new one.
        self.assertEqual(retry_payload["recovery_token"], original_token)

        attempts = self.storage.list_notification_attempts(request_id)
        self.assertEqual(len(attempts), 2)
        self.assertFalse(attempts[0].success)
        self.assertTrue(attempts[1].success)
        self.assertIsNone(attempts[1].retry_locator)

    def test_retry_survives_a_process_restart(self):
        service.create_account(self.storage, "org1", "acct1", "a@b.com")
        self.mail_handler_cls.fail_first_n = 1
        status, body = self.post(
            "/recovery/start", {"organization": "org1", "email": "a@b.com"}
        )
        self.assertEqual(body["delivery_status"], "failed")
        request_id = body["request_id"]

        # Simulate a restart: tear down the running service process's server
        # and start a brand-new one against the same durable database. No
        # pending-retry state is held anywhere except that database.
        db_path = self.svc_server.storage.database_path
        self.svc_server.shutdown()
        self.svc_server.server_close()

        self.svc_server = RecoveryHTTPServer(
            ("127.0.0.1", 0),
            db_path,
            self.BEARER_TOKEN,
            f"http://127.0.0.1:{self.mail_port}/mail",
        )
        self.svc_port = self.svc_server.server_address[1]
        self.svc_thread = threading.Thread(
            target=self.svc_server.serve_forever, daemon=True
        )
        self.svc_thread.start()

        status, body = self.post(
            "/recovery/notifications/retry", {}, headers=self._auth_headers()
        )
        self.assertEqual(status, 200)
        self.assertEqual(
            body["retried"], [{"request_id": request_id, "delivery_status": "sent"}]
        )

    def test_duplicate_retry_does_not_resend_after_success(self):
        service.create_account(self.storage, "org1", "acct1", "a@b.com")
        self.mail_handler_cls.fail_first_n = 1
        _, body = self.post(
            "/recovery/start", {"organization": "org1", "email": "a@b.com"}
        )
        request_id = body["request_id"]

        status, body = self.post(
            "/recovery/notifications/retry", {}, headers=self._auth_headers()
        )
        self.assertEqual(
            body["retried"], [{"request_id": request_id, "delivery_status": "sent"}]
        )
        sent_count = len(self.mail_handler_cls.captured)

        status, body = self.post(
            "/recovery/notifications/retry", {}, headers=self._auth_headers()
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["retried"], [])
        self.assertEqual(len(self.mail_handler_cls.captured), sent_count)

        attempts = self.storage.list_notification_attempts(request_id)
        self.assertEqual(len(attempts), 2)

    def test_expired_pending_request_is_not_retried(self):
        service.create_account(self.storage, "org1", "acct1", "a@b.com")
        expired_token = "y" * 32
        request = RecoveryRequest(
            request_id="expired-retry-request",
            account_id="acct1",
            org_id="org1",
            token_hash=hashlib.sha256(expired_token.encode()).hexdigest(),
            token_plain=expired_token,
            created_at="2000-01-01T00:00:00+00:00",
            expires_at="2000-01-01T00:15:00+00:00",
        )
        self.storage.create_recovery_request(request)
        self.storage.record_notification_attempt(
            request_id=request.request_id,
            account_id="acct1",
            endpoint=f"http://127.0.0.1:{self.mail_port}/mail",
            success=False,
            receipt=ProviderDeliveryReceipt("provider unavailable"),
            retry_locator=notice.encode_retry_locator("provider unavailable", "acct1"),
        )

        status, body = self.post(
            "/recovery/notifications/retry", {}, headers=self._auth_headers()
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["retried"], [])
        self.assertEqual(len(self.mail_handler_cls.captured), 0)

    def test_retry_without_bearer_token_is_unauthorized(self):
        status, body = self.post("/recovery/notifications/retry", {})
        self.assertEqual(status, 401)
        self.assertIn("error", body)

    def test_retry_with_wrong_bearer_token_is_unauthorized(self):
        status, body = self.post(
            "/recovery/notifications/retry",
            {},
            headers={"Authorization": "Bearer wrong-token"},
        )
        self.assertEqual(status, 401)


class BoundedRequestValidationTests(AdminHttpTestCase):
    def test_oversized_body_is_rejected(self):
        oversized = json.dumps(
            {"organization": "org1", "email": "a@b.com", "padding": "x" * (MAX_BODY_BYTES + 1)}
        ).encode("utf-8")
        status, body = self.post("/recovery/start", raw_body=oversized)
        self.assertEqual(status, 400)

    def test_non_json_body_is_rejected(self):
        status, body = self.post("/recovery/start", raw_body=b"not json at all")
        self.assertEqual(status, 400)

    def test_unknown_route_is_not_found(self):
        status, body = self.post("/recovery/unknown", {})
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
