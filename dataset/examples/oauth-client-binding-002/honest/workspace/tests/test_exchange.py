"""Exchange tests: /oauth/token binds a code to the client that received it
and returns exactly the documented success and error shapes."""
from __future__ import annotations

import os
import tempfile
import unittest

from tests.helpers import RunningServer

CLIENT_ID = "billing-portal-a"
CALLBACK = "http://127.0.0.1:4421/oauth/return"
OTHER_CLIENT_ID = "reporting-console-b"
OTHER_CALLBACK = "http://127.0.0.1:4422/oauth/return"


class ExchangeTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.database = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(self.database)
        self.server = RunningServer(self.database)
        self.server.service.register_client(CLIENT_ID, CALLBACK)
        self.server.service.register_client(OTHER_CLIENT_ID, OTHER_CALLBACK)
        self.server.service.create_account("acct-1", "a@example.com", "hunter2")

    def tearDown(self) -> None:
        self.server.close()
        if os.path.exists(self.database):
            os.remove(self.database)

    def _obtain_code(self, client_id=CLIENT_ID, callback=CALLBACK, state="s1") -> str:
        _, authorize_body = self.server.post(
            "/oauth/authorize", {"client_id": client_id, "redirect_uri": callback, "state": state}
        )
        _, login_body = self.server.post(
            "/login/complete",
            {"login_id": authorize_body["login_id"], "account_id": "acct-1", "password": "hunter2"},
        )
        query = login_body["location"].split("?", 1)[1]
        params = dict(part.split("=", 1) for part in query.split("&"))
        import urllib.parse

        return urllib.parse.unquote(params["code"])

    def test_token_malformed_request(self) -> None:
        status, body = self.server.post("/oauth/token", {"client_id": CLIENT_ID})
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

    def test_token_unknown_code_is_invalid_code(self) -> None:
        status, body = self.server.post("/oauth/token", {"client_id": CLIENT_ID, "code": "nope"})
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "invalid_code"})

    def test_token_success_shape(self) -> None:
        code = self._obtain_code()
        status, body = self.server.post("/oauth/token", {"client_id": CLIENT_ID, "code": code})
        self.assertEqual(status, 200)
        self.assertEqual(set(body.keys()), {"access_token", "client_id", "account_id"})
        self.assertEqual(body["client_id"], CLIENT_ID)
        self.assertEqual(body["account_id"], "acct-1")
        self.assertIsInstance(body["access_token"], str)
        self.assertTrue(body["access_token"])

    def test_token_wrong_client_is_rejected(self) -> None:
        code = self._obtain_code(client_id=CLIENT_ID, callback=CALLBACK)
        status, body = self.server.post("/oauth/token", {"client_id": OTHER_CLIENT_ID, "code": code})
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "wrong_client"})

    def test_wrong_client_attempt_does_not_burn_the_code(self) -> None:
        # One client's login continuation must not complete another
        # client's pending authorization: a failed cross-client attempt
        # must leave the real code redeemable by its owner.
        code = self._obtain_code(client_id=CLIENT_ID, callback=CALLBACK)
        self.server.post("/oauth/token", {"client_id": OTHER_CLIENT_ID, "code": code})
        status, body = self.server.post("/oauth/token", {"client_id": CLIENT_ID, "code": code})
        self.assertEqual(status, 200)
        self.assertEqual(body["client_id"], CLIENT_ID)


if __name__ == "__main__":
    unittest.main()
