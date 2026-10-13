"""Callback / redirect-URI validation and the four /login/complete rejection
reasons: invalid_login, invalid_continuation, invalid_authorization, and
invalid_credentials."""
from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from tests._util import post_json, run_cli, start_server


class CallbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db = str(Path(self._tmpdir.name) / "state.db")
        run_cli("create-account", "acct-1", "a@example.com", "pw123", "--database", self.db)
        run_cli("register-client", "client-a", "http://127.0.0.1:9999/cb", "--database", self.db)
        self.server = start_server(self.db)

    def tearDown(self) -> None:
        self.server.close()
        self._tmpdir.cleanup()

    def test_unregistered_client_rejected(self) -> None:
        status, body = post_json(
            self.server.base_url,
            "/oauth/authorize",
            {"client_id": "no-such-client", "redirect_uri": "http://127.0.0.1:9999/cb", "state": "s"},
        )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "unregistered_callback"})

    def test_mismatched_redirect_uri_rejected(self) -> None:
        status, body = post_json(
            self.server.base_url,
            "/oauth/authorize",
            {"client_id": "client-a", "redirect_uri": "http://127.0.0.1:9999/wrong", "state": "s"},
        )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "unregistered_callback"})

    def test_malformed_authorize_request(self) -> None:
        status, body = post_json(
            self.server.base_url,
            "/oauth/authorize",
            {"client_id": "client-a", "redirect_uri": "http://127.0.0.1:9999/cb"},
        )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

        status, body = post_json(
            self.server.base_url,
            "/oauth/authorize",
            {
                "client_id": "client-a",
                "redirect_uri": "http://127.0.0.1:9999/cb",
                "state": "s",
                "extra": "nope",
            },
        )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

        status, body = post_json(
            self.server.base_url,
            "/oauth/authorize",
            {"client_id": "client-a", "redirect_uri": "http://127.0.0.1:9999/cb", "state": 123},
        )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

    def test_unknown_login_id_rejected(self) -> None:
        status, body = post_json(
            self.server.base_url,
            "/login/complete",
            {"login_id": "does-not-exist", "account_id": "acct-1", "password": "pw123"},
        )
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "invalid_login"})

    def test_wrong_credentials_rejected(self) -> None:
        _, authorize_body = post_json(
            self.server.base_url,
            "/oauth/authorize",
            {"client_id": "client-a", "redirect_uri": "http://127.0.0.1:9999/cb", "state": "s"},
        )
        login_id = authorize_body["login_id"]

        status, body = post_json(
            self.server.base_url,
            "/login/complete",
            {"login_id": login_id, "account_id": "acct-1", "password": "wrong-password"},
        )
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "invalid_credentials"})

        status, body = post_json(
            self.server.base_url,
            "/login/complete",
            {"login_id": login_id, "account_id": "no-such-account", "password": "pw123"},
        )
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "invalid_credentials"})

    def test_completed_login_cannot_be_completed_again(self) -> None:
        _, authorize_body = post_json(
            self.server.base_url,
            "/oauth/authorize",
            {"client_id": "client-a", "redirect_uri": "http://127.0.0.1:9999/cb", "state": "s"},
        )
        login_id = authorize_body["login_id"]

        status, _ = post_json(
            self.server.base_url,
            "/login/complete",
            {"login_id": login_id, "account_id": "acct-1", "password": "pw123"},
        )
        self.assertEqual(status, 200)

        status, body = post_json(
            self.server.base_url,
            "/login/complete",
            {"login_id": login_id, "account_id": "acct-1", "password": "pw123"},
        )
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "invalid_authorization"})

    def test_broken_continuation_rejected(self) -> None:
        imported = json.loads(
            run_cli(
                "import-legacy-login",
                "client-broken",
                "http://127.0.0.1:6000/cb",
                "handle-broken",
                "state-broken",
                "--database",
                self.db,
            ).stdout
        )

        # Corrupt the durable client registration the recovery journal
        # depends on, simulating a callback that can no longer be resolved.
        conn = sqlite3.connect(self.db)
        with conn:
            conn.execute("DELETE FROM clients WHERE client_id = ?", ("client-broken",))
        conn.close()

        status, body = post_json(
            self.server.base_url,
            "/login/complete",
            {"login_id": imported["login_id"], "account_id": "acct-1", "password": "pw123"},
        )
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "invalid_continuation"})


if __name__ == "__main__":
    unittest.main()
