"""Replay tests: authorization codes are single-use and short-lived, using
--code-ttl-seconds-style construction for deterministic expiry."""
from __future__ import annotations

import os
import tempfile
import time
import unittest
import urllib.parse

from tests.helpers import RunningServer

CLIENT_ID = "billing-portal-a"
CALLBACK = "http://127.0.0.1:4421/oauth/return"


class ReplayTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.database = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(self.database)

    def tearDown(self) -> None:
        if os.path.exists(self.database):
            os.remove(self.database)

    def _obtain_code(self, server: RunningServer) -> str:
        _, authorize_body = server.post(
            "/oauth/authorize", {"client_id": CLIENT_ID, "redirect_uri": CALLBACK, "state": "s1"}
        )
        _, login_body = server.post(
            "/login/complete",
            {"login_id": authorize_body["login_id"], "account_id": "acct-1", "password": "hunter2"},
        )
        query = login_body["location"].split("?", 1)[1]
        params = dict(part.split("=", 1) for part in query.split("&"))
        return urllib.parse.unquote(params["code"])

    def test_replayed_code_is_rejected(self) -> None:
        server = RunningServer(self.database, code_ttl_seconds=120)
        try:
            server.service.register_client(CLIENT_ID, CALLBACK)
            server.service.create_account("acct-1", "a@example.com", "hunter2")
            code = self._obtain_code(server)

            first_status, _ = server.post("/oauth/token", {"client_id": CLIENT_ID, "code": code})
            self.assertEqual(first_status, 200)

            second_status, second_body = server.post(
                "/oauth/token", {"client_id": CLIENT_ID, "code": code}
            )
            self.assertEqual(second_status, 403)
            self.assertEqual(second_body, {"error": "invalid_code"})
        finally:
            server.close()

    def test_expired_code_is_rejected_with_short_ttl(self) -> None:
        server = RunningServer(self.database, code_ttl_seconds=1)
        try:
            server.service.register_client(CLIENT_ID, CALLBACK)
            server.service.create_account("acct-1", "a@example.com", "hunter2")
            code = self._obtain_code(server)

            time.sleep(1.2)

            status, body = server.post("/oauth/token", {"client_id": CLIENT_ID, "code": code})
            self.assertEqual(status, 403)
            self.assertEqual(body, {"error": "invalid_code"})
        finally:
            server.close()

    def test_expired_code_stays_rejected_on_further_attempts(self) -> None:
        server = RunningServer(self.database, code_ttl_seconds=1)
        try:
            server.service.register_client(CLIENT_ID, CALLBACK)
            server.service.create_account("acct-1", "a@example.com", "hunter2")
            code = self._obtain_code(server)
            time.sleep(1.2)

            first_status, _ = server.post("/oauth/token", {"client_id": CLIENT_ID, "code": code})
            second_status, _ = server.post("/oauth/token", {"client_id": CLIENT_ID, "code": code})

            self.assertEqual(first_status, 403)
            self.assertEqual(second_status, 403)
        finally:
            server.close()


if __name__ == "__main__":
    unittest.main()
