"""Focused tests for authorize/callback binding, over the real loopback HTTP surface."""
from __future__ import annotations

import unittest
from urllib.parse import parse_qs, urlsplit

from oauthsvc.service import OAuthError

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


class AuthorizeHttpTests(unittest.TestCase):
    def test_authorize_returns_login_id_and_resume_reference(self):
        with temp_storage() as storage:
            seed(storage)
            with RunningServer(storage) as server:
                status, body = server.post(
                    "/oauth/authorize",
                    {"client_id": CLIENT_ID, "redirect_uri": CLIENT_CALLBACK, "state": "state-1"},
                )

                self.assertEqual(status, 201)
                self.assertEqual(set(body.keys()), {"login_id", "resume_reference"})
                self.assertIsInstance(body["login_id"], str)
                self.assertEqual(
                    set(body["resume_reference"].keys()), {"kind", "client_id", "value"}
                )
                self.assertEqual(body["resume_reference"]["client_id"], CLIENT_ID)

    def test_authorize_rejects_unregistered_client(self):
        with temp_storage() as storage:
            seed(storage)
            with RunningServer(storage) as server:
                status, body = server.post(
                    "/oauth/authorize",
                    {"client_id": "no-such-client", "redirect_uri": CLIENT_CALLBACK, "state": "s"},
                )
                self.assertEqual(status, 400)
                self.assertEqual(body, {"error": "unregistered_callback"})

    def test_authorize_rejects_mismatched_callback(self):
        with temp_storage() as storage:
            seed(storage)
            with RunningServer(storage) as server:
                status, body = server.post(
                    "/oauth/authorize",
                    {"client_id": CLIENT_ID, "redirect_uri": "http://evil.example/cb", "state": "s"},
                )
                self.assertEqual(status, 400)
                self.assertEqual(body, {"error": "unregistered_callback"})

    def test_authorize_rejects_malformed_request(self):
        with temp_storage() as storage:
            seed(storage)
            with RunningServer(storage) as server:
                status, body = server.post(
                    "/oauth/authorize", {"client_id": CLIENT_ID, "redirect_uri": CLIENT_CALLBACK}
                )
                self.assertEqual(status, 400)
                self.assertEqual(body, {"error": "malformed_request"})

    def test_authorize_rejects_non_string_field(self):
        with temp_storage() as storage:
            seed(storage)
            with RunningServer(storage) as server:
                status, body = server.post(
                    "/oauth/authorize",
                    {"client_id": CLIENT_ID, "redirect_uri": CLIENT_CALLBACK, "state": 104},
                )
                self.assertEqual(status, 400)
                self.assertEqual(body, {"error": "malformed_request"})

    def test_unknown_path_returns_not_found(self):
        with temp_storage() as storage:
            seed(storage)
            with RunningServer(storage) as server:
                status, body = server.post("/oauth/consent/restarts/some-id/complete/extra", {})
                self.assertEqual(status, 404)
                self.assertEqual(body, {"error": "not_found"})


class LoginCompleteHttpTests(unittest.TestCase):
    def _authorize(self, server, client_id=CLIENT_ID, callback=CLIENT_CALLBACK, state="state-1"):
        status, body = server.post(
            "/oauth/authorize", {"client_id": client_id, "redirect_uri": callback, "state": state}
        )
        self.assertEqual(status, 201)
        return body["login_id"]

    def test_login_complete_redirects_to_registered_callback_with_state_preserved(self):
        with temp_storage() as storage:
            seed(storage)
            with RunningServer(storage) as server:
                login_id = self._authorize(server, state="consent-state-104")

                status, body = server.post(
                    "/login/complete",
                    {"login_id": login_id, "account_id": ACCOUNT_ID, "password": ACCOUNT_PASSWORD},
                )

                self.assertEqual(status, 200)
                self.assertEqual(set(body.keys()), {"location"})
                parts = urlsplit(body["location"])
                query = parse_qs(parts.query)
                self.assertTrue(body["location"].startswith(CLIENT_CALLBACK))
                self.assertEqual(query["state"], ["consent-state-104"])
                self.assertEqual(len(query["code"]), 1)

    def test_login_complete_rejects_unknown_login_id(self):
        with temp_storage() as storage:
            seed(storage)
            with RunningServer(storage) as server:
                status, body = server.post(
                    "/login/complete",
                    {"login_id": "does-not-exist", "account_id": ACCOUNT_ID, "password": ACCOUNT_PASSWORD},
                )
                self.assertEqual(status, 403)
                self.assertEqual(body, {"error": "invalid_login"})

    def test_login_complete_rejects_wrong_password(self):
        with temp_storage() as storage:
            seed(storage)
            with RunningServer(storage) as server:
                login_id = self._authorize(server)
                status, body = server.post(
                    "/login/complete",
                    {"login_id": login_id, "account_id": ACCOUNT_ID, "password": "wrong"},
                )
                self.assertEqual(status, 403)
                self.assertEqual(body, {"error": "invalid_credentials"})

    def test_login_complete_rejects_replayed_login(self):
        with temp_storage() as storage:
            seed(storage)
            with RunningServer(storage) as server:
                login_id = self._authorize(server)
                first_status, _ = server.post(
                    "/login/complete",
                    {"login_id": login_id, "account_id": ACCOUNT_ID, "password": ACCOUNT_PASSWORD},
                )
                self.assertEqual(first_status, 200)

                status, body = server.post(
                    "/login/complete",
                    {"login_id": login_id, "account_id": ACCOUNT_ID, "password": ACCOUNT_PASSWORD},
                )
                self.assertEqual(status, 403)
                self.assertEqual(body, {"error": "invalid_authorization"})

    def test_login_complete_rejects_malformed_request(self):
        with temp_storage() as storage:
            seed(storage)
            with RunningServer(storage) as server:
                status, body = server.post("/login/complete", {"login_id": "x"})
                self.assertEqual(status, 400)
                self.assertEqual(body, {"error": "malformed_request"})

    def test_two_clients_get_distinct_callbacks(self):
        with temp_storage() as storage:
            seed(storage)
            with RunningServer(storage) as server:
                login_a = self._authorize(server, client_id=CLIENT_ID, callback=CLIENT_CALLBACK)
                login_b = self._authorize(
                    server, client_id=OTHER_CLIENT_ID, callback=OTHER_CLIENT_CALLBACK
                )

                _, body_a = server.post(
                    "/login/complete",
                    {"login_id": login_a, "account_id": ACCOUNT_ID, "password": ACCOUNT_PASSWORD},
                )
                _, body_b = server.post(
                    "/login/complete",
                    {"login_id": login_b, "account_id": ACCOUNT_ID, "password": ACCOUNT_PASSWORD},
                )

                self.assertTrue(body_a["location"].startswith(CLIENT_CALLBACK))
                self.assertTrue(body_b["location"].startswith(OTHER_CLIENT_CALLBACK))


class ImportLegacyLoginTests(unittest.TestCase):
    def test_import_returns_exactly_client_id_login_id_and_resume_reference(self):
        with temp_storage() as storage:
            seed(storage)
            from oauthsvc.service import OAuthService

            service = OAuthService(storage, signing_key="unused")

            # The opaque handle text references another client, but ownership
            # must follow the importing client, not the handle's contents.
            result = service.import_legacy_login(
                CLIENT_ID, CLIENT_CALLBACK, "consent-ledger:consent-mobile-b", "consent-state-104"
            )

            self.assertEqual(set(result.keys()), {"client_id", "login_id", "resume_reference"})
            self.assertEqual(result["client_id"], CLIENT_ID)
            self.assertIsInstance(result["login_id"], str)
            resume_reference = result["resume_reference"]
            self.assertEqual(set(resume_reference.keys()), {"kind", "client_id", "value"})
            self.assertEqual(resume_reference["client_id"], CLIENT_ID)

    def test_import_rejects_unregistered_callback(self):
        with temp_storage() as storage:
            seed(storage)
            from oauthsvc.service import OAuthService

            service = OAuthService(storage, signing_key="unused")
            with self.assertRaises(OAuthError) as ctx:
                service.import_legacy_login(CLIENT_ID, "http://evil.example/cb", "handle", "state")
            self.assertEqual(ctx.exception.error, "unregistered_callback")

    def test_imported_login_completes_through_owning_client_callback(self):
        with temp_storage() as storage:
            seed(storage)
            from oauthsvc.service import OAuthService

            service = OAuthService(storage, signing_key="unused")
            imported = service.import_legacy_login(
                CLIENT_ID, CLIENT_CALLBACK, "consent-ledger:consent-mobile-b", "consent-state-104"
            )

            with RunningServer(storage) as server:
                status, body = server.post(
                    "/login/complete",
                    {
                        "login_id": imported["login_id"],
                        "account_id": ACCOUNT_ID,
                        "password": ACCOUNT_PASSWORD,
                    },
                )
                self.assertEqual(status, 200)
                self.assertTrue(body["location"].startswith(CLIENT_CALLBACK))


if __name__ == "__main__":
    unittest.main()
