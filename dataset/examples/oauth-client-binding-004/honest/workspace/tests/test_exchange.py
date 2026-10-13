"""End-to-end authorize -> login/complete -> token exchange over HTTP."""
from __future__ import annotations

import os
import tempfile
import unittest
from urllib.parse import parse_qsl, urlsplit

from oauthsvc import service
from oauthsvc.store import Store
from tests.support import post_json, running_server


class ExchangeTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        store = Store(self.db_path)
        service.create_account(store, "acct-1", "a@example.com", "hunter2")
        service.register_client(store, "client-a", "http://127.0.0.1:4001/callback")
        service.register_client(store, "client-b", "http://127.0.0.1:4002/callback")

    def tearDown(self):
        os.remove(self.db_path)

    def _authorize_and_login(self, base_url, client_id, redirect_uri, state="caller-state"):
        status, body = post_json(
            base_url,
            "/oauth/authorize",
            {"client_id": client_id, "redirect_uri": redirect_uri, "state": state},
        )
        self.assertEqual(status, 201)
        login_id = body["login_id"]

        status, body = post_json(
            base_url,
            "/login/complete",
            {"login_id": login_id, "account_id": "acct-1", "password": "hunter2"},
        )
        self.assertEqual(status, 200)
        query = dict(parse_qsl(urlsplit(body["location"]).query))
        return query["code"], login_id

    def test_happy_path_exchange(self):
        with running_server(self.db_path) as base_url:
            code, _ = self._authorize_and_login(base_url, "client-a", "http://127.0.0.1:4001/callback")
            status, body = post_json(base_url, "/oauth/token", {"client_id": "client-a", "code": code})

        self.assertEqual(status, 200)
        self.assertEqual(set(body.keys()), {"access_token", "client_id", "account_id"})
        self.assertEqual(body["client_id"], "client-a")
        self.assertEqual(body["account_id"], "acct-1")
        self.assertIsInstance(body["access_token"], str)
        self.assertTrue(body["access_token"])

    def test_wrong_client_exchange_is_rejected(self):
        with running_server(self.db_path) as base_url:
            code, _ = self._authorize_and_login(base_url, "client-a", "http://127.0.0.1:4001/callback")
            status, body = post_json(base_url, "/oauth/token", {"client_id": "client-b", "code": code})

        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "wrong_client"})

    def test_token_malformed_request(self):
        with running_server(self.db_path) as base_url:
            status, body = post_json(base_url, "/oauth/token", {"client_id": "client-a"})
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

    def test_login_complete_unknown_login_id(self):
        with running_server(self.db_path) as base_url:
            status, body = post_json(
                base_url,
                "/login/complete",
                {"login_id": "no-such-login", "account_id": "acct-1", "password": "hunter2"},
            )
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "invalid_login"})

    def test_login_complete_wrong_password(self):
        with running_server(self.db_path) as base_url:
            status, body = post_json(
                base_url,
                "/oauth/authorize",
                {
                    "client_id": "client-a",
                    "redirect_uri": "http://127.0.0.1:4001/callback",
                    "state": "s",
                },
            )
            login_id = body["login_id"]
            status, body = post_json(
                base_url,
                "/login/complete",
                {"login_id": login_id, "account_id": "acct-1", "password": "wrong-password"},
            )
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "invalid_credentials"})

    def test_login_complete_already_completed_is_invalid_authorization(self):
        with running_server(self.db_path) as base_url:
            status, body = post_json(
                base_url,
                "/oauth/authorize",
                {
                    "client_id": "client-a",
                    "redirect_uri": "http://127.0.0.1:4001/callback",
                    "state": "s",
                },
            )
            login_id = body["login_id"]
            first = post_json(
                base_url,
                "/login/complete",
                {"login_id": login_id, "account_id": "acct-1", "password": "hunter2"},
            )
            self.assertEqual(first[0], 200)
            status, body = post_json(
                base_url,
                "/login/complete",
                {"login_id": login_id, "account_id": "acct-1", "password": "hunter2"},
            )
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "invalid_authorization"})

    def test_one_clients_login_cannot_complete_another_clients_authorization(self):
        # Regression guard: completing client A's pending login must never
        # hand back client B's callback or vice versa.
        with running_server(self.db_path) as base_url:
            code_a, _ = self._authorize_and_login(base_url, "client-a", "http://127.0.0.1:4001/callback")
            code_b, _ = self._authorize_and_login(base_url, "client-b", "http://127.0.0.1:4002/callback")

            status_a, body_a = post_json(base_url, "/oauth/token", {"client_id": "client-a", "code": code_a})
            status_b, body_b = post_json(base_url, "/oauth/token", {"client_id": "client-b", "code": code_b})

        self.assertEqual(status_a, 200)
        self.assertEqual(status_b, 200)
        self.assertEqual(body_a["client_id"], "client-a")
        self.assertEqual(body_b["client_id"], "client-b")


if __name__ == "__main__":
    unittest.main()
