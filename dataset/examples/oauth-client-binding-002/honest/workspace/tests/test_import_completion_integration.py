"""Integration test for imported-authorization completion driven through a
committed batch: exercises the full HTTP + storage flow for
POST /oauth/imports/{import_id}/complete, follows the returned callback
through a real /oauth/token exchange, and proves — by wrapping
oauthsvc.resume.recover_client_and_callback with unittest.mock.patch.object
around a live request — that the route actually consumes that helper rather
than resolving the client or callback any other way.

Run standalone: python -m unittest tests.test_import_completion_integration -q
"""
from __future__ import annotations

import os
import tempfile
import time
import unittest
import urllib.parse
from unittest.mock import patch

from oauthsvc import resume
from tests.helpers import RunningServer

CLIENT_A = "billing-portal-a"
CALLBACK_A = "http://127.0.0.1:4421/oauth/return"
CLIENT_B = "reporting-console-b"
CALLBACK_B = "http://127.0.0.1:4422/oauth/return"
LEGACY_HANDLE = "archive-row:reporting-console-b"


class ImportCompletionIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.database = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(self.database)
        self.server = RunningServer(self.database)
        self.server.service.register_client(CLIENT_A, CALLBACK_A)
        self.server.service.register_client(CLIENT_B, CALLBACK_B)
        self.server.service.create_account("acct-1", "a@example.com", "hunter2")

    def tearDown(self) -> None:
        self.server.close()
        if os.path.exists(self.database):
            os.remove(self.database)

    def _quarantine_row(self, **overrides) -> tuple[str, str]:
        row = {
            "account_id": "acct-1",
            "client_id": CLIENT_A,
            "redirect_uri": CALLBACK_A,
            "legacy_handle": LEGACY_HANDLE,
            "state": "import-state-1",
        }
        row.update(overrides)
        status, body = self.server.post("/oauth/import-batches", {"login_ids": [row]})
        self.assertEqual(status, 201)
        return body["batch_id"], body["accepted"][0]["import_id"]

    def _commit(self, batch_id: str) -> None:
        status, body = self.server.post(
            f"/oauth/import-batches/{batch_id}/validate", {"commit": True}
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "committed")

    def _committed_import(self, **overrides) -> str:
        batch_id, import_id = self._quarantine_row(**overrides)
        self._commit(batch_id)
        return import_id

    # -- rejections ----------------------------------------------------
    def test_quarantined_row_is_rejected_before_commit(self) -> None:
        _, import_id = self._quarantine_row()
        status, body = self.server.post(
            f"/oauth/imports/{import_id}/complete", {"account_id": "acct-1", "password": "hunter2"}
        )
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "invalid_login"})

    def test_wrong_password_after_commit_is_rejected(self) -> None:
        import_id = self._committed_import()
        status, body = self.server.post(
            f"/oauth/imports/{import_id}/complete", {"account_id": "acct-1", "password": "wrong"}
        )
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "invalid_credentials"})

    def test_callback_substitution_is_rejected(self) -> None:
        import_id = self._committed_import()
        status, body = self.server.post(
            f"/oauth/imports/{import_id}/complete",
            {
                "account_id": "acct-1",
                "password": "hunter2",
                "redirect_uri": "http://attacker.example/steal",
            },
        )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

    def test_wrong_client_exchange_is_rejected(self) -> None:
        import_id = self._committed_import()
        _, complete_body = self.server.post(
            f"/oauth/imports/{import_id}/complete", {"account_id": "acct-1", "password": "hunter2"}
        )
        query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(complete_body["location"]).query))
        code = urllib.parse.unquote(query["code"])

        status, body = self.server.post("/oauth/token", {"client_id": CLIENT_B, "code": code})
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "wrong_client"})

    # -- full flow: complete, exchange, single-use, replay ----------------
    def test_completed_import_exchanges_for_bound_token_and_rejects_replay(self) -> None:
        import_id = self._committed_import(state="caller-state-77")

        status, complete_body = self.server.post(
            f"/oauth/imports/{import_id}/complete", {"account_id": "acct-1", "password": "hunter2"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(set(complete_body.keys()), {"location"})
        parsed = urllib.parse.urlsplit(complete_body["location"])
        self.assertEqual(f"{parsed.scheme}://{parsed.netloc}{parsed.path}", CALLBACK_A)
        query = dict(urllib.parse.parse_qsl(parsed.query))
        self.assertEqual(query["state"], "caller-state-77")
        code = urllib.parse.unquote(query["code"])

        # Provenance and expiry, verified before exchange.
        code_record = self.server.service.store.get_authorization_code(code)
        self.assertIsNotNone(code_record)
        self.assertEqual(code_record.client_id, CLIENT_A)
        self.assertEqual(code_record.account_id, "acct-1")
        self.assertEqual(code_record.login_id, import_id)
        self.assertFalse(code_record.used)
        self.assertGreater(code_record.expires_at, time.time())

        exchange_status, exchange_body = self.server.post(
            "/oauth/token", {"client_id": CLIENT_A, "code": code}
        )
        self.assertEqual(exchange_status, 200)
        self.assertEqual(set(exchange_body.keys()), {"access_token", "client_id", "account_id"})
        self.assertEqual(exchange_body["client_id"], CLIENT_A)
        self.assertEqual(exchange_body["account_id"], "acct-1")
        self.assertTrue(exchange_body["access_token"])

        # Single-use: the code is now consumed.
        used_record = self.server.service.store.get_authorization_code(code)
        self.assertTrue(used_record.used)

        replay_status, replay_body = self.server.post(
            "/oauth/token", {"client_id": CLIENT_A, "code": code}
        )
        self.assertEqual(replay_status, 403)
        self.assertEqual(replay_body, {"error": "invalid_code"})

    # -- proves the route consumes oauthsvc.resume.recover_client_and_callback
    def test_completion_consumes_recover_client_and_callback_exactly_once(self) -> None:
        import_id = self._committed_import()
        pending = self.server.service.store.get_pending_authorization(import_id)
        stored_locator = pending.resume_value

        with patch.object(
            resume, "recover_client_and_callback", wraps=resume.recover_client_and_callback
        ) as recover_spy:
            status, body = self.server.post(
                f"/oauth/imports/{import_id}/complete",
                {"account_id": "acct-1", "password": "hunter2"},
            )

        self.assertEqual(status, 200)
        self.assertIn(CALLBACK_A, body["location"])
        recover_spy.assert_called_once()
        call_args = recover_spy.call_args.args
        self.assertEqual(call_args[0], stored_locator)
        self.assertEqual(call_args[1], CLIENT_A)


if __name__ == "__main__":
    unittest.main()
