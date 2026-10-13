"""Focused tests for durable browser-consent restart tickets."""
from __future__ import annotations

import os
import unittest

from oauthsvc import resume
from oauthsvc.service import OAuthError, OAuthService
from oauthsvc.storage import Storage

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


class ConsentRestartHttpTests(unittest.TestCase):
    def _authorize(self, server, client_id=CLIENT_ID, callback=CLIENT_CALLBACK, state="state-1"):
        status, body = server.post(
            "/oauth/authorize", {"client_id": client_id, "redirect_uri": callback, "state": state}
        )
        self.assertEqual(status, 201)
        return body["login_id"]

    def test_restart_returns_exactly_restart_id_and_pending_client_id(self):
        with temp_storage() as storage:
            seed(storage)
            with RunningServer(storage) as server:
                login_id = self._authorize(server)

                status, body = server.post(
                    "/oauth/consent/restarts",
                    {"login_id": login_id, "approved_scopes": ["profile.read", "devices.list"]},
                )

                self.assertEqual(status, 201)
                self.assertEqual(set(body.keys()), {"restart_id", "pending_client_id"})
                self.assertIsInstance(body["restart_id"], str)
                self.assertEqual(body["pending_client_id"], CLIENT_ID)

    def test_restart_names_authoritative_owner_per_client(self):
        with temp_storage() as storage:
            seed(storage)
            with RunningServer(storage) as server:
                login_a = self._authorize(server, client_id=CLIENT_ID, callback=CLIENT_CALLBACK)
                login_b = self._authorize(
                    server, client_id=OTHER_CLIENT_ID, callback=OTHER_CLIENT_CALLBACK
                )

                _, body_a = server.post(
                    "/oauth/consent/restarts", {"login_id": login_a, "approved_scopes": ["profile.read"]}
                )
                _, body_b = server.post(
                    "/oauth/consent/restarts", {"login_id": login_b, "approved_scopes": ["profile.read"]}
                )

                self.assertEqual(body_a["pending_client_id"], CLIENT_ID)
                self.assertEqual(body_b["pending_client_id"], OTHER_CLIENT_ID)
                self.assertNotEqual(body_a["restart_id"], body_b["restart_id"])

    def test_restart_rejects_unknown_login_id(self):
        with temp_storage() as storage:
            seed(storage)
            with RunningServer(storage) as server:
                status, body = server.post(
                    "/oauth/consent/restarts",
                    {"login_id": "does-not-exist", "approved_scopes": ["profile.read"]},
                )
                self.assertEqual(status, 403)
                self.assertEqual(body, {"error": "invalid_login"})

    def test_restart_rejects_already_completed_login(self):
        with temp_storage() as storage:
            seed(storage)
            with RunningServer(storage) as server:
                login_id = self._authorize(server)
                status, _ = server.post(
                    "/login/complete",
                    {"login_id": login_id, "account_id": ACCOUNT_ID, "password": ACCOUNT_PASSWORD},
                )
                self.assertEqual(status, 200)

                status, body = server.post(
                    "/oauth/consent/restarts",
                    {"login_id": login_id, "approved_scopes": ["profile.read"]},
                )
                self.assertEqual(status, 403)
                self.assertEqual(body, {"error": "invalid_authorization"})

    def test_restart_does_not_expose_stored_credentials(self):
        with temp_storage() as storage:
            seed(storage)
            with RunningServer(storage) as server:
                login_id = self._authorize(server)
                _, body = server.post(
                    "/oauth/consent/restarts", {"login_id": login_id, "approved_scopes": ["profile.read"]}
                )
                serialized = str(body)
                self.assertNotIn(ACCOUNT_PASSWORD, serialized)
                self.assertNotIn("password", serialized)
                self.assertNotIn("browser_handle", serialized)
                self.assertNotIn("account_id", serialized)


class ConsentRestartMalformedRequestTests(unittest.TestCase):
    def test_missing_field_is_malformed(self):
        with temp_storage() as storage:
            seed(storage)
            with RunningServer(storage) as server:
                status, body = server.post("/oauth/consent/restarts", {"login_id": "x"})
                self.assertEqual(status, 400)
                self.assertEqual(body, {"error": "malformed_request"})

    def test_extra_field_is_malformed(self):
        with temp_storage() as storage:
            seed(storage)
            with RunningServer(storage) as server:
                status, body = server.post(
                    "/oauth/consent/restarts",
                    {"login_id": "x", "approved_scopes": ["a"], "state": "extra"},
                )
                self.assertEqual(status, 400)
                self.assertEqual(body, {"error": "malformed_request"})

    def test_non_string_login_id_is_malformed(self):
        with temp_storage() as storage:
            seed(storage)
            with RunningServer(storage) as server:
                status, body = server.post(
                    "/oauth/consent/restarts", {"login_id": 104, "approved_scopes": ["a"]}
                )
                self.assertEqual(status, 400)
                self.assertEqual(body, {"error": "malformed_request"})

    def test_non_list_approved_scopes_is_malformed(self):
        with temp_storage() as storage:
            seed(storage)
            with RunningServer(storage) as server:
                status, body = server.post(
                    "/oauth/consent/restarts", {"login_id": "x", "approved_scopes": "profile.read"}
                )
                self.assertEqual(status, 400)
                self.assertEqual(body, {"error": "malformed_request"})

    def test_approved_scopes_with_non_string_item_is_malformed(self):
        with temp_storage() as storage:
            seed(storage)
            with RunningServer(storage) as server:
                status, body = server.post(
                    "/oauth/consent/restarts", {"login_id": "x", "approved_scopes": ["profile.read", 1]}
                )
                self.assertEqual(status, 400)
                self.assertEqual(body, {"error": "malformed_request"})

    def test_request_body_that_is_not_an_object_is_malformed(self):
        with temp_storage() as storage:
            seed(storage)
            with RunningServer(storage) as server:
                status, body = server.post_raw("/oauth/consent/restarts", b"[1, 2, 3]")
                self.assertEqual(status, 400)
                self.assertEqual(body, {"error": "malformed_request"})


class ConsentRestartPersistenceTests(unittest.TestCase):
    def test_restart_ticket_stores_exact_callback_scopes_state_and_expiry(self):
        with temp_storage() as storage:
            seed(storage)
            service = OAuthService(storage, signing_key="k", code_ttl_seconds=42)

            authorize_result = service.authorize(CLIENT_ID, CLIENT_CALLBACK, "consent-state-104")
            login_id = authorize_result["login_id"]

            result = service.create_consent_restart(login_id, ["profile.read", "devices.list"])

            restart = storage.get_consent_restart(result["restart_id"])
            self.assertIsNotNone(restart)
            self.assertEqual(restart.login_id, login_id)
            self.assertEqual(restart.client_id, CLIENT_ID)
            self.assertIsNone(restart.account_id)
            self.assertEqual(restart.redirect_uri, CLIENT_CALLBACK)
            self.assertEqual(restart.approved_scopes, ["profile.read", "devices.list"])
            self.assertEqual(restart.state, "consent-state-104")
            self.assertTrue(restart.browser_handle)
            self.assertEqual(restart.locator, resume.encode_continuation_locator(restart.browser_handle, CLIENT_ID))
            self.assertGreater(restart.expires_at, 0)

    def test_restart_ticket_survives_a_fresh_storage_handle(self):
        fd, path = __import__("tempfile").mkstemp(suffix=".db")
        os.close(fd)
        os.remove(path)
        try:
            storage = Storage(path)
            seed(storage)
            service = OAuthService(storage, signing_key="k")
            authorize_result = service.authorize(CLIENT_ID, CLIENT_CALLBACK, "state-1")
            result = service.create_consent_restart(authorize_result["login_id"], ["profile.read"])
            storage.close()

            reopened = Storage(path)
            try:
                restart = reopened.get_consent_restart(result["restart_id"])
                self.assertIsNotNone(restart)
                self.assertEqual(restart.client_id, CLIENT_ID)
                self.assertEqual(restart.redirect_uri, CLIENT_CALLBACK)
                self.assertEqual(restart.approved_scopes, ["profile.read"])
            finally:
                reopened.close()
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_repeated_restarts_for_same_login_each_persist_independently(self):
        with temp_storage() as storage:
            seed(storage)
            service = OAuthService(storage, signing_key="k")
            authorize_result = service.authorize(CLIENT_ID, CLIENT_CALLBACK, "state-1")
            login_id = authorize_result["login_id"]

            first = service.create_consent_restart(login_id, ["profile.read"])
            second = service.create_consent_restart(login_id, ["devices.list"])

            self.assertNotEqual(first["restart_id"], second["restart_id"])
            first_restart = storage.get_consent_restart(first["restart_id"])
            second_restart = storage.get_consent_restart(second["restart_id"])
            self.assertNotEqual(first_restart.browser_handle, second_restart.browser_handle)
            self.assertEqual(first_restart.approved_scopes, ["profile.read"])
            self.assertEqual(second_restart.approved_scopes, ["devices.list"])


class ConsentRestartDuplicateHandleTests(unittest.TestCase):
    def test_duplicate_handle_text_stays_bound_to_its_own_client(self):
        with temp_storage() as storage:
            seed(storage)
            storage.create_pending_authorization(
                "login-a", CLIENT_ID, CLIENT_CALLBACK, "state-a", source="native", created_at=0.0
            )
            storage.create_pending_authorization(
                "login-b", OTHER_CLIENT_ID, OTHER_CLIENT_CALLBACK, "state-b", source="native", created_at=0.0
            )

            shared_handle = "consent-ledger:shared-handle"
            locator_a = resume.encode_continuation_locator(shared_handle, CLIENT_ID)
            locator_b = resume.encode_continuation_locator(shared_handle, OTHER_CLIENT_ID)

            storage.create_consent_restart(
                restart_id="restart-a",
                login_id="login-a",
                client_id=CLIENT_ID,
                redirect_uri=CLIENT_CALLBACK,
                approved_scopes=["profile.read"],
                state="state-a",
                browser_handle=shared_handle,
                locator=locator_a,
                created_at=0.0,
                expires_at=100.0,
            )
            storage.create_consent_restart(
                restart_id="restart-b",
                login_id="login-b",
                client_id=OTHER_CLIENT_ID,
                redirect_uri=OTHER_CLIENT_CALLBACK,
                approved_scopes=["devices.list"],
                state="state-b",
                browser_handle=shared_handle,
                locator=locator_b,
                created_at=0.0,
                expires_at=100.0,
            )

            restart_a = storage.get_consent_restart("restart-a")
            restart_b = storage.get_consent_restart("restart-b")

            self.assertEqual(restart_a.browser_handle, restart_b.browser_handle)
            self.assertEqual(restart_a.client_id, CLIENT_ID)
            self.assertEqual(restart_b.client_id, OTHER_CLIENT_ID)
            self.assertEqual(restart_a.redirect_uri, CLIENT_CALLBACK)
            self.assertEqual(restart_b.redirect_uri, OTHER_CLIENT_CALLBACK)


class ConsentRestartExactCallbackTests(unittest.TestCase):
    def test_restart_uses_pending_authorization_callback_not_a_recomputed_one(self):
        with temp_storage() as storage:
            seed(storage)
            service = OAuthService(storage, signing_key="k")
            authorize_result = service.authorize(CLIENT_ID, CLIENT_CALLBACK, "state-1")

            result = service.create_consent_restart(authorize_result["login_id"], ["profile.read"])
            restart = storage.get_consent_restart(result["restart_id"])

            self.assertEqual(restart.redirect_uri, CLIENT_CALLBACK)
            self.assertNotEqual(restart.redirect_uri, OTHER_CLIENT_CALLBACK)

    def test_restart_rejected_when_registered_callback_no_longer_matches_pending(self):
        with temp_storage() as storage:
            seed(storage)
            service = OAuthService(storage, signing_key="k")
            authorize_result = service.authorize(CLIENT_ID, CLIENT_CALLBACK, "state-1")

            with storage._lock, storage._conn:
                storage._conn.execute(
                    "UPDATE clients SET redirect_uri = ? WHERE client_id = ?",
                    ("http://127.0.0.1:9999/moved", CLIENT_ID),
                )

            with self.assertRaises(OAuthError) as ctx:
                service.create_consent_restart(authorize_result["login_id"], ["profile.read"])
            self.assertEqual(ctx.exception.error, "invalid_authorization")


if __name__ == "__main__":
    unittest.main()
