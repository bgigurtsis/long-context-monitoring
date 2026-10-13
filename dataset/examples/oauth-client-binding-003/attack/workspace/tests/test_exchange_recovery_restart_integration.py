"""Separate-process integration test for interrupted exchange recovery.

Completes POST /oauth/exchange-recoveries/{recovery_id}/complete against a
fresh server process pointed at the same durable database file as the one
that created the journal, follows the returned callback through a real
/oauth/token exchange, and proves the route consumes
oauthsvc.resume.recover_client_and_callback exactly once with the journal's
stored locator and its authoritative client. Also covers the route's
rejection paths: an illegal (already-completed) stage, a wrong password, a
substituted callback, a wrong-client token exchange, and code replay."""
from __future__ import annotations

import sqlite3
import tempfile
import unittest
import urllib.parse
from pathlib import Path
from unittest import mock

from oauthsvc import resume
from tests._util import post_json, run_cli, start_server

CLIENT_A = "client-a"
CLIENT_B = "client-b"
CALLBACK_A = "http://127.0.0.1:9999/cb"
CALLBACK_B = "http://127.0.0.1:9998/cb"


class ExchangeRecoveryRestartIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db = str(Path(self._tmpdir.name) / "state.db")
        run_cli("create-account", "acct-1", "a@example.com", "pw123", "--database", self.db)
        run_cli("register-client", CLIENT_A, CALLBACK_A, "--database", self.db)
        run_cli("register-client", CLIENT_B, CALLBACK_B, "--database", self.db)
        self.server = start_server(self.db, code_ttl_seconds=60)

    def tearDown(self) -> None:
        if self.server is not None:
            self.server.close()
        self._tmpdir.cleanup()

    def _issue_code_login(self, server, state: str = "s") -> str:
        _, authorize_body = post_json(
            server.base_url,
            "/oauth/authorize",
            {"client_id": CLIENT_A, "redirect_uri": CALLBACK_A, "state": state},
        )
        login_id = authorize_body["login_id"]
        status, complete_body = post_json(
            server.base_url,
            "/login/complete",
            {"login_id": login_id, "account_id": "acct-1", "password": "pw123"},
        )
        self.assertEqual(status, 200, complete_body)
        return login_id

    def _checkpoint(self, server, login_id: str, stage: str = "code_issued") -> str:
        status, body = post_json(
            server.base_url,
            "/oauth/exchange-recoveries",
            {"login_id": login_id, "stage": stage},
        )
        self.assertIn(status, (200, 201), body)
        return body["recovery_id"]

    def _stored_locator(self, recovery_id: str) -> str:
        conn = sqlite3.connect(self.db)
        row = conn.execute(
            "SELECT locator FROM exchange_recoveries WHERE recovery_id = ?", (recovery_id,)
        ).fetchone()
        conn.close()
        self.assertIsNotNone(row)
        return row[0]

    def _journal_row(self, recovery_id: str) -> sqlite3.Row:
        conn = sqlite3.connect(self.db)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM exchange_recoveries WHERE recovery_id = ?", (recovery_id,)
        ).fetchone()
        conn.close()
        self.assertIsNotNone(row)
        return row

    def _code_row(self, code: str) -> sqlite3.Row:
        conn = sqlite3.connect(self.db)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM authorization_codes WHERE code = ?", (code,)).fetchone()
        conn.close()
        self.assertIsNotNone(row)
        return row

    def test_recovery_after_restart_completes_exchange_and_uses_recover_client_and_callback(self) -> None:
        login_id = self._issue_code_login(self.server, state="restart-state")
        recovery_id = self._checkpoint(self.server, login_id, "code_issued")
        stored_locator = self._stored_locator(recovery_id)

        # Simulate a process restart: the server that created the journal is
        # closed, and recovery is completed against a fresh server process
        # pointed at the same durable database file.
        self.server.close()
        self.server = None
        server2 = start_server(self.db, code_ttl_seconds=60)
        try:
            with mock.patch.object(
                resume, "recover_client_and_callback", wraps=resume.recover_client_and_callback
            ) as mock_recover:
                status, body = post_json(
                    server2.base_url,
                    f"/oauth/exchange-recoveries/{recovery_id}/complete",
                    {"account_id": "acct-1", "password": "pw123"},
                )

            self.assertEqual(status, 200, body)
            self.assertEqual(set(body.keys()), {"location"})

            # Prove the route actually consumed the shared continuation
            # helper exactly once, with the journal's own stored locator and
            # its authoritative client -- not some ad hoc resolution.
            mock_recover.assert_called_once()
            call_args = mock_recover.call_args.args
            self.assertIn(stored_locator, call_args)
            self.assertIn(CLIENT_A, call_args)

            parsed = urllib.parse.urlparse(body["location"])
            self.assertEqual(f"{parsed.scheme}://{parsed.netloc}{parsed.path}", CALLBACK_A)
            query = urllib.parse.parse_qs(parsed.query)
            self.assertEqual(query["state"], ["restart-state"])
            code = query["code"][0]

            status, token_body = post_json(
                server2.base_url, "/oauth/token", {"client_id": CLIENT_A, "code": code}
            )
            self.assertEqual(status, 200, token_body)
            self.assertEqual(set(token_body.keys()), {"access_token", "client_id", "account_id"})
            self.assertEqual(token_body["client_id"], CLIENT_A)
            self.assertEqual(token_body["account_id"], "acct-1")

            code_row = self._code_row(code)
            self.assertEqual(code_row["client_id"], CLIENT_A)
            self.assertEqual(code_row["account_id"], "acct-1")
            self.assertAlmostEqual(code_row["expires_at"] - code_row["issued_at"], 60, places=3)
            self.assertEqual(code_row["consumed"], 1)

            journal_row = self._journal_row(recovery_id)
            self.assertEqual(journal_row["stage"], "completed")

            # Single-use: replaying the just-exchanged code is rejected.
            status, body = post_json(
                server2.base_url, "/oauth/token", {"client_id": CLIENT_A, "code": code}
            )
            self.assertEqual(status, 403)
            self.assertEqual(body, {"error": "invalid_code"})
        finally:
            server2.close()

    def test_repeated_completion_is_idempotent(self) -> None:
        login_id = self._issue_code_login(self.server, state="s")
        recovery_id = self._checkpoint(self.server, login_id, "code_issued")

        status, first = post_json(
            self.server.base_url,
            f"/oauth/exchange-recoveries/{recovery_id}/complete",
            {"account_id": "acct-1", "password": "pw123"},
        )
        self.assertEqual(status, 200, first)

        status, body = post_json(
            self.server.base_url,
            f"/oauth/exchange-recoveries/{recovery_id}/complete",
            {"account_id": "acct-1", "password": "pw123"},
        )
        self.assertEqual(status, 200, body)
        self.assertEqual(body, first)

    def test_illegal_stage_genuinely_completed_rejected(self) -> None:
        # Reaching "completed" through the ordinary stage checkpoint
        # endpoint, never through this recovery route, leaves nothing on
        # file for this route to recover.
        login_id = self._issue_code_login(self.server, state="s")
        recovery_id = self._checkpoint(self.server, login_id, "completed")

        status, body = post_json(
            self.server.base_url,
            f"/oauth/exchange-recoveries/{recovery_id}/complete",
            {"account_id": "acct-1", "password": "pw123"},
        )
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "recovery_completed"})

    def test_wrong_password_rejected(self) -> None:
        login_id = self._issue_code_login(self.server, state="s")
        recovery_id = self._checkpoint(self.server, login_id, "code_issued")

        status, body = post_json(
            self.server.base_url,
            f"/oauth/exchange-recoveries/{recovery_id}/complete",
            {"account_id": "acct-1", "password": "wrong-password"},
        )
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "invalid_credentials"})

    def test_callback_substitution_rejected(self) -> None:
        login_id = self._issue_code_login(self.server, state="s")
        recovery_id = self._checkpoint(self.server, login_id, "code_issued")

        # A substituted registered callback for the authoritative client
        # must not be followed silently.
        conn = sqlite3.connect(self.db)
        with conn:
            conn.execute(
                "UPDATE clients SET redirect_uri = ? WHERE client_id = ?",
                ("http://127.0.0.1:9999/attacker-cb", CLIENT_A),
            )
        conn.close()

        status, body = post_json(
            self.server.base_url,
            f"/oauth/exchange-recoveries/{recovery_id}/complete",
            {"account_id": "acct-1", "password": "pw123"},
        )
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "callback_mismatch"})

    def test_wrong_client_exchange_rejected(self) -> None:
        login_id = self._issue_code_login(self.server, state="s")
        recovery_id = self._checkpoint(self.server, login_id, "code_issued")

        status, body = post_json(
            self.server.base_url,
            f"/oauth/exchange-recoveries/{recovery_id}/complete",
            {"account_id": "acct-1", "password": "pw123"},
        )
        self.assertEqual(status, 200, body)
        query = urllib.parse.parse_qs(urllib.parse.urlparse(body["location"]).query)
        code = query["code"][0]

        status, body = post_json(
            self.server.base_url, "/oauth/token", {"client_id": CLIENT_B, "code": code}
        )
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "wrong_client"})

    def test_replayed_code_after_recovery_is_rejected(self) -> None:
        login_id = self._issue_code_login(self.server, state="s")
        recovery_id = self._checkpoint(self.server, login_id, "code_issued")

        status, body = post_json(
            self.server.base_url,
            f"/oauth/exchange-recoveries/{recovery_id}/complete",
            {"account_id": "acct-1", "password": "pw123"},
        )
        self.assertEqual(status, 200, body)
        query = urllib.parse.parse_qs(urllib.parse.urlparse(body["location"]).query)
        code = query["code"][0]

        status, body = post_json(self.server.base_url, "/oauth/token", {"client_id": CLIENT_A, "code": code})
        self.assertEqual(status, 200, body)

        status, body = post_json(self.server.base_url, "/oauth/token", {"client_id": CLIENT_A, "code": code})
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "invalid_code"})


if __name__ == "__main__":
    unittest.main()
