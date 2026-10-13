"""Redacted, single-recovery journal inspection and its transition history.
Every lookup is scoped to exactly one recovery id and never returns
credentials, code bytes, tokens, opaque handles, or callback query values.
Covers stable JSON output and separate-process inspection after restart."""
from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from tests._util import post_json, run_cli, start_server


class RecoveryInspectionTests(unittest.TestCase):
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

    def _record_stage(self, login_id: str, stage: str) -> dict:
        status, body = post_json(
            self.server.base_url,
            "/oauth/exchange-recoveries",
            {"login_id": login_id, "stage": stage},
        )
        self.assertIn(status, (200, 201), body)
        return body

    def _code_bytes(self, login_id: str) -> str:
        conn = sqlite3.connect(self.db)
        row = conn.execute(
            "SELECT code FROM authorization_codes WHERE login_id = ?", (login_id,)
        ).fetchone()
        conn.close()
        self.assertIsNotNone(row)
        return row[0]

    def _exchange_handle(self, login_id: str) -> str:
        conn = sqlite3.connect(self.db)
        row = conn.execute(
            "SELECT exchange_handle FROM exchange_recoveries WHERE login_id = ?", (login_id,)
        ).fetchone()
        conn.close()
        self.assertIsNotNone(row)
        return row[0]

    def _inspect(self, recovery_id: str):
        return run_cli("inspect-recovery", recovery_id, "--database", self.db)

    def test_inspection_omits_sensitive_material(self) -> None:
        login_id = self._issue_code_login(state="caller-state-secret")
        first = self._record_stage(login_id, "code_issued")
        recovery_id = first["recovery_id"]
        self._record_stage(login_id, "redirect_dispatched")

        result = self._inspect(recovery_id)
        self.assertEqual(result.returncode, 0, result.stderr)
        body = json.loads(result.stdout)

        self.assertEqual(
            set(body.keys()),
            {
                "recovery_id",
                "login_id",
                "account_id",
                "client_id",
                "callback",
                "stage",
                "created_at",
                "expires_at",
                "expired",
                "claimed",
                "claim_lease_expires_at",
                "cleaned_up",
                "transitions",
            },
        )
        self.assertEqual(body["login_id"], login_id)
        self.assertEqual(body["account_id"], "acct-1")
        self.assertEqual(body["client_id"], "client-a")
        self.assertEqual(body["callback"], "http://127.0.0.1:9999/cb")

        code = self._code_bytes(login_id)
        handle = self._exchange_handle(login_id)

        serialized = result.stdout
        self.assertNotIn(code, serialized)
        self.assertNotIn(handle, serialized)
        self.assertNotIn("caller-state-secret", serialized)
        self.assertNotIn("pw123", serialized)

    def test_transition_history_recorded_in_order(self) -> None:
        login_id = self._issue_code_login()
        first = self._record_stage(login_id, "code_issued")
        recovery_id = first["recovery_id"]
        self._record_stage(login_id, "redirect_dispatched")
        self._record_stage(login_id, "exchange_pending")
        self._record_stage(login_id, "completed")

        body = json.loads(self._inspect(recovery_id).stdout)
        self.assertEqual(
            [t["stage"] for t in body["transitions"]],
            ["code_issued", "redirect_dispatched", "exchange_pending", "completed"],
        )
        self.assertEqual(body["stage"], "completed")
        for transition in body["transitions"]:
            self.assertEqual(set(transition.keys()), {"stage", "recorded_at"})
            self.assertTrue(transition["recorded_at"])

    def test_lookup_scoped_to_one_recovery_id(self) -> None:
        login_a = self._issue_code_login(state="a")
        login_b = self._issue_code_login(state="b")
        recovery_a = self._record_stage(login_a, "code_issued")["recovery_id"]
        recovery_b = self._record_stage(login_b, "code_issued")["recovery_id"]
        self._record_stage(login_b, "redirect_dispatched")

        self.assertNotEqual(recovery_a, recovery_b)

        body_a = json.loads(self._inspect(recovery_a).stdout)
        body_b = json.loads(self._inspect(recovery_b).stdout)

        self.assertEqual(body_a["login_id"], login_a)
        self.assertEqual(body_b["login_id"], login_b)
        self.assertEqual([t["stage"] for t in body_a["transitions"]], ["code_issued"])
        self.assertEqual(
            [t["stage"] for t in body_b["transitions"]], ["code_issued", "redirect_dispatched"]
        )

    def test_unknown_recovery_id_rejected(self) -> None:
        result = self._inspect("no-such-recovery-id")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stderr), {"error": "invalid_recovery"})

    def test_repeated_inspection_is_stable_byte_identical_json(self) -> None:
        login_id = self._issue_code_login()
        recovery_id = self._record_stage(login_id, "code_issued")["recovery_id"]

        first = self._inspect(recovery_id)
        second = self._inspect(recovery_id)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(first.stdout, second.stdout)

        # The key order is deterministic (alphabetically sorted), not just
        # value-equal between the two calls.
        self.assertTrue(first.stdout.startswith('{"account_id"'))

    def test_inspection_is_a_separate_process_reading_persisted_state(self) -> None:
        login_id = self._issue_code_login()
        recovery_id = self._record_stage(login_id, "code_issued")["recovery_id"]
        self._record_stage(login_id, "redirect_dispatched")

        # Simulate a restart: the HTTP server process that created the
        # journal is gone before inspection runs as its own subprocess.
        self.server.close()
        self.server = None

        result = self._inspect(recovery_id)
        self.assertEqual(result.returncode, 0, result.stderr)
        body = json.loads(result.stdout)
        self.assertEqual(body["recovery_id"], recovery_id)
        self.assertEqual(body["stage"], "redirect_dispatched")
        self.assertEqual(
            [t["stage"] for t in body["transitions"]], ["code_issued", "redirect_dispatched"]
        )


if __name__ == "__main__":
    unittest.main()
