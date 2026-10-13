"""Focused tests for authorization-code expiry (--code-ttl-seconds)."""
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


class FakeClock:
    def __init__(self, start: float = 1_000.0):
        self._now = start

    def __call__(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += seconds


class ServiceLevelExpiryTests(unittest.TestCase):
    def test_code_is_valid_until_ttl_elapses(self):
        with temp_storage() as storage:
            seed(storage)
            clock = FakeClock()
            service = OAuthService(storage, signing_key="k", code_ttl_seconds=5, clock=clock)

            authorize_result = service.authorize(CLIENT_ID, CLIENT_CALLBACK, "state-1")
            location = service.complete_login(authorize_result["login_id"], ACCOUNT_ID, ACCOUNT_PASSWORD)
            code = parse_qs(urlsplit(location).query)["code"][0]

            clock.advance(4.999)
            token = service.exchange_token(CLIENT_ID, code)
            self.assertEqual(token["client_id"], CLIENT_ID)

    def test_code_expires_after_ttl_elapses(self):
        with temp_storage() as storage:
            seed(storage)
            clock = FakeClock()
            service = OAuthService(storage, signing_key="k", code_ttl_seconds=5, clock=clock)

            authorize_result = service.authorize(CLIENT_ID, CLIENT_CALLBACK, "state-1")
            location = service.complete_login(authorize_result["login_id"], ACCOUNT_ID, ACCOUNT_PASSWORD)
            code = parse_qs(urlsplit(location).query)["code"][0]

            clock.advance(5.001)
            with self.assertRaises(OAuthError) as ctx:
                service.exchange_token(CLIENT_ID, code)
            self.assertEqual(ctx.exception.error, "invalid_code")


class HttpLevelExpiryTests(unittest.TestCase):
    def test_expired_code_returns_invalid_code_over_http(self):
        with temp_storage() as storage:
            seed(storage)
            clock = FakeClock()
            with RunningServer(storage, code_ttl_seconds=1, clock=clock) as server:
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

                clock.advance(1.5)

                status, body = server.post("/oauth/token", {"client_id": CLIENT_ID, "code": code})

                self.assertEqual(status, 403)
                self.assertEqual(body, {"error": "invalid_code"})


if __name__ == "__main__":
    unittest.main()
