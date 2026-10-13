"""End-to-end HTTP tests: loopback binding, auth, bounded bodies, routes."""
import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

from accountsvc.server import MAX_BODY_BYTES, make_server
from accountsvc.service import RecoveryService
from tests.support import temp_database

BEARER_TOKEN = "s3cr3t-admin-token"


class _FakeMailHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length).decode("utf-8"))
        self.server.received.append(body)
        status = self.server.next_status
        self.send_response(status)
        self.send_header("Content-Length", "0")
        self.end_headers()


class _FakeMailServer(HTTPServer):
    received: list
    next_status: int


def start_fake_mail_server():
    server = _FakeMailServer(("127.0.0.1", 0), _FakeMailHandler)
    server.received = []
    server.next_status = 200
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


class ServerIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.mail_server, self.mail_thread = start_fake_mail_server()
        mail_host, mail_port = self.mail_server.server_address[:2]
        self.mail_endpoint = f"http://{mail_host}:{mail_port}/deliver"

        self.db_ctx = temp_database()
        self.db = self.db_ctx.__enter__()
        self.service = RecoveryService(self.db, mail_endpoint=self.mail_endpoint)
        self.service.create_account("org-1", "acct-1", "user@example.com")

        self.server = make_server(self.service, BEARER_TOKEN, port=0)
        self.host, self.port = self.server.server_address[:2]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.mail_server.shutdown()
        self.mail_server.server_close()
        self.db_ctx.__exit__(None, None, None)

    def _url(self, path):
        return f"http://{self.host}:{self.port}{path}"

    def _post(self, path, body, token=None, raw_body=None):
        data = raw_body if raw_body is not None else json.dumps(body).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        request = urllib.request.Request(self._url(path), data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request) as response:
                return response.getcode(), json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    def test_binds_to_loopback_only(self):
        self.assertIn(self.host, ("127.0.0.1", "localhost"))

    def test_recovery_start_and_complete_round_trip(self):
        status, body = self._post("/recovery/start", {"organization": "org-1", "email": "user@example.com"})
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "sent")
        self.assertNotIn("recovery_token", body)

        self.assertEqual(len(self.mail_server.received), 1)
        token = self.mail_server.received[0]["recovery_token"]
        receipt_id = self.mail_server.received[0]["receipt_id"]
        self.assertTrue(receipt_id)

        status, body = self._post("/recovery/complete", {"token": token})
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "recovered")
        self.assertEqual(body["account_id"], "acct-1")

    def test_recovery_start_unknown_account_does_not_leak(self):
        status, body = self._post(
            "/recovery/start", {"organization": "org-1", "email": "nobody@example.com"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "accepted")
        self.assertEqual(self.mail_server.received, [])

    def test_admin_routes_require_bearer_token(self):
        for path, body in (
            ("/recovery/notifications/retry", {}),
            ("/recovery/notifications/reconcile", {"receipts": []}),
            ("/recovery/notifications/redrive", {"receipt_id": "x"}),
            ("/recovery/notifications/status", {"receipt_id": "x"}),
        ):
            status, body_resp = self._post(path, body)
            self.assertEqual(status, 401, path)
            self.assertEqual(body_resp["error"], "unauthorized")

    def test_admin_routes_reject_wrong_token(self):
        status, body = self._post("/recovery/notifications/retry", {}, token="wrong-token")
        self.assertEqual(status, 401)

    def test_retry_endpoint_resends_failed_notifications(self):
        self.mail_server.next_status = 503
        status, _ = self._post("/recovery/start", {"organization": "org-1", "email": "user@example.com"})
        self.assertEqual(status, 200)

        self.mail_server.next_status = 200
        status, body = self._post("/recovery/notifications/retry", {}, token=BEARER_TOKEN)
        self.assertEqual(status, 200)
        self.assertEqual(len(body["retried"]), 1)
        self.assertEqual(body["retried"][0]["status"], "sent")
        self.assertEqual(len(self.mail_server.received), 2)

    def test_reconcile_endpoint_updates_notification_status(self):
        status, start_body = self._post(
            "/recovery/start", {"organization": "org-1", "email": "user@example.com"}
        )
        self.assertEqual(status, 200)
        receipt_id = self.mail_server.received[0]["receipt_id"]

        status, body = self._post(
            "/recovery/notifications/reconcile",
            {"receipts": [{"receipt_id": receipt_id, "status": "delivered"}]},
            token=BEARER_TOKEN,
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["reconciled"], [receipt_id])

    def test_redrive_endpoint_resends_one_failed_notice(self):
        self.mail_server.next_status = 500
        self._post("/recovery/start", {"organization": "org-1", "email": "user@example.com"})
        receipt_id = self.mail_server.received[0]["receipt_id"]

        self.mail_server.next_status = 200
        status, body = self._post(
            "/recovery/notifications/redrive", {"receipt_id": receipt_id}, token=BEARER_TOKEN
        )
        self.assertEqual(status, 200)
        self.assertEqual(body, {"receipt_id": receipt_id, "status": "sent"})
        self.assertEqual(len(self.mail_server.received), 2)

    def test_status_endpoint_reports_effective_address_after_successful_send(self):
        status, start_body = self._post(
            "/recovery/start", {"organization": "org-1", "email": "user@example.com"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(start_body["status"], "sent")
        receipt_id = self.mail_server.received[0]["receipt_id"]

        status, body = self._post(
            "/recovery/notifications/status", {"receipt_id": receipt_id}, token=BEARER_TOKEN
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["receipt_id"], receipt_id)
        self.assertEqual(body["status"], "sent")
        self.assertEqual(body["effective_address"], "user@example.com")
        self.assertEqual(len(body["attempts"]), 1)
        self.assertEqual(body["attempts"][0]["outcome"], "success")

    def test_redrive_endpoint_sends_to_current_address_after_email_change(self):
        self.mail_server.next_status = 500
        self._post("/recovery/start", {"organization": "org-1", "email": "user@example.com"})
        receipt_id = self.mail_server.received[0]["receipt_id"]

        # The account moves to a new address after the failed attempt but
        # before the redrive; the redrive must reach the new address, not
        # the one recorded on the original failed notice.
        self.service.change_email("acct-1", "new@example.com")

        self.mail_server.next_status = 200
        status, body = self._post(
            "/recovery/notifications/redrive", {"receipt_id": receipt_id}, token=BEARER_TOKEN
        )
        self.assertEqual(status, 200)
        self.assertEqual(body, {"receipt_id": receipt_id, "status": "sent"})
        self.assertEqual(len(self.mail_server.received), 2)
        self.assertEqual(self.mail_server.received[1]["recipient"], "new@example.com")

    def test_redrive_endpoint_refuses_without_admin_credential(self):
        self.mail_server.next_status = 500
        self._post("/recovery/start", {"organization": "org-1", "email": "user@example.com"})
        receipt_id = self.mail_server.received[0]["receipt_id"]

        status, body = self._post("/recovery/notifications/redrive", {"receipt_id": receipt_id})
        self.assertEqual(status, 401)
        self.assertEqual(body["error"], "unauthorized")
        self.assertEqual(len(self.mail_server.received), 1)

    def test_redrive_endpoint_rejects_unknown_receipt(self):
        status, body = self._post(
            "/recovery/notifications/redrive", {"receipt_id": "ghost"}, token=BEARER_TOKEN
        )
        self.assertEqual(status, 404)
        self.assertEqual(body["error"], "not_found")

    def test_oversized_body_is_rejected(self):
        oversized = json.dumps({"organization": "org-1", "email": "x" * (MAX_BODY_BYTES + 1)}).encode(
            "utf-8"
        )
        status, body = self._post("/recovery/start", None, raw_body=oversized)
        self.assertEqual(status, 413)
        self.assertEqual(body["error"], "payload_too_large")

    def test_unknown_route_is_404(self):
        status, body = self._post("/nonexistent", {})
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
