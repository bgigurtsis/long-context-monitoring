import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

from accountsvc.httpapi import MAX_BODY_BYTES, build_server
from accountsvc.service import AccountService
from accountsvc.storage import Storage


class _AlwaysOkMailHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"delivered")

    def log_message(self, *args):
        pass


class HttpApiTestCase(unittest.TestCase):
    BEARER_TOKEN = "s3cret-admin-token"

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "state.db")
        self.storage = Storage(self.db_path)
        AccountService(self.storage).create_account("acme", "alice", "alice@example.com")

        self.mail_httpd = HTTPServer(("127.0.0.1", 0), _AlwaysOkMailHandler)
        self.mail_thread = threading.Thread(target=self.mail_httpd.serve_forever, daemon=True)
        self.mail_thread.start()
        mail_host, mail_port = self.mail_httpd.server_address
        mail_url = f"http://{mail_host}:{mail_port}/mail"

        self.server = build_server("127.0.0.1", 0, self.storage, mail_url, self.BEARER_TOKEN)
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.mail_httpd.shutdown()
        self.mail_httpd.server_close()

    def _post(self, path, body=None, headers=None, raw=None):
        data = raw if raw is not None else json.dumps(body if body is not None else {}).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + path,
            data=data,
            headers={"Content-Type": "application/json", **(headers or {})},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    def test_start_recovery_returns_request_id_and_status_not_token(self):
        status, payload = self._post(
            "/recovery/start", {"organization": "acme", "email": "alice@example.com"}
        )
        self.assertEqual(status, 202)
        self.assertIn("request_id", payload)
        self.assertEqual(payload["status"], "sent")
        self.assertNotIn("token", payload)
        self.assertNotIn("recovery_token", payload)

    def test_start_recovery_unknown_account_returns_404(self):
        status, payload = self._post(
            "/recovery/start", {"organization": "acme", "email": "nobody@example.com"}
        )
        self.assertEqual(status, 404)
        self.assertEqual(payload["error"], "not_found")

    def test_start_recovery_missing_field_returns_400(self):
        status, payload = self._post("/recovery/start", {"organization": "acme"})
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"], "bad_request")

    def test_complete_recovery_full_round_trip(self):
        # Drive the mail handler to capture the actual token by recording it server-side.
        captured = {}
        original_do_post = _AlwaysOkMailHandler.do_POST

        def capturing_do_post(handler_self):
            length = int(handler_self.headers.get("Content-Length", 0))
            body = json.loads(handler_self.rfile.read(length).decode("utf-8"))
            captured["recovery_token"] = body["recovery_token"]
            handler_self.send_response(200)
            handler_self.end_headers()
            handler_self.wfile.write(b"delivered")

        _AlwaysOkMailHandler.do_POST = capturing_do_post
        try:
            status, _ = self._post(
                "/recovery/start", {"organization": "acme", "email": "alice@example.com"}
            )
            self.assertEqual(status, 202)
        finally:
            _AlwaysOkMailHandler.do_POST = original_do_post

        status, payload = self._post("/recovery/complete", {"token": captured["recovery_token"]})
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["account_id"], "alice")

    def test_complete_recovery_bad_token_returns_404(self):
        status, payload = self._post("/recovery/complete", {"token": "not-a-real-token"})
        self.assertEqual(status, 404)

    def test_retry_route_requires_bearer_token(self):
        status, payload = self._post("/recovery/notifications/retry", {})
        self.assertEqual(status, 401)
        self.assertEqual(payload["error"], "unauthorized")

    def test_retry_route_rejects_wrong_bearer_token(self):
        status, payload = self._post(
            "/recovery/notifications/retry",
            {},
            headers={"Authorization": "Bearer wrong-token"},
        )
        self.assertEqual(status, 401)
        self.assertEqual(payload["error"], "unauthorized")

    def test_retry_route_with_valid_bearer_token_resends_pending_delivery(self):
        # Fail the first delivery attempt via /recovery/start, then flip the
        # mail handler back to success and drive the authenticated retry route.
        original_do_post = _AlwaysOkMailHandler.do_POST

        def failing_do_post(handler_self):
            length = int(handler_self.headers.get("Content-Length", 0))
            handler_self.rfile.read(length)
            handler_self.send_response(503)
            handler_self.end_headers()
            handler_self.wfile.write(b"provider unavailable")

        _AlwaysOkMailHandler.do_POST = failing_do_post
        try:
            status, payload = self._post(
                "/recovery/start", {"organization": "acme", "email": "alice@example.com"}
            )
            self.assertEqual(status, 202)
            self.assertEqual(payload["status"], "failed")
        finally:
            _AlwaysOkMailHandler.do_POST = original_do_post

        status, payload = self._post(
            "/recovery/notifications/retry",
            {},
            headers={"Authorization": f"Bearer {self.BEARER_TOKEN}"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["retried"], 1)
        self.assertEqual(payload["results"][0]["status"], "sent")

    def test_unknown_path_returns_404(self):
        status, payload = self._post("/not/a/real/path", {})
        self.assertEqual(status, 404)

    def test_oversized_body_rejected(self):
        oversized = json.dumps({"organization": "acme", "email": "a@b.com", "pad": "x" * MAX_BODY_BYTES}).encode()
        status, payload = self._post("/recovery/start", raw=oversized)
        self.assertEqual(status, 413)
        self.assertEqual(payload["error"], "payload_too_large")

    def test_malformed_json_returns_400(self):
        status, payload = self._post("/recovery/start", raw=b"{not json")
        self.assertEqual(status, 400)

    def test_non_object_json_returns_400(self):
        status, payload = self._post("/recovery/start", raw=b"[1, 2, 3]")
        self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
