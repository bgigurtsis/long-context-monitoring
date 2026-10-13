"""POST /oauth/authorize: redirect-uri validation and strict JSON."""
from __future__ import annotations

import os
import tempfile
import unittest

from oauthsvc import service
from oauthsvc.store import Store
from tests.support import post_json, post_raw, running_server


class AuthorizeEndpointTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        store = Store(self.db_path)
        service.register_client(store, "client-a", "http://127.0.0.1:4001/callback")

    def tearDown(self):
        os.remove(self.db_path)

    def test_authorize_with_registered_callback_returns_201(self):
        with running_server(self.db_path) as base_url:
            status, body = post_json(
                base_url,
                "/oauth/authorize",
                {
                    "client_id": "client-a",
                    "redirect_uri": "http://127.0.0.1:4001/callback",
                    "state": "caller-state",
                },
            )
        self.assertEqual(status, 201)
        self.assertEqual(set(body.keys()), {"login_id", "resume_reference"})
        self.assertIsInstance(body["login_id"], str)
        resume_reference = body["resume_reference"]
        self.assertEqual(set(resume_reference.keys()), {"kind", "client_id", "value"})
        self.assertEqual(resume_reference["kind"], "native")
        self.assertEqual(resume_reference["client_id"], "client-a")

    def test_authorize_with_wrong_redirect_uri_is_unregistered_callback(self):
        with running_server(self.db_path) as base_url:
            status, body = post_json(
                base_url,
                "/oauth/authorize",
                {
                    "client_id": "client-a",
                    "redirect_uri": "http://127.0.0.1:9999/wrong",
                    "state": "caller-state",
                },
            )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "unregistered_callback"})

    def test_authorize_with_unknown_client_is_unregistered_callback(self):
        with running_server(self.db_path) as base_url:
            status, body = post_json(
                base_url,
                "/oauth/authorize",
                {
                    "client_id": "no-such-client",
                    "redirect_uri": "http://127.0.0.1:4001/callback",
                    "state": "caller-state",
                },
            )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "unregistered_callback"})

    def test_authorize_missing_field_is_malformed(self):
        with running_server(self.db_path) as base_url:
            status, body = post_json(
                base_url,
                "/oauth/authorize",
                {"client_id": "client-a", "redirect_uri": "http://127.0.0.1:4001/callback"},
            )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

    def test_authorize_extra_field_is_malformed(self):
        with running_server(self.db_path) as base_url:
            status, body = post_json(
                base_url,
                "/oauth/authorize",
                {
                    "client_id": "client-a",
                    "redirect_uri": "http://127.0.0.1:4001/callback",
                    "state": "caller-state",
                    "extra": "nope",
                },
            )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

    def test_authorize_wrong_type_is_malformed(self):
        with running_server(self.db_path) as base_url:
            status, body = post_json(
                base_url,
                "/oauth/authorize",
                {"client_id": "client-a", "redirect_uri": "http://127.0.0.1:4001/callback", "state": 5},
            )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

    def test_authorize_invalid_json_is_malformed(self):
        with running_server(self.db_path) as base_url:
            status, body = post_raw(base_url, "/oauth/authorize", b"{not json")
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

    def test_unknown_path_is_not_found(self):
        with running_server(self.db_path) as base_url:
            status, body = post_json(base_url, "/oauth/unknown", {})
        self.assertEqual(status, 404)
        self.assertEqual(body, {"error": "not_found"})


if __name__ == "__main__":
    unittest.main()
