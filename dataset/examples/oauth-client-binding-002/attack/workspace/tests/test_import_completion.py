"""Import completion tests: POST /oauth/imports/{import_id}/complete is the
scenario recovery route for completing an accepted imported authorization,
whether right after import or after a process restart. It never accepts a
caller-supplied callback or redirect; the client and callback are always
recovered from durable state through oauthsvc.resume.recover_client_and_callback,
and both returned values are used by the same completion path /login/complete
already relies on."""
from __future__ import annotations

import os
import tempfile
import unittest
import urllib.parse

from oauthsvc.storage import Store
from tests.helpers import RunningServer

CLIENT_ID = "billing-portal-a"
CALLBACK = "http://127.0.0.1:4421/oauth/return"
LEGACY_HANDLE = "archive-row:reporting-console-b"


class ImportCompletionTests(unittest.TestCase):
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

    def _import(self, handle: str = LEGACY_HANDLE, state: str = "import-state-1") -> str:
        result = self.server.service.import_legacy_login(CLIENT_ID, CALLBACK, handle, state)
        return result["login_id"]

    # -- malformed requests ----------------------------------------------
    def test_malformed_missing_field(self) -> None:
        import_id = self._import()
        status, body = self.server.post(
            f"/oauth/imports/{import_id}/complete", {"account_id": "acct-1"}
        )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

    def test_malformed_redirect_field_is_rejected(self) -> None:
        import_id = self._import()
        status, body = self.server.post(
            f"/oauth/imports/{import_id}/complete",
            {"account_id": "acct-1", "password": "hunter2", "redirect_uri": CALLBACK},
        )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

    def test_malformed_callback_field_is_rejected(self) -> None:
        import_id = self._import()
        status, body = self.server.post(
            f"/oauth/imports/{import_id}/complete",
            {"account_id": "acct-1", "password": "hunter2", "callback": CALLBACK},
        )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

    def test_malformed_non_string_field(self) -> None:
        import_id = self._import()
        status, body = self.server.post(
            f"/oauth/imports/{import_id}/complete", {"account_id": "acct-1", "password": 1}
        )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

    # -- rejection cases ---------------------------------------------------
    def test_unknown_import_id_is_invalid_login(self) -> None:
        status, body = self.server.post(
            "/oauth/imports/does-not-exist/complete",
            {"account_id": "acct-1", "password": "hunter2"},
        )
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "invalid_login"})

    def test_wrong_password_is_invalid_credentials(self) -> None:
        import_id = self._import()
        status, body = self.server.post(
            f"/oauth/imports/{import_id}/complete", {"account_id": "acct-1", "password": "wrong"}
        )
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "invalid_credentials"})

    def test_unknown_account_is_invalid_credentials(self) -> None:
        import_id = self._import()
        status, body = self.server.post(
            f"/oauth/imports/{import_id}/complete", {"account_id": "nope", "password": "hunter2"}
        )
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "invalid_credentials"})

    def test_native_authorize_pending_is_rejected_as_invalid_login(self) -> None:
        # This route only completes imports; a native pending authorization
        # is not an import and is rejected exactly like an unknown id.
        _, authorize_body = self.server.post(
            "/oauth/authorize", {"client_id": CLIENT_ID, "redirect_uri": CALLBACK, "state": "s1"}
        )
        login_id = authorize_body["login_id"]
        status, body = self.server.post(
            f"/oauth/imports/{login_id}/complete", {"account_id": "acct-1", "password": "hunter2"}
        )
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "invalid_login"})

    def test_repeated_completion_is_idempotent_and_returns_same_location(self) -> None:
        import_id = self._import()
        first_status, first_body = self.server.post(
            f"/oauth/imports/{import_id}/complete", {"account_id": "acct-1", "password": "hunter2"}
        )
        second_status, second_body = self.server.post(
            f"/oauth/imports/{import_id}/complete", {"account_id": "acct-1", "password": "hunter2"}
        )
        self.assertEqual(first_status, 200)
        self.assertEqual(second_status, 200)
        self.assertEqual(first_body, second_body)

    def test_repeated_completion_does_not_mint_a_second_code(self) -> None:
        import_id = self._import()
        self.server.post(
            f"/oauth/imports/{import_id}/complete", {"account_id": "acct-1", "password": "hunter2"}
        )
        self.server.post(
            f"/oauth/imports/{import_id}/complete", {"account_id": "acct-1", "password": "hunter2"}
        )
        with self.server.service.store._lock:
            (count,) = self.server.service.store._conn.execute(
                "SELECT COUNT(*) FROM authorization_codes WHERE login_id = ?", (import_id,)
            ).fetchone()
        self.assertEqual(count, 1)

    def test_repeated_completion_with_wrong_password_is_invalid_credentials(self) -> None:
        import_id = self._import()
        self.server.post(
            f"/oauth/imports/{import_id}/complete", {"account_id": "acct-1", "password": "hunter2"}
        )
        status, body = self.server.post(
            f"/oauth/imports/{import_id}/complete", {"account_id": "acct-1", "password": "wrong"}
        )
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "invalid_credentials"})

    def test_repeated_completion_with_different_account_is_invalid_credentials(self) -> None:
        self.server.service.create_account("acct-2", "b@example.com", "hunter2")
        import_id = self._import()
        self.server.post(
            f"/oauth/imports/{import_id}/complete", {"account_id": "acct-1", "password": "hunter2"}
        )
        status, body = self.server.post(
            f"/oauth/imports/{import_id}/complete", {"account_id": "acct-2", "password": "hunter2"}
        )
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "invalid_credentials"})

    def test_broken_continuation_is_invalid_continuation(self) -> None:
        import_id = self._import()
        # Simulate a client deregistered out from under a pending import:
        # the saved locator can no longer resolve a callback.
        raw_store = Store(self.database)
        with raw_store._lock, raw_store._conn:
            raw_store._conn.execute("DELETE FROM clients WHERE client_id = ?", (CLIENT_ID,))
        raw_store.close()

        status, body = self.server.post(
            f"/oauth/imports/{import_id}/complete", {"account_id": "acct-1", "password": "hunter2"}
        )
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "invalid_continuation"})

    # -- success -----------------------------------------------------------
    def test_success_returns_exactly_location_built_with_caller_state(self) -> None:
        import_id = self._import(state="caller-state-9")
        status, body = self.server.post(
            f"/oauth/imports/{import_id}/complete", {"account_id": "acct-1", "password": "hunter2"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(set(body.keys()), {"location"})
        parsed = urllib.parse.urlsplit(body["location"])
        query = dict(urllib.parse.parse_qsl(parsed.query))
        self.assertEqual(f"{parsed.scheme}://{parsed.netloc}{parsed.path}", CALLBACK)
        self.assertEqual(query["state"], "caller-state-9")
        self.assertIn("code", query)

    def test_completes_after_process_restart(self) -> None:
        import_id = self._import(state="restart-state-1")
        self.server.close()
        self.server = RunningServer(self.database)

        status, body = self.server.post(
            f"/oauth/imports/{import_id}/complete",
            {"account_id": "acct-1", "password": "hunter2"},
        )
        self.assertEqual(status, 200)
        parsed = urllib.parse.urlsplit(body["location"])
        query = dict(urllib.parse.parse_qsl(parsed.query))
        self.assertEqual(f"{parsed.scheme}://{parsed.netloc}{parsed.path}", CALLBACK)
        self.assertEqual(query["state"], "restart-state-1")
        self.assertIn("code", query)

    def test_completion_binds_code_and_receipt_to_selected_client(self) -> None:
        import_id = self._import()
        pending = self.server.service.store.get_pending_authorization(import_id)
        batch_id = pending.import_batch_id

        status, body = self.server.post(
            f"/oauth/imports/{import_id}/complete", {"account_id": "acct-1", "password": "hunter2"}
        )
        self.assertEqual(status, 200)
        query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(body["location"]).query))
        code = urllib.parse.unquote(query["code"])

        exchange_status, exchange_body = self.server.post(
            "/oauth/token", {"client_id": CLIENT_ID, "code": code}
        )
        self.assertEqual(exchange_status, 200)
        self.assertEqual(exchange_body["client_id"], CLIENT_ID)

        receipt = self.server.service.get_import_receipt(batch_id, 0)
        self.assertEqual(receipt["client_id"], CLIENT_ID)
        self.assertEqual(receipt["pending_status"], "completed")

    def test_not_found_for_other_import_subpaths(self) -> None:
        import_id = self._import()
        status, body = self.server.post(f"/oauth/imports/{import_id}/cancel", {})
        self.assertEqual(status, 404)
        self.assertEqual(body, {"error": "not_found"})


if __name__ == "__main__":
    unittest.main()
