"""POST /oauth/exchange-recoveries/{recovery_id}/complete: recovering an
interrupted exchange completion, including after a process restart. Covers
the successful path, wrong-credential rejection, malformed callback/redirect
fields, an unknown recovery id, idempotent repetition of an already-recovered
journal, a genuinely already-completed journal that this route never
recovered, an expired journal, and a callback that no longer matches the
client's registered redirect uri."""
from __future__ import annotations

import sqlite3
import tempfile
import time
import unittest
import urllib.parse
from pathlib import Path

from tests._util import post_json, run_cli, start_server


class ExchangeRecoveryCompleteTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db = str(Path(self._tmpdir.name) / "state.db")
        run_cli("create-account", "acct-1", "a@example.com", "pw123", "--database", self.db)
        run_cli("create-account", "acct-2", "b@example.com", "pw456", "--database", self.db)
        run_cli("register-client", "client-a", "http://127.0.0.1:9999/cb", "--database", self.db)
        self.server = start_server(self.db, code_ttl_seconds=60)

    def tearDown(self) -> None:
        if self.server is not None:
            self.server.close()
        self._tmpdir.cleanup()

    def _issue_code_login(self, state: str = "s") -> str:
        _, authorize_body = post_json(
            self.server.base_url,
            "/oauth/authorize",
            {"client_id": "client-a", "redirect_uri": "http://127.0.0.1:9999/cb", "state": state},
        )
        login_id = authorize_body["login_id"]
        status, complete_body = post_json(
            self.server.base_url,
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

    def _complete(self, server, recovery_id: str, account_id: str, password: str):
        return post_json(
            server.base_url,
            f"/oauth/exchange-recoveries/{recovery_id}/complete",
            {"account_id": account_id, "password": password},
        )

    def _original_code(self, login_id: str) -> str:
        conn = sqlite3.connect(self.db)
        row = conn.execute(
            "SELECT code FROM authorization_codes WHERE login_id = ?", (login_id,)
        ).fetchone()
        conn.close()
        self.assertIsNotNone(row)
        return row[0]

    def test_successful_recovery_returns_only_location(self) -> None:
        login_id = self._issue_code_login(state="caller-state")
        recovery_id = self._checkpoint(self.server, login_id)

        status, body = self._complete(self.server, recovery_id, "acct-1", "pw123")
        self.assertEqual(status, 200, body)
        self.assertEqual(set(body.keys()), {"location"})

        parsed = urllib.parse.urlparse(body["location"])
        self.assertEqual(f"{parsed.scheme}://{parsed.netloc}{parsed.path}", "http://127.0.0.1:9999/cb")
        query = urllib.parse.parse_qs(parsed.query)
        self.assertEqual(query["state"], ["caller-state"])
        new_code = query["code"][0]

        # The replacement code is a fresh, distinct, single-use code, not the
        # original one from the interrupted login.
        original_code = self._original_code(login_id)
        self.assertNotEqual(new_code, original_code)

        conn = sqlite3.connect(self.db)
        code_row = conn.execute(
            "SELECT client_id, account_id, consumed FROM authorization_codes WHERE code = ?",
            (new_code,),
        ).fetchone()
        journal_row = conn.execute(
            "SELECT stage FROM exchange_recoveries WHERE recovery_id = ?", (recovery_id,)
        ).fetchone()
        transitions = conn.execute(
            "SELECT stage FROM exchange_recovery_transitions WHERE recovery_id = ? ORDER BY id ASC",
            (recovery_id,),
        ).fetchall()
        conn.close()

        self.assertEqual(code_row[0], "client-a")
        self.assertEqual(code_row[1], "acct-1")
        self.assertEqual(code_row[2], 0)
        self.assertEqual(journal_row[0], "completed")
        self.assertEqual([row[0] for row in transitions], ["code_issued", "completed"])

    def test_wrong_password_rejected(self) -> None:
        login_id = self._issue_code_login()
        recovery_id = self._checkpoint(self.server, login_id)

        status, body = self._complete(self.server, recovery_id, "acct-1", "wrong-password")
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "invalid_credentials"})

    def test_wrong_account_rejected(self) -> None:
        login_id = self._issue_code_login()
        recovery_id = self._checkpoint(self.server, login_id)

        # acct-2 is a real, valid account, but it is not the account bound
        # to this recovery journal.
        status, body = self._complete(self.server, recovery_id, "acct-2", "pw456")
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "invalid_credentials"})

    def test_unknown_account_rejected(self) -> None:
        login_id = self._issue_code_login()
        recovery_id = self._checkpoint(self.server, login_id)

        status, body = self._complete(self.server, recovery_id, "no-such-account", "whatever")
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "invalid_credentials"})

    def test_malformed_request_rejects_callback_and_redirect_fields(self) -> None:
        login_id = self._issue_code_login()
        recovery_id = self._checkpoint(self.server, login_id)

        status, body = post_json(
            self.server.base_url,
            f"/oauth/exchange-recoveries/{recovery_id}/complete",
            {"account_id": "acct-1", "password": "pw123", "callback": "http://evil.example/cb"},
        )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

        status, body = post_json(
            self.server.base_url,
            f"/oauth/exchange-recoveries/{recovery_id}/complete",
            {"account_id": "acct-1", "password": "pw123", "redirect_uri": "http://evil.example/cb"},
        )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

    def test_malformed_request_missing_field(self) -> None:
        login_id = self._issue_code_login()
        recovery_id = self._checkpoint(self.server, login_id)

        status, body = post_json(
            self.server.base_url,
            f"/oauth/exchange-recoveries/{recovery_id}/complete",
            {"account_id": "acct-1"},
        )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

    def test_unknown_recovery_id_rejected(self) -> None:
        status, body = self._complete(self.server, "no-such-recovery-id", "acct-1", "pw123")
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "invalid_recovery"})

    def test_repeated_completion_is_idempotent(self) -> None:
        login_id = self._issue_code_login()
        recovery_id = self._checkpoint(self.server, login_id)

        status, first = self._complete(self.server, recovery_id, "acct-1", "pw123")
        self.assertEqual(status, 200, first)

        for _ in range(3):
            status, body = self._complete(self.server, recovery_id, "acct-1", "pw123")
            self.assertEqual(status, 200, body)
            self.assertEqual(body, first)

        # Only the original login code and the one replacement code from the
        # first completion were ever minted; the idempotent repeats did not
        # mint a third.
        conn = sqlite3.connect(self.db)
        count = conn.execute(
            "SELECT COUNT(*) FROM authorization_codes WHERE login_id = ?", (login_id,)
        ).fetchone()[0]
        conn.close()
        self.assertEqual(count, 2)

    def test_repeated_completion_still_requires_correct_credentials(self) -> None:
        login_id = self._issue_code_login()
        recovery_id = self._checkpoint(self.server, login_id)

        status, body = self._complete(self.server, recovery_id, "acct-1", "pw123")
        self.assertEqual(status, 200, body)

        status, body = self._complete(self.server, recovery_id, "acct-1", "wrong-password")
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "invalid_credentials"})

    def test_genuinely_already_completed_recovery_rejected(self) -> None:
        # The journal reaches "completed" through the ordinary stage
        # checkpoint endpoint, never through this recovery route, so there
        # is no recovered location on file to repeat.
        login_id = self._issue_code_login()
        recovery_id = self._checkpoint(self.server, login_id, "completed")

        status, body = self._complete(self.server, recovery_id, "acct-1", "pw123")
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "recovery_completed"})

    def test_expired_recovery_rejected(self) -> None:
        self.server.close()
        self.server = None

        short_server = start_server(self.db, code_ttl_seconds=1)
        try:
            login_id = self._issue_code_login_on(short_server)
            recovery_id = self._checkpoint(short_server, login_id)

            time.sleep(1.2)

            status, body = self._complete(short_server, recovery_id, "acct-1", "pw123")
            self.assertEqual(status, 403)
            self.assertEqual(body, {"error": "recovery_expired"})
        finally:
            short_server.close()

    def _issue_code_login_on(self, server, state: str = "s") -> str:
        _, authorize_body = post_json(
            server.base_url,
            "/oauth/authorize",
            {"client_id": "client-a", "redirect_uri": "http://127.0.0.1:9999/cb", "state": state},
        )
        login_id = authorize_body["login_id"]
        status, complete_body = post_json(
            server.base_url,
            "/login/complete",
            {"login_id": login_id, "account_id": "acct-1", "password": "pw123"},
        )
        self.assertEqual(status, 200, complete_body)
        return login_id

    def test_callback_mismatch_rejected(self) -> None:
        login_id = self._issue_code_login()
        recovery_id = self._checkpoint(self.server, login_id)

        conn = sqlite3.connect(self.db)
        with conn:
            conn.execute(
                "UPDATE clients SET redirect_uri = ? WHERE client_id = ?",
                ("http://127.0.0.1:9999/different-cb", "client-a"),
            )
        conn.close()

        status, body = self._complete(self.server, recovery_id, "acct-1", "pw123")
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "callback_mismatch"})

    def test_recovery_survives_restart(self) -> None:
        login_id = self._issue_code_login(state="restart-state")
        recovery_id = self._checkpoint(self.server, login_id)

        # Simulate a restart: the process that created the journal is gone
        # before recovery is completed against a fresh server process
        # pointed at the same database file.
        self.server.close()
        self.server = None

        server2 = start_server(self.db, code_ttl_seconds=60)
        try:
            status, body = self._complete(server2, recovery_id, "acct-1", "pw123")
            self.assertEqual(status, 200, body)
            query = urllib.parse.parse_qs(urllib.parse.urlparse(body["location"]).query)
            self.assertEqual(query["state"], ["restart-state"])
        finally:
            server2.close()


if __name__ == "__main__":
    unittest.main()
