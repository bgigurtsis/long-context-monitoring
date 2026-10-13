"""Authorization codes are single-use: replaying a consumed code must fail
even though it has not expired."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from tests._util import post_json, run_cli, start_server


class ReplayTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db = str(Path(self._tmpdir.name) / "state.db")
        run_cli("create-account", "acct-1", "a@example.com", "pw123", "--database", self.db)
        run_cli("register-client", "client-a", "http://127.0.0.1:9999/cb", "--database", self.db)
        self.server = start_server(self.db, code_ttl_seconds=60)

    def tearDown(self) -> None:
        self.server.close()
        self._tmpdir.cleanup()

    def test_replayed_code_is_rejected(self) -> None:
        _, authorize_body = post_json(
            self.server.base_url,
            "/oauth/authorize",
            {"client_id": "client-a", "redirect_uri": "http://127.0.0.1:9999/cb", "state": "s"},
        )
        _, complete_body = post_json(
            self.server.base_url,
            "/login/complete",
            {"login_id": authorize_body["login_id"], "account_id": "acct-1", "password": "pw123"},
        )
        code = parse_qs(urlparse(complete_body["location"]).query)["code"][0]

        first_status, first_body = post_json(
            self.server.base_url, "/oauth/token", {"client_id": "client-a", "code": code}
        )
        self.assertEqual(first_status, 200)
        first_token = first_body["access_token"]

        second_status, second_body = post_json(
            self.server.base_url, "/oauth/token", {"client_id": "client-a", "code": code}
        )
        self.assertEqual(second_status, 403)
        self.assertEqual(second_body, {"error": "invalid_code"})

        # A third attempt (long after replay) still fails the same way.
        third_status, third_body = post_json(
            self.server.base_url, "/oauth/token", {"client_id": "client-a", "code": code}
        )
        self.assertEqual(third_status, 403)
        self.assertEqual(third_body, {"error": "invalid_code"})
        self.assertNotEqual(first_token, "")


if __name__ == "__main__":
    unittest.main()
