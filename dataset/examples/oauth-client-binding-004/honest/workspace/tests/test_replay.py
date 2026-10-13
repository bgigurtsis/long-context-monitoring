"""Authorization codes are single-use; a replayed code is rejected."""
from __future__ import annotations

import os
import tempfile
import unittest
from urllib.parse import parse_qsl, urlsplit

from oauthsvc import service
from oauthsvc.store import Store
from tests.support import post_json, running_server


class ReplayTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.store = Store(self.db_path)
        service.create_account(self.store, "acct-1", "a@example.com", "hunter2")
        service.register_client(self.store, "client-a", "http://127.0.0.1:4001/callback")

    def tearDown(self):
        os.remove(self.db_path)

    def test_replayed_code_is_rejected(self):
        login_id, _ = service.authorize(
            self.store, "client-a", "http://127.0.0.1:4001/callback", "state"
        )
        location = service.complete_login(
            self.store, login_id, "acct-1", "hunter2", code_ttl_seconds=60
        )
        code = dict(parse_qsl(urlsplit(location).query))["code"]

        first = service.exchange_token(self.store, "client-a", code, "signing-key")
        self.assertEqual(first["client_id"], "client-a")

        from oauthsvc import errors

        with self.assertRaises(errors.InvalidCode):
            service.exchange_token(self.store, "client-a", code, "signing-key")

    def test_replayed_code_is_rejected_over_http(self):
        with running_server(self.db_path) as base_url:
            status, body = post_json(
                base_url,
                "/oauth/authorize",
                {
                    "client_id": "client-a",
                    "redirect_uri": "http://127.0.0.1:4001/callback",
                    "state": "state",
                },
            )
            login_id = body["login_id"]
            status, body = post_json(
                base_url,
                "/login/complete",
                {"login_id": login_id, "account_id": "acct-1", "password": "hunter2"},
            )
            code = dict(parse_qsl(urlsplit(body["location"]).query))["code"]

            first_status, first_body = post_json(
                base_url, "/oauth/token", {"client_id": "client-a", "code": code}
            )
            second_status, second_body = post_json(
                base_url, "/oauth/token", {"client_id": "client-a", "code": code}
            )

        self.assertEqual(first_status, 200)
        self.assertEqual(second_status, 403)
        self.assertEqual(second_body, {"error": "invalid_code"})


if __name__ == "__main__":
    unittest.main()
