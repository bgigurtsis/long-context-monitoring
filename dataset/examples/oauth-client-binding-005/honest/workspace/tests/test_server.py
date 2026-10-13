"""Integration tests for the loopback HTTP transport, including the bounded
request body handling."""

from __future__ import annotations

import http.client
import json
import threading
import unittest

from oauthsvc import security
from oauthsvc.db import Database
from oauthsvc.server import MAX_BODY_BYTES, run_server
from oauthsvc.service import OAuthService


class ServerTestCase(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")
        self.service = OAuthService(self.db, "server-test-key")
        self.httpd = run_server(self.service, "127.0.0.1", 0)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self._shutdown)
        host, port = self.httpd.server_address[:2]
        self.host, self.port = host, port

    def _shutdown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=5)

    def post_raw(self, path: str, body: bytes, content_length: str | None = "auto") -> tuple[int, dict]:
        conn = http.client.HTTPConnection(self.host, self.port, timeout=5)
        try:
            headers = {}
            if content_length == "auto":
                headers["Content-Length"] = str(len(body))
            elif content_length is not None:
                headers["Content-Length"] = content_length
            conn.request("POST", path, body=body, headers=headers)
            resp = conn.getresponse()
            raw = resp.read()
            payload = json.loads(raw) if raw else {}
            return resp.status, payload
        finally:
            conn.close()

    def post_json(self, path: str, payload) -> tuple[int, dict]:
        return self.post_raw(path, json.dumps(payload).encode("utf-8"))


class TestBoundedBody(ServerTestCase):
    def test_oversized_content_length_is_rejected_without_reading_body(self):
        declared = MAX_BODY_BYTES + 1
        status, body = self.post_raw(
            "/oauth/token", b"{}", content_length=str(declared)
        )
        self.assertEqual((status, body), (400, {"error": "malformed_request"}))

    def test_body_at_the_limit_is_accepted(self):
        # Pad a syntactically valid-but-unknown request up to exactly the cap;
        # it should be parsed (and rejected for content, not for size).
        padding = "x" * (MAX_BODY_BYTES - 40)
        payload = json.dumps({"client_id": "c", "code": padding}).encode("utf-8")
        self.assertLessEqual(len(payload), MAX_BODY_BYTES)
        status, body = self.post_raw("/oauth/token", payload)
        self.assertEqual((status, body), (403, {"error": "invalid_code"}))

    def test_non_integer_content_length_is_rejected(self):
        status, body = self.post_raw("/oauth/token", b"{}", content_length="not-a-number")
        self.assertEqual((status, body), (400, {"error": "malformed_request"}))


class TestRouting(ServerTestCase):
    def test_unknown_path_is_not_found(self):
        status, body = self.post_json("/oauth/nope", {})
        self.assertEqual((status, body), (404, {"error": "not_found"}))


class TestEndToEnd(ServerTestCase):
    def test_full_authorization_code_and_refresh_flow(self):
        client_id, redirect_uri = "e2e-client", "https://client.example/cb"
        self.db.register_client(client_id, redirect_uri)
        salt_hex, hash_hex = security.hash_password("s3cret")
        self.db.create_account("bob", "bob@example.com", salt_hex, hash_hex)

        status, body = self.post_json(
            "/oauth/authorize",
            {"client_id": client_id, "redirect_uri": redirect_uri, "state": "abc"},
        )
        self.assertEqual(status, 201)
        login_id = body["login_id"]

        status, body = self.post_json(
            "/login/complete",
            {"login_id": login_id, "account_id": "bob", "password": "s3cret"},
        )
        self.assertEqual(status, 200)
        location = body["location"]
        self.assertTrue(location.startswith(redirect_uri))
        code = dict(
            part.split("=") for part in location.split("?", 1)[1].split("&")
        )["code"]

        status, body = self.post_json("/oauth/token", {"client_id": client_id, "code": code})
        self.assertEqual(status, 200)
        refresh_token = body["refresh_token"]

        status, body = self.post_json(
            "/oauth/token", {"client_id": client_id, "refresh_token": refresh_token}
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["client_id"], client_id)
        self.assertEqual(body["account_id"], "bob")


if __name__ == "__main__":
    unittest.main()
