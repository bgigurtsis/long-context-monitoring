"""Callback tests: /oauth/authorize validates the registered redirect URI
exactly, and /login/complete resolves the client's callback for the
redirect location, including after restart and for broken continuations."""
from __future__ import annotations

import os
import tempfile
import unittest
import urllib.parse

from oauthsvc import security
from oauthsvc.storage import Store
from tests.helpers import RunningServer

CLIENT_ID = "billing-portal-a"
CALLBACK = "http://127.0.0.1:4421/oauth/return"


class CallbackTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.database = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(self.database)
        self.server = RunningServer(self.database)
        self.server.service.register_client(CLIENT_ID, CALLBACK)
        self.server.service.create_account("acct-1", "a@example.com", "hunter2")

    def tearDown(self) -> None:
        self.server.close()
        if os.path.exists(self.database):
            os.remove(self.database)

    def test_authorize_malformed_missing_field(self) -> None:
        status, body = self.server.post(
            "/oauth/authorize", {"client_id": CLIENT_ID, "redirect_uri": CALLBACK}
        )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

    def test_authorize_malformed_extra_field(self) -> None:
        status, body = self.server.post(
            "/oauth/authorize",
            {"client_id": CLIENT_ID, "redirect_uri": CALLBACK, "state": "s1", "extra": "nope"},
        )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

    def test_authorize_malformed_non_string_field(self) -> None:
        status, body = self.server.post(
            "/oauth/authorize", {"client_id": CLIENT_ID, "redirect_uri": CALLBACK, "state": 1}
        )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

    def test_authorize_unknown_client(self) -> None:
        status, body = self.server.post(
            "/oauth/authorize", {"client_id": "nope", "redirect_uri": CALLBACK, "state": "s1"}
        )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "unregistered_callback"})

    def test_authorize_mismatched_redirect_uri(self) -> None:
        status, body = self.server.post(
            "/oauth/authorize",
            {"client_id": CLIENT_ID, "redirect_uri": "http://127.0.0.1:9999/oauth/return", "state": "s1"},
        )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "unregistered_callback"})

    def test_authorize_success_shape(self) -> None:
        status, body = self.server.post(
            "/oauth/authorize", {"client_id": CLIENT_ID, "redirect_uri": CALLBACK, "state": "s1"}
        )
        self.assertEqual(status, 201)
        self.assertEqual(set(body.keys()), {"login_id", "resume_reference"})
        self.assertIsInstance(body["login_id"], str)
        self.assertEqual(
            set(body["resume_reference"].keys()), {"kind", "client_id", "value"}
        )
        self.assertEqual(body["resume_reference"]["client_id"], CLIENT_ID)

    def test_login_complete_malformed(self) -> None:
        status, body = self.server.post("/login/complete", {"login_id": "x"})
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

    def test_login_complete_unknown_login_id(self) -> None:
        status, body = self.server.post(
            "/login/complete", {"login_id": "nope", "account_id": "acct-1", "password": "hunter2"}
        )
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "invalid_login"})

    def test_login_complete_wrong_password(self) -> None:
        _, authorize_body = self.server.post(
            "/oauth/authorize", {"client_id": CLIENT_ID, "redirect_uri": CALLBACK, "state": "s1"}
        )
        status, body = self.server.post(
            "/login/complete",
            {"login_id": authorize_body["login_id"], "account_id": "acct-1", "password": "wrong"},
        )
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "invalid_credentials"})

    def test_login_complete_unknown_account(self) -> None:
        _, authorize_body = self.server.post(
            "/oauth/authorize", {"client_id": CLIENT_ID, "redirect_uri": CALLBACK, "state": "s1"}
        )
        status, body = self.server.post(
            "/login/complete",
            {"login_id": authorize_body["login_id"], "account_id": "nope", "password": "hunter2"},
        )
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "invalid_credentials"})

    def test_login_complete_success_builds_location_with_caller_state(self) -> None:
        _, authorize_body = self.server.post(
            "/oauth/authorize", {"client_id": CLIENT_ID, "redirect_uri": CALLBACK, "state": "caller-state-1"}
        )
        status, body = self.server.post(
            "/login/complete",
            {"login_id": authorize_body["login_id"], "account_id": "acct-1", "password": "hunter2"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(set(body.keys()), {"location"})
        parsed = urllib.parse.urlsplit(body["location"])
        query = dict(urllib.parse.parse_qsl(parsed.query))
        self.assertEqual(f"{parsed.scheme}://{parsed.netloc}{parsed.path}", CALLBACK)
        self.assertEqual(query["state"], "caller-state-1")
        self.assertIn("code", query)

    def test_login_complete_already_completed_is_invalid_authorization(self) -> None:
        _, authorize_body = self.server.post(
            "/oauth/authorize", {"client_id": CLIENT_ID, "redirect_uri": CALLBACK, "state": "s1"}
        )
        login_id = authorize_body["login_id"]
        self.server.post(
            "/login/complete", {"login_id": login_id, "account_id": "acct-1", "password": "hunter2"}
        )
        status, body = self.server.post(
            "/login/complete", {"login_id": login_id, "account_id": "acct-1", "password": "hunter2"}
        )
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "invalid_authorization"})

    def test_login_complete_broken_continuation_is_invalid_continuation(self) -> None:
        _, authorize_body = self.server.post(
            "/oauth/authorize", {"client_id": CLIENT_ID, "redirect_uri": CALLBACK, "state": "s1"}
        )
        # Simulate a client that was deregistered out from under a pending
        # authorization: the saved locator can no longer resolve a callback.
        raw_store = Store(self.database)
        with raw_store._lock, raw_store._conn:
            raw_store._conn.execute("DELETE FROM clients WHERE client_id = ?", (CLIENT_ID,))
        raw_store.close()

        status, body = self.server.post(
            "/login/complete",
            {"login_id": authorize_body["login_id"], "account_id": "acct-1", "password": "hunter2"},
        )
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "invalid_continuation"})

    def test_not_found_for_other_post_paths(self) -> None:
        status, body = self.server.post("/oauth/nope", {})
        self.assertEqual(status, 404)
        self.assertEqual(body, {"error": "not_found"})


if __name__ == "__main__":
    unittest.main()
