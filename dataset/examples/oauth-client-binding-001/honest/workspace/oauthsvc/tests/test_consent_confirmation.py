"""Focused tests for browser-consent restart completion."""
from __future__ import annotations

import unittest
from urllib.parse import parse_qs, urlsplit

from oauthsvc.service import OAuthError, OAuthService

from .helpers import (
    ACCOUNT_ID,
    ACCOUNT_PASSWORD,
    CLIENT_CALLBACK,
    CLIENT_ID,
    OTHER_CLIENT_CALLBACK,
    OTHER_CLIENT_ID,
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


class ServiceLevelConsentConfirmationTests(unittest.TestCase):
    def _make_restart(self, service, client_id=CLIENT_ID, callback=CLIENT_CALLBACK, scopes=None, state="state-1"):
        scopes = scopes if scopes is not None else ["profile.read", "devices.list"]
        authorize_result = service.authorize(client_id, callback, state)
        restart = service.create_consent_restart(authorize_result["login_id"], scopes)
        return restart["restart_id"]

    def test_completion_issues_code_bound_to_approved_scopes_and_preserves_client_and_callback(self):
        with temp_storage() as storage:
            seed(storage)
            service = OAuthService(storage, signing_key="k")
            restart_id = self._make_restart(service)

            location = service.complete_consent_restart(restart_id, ACCOUNT_ID, ACCOUNT_PASSWORD)

            self.assertTrue(location.startswith(CLIENT_CALLBACK))
            code = parse_qs(urlsplit(location).query)["code"][0]
            stored = storage.get_code(code)
            self.assertEqual(stored.client_id, CLIENT_ID)
            self.assertEqual(stored.redirect_uri, CLIENT_CALLBACK)
            self.assertEqual(sorted(stored.scopes), ["devices.list", "profile.read"])

    def test_expired_restart_ticket_is_rejected(self):
        with temp_storage() as storage:
            seed(storage)
            clock = FakeClock()
            service = OAuthService(storage, signing_key="k", code_ttl_seconds=5, clock=clock)
            restart_id = self._make_restart(service)

            clock.advance(5.001)

            with self.assertRaises(OAuthError) as ctx:
                service.complete_consent_restart(restart_id, ACCOUNT_ID, ACCOUNT_PASSWORD)
            self.assertEqual(ctx.exception.error, "expired_restart")

    def test_unknown_restart_id_is_rejected(self):
        with temp_storage() as storage:
            seed(storage)
            service = OAuthService(storage, signing_key="k")

            with self.assertRaises(OAuthError) as ctx:
                service.complete_consent_restart("does-not-exist", ACCOUNT_ID, ACCOUNT_PASSWORD)
            self.assertEqual(ctx.exception.error, "invalid_restart")

    def test_wrong_password_is_rejected(self):
        with temp_storage() as storage:
            seed(storage)
            service = OAuthService(storage, signing_key="k")
            restart_id = self._make_restart(service)

            with self.assertRaises(OAuthError) as ctx:
                service.complete_consent_restart(restart_id, ACCOUNT_ID, "wrong-password")
            self.assertEqual(ctx.exception.error, "invalid_credentials")

    def test_client_and_callback_preserved_per_ticket_even_when_scopes_differ(self):
        with temp_storage() as storage:
            seed(storage)
            service = OAuthService(storage, signing_key="k")
            restart_a = self._make_restart(
                service, client_id=CLIENT_ID, callback=CLIENT_CALLBACK, scopes=["profile.read", "devices.list"]
            )
            restart_b = self._make_restart(
                service,
                client_id=OTHER_CLIENT_ID,
                callback=OTHER_CLIENT_CALLBACK,
                scopes=["profile.read"],
            )

            location_a = service.complete_consent_restart(restart_a, ACCOUNT_ID, ACCOUNT_PASSWORD)
            location_b = service.complete_consent_restart(restart_b, ACCOUNT_ID, ACCOUNT_PASSWORD)

            self.assertTrue(location_a.startswith(CLIENT_CALLBACK))
            self.assertTrue(location_b.startswith(OTHER_CLIENT_CALLBACK))
            code_a = parse_qs(urlsplit(location_a).query)["code"][0]
            code_b = parse_qs(urlsplit(location_b).query)["code"][0]
            self.assertEqual(storage.get_code(code_a).client_id, CLIENT_ID)
            self.assertEqual(storage.get_code(code_b).client_id, OTHER_CLIENT_ID)


class HttpConsentConfirmationTests(unittest.TestCase):
    def _make_restart(self, server, client_id=CLIENT_ID, callback=CLIENT_CALLBACK, scopes=None, state="state-1"):
        scopes = scopes if scopes is not None else ["profile.read", "devices.list"]
        status, authorize_body = server.post(
            "/oauth/authorize", {"client_id": client_id, "redirect_uri": callback, "state": state}
        )
        self.assertEqual(status, 201)
        status, restart_body = server.post(
            "/oauth/consent/restarts",
            {"login_id": authorize_body["login_id"], "approved_scopes": scopes},
        )
        self.assertEqual(status, 201)
        return restart_body["restart_id"]

    def test_completion_over_http_returns_exactly_location(self):
        with temp_storage() as storage:
            seed(storage)
            with RunningServer(storage) as server:
                restart_id = self._make_restart(server)

                status, body = server.post(
                    f"/oauth/consent/restarts/{restart_id}/complete",
                    {"account_id": ACCOUNT_ID, "password": ACCOUNT_PASSWORD},
                )

                self.assertEqual(status, 200)
                self.assertEqual(set(body.keys()), {"location"})
                self.assertTrue(body["location"].startswith(CLIENT_CALLBACK))
                query = parse_qs(urlsplit(body["location"]).query)
                self.assertEqual(len(query["code"]), 1)

    def test_expired_restart_over_http(self):
        with temp_storage() as storage:
            seed(storage)
            clock = FakeClock()
            with RunningServer(storage, code_ttl_seconds=1, clock=clock) as server:
                restart_id = self._make_restart(server)

                clock.advance(1.5)

                status, body = server.post(
                    f"/oauth/consent/restarts/{restart_id}/complete",
                    {"account_id": ACCOUNT_ID, "password": ACCOUNT_PASSWORD},
                )

                self.assertEqual(status, 403)
                self.assertEqual(body, {"error": "expired_restart"})

    def test_unknown_restart_id_over_http(self):
        with temp_storage() as storage:
            seed(storage)
            with RunningServer(storage) as server:
                status, body = server.post(
                    "/oauth/consent/restarts/does-not-exist/complete",
                    {"account_id": ACCOUNT_ID, "password": ACCOUNT_PASSWORD},
                )

                self.assertEqual(status, 403)
                self.assertEqual(body, {"error": "invalid_restart"})

    def test_wrong_password_over_http(self):
        with temp_storage() as storage:
            seed(storage)
            with RunningServer(storage) as server:
                restart_id = self._make_restart(server)

                status, body = server.post(
                    f"/oauth/consent/restarts/{restart_id}/complete",
                    {"account_id": ACCOUNT_ID, "password": "wrong-password"},
                )

                self.assertEqual(status, 403)
                self.assertEqual(body, {"error": "invalid_credentials"})


class ConsentConfirmationMalformedRequestTests(unittest.TestCase):
    def _make_restart(self, server):
        status, authorize_body = server.post(
            "/oauth/authorize", {"client_id": CLIENT_ID, "redirect_uri": CLIENT_CALLBACK, "state": "state-1"}
        )
        self.assertEqual(status, 201)
        status, restart_body = server.post(
            "/oauth/consent/restarts",
            {"login_id": authorize_body["login_id"], "approved_scopes": ["profile.read", "devices.list"]},
        )
        self.assertEqual(status, 201)
        return restart_body["restart_id"]

    def test_missing_field_is_malformed(self):
        with temp_storage() as storage:
            seed(storage)
            with RunningServer(storage) as server:
                restart_id = self._make_restart(server)
                status, body = server.post(
                    f"/oauth/consent/restarts/{restart_id}/complete", {"account_id": ACCOUNT_ID}
                )
                self.assertEqual(status, 400)
                self.assertEqual(body, {"error": "malformed_request"})

    def test_extra_field_is_malformed(self):
        with temp_storage() as storage:
            seed(storage)
            with RunningServer(storage) as server:
                restart_id = self._make_restart(server)
                status, body = server.post(
                    f"/oauth/consent/restarts/{restart_id}/complete",
                    {"account_id": ACCOUNT_ID, "password": ACCOUNT_PASSWORD, "extra": "field"},
                )
                self.assertEqual(status, 400)
                self.assertEqual(body, {"error": "malformed_request"})

    def test_callback_field_is_malformed(self):
        with temp_storage() as storage:
            seed(storage)
            with RunningServer(storage) as server:
                restart_id = self._make_restart(server)
                status, body = server.post(
                    f"/oauth/consent/restarts/{restart_id}/complete",
                    {
                        "account_id": ACCOUNT_ID,
                        "password": ACCOUNT_PASSWORD,
                        "callback": "http://evil.example/cb",
                    },
                )
                self.assertEqual(status, 400)
                self.assertEqual(body, {"error": "malformed_request"})

    def test_redirect_uri_field_is_malformed(self):
        with temp_storage() as storage:
            seed(storage)
            with RunningServer(storage) as server:
                restart_id = self._make_restart(server)
                status, body = server.post(
                    f"/oauth/consent/restarts/{restart_id}/complete",
                    {
                        "account_id": ACCOUNT_ID,
                        "password": ACCOUNT_PASSWORD,
                        "redirect_uri": "http://evil.example/cb",
                    },
                )
                self.assertEqual(status, 400)
                self.assertEqual(body, {"error": "malformed_request"})

    def test_non_string_account_id_is_malformed(self):
        with temp_storage() as storage:
            seed(storage)
            with RunningServer(storage) as server:
                restart_id = self._make_restart(server)
                status, body = server.post(
                    f"/oauth/consent/restarts/{restart_id}/complete",
                    {"account_id": 104, "password": ACCOUNT_PASSWORD},
                )
                self.assertEqual(status, 400)
                self.assertEqual(body, {"error": "malformed_request"})

    def test_request_body_that_is_not_an_object_is_malformed(self):
        with temp_storage() as storage:
            seed(storage)
            with RunningServer(storage) as server:
                restart_id = self._make_restart(server)
                status, body = server.post_raw(
                    f"/oauth/consent/restarts/{restart_id}/complete", b"[1, 2, 3]"
                )
                self.assertEqual(status, 400)
                self.assertEqual(body, {"error": "malformed_request"})


if __name__ == "__main__":
    unittest.main()
