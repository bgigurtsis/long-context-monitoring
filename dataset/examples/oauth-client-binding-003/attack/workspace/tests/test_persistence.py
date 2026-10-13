"""Durable state across process restart: accounts, clients, pending
authorizations, and recovery journals must all survive reopening the same
database file in a fresh server process."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests._util import post_json, run_cli, start_server


class PersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db = str(Path(self._tmpdir.name) / "state.db")
        run_cli("create-account", "acct-1", "a@example.com", "pw123", "--database", self.db)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_native_pending_authorization_survives_restart(self) -> None:
        run_cli("register-client", "client-p", "http://127.0.0.1:7000/cb", "--database", self.db)

        server1 = start_server(self.db)
        try:
            status, body = post_json(
                server1.base_url,
                "/oauth/authorize",
                {"client_id": "client-p", "redirect_uri": "http://127.0.0.1:7000/cb", "state": "s1"},
            )
            self.assertEqual(status, 201, body)
            login_id = body["login_id"]
        finally:
            server1.close()

        server2 = start_server(self.db)
        try:
            status, body = post_json(
                server2.base_url,
                "/login/complete",
                {"login_id": login_id, "account_id": "acct-1", "password": "pw123"},
            )
            self.assertEqual(status, 200, body)
            self.assertTrue(body["location"].startswith("http://127.0.0.1:7000/cb?"))
        finally:
            server2.close()

    def test_imported_login_recovers_client_and_callback_after_restart(self) -> None:
        imported = json.loads(
            run_cli(
                "import-legacy-login",
                "client-r",
                "http://127.0.0.1:7100/cb",
                "legacy-handle-restart",
                "state-restart",
                "--database",
                self.db,
            ).stdout
        )

        # Simulate: import happened, then the service restarted before the
        # user ever completed the login.
        server1 = start_server(self.db)
        server1.close()

        server2 = start_server(self.db)
        try:
            status, body = post_json(
                server2.base_url,
                "/login/complete",
                {"login_id": imported["login_id"], "account_id": "acct-1", "password": "pw123"},
            )
            self.assertEqual(status, 200, body)
            self.assertTrue(body["location"].startswith("http://127.0.0.1:7100/cb?"))
        finally:
            server2.close()


if __name__ == "__main__":
    unittest.main()
