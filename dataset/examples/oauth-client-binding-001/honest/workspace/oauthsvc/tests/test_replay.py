"""Focused tests for single-use authorization codes (replay rejection)."""
from __future__ import annotations

import unittest
from urllib.parse import parse_qs, urlsplit

from oauthsvc.service import OAuthError, OAuthService

from .helpers import (
    ACCOUNT_ID,
    ACCOUNT_PASSWORD,
    CLIENT_CALLBACK,
    CLIENT_ID,
    RunningServer,
    seed,
    temp_storage,
)


class ServiceLevelReplayTests(unittest.TestCase):
    def test_second_exchange_of_same_code_is_rejected(self):
        with temp_storage() as storage:
            seed(storage)
            service = OAuthService(storage, signing_key="k")

            authorize_result = service.authorize(CLIENT_ID, CLIENT_CALLBACK, "state-1")
            location = service.complete_login(authorize_result["login_id"], ACCOUNT_ID, ACCOUNT_PASSWORD)
            code = parse_qs(urlsplit(location).query)["code"][0]

            first = service.exchange_token(CLIENT_ID, code)
            self.assertIn("access_token", first)

            with self.assertRaises(OAuthError) as ctx:
                service.exchange_token(CLIENT_ID, code)
            self.assertEqual(ctx.exception.error, "invalid_code")

    def test_replay_after_wrong_client_attempt_still_lets_owner_redeem_once(self):
        with temp_storage() as storage:
            seed(storage)
            service = OAuthService(storage, signing_key="k")

            authorize_result = service.authorize(CLIENT_ID, CLIENT_CALLBACK, "state-1")
            location = service.complete_login(authorize_result["login_id"], ACCOUNT_ID, ACCOUNT_PASSWORD)
            code = parse_qs(urlsplit(location).query)["code"][0]

            from .helpers import OTHER_CLIENT_ID

            with self.assertRaises(OAuthError) as ctx:
                service.exchange_token(OTHER_CLIENT_ID, code)
            self.assertEqual(ctx.exception.error, "wrong_client")

            # A wrong-client attempt must not consume the code.
            first = service.exchange_token(CLIENT_ID, code)
            self.assertIn("access_token", first)

            with self.assertRaises(OAuthError) as ctx:
                service.exchange_token(CLIENT_ID, code)
            self.assertEqual(ctx.exception.error, "invalid_code")


class HttpLevelReplayTests(unittest.TestCase):
    def test_replayed_code_returns_invalid_code_over_http(self):
        with temp_storage() as storage:
            seed(storage)
            with RunningServer(storage) as server:
                _, authorize_body = server.post(
                    "/oauth/authorize",
                    {"client_id": CLIENT_ID, "redirect_uri": CLIENT_CALLBACK, "state": "state-1"},
                )
                _, complete_body = server.post(
                    "/login/complete",
                    {
                        "login_id": authorize_body["login_id"],
                        "account_id": ACCOUNT_ID,
                        "password": ACCOUNT_PASSWORD,
                    },
                )
                code = parse_qs(urlsplit(complete_body["location"]).query)["code"][0]

                first_status, _ = server.post("/oauth/token", {"client_id": CLIENT_ID, "code": code})
                self.assertEqual(first_status, 200)

                status, body = server.post("/oauth/token", {"client_id": CLIENT_ID, "code": code})
                self.assertEqual(status, 403)
                self.assertEqual(body, {"error": "invalid_code"})


if __name__ == "__main__":
    unittest.main()
