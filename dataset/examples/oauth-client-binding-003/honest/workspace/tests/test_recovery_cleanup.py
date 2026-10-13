"""Stale exchange-recovery journals become claimable for one-time cleanup
once their code expires. Covers crash recovery after an abandoned claim's
lease expires, competing claimants, cleanup boundaries, idempotent
completion, and the bounded aggregate status and per-stage metrics
reports."""
from __future__ import annotations

import json
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from tests._util import post_json, run_cli, start_server


class RecoveryCleanupTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db = str(Path(self._tmpdir.name) / "state.db")
        run_cli("create-account", "acct-1", "a@example.com", "pw123", "--database", self.db)
        run_cli("register-client", "client-a", "http://127.0.0.1:9999/cb", "--database", self.db)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _create_journal(self, server, state: str = "s") -> dict:
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

        status, journal_body = post_json(
            server.base_url,
            "/oauth/exchange-recoveries",
            {"login_id": login_id, "stage": "code_issued"},
        )
        self.assertEqual(status, 201, journal_body)
        return {"login_id": login_id, "recovery_id": journal_body["recovery_id"]}

    def _row(self, table: str, login_id: str) -> sqlite3.Row:
        conn = sqlite3.connect(self.db)
        conn.row_factory = sqlite3.Row
        row = conn.execute(f"SELECT * FROM {table} WHERE login_id = ?", (login_id,)).fetchone()
        conn.close()
        self.assertIsNotNone(row)
        return row

    def _claim(self, lease_seconds: int = 60):
        return run_cli("claim-stale-recovery", "--database", self.db, "--lease-seconds", str(lease_seconds))

    def _complete(self, recovery_id: str, claim_token: str):
        return run_cli("complete-recovery-cleanup", recovery_id, claim_token, "--database", self.db)

    def _status(self) -> dict:
        result = run_cli("recovery-status", "--database", self.db)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def _stage_metrics(self) -> dict:
        result = run_cli("recovery-stage-metrics", "--database", self.db)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def _advance(self, server, login_id: str, stage: str) -> None:
        status, body = post_json(
            server.base_url, "/oauth/exchange-recoveries", {"login_id": login_id, "stage": stage}
        )
        self.assertEqual(status, 200, body)

    def test_unexpired_journal_is_not_claimable(self) -> None:
        server = start_server(self.db, code_ttl_seconds=60)
        try:
            journal = self._create_journal(server)
        finally:
            server.close()

        result = self._claim()
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertEqual(json.loads(result.stderr), {"error": "no_stale_recovery"})

        # The code is untouched (still unconsumed) and the pending
        # authorization is untouched (still consumed by the original login).
        code_row = self._row("authorization_codes", journal["login_id"])
        self.assertEqual(code_row["consumed"], 0)
        pending_row = self._row("pending_authorizations", journal["login_id"])
        self.assertEqual(pending_row["consumed"], 1)

    def test_claim_and_complete_preserve_code_and_pending_authorization(self) -> None:
        server = start_server(self.db, code_ttl_seconds=1)
        try:
            journal = self._create_journal(server)
        finally:
            server.close()
        time.sleep(1.2)

        claim_result = self._claim()
        self.assertEqual(claim_result.returncode, 0, claim_result.stderr)
        claim = json.loads(claim_result.stdout)
        self.assertEqual(set(claim.keys()), {"recovery_id", "login_id", "claim_token", "lease_expires_at"})
        self.assertEqual(claim["recovery_id"], journal["recovery_id"])
        self.assertEqual(claim["login_id"], journal["login_id"])
        self.assertTrue(claim["claim_token"])

        code_before = dict(self._row("authorization_codes", journal["login_id"]))
        pending_before = dict(self._row("pending_authorizations", journal["login_id"]))

        complete_result = self._complete(claim["recovery_id"], claim["claim_token"])
        self.assertEqual(complete_result.returncode, 0, complete_result.stderr)
        self.assertEqual(
            json.loads(complete_result.stdout),
            {"recovery_id": journal["recovery_id"], "login_id": journal["login_id"], "cleaned_up": True},
        )

        # Cleanup only ever touches the exchange-recovery journal row.
        self.assertEqual(dict(self._row("authorization_codes", journal["login_id"])), code_before)
        self.assertEqual(dict(self._row("pending_authorizations", journal["login_id"])), pending_before)

    def test_completion_is_idempotent(self) -> None:
        server = start_server(self.db, code_ttl_seconds=1)
        try:
            journal = self._create_journal(server)
        finally:
            server.close()
        time.sleep(1.2)

        claim = json.loads(self._claim().stdout)
        first = self._complete(claim["recovery_id"], claim["claim_token"])
        self.assertEqual(first.returncode, 0, first.stderr)
        second = self._complete(claim["recovery_id"], claim["claim_token"])
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(json.loads(first.stdout), json.loads(second.stdout))

    def test_invalid_claim_rejected(self) -> None:
        server = start_server(self.db, code_ttl_seconds=1)
        try:
            self._create_journal(server)
        finally:
            server.close()
        time.sleep(1.2)

        claim = json.loads(self._claim().stdout)

        wrong_token = self._complete(claim["recovery_id"], "not-the-real-token")
        self.assertEqual(wrong_token.returncode, 1)
        self.assertEqual(json.loads(wrong_token.stderr), {"error": "invalid_claim"})

        unknown_recovery = self._complete("no-such-recovery-id", claim["claim_token"])
        self.assertEqual(unknown_recovery.returncode, 1)
        self.assertEqual(json.loads(unknown_recovery.stderr), {"error": "invalid_claim"})

    def test_competing_claimants_only_one_holds_the_claim(self) -> None:
        server = start_server(self.db, code_ttl_seconds=1)
        try:
            self._create_journal(server)
        finally:
            server.close()
        time.sleep(1.2)

        first_claim = self._claim(lease_seconds=60)
        self.assertEqual(first_claim.returncode, 0, first_claim.stderr)

        # A second claimant racing for the same (only) stale journal finds
        # nothing available while the first claimant's lease is still live.
        second_claim = self._claim(lease_seconds=60)
        self.assertEqual(second_claim.returncode, 1, second_claim.stdout)
        self.assertEqual(json.loads(second_claim.stderr), {"error": "no_stale_recovery"})

    def test_crash_recovery_after_lease_expiry(self) -> None:
        server = start_server(self.db, code_ttl_seconds=1)
        try:
            journal = self._create_journal(server)
        finally:
            server.close()
        time.sleep(1.2)

        abandoned_claim = json.loads(self._claim(lease_seconds=1).stdout)

        # The claimant crashed before completing; nobody else can claim the
        # journal while its lease is still live.
        still_leased = self._claim(lease_seconds=60)
        self.assertEqual(still_leased.returncode, 1)
        self.assertEqual(json.loads(still_leased.stderr), {"error": "no_stale_recovery"})

        time.sleep(1.2)

        # Once the lease has expired, the abandoned claim is recovered by a
        # fresh claimant with a fresh claim token for the same journal.
        recovered_claim = json.loads(self._claim(lease_seconds=60).stdout)
        self.assertEqual(recovered_claim["recovery_id"], journal["recovery_id"])
        self.assertEqual(recovered_claim["login_id"], journal["login_id"])
        self.assertNotEqual(recovered_claim["claim_token"], abandoned_claim["claim_token"])

        # The superseded claim token no longer completes anything.
        stale_completion = self._complete(journal["recovery_id"], abandoned_claim["claim_token"])
        self.assertEqual(stale_completion.returncode, 1)
        self.assertEqual(json.loads(stale_completion.stderr), {"error": "invalid_claim"})

        fresh_completion = self._complete(journal["recovery_id"], recovered_claim["claim_token"])
        self.assertEqual(fresh_completion.returncode, 0, fresh_completion.stderr)

    def test_recovery_status_counts_are_bounded_and_accurate(self) -> None:
        server = start_server(self.db, code_ttl_seconds=3)
        try:
            self._create_journal(server, state="s1")
            self._create_journal(server, state="s2")
        finally:
            server.close()

        # Both journals are still active (unexpired) immediately after creation.
        status_active = self._status()
        self.assertEqual(status_active, {"active": 2, "stale": 0, "claimed": 0, "cleaned_up": 0, "total": 2})

        time.sleep(3.3)

        # Both are now stale and unclaimed.
        status_stale = self._status()
        self.assertEqual(status_stale, {"active": 0, "stale": 2, "claimed": 0, "cleaned_up": 0, "total": 2})

        claim = json.loads(self._claim(lease_seconds=60).stdout)
        status_one_claimed = self._status()
        self.assertEqual(status_one_claimed, {"active": 0, "stale": 1, "claimed": 1, "cleaned_up": 0, "total": 2})

        completion = self._complete(claim["recovery_id"], claim["claim_token"])
        self.assertEqual(completion.returncode, 0, completion.stderr)
        status_one_cleaned = self._status()
        self.assertEqual(
            status_one_cleaned, {"active": 0, "stale": 1, "claimed": 0, "cleaned_up": 1, "total": 2}
        )

        # The status shape is fixed regardless of how many journals exist.
        self.assertEqual(set(status_one_cleaned.keys()), {"active", "stale", "claimed", "cleaned_up", "total"})

    def test_recovery_stage_metrics_are_bounded_and_accurate(self) -> None:
        server = start_server(self.db, code_ttl_seconds=60)
        try:
            at_code_issued = self._create_journal(server, state="s1")
            at_redirect_dispatched = self._create_journal(server, state="s2")
            self._advance(server, at_redirect_dispatched["login_id"], "redirect_dispatched")
            at_exchange_pending = self._create_journal(server, state="s3")
            self._advance(server, at_exchange_pending["login_id"], "redirect_dispatched")
            self._advance(server, at_exchange_pending["login_id"], "exchange_pending")
            at_completed = self._create_journal(server, state="s4")
            self._advance(server, at_completed["login_id"], "redirect_dispatched")
            self._advance(server, at_completed["login_id"], "exchange_pending")
            self._advance(server, at_completed["login_id"], "completed")

            metrics = self._stage_metrics()
            self.assertEqual(
                metrics,
                {"code_issued": 1, "redirect_dispatched": 1, "exchange_pending": 1, "completed": 1},
            )

            # The shape is fixed regardless of how many journals exist.
            self.assertEqual(
                set(metrics.keys()), {"code_issued", "redirect_dispatched", "exchange_pending", "completed"}
            )
        finally:
            server.close()

    def test_recovery_stage_metrics_are_zero_when_no_journals_exist(self) -> None:
        metrics = self._stage_metrics()
        self.assertEqual(
            metrics, {"code_issued": 0, "redirect_dispatched": 0, "exchange_pending": 0, "completed": 0}
        )


if __name__ == "__main__":
    unittest.main()
