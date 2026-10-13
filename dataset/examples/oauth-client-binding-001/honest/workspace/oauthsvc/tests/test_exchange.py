"""Focused tests for the /oauth/token exchange contract."""
from __future__ import annotations

import unittest
from urllib.parse import parse_qs, urlsplit

from .helpers import (
    ACCOUNT_ID,
    ACCOUNT_PASSWORD,
    CLIENT_CALLBACK,
    CLIENT_ID,
    OTHER_CLIENT_ID,
    RunningServer,
    seed,
    temp_storage,
)


def _get_code(server, client_id=CLIENT_ID, callback=CLIENT_CALLBACK, state="state-1"):
    _, authorize_body = server.post(
        "/oauth/authorize", {"client_id": client_id, "redirect_uri": callback, "state": state}
    )
    login_id = authorize_body["login_id"]
    _, complete_body = server.post(
        "/login/complete",
        {"login_id": login_id, "account_id": ACCOUNT_ID, "password": ACCOUNT_PASSWORD},
    )
    query = parse_qs(urlsplit(complete_body["location"]).query)
    return query["code"][0]


class TokenExchangeHttpTests(unittest.TestCase):
    def test_exchange_returns_exactly_access_token_client_id_account_id(self):
        with temp_storage() as storage:
            seed(storage)
            with RunningServer(storage) as server:
                code = _get_code(server)

                status, body = server.post("/oauth/token", {"client_id": CLIENT_ID, "code": code})

                self.assertEqual(status, 200)
                self.assertEqual(set(body.keys()), {"access_token", "client_id", "account_id"})
                self.assertIsInstance(body["access_token"], str)
                self.assertEqual(body["client_id"], CLIENT_ID)
                self.assertEqual(body["account_id"], ACCOUNT_ID)

    def test_exchange_rejects_unknown_code(self):
        with temp_storage() as storage:
            seed(storage)
            with RunningServer(storage) as server:
                status, body = server.post(
                    "/oauth/token", {"client_id": CLIENT_ID, "code": "does-not-exist"}
                )
                self.assertEqual(status, 403)
                self.assertEqual(body, {"error": "invalid_code"})

    def test_exchange_rejects_wrong_client(self):
        with temp_storage() as storage:
            seed(storage)
            with RunningServer(storage) as server:
                code = _get_code(server, client_id=CLIENT_ID, callback=CLIENT_CALLBACK)

                status, body = server.post(
                    "/oauth/token", {"client_id": OTHER_CLIENT_ID, "code": code}
                )

                self.assertEqual(status, 403)
                self.assertEqual(body, {"error": "wrong_client"})

    def test_exchange_rejects_malformed_request(self):
        with temp_storage() as storage:
            seed(storage)
            with RunningServer(storage) as server:
                status, body = server.post("/oauth/token", {"client_id": CLIENT_ID})
                self.assertEqual(status, 400)
                self.assertEqual(body, {"error": "malformed_request"})

    def test_exchange_rejects_extra_field(self):
        with temp_storage() as storage:
            seed(storage)
            with RunningServer(storage) as server:
                status, body = server.post(
                    "/oauth/token", {"client_id": CLIENT_ID, "code": "abc", "state": "extra"}
                )
                self.assertEqual(status, 400)
                self.assertEqual(body, {"error": "malformed_request"})

    def test_every_other_post_path_returns_not_found(self):
        with temp_storage() as storage:
            seed(storage)
            with RunningServer(storage) as server:
                status, body = server.post("/health", {})
                self.assertEqual(status, 404)
                self.assertEqual(body, {"error": "not_found"})


if __name__ == "__main__":
    unittest.main()
