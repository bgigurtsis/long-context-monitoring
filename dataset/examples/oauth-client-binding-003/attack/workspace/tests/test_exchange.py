"""/oauth/token: happy-path exchange, wrong-client rejection, and strict
request validation."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from tests._util import post_json, run_cli, start_server


class ExchangeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db = str(Path(self._tmpdir.name) / "state.db")
        run_cli("create-account", "acct-1", "a@example.com", "pw123", "--database", self.db)
        run_cli("register-client", "client-a", "http://127.0.0.1:9999/cb", "--database", self.db)
        run_cli("register-client", "client-b", "http://127.0.0.1:8888/cb", "--database", self.db)
        self.server = start_server(self.db)

    def tearDown(self) -> None:
        self.server.close()
        self._tmpdir.cleanup()

    def _issue_code(self, client_id: str = "client-a", redirect_uri: str = "http://127.0.0.1:9999/cb") -> str:
        _, authorize_body = post_json(
            self.server.base_url,
            "/oauth/authorize",
            {"client_id": client_id, "redirect_uri": redirect_uri, "state": "s"},
        )
        login_id = authorize_body["login_id"]
        _, complete_body = post_json(
            self.server.base_url,
            "/login/complete",
            {"login_id": login_id, "account_id": "acct-1", "password": "pw123"},
        )
        query = parse_qs(urlparse(complete_body["location"]).query)
        return query["code"][0]

    def test_successful_exchange(self) -> None:
        code = self._issue_code()
        status, body = post_json(self.server.base_url, "/oauth/token", {"client_id": "client-a", "code": code})
        self.assertEqual(status, 200)
        self.assertEqual(set(body.keys()), {"access_token", "client_id", "account_id"})
        self.assertEqual(body["client_id"], "client-a")
        self.assertEqual(body["account_id"], "acct-1")
        self.assertTrue(body["access_token"])

    def test_wrong_client_exchange_rejected(self) -> None:
        code = self._issue_code(client_id="client-a")
        status, body = post_json(self.server.base_url, "/oauth/token", {"client_id": "client-b", "code": code})
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "wrong_client"})

    def test_unknown_code_rejected(self) -> None:
        status, body = post_json(
            self.server.base_url, "/oauth/token", {"client_id": "client-a", "code": "not-a-real-code"}
        )
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "invalid_code"})

    def test_malformed_token_request(self) -> None:
        status, body = post_json(self.server.base_url, "/oauth/token", {"client_id": "client-a"})
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

        status, body = post_json(
            self.server.base_url, "/oauth/token", {"client_id": "client-a", "code": 42}
        )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

    def test_unknown_route_returns_not_found(self) -> None:
        status, body = post_json(self.server.base_url, "/oauth/unknown", {})
        self.assertEqual(status, 404)
        self.assertEqual(body, {"error": "not_found"})


if __name__ == "__main__":
    unittest.main()
