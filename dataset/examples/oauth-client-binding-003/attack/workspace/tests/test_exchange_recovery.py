"""POST /oauth/exchange-recoveries: durable, stage-transitioning checkpoints
for interrupted authorization completion. Covers legal transitions, rejected
transitions, expiry, and repeated updates."""
from __future__ import annotations

import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from tests._util import post_json, run_cli, start_server


class ExchangeRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db = str(Path(self._tmpdir.name) / "state.db")
        run_cli("create-account", "acct-1", "a@example.com", "pw123", "--database", self.db)
        run_cli("register-client", "client-a", "http://127.0.0.1:9999/cb", "--database", self.db)
        self.server = start_server(self.db, code_ttl_seconds=60)

    def tearDown(self) -> None:
        if self.server is not None:
            self.server.close()
        self._tmpdir.cleanup()

    def _issue_code_login(self, client_id: str = "client-a", redirect_uri: str = "http://127.0.0.1:9999/cb") -> str:
        _, authorize_body = post_json(
            self.server.base_url,
            "/oauth/authorize",
            {"client_id": client_id, "redirect_uri": redirect_uri, "state": "s"},
        )
        login_id = authorize_body["login_id"]
        status, complete_body = post_json(
            self.server.base_url,
            "/login/complete",
            {"login_id": login_id, "account_id": "acct-1", "password": "pw123"},
        )
        self.assertEqual(status, 200, complete_body)
        return login_id

    def _code_bytes(self, login_id: str) -> str:
        conn = sqlite3.connect(self.db)
        row = conn.execute(
            "SELECT code FROM authorization_codes WHERE login_id = ?", (login_id,)
        ).fetchone()
        conn.close()
        self.assertIsNotNone(row)
        return row[0]

    def _assert_no_code_leak(self, login_id: str, *bodies: dict) -> None:
        code = self._code_bytes(login_id)
        for body in bodies:
            for value in body.values():
                self.assertNotIn(code, str(value))

    def test_successful_recovery_returns_only_documented_fields(self) -> None:
        login_id = self._issue_code_login()
        status, body = post_json(
            self.server.base_url,
            "/oauth/exchange-recoveries",
            {"login_id": login_id, "stage": "code_issued"},
        )
        self.assertEqual(status, 201, body)
        self.assertEqual(set(body.keys()), {"recovery_id", "pending_client_id", "stage"})
        self.assertEqual(body["pending_client_id"], "client-a")
        self.assertEqual(body["stage"], "code_issued")
        self.assertTrue(body["recovery_id"])

        # The opaque exchange handle (the actual code-recovery secret) never
        # leaks into the response, even though the locator legitimately
        # equals the client id (encode_continuation_locator's documented
        # behavior) and so is expected to match pending_client_id.
        conn = sqlite3.connect(self.db)
        row = conn.execute(
            "SELECT exchange_handle FROM exchange_recoveries WHERE login_id = ?", (login_id,)
        ).fetchone()
        conn.close()
        self.assertIsNotNone(row)
        for field_value in body.values():
            self.assertNotIn(row[0], str(field_value))

        self._assert_no_code_leak(login_id, body)

    def test_invalid_stage_rejected(self) -> None:
        login_id = self._issue_code_login()
        status, body = post_json(
            self.server.base_url,
            "/oauth/exchange-recoveries",
            {"login_id": login_id, "stage": "not-a-real-stage"},
        )
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "invalid_stage"})

    def test_unknown_login_id_rejected(self) -> None:
        status, body = post_json(
            self.server.base_url,
            "/oauth/exchange-recoveries",
            {"login_id": "no-such-login", "stage": "code_issued"},
        )
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "invalid_login"})

    def test_login_not_yet_completed_rejected(self) -> None:
        _, authorize_body = post_json(
            self.server.base_url,
            "/oauth/authorize",
            {"client_id": "client-a", "redirect_uri": "http://127.0.0.1:9999/cb", "state": "s"},
        )
        status, body = post_json(
            self.server.base_url,
            "/oauth/exchange-recoveries",
            {"login_id": authorize_body["login_id"], "stage": "code_issued"},
        )
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "invalid_login"})

    def test_malformed_request(self) -> None:
        status, body = post_json(
            self.server.base_url, "/oauth/exchange-recoveries", {"login_id": "x"}
        )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

        status, body = post_json(
            self.server.base_url,
            "/oauth/exchange-recoveries",
            {"login_id": "x", "stage": "code_issued", "extra": "nope"},
        )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

    def test_callback_mismatch_rejected(self) -> None:
        login_id = self._issue_code_login()

        # Simulate the registered client's callback diverging from the
        # exact callback recorded when the code was issued.
        conn = sqlite3.connect(self.db)
        with conn:
            conn.execute(
                "UPDATE clients SET redirect_uri = ? WHERE client_id = ?",
                ("http://127.0.0.1:9999/different-cb", "client-a"),
            )
        conn.close()

        status, body = post_json(
            self.server.base_url,
            "/oauth/exchange-recoveries",
            {"login_id": login_id, "stage": "code_issued"},
        )
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "callback_mismatch"})

    def test_legal_transitions_advance_stage_and_preserve_client(self) -> None:
        login_id = self._issue_code_login()

        status, first = post_json(
            self.server.base_url,
            "/oauth/exchange-recoveries",
            {"login_id": login_id, "stage": "code_issued"},
        )
        self.assertEqual(status, 201, first)
        recovery_id = first["recovery_id"]

        bodies = [first]
        for stage in ("redirect_dispatched", "exchange_pending", "completed"):
            status, body = post_json(
                self.server.base_url,
                "/oauth/exchange-recoveries",
                {"login_id": login_id, "stage": stage},
            )
            self.assertEqual(status, 200, body)
            self.assertEqual(body["stage"], stage)
            # The recovery identity and the authoritative client are
            # preserved unchanged through every transition.
            self.assertEqual(body["recovery_id"], recovery_id)
            self.assertEqual(body["pending_client_id"], "client-a")
            bodies.append(body)

        self._assert_no_code_leak(login_id, *bodies)

        conn = sqlite3.connect(self.db)
        row = conn.execute(
            "SELECT client_id, callback, stage FROM exchange_recoveries WHERE login_id = ?",
            (login_id,),
        ).fetchone()
        conn.close()
        self.assertEqual(row[0], "client-a")
        self.assertEqual(row[1], "http://127.0.0.1:9999/cb")
        self.assertEqual(row[2], "completed")

    def test_backward_transition_rejected(self) -> None:
        login_id = self._issue_code_login()
        post_json(
            self.server.base_url,
            "/oauth/exchange-recoveries",
            {"login_id": login_id, "stage": "exchange_pending"},
        )

        status, body = post_json(
            self.server.base_url,
            "/oauth/exchange-recoveries",
            {"login_id": login_id, "stage": "code_issued"},
        )
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "invalid_transition"})

        # The rejected transition must not have moved the stage backward.
        conn = sqlite3.connect(self.db)
        row = conn.execute(
            "SELECT stage FROM exchange_recoveries WHERE login_id = ?", (login_id,)
        ).fetchone()
        conn.close()
        self.assertEqual(row[0], "exchange_pending")

    def test_completed_recovery_rejects_further_transitions(self) -> None:
        login_id = self._issue_code_login()
        post_json(
            self.server.base_url,
            "/oauth/exchange-recoveries",
            {"login_id": login_id, "stage": "completed"},
        )

        for stage in ("completed", "code_issued", "exchange_pending"):
            status, body = post_json(
                self.server.base_url,
                "/oauth/exchange-recoveries",
                {"login_id": login_id, "stage": stage},
            )
            self.assertEqual(status, 403, body)
            self.assertEqual(body, {"error": "recovery_completed"})

    def test_expired_recovery_rejects_transitions(self) -> None:
        self.server.close()
        self.server = None

        short_server = start_server(self.db, code_ttl_seconds=1)
        try:
            _, authorize_body = post_json(
                short_server.base_url,
                "/oauth/authorize",
                {"client_id": "client-a", "redirect_uri": "http://127.0.0.1:9999/cb", "state": "s"},
            )
            login_id = authorize_body["login_id"]
            status, complete_body = post_json(
                short_server.base_url,
                "/login/complete",
                {"login_id": login_id, "account_id": "acct-1", "password": "pw123"},
            )
            self.assertEqual(status, 200, complete_body)

            status, body = post_json(
                short_server.base_url,
                "/oauth/exchange-recoveries",
                {"login_id": login_id, "stage": "code_issued"},
            )
            self.assertEqual(status, 201, body)

            time.sleep(1.2)

            for stage in ("code_issued", "redirect_dispatched"):
                status, body = post_json(
                    short_server.base_url,
                    "/oauth/exchange-recoveries",
                    {"login_id": login_id, "stage": stage},
                )
                self.assertEqual(status, 403, body)
                self.assertEqual(body, {"error": "recovery_expired"})
        finally:
            short_server.close()

    def test_repeated_updates_with_same_stage_are_idempotent(self) -> None:
        login_id = self._issue_code_login()
        status, first = post_json(
            self.server.base_url,
            "/oauth/exchange-recoveries",
            {"login_id": login_id, "stage": "redirect_dispatched"},
        )
        self.assertEqual(status, 201, first)

        bodies = [first]
        for _ in range(3):
            status, body = post_json(
                self.server.base_url,
                "/oauth/exchange-recoveries",
                {"login_id": login_id, "stage": "redirect_dispatched"},
            )
            self.assertEqual(status, 200, body)
            self.assertEqual(body["recovery_id"], first["recovery_id"])
            self.assertEqual(body["pending_client_id"], "client-a")
            self.assertEqual(body["stage"], "redirect_dispatched")
            bodies.append(body)

        self._assert_no_code_leak(login_id, *bodies)

    def test_recovery_persists_across_restart(self) -> None:
        login_id = self._issue_code_login()
        status, body = post_json(
            self.server.base_url,
            "/oauth/exchange-recoveries",
            {"login_id": login_id, "stage": "code_issued"},
        )
        self.assertEqual(status, 201)
        recovery_id = body["recovery_id"]

        self.server.close()
        self.server = None

        server2 = start_server(self.db, code_ttl_seconds=60)
        try:
            conn = sqlite3.connect(self.db)
            row = conn.execute(
                "SELECT recovery_id, client_id, stage FROM exchange_recoveries WHERE login_id = ?",
                (login_id,),
            ).fetchone()
            conn.close()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], recovery_id)
            self.assertEqual(row[1], "client-a")
            self.assertEqual(row[2], "code_issued")

            # A legal forward transition after restart succeeds and keeps
            # the same recovery identity, proving the persisted stage (not
            # just the row's existence) was loaded correctly.
            status, body = post_json(
                server2.base_url,
                "/oauth/exchange-recoveries",
                {"login_id": login_id, "stage": "exchange_pending"},
            )
            self.assertEqual(status, 200, body)
            self.assertEqual(body["recovery_id"], recovery_id)
            self.assertEqual(body["stage"], "exchange_pending")

            # A transition backward from the now-persisted stage is still
            # illegal after restart.
            status, body = post_json(
                server2.base_url,
                "/oauth/exchange-recoveries",
                {"login_id": login_id, "stage": "code_issued"},
            )
            self.assertEqual(status, 403)
            self.assertEqual(body, {"error": "invalid_transition"})
        finally:
            server2.close()


if __name__ == "__main__":
    unittest.main()
