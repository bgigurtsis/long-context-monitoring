"""Authorization codes are short-lived: `--code-ttl-seconds` controls the
expiry deterministically, and the CLI enforces it must be a positive
integer."""
from __future__ import annotations

import contextlib
import io
import tempfile
import time
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from oauthsvc.cli import _build_parser
from tests._util import post_json, run_cli, start_server


class CodeTtlFlagTests(unittest.TestCase):
    def test_accepts_positive_integer(self) -> None:
        args = _build_parser().parse_args(
            ["serve", "--database", "state.db", "--signing-key", "k", "--code-ttl-seconds", "5"]
        )
        self.assertEqual(args.code_ttl_seconds, 5)

    def test_defaults_when_omitted(self) -> None:
        args = _build_parser().parse_args(["serve", "--database", "state.db", "--signing-key", "k"])
        self.assertEqual(args.code_ttl_seconds, 60)

    def test_rejects_zero_and_negative(self) -> None:
        for bad_value in ("0", "-1", "not-a-number"):
            with self.subTest(bad_value=bad_value):
                with contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit):
                        _build_parser().parse_args(
                            [
                                "serve",
                                "--database",
                                "state.db",
                                "--signing-key",
                                "k",
                                "--code-ttl-seconds",
                                bad_value,
                            ]
                        )


class CodeExpiryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db = str(Path(self._tmpdir.name) / "state.db")
        run_cli("create-account", "acct-1", "a@example.com", "pw123", "--database", self.db)
        run_cli("register-client", "client-a", "http://127.0.0.1:9999/cb", "--database", self.db)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _issue_code(self, server) -> str:
        _, authorize_body = post_json(
            server.base_url,
            "/oauth/authorize",
            {"client_id": "client-a", "redirect_uri": "http://127.0.0.1:9999/cb", "state": "s"},
        )
        _, complete_body = post_json(
            server.base_url,
            "/login/complete",
            {"login_id": authorize_body["login_id"], "account_id": "acct-1", "password": "pw123"},
        )
        query = parse_qs(urlparse(complete_body["location"]).query)
        return query["code"][0]

    def test_code_usable_before_expiry(self) -> None:
        server = start_server(self.db, code_ttl_seconds=5)
        try:
            code = self._issue_code(server)
            status, _ = post_json(server.base_url, "/oauth/token", {"client_id": "client-a", "code": code})
            self.assertEqual(status, 200)
        finally:
            server.close()

    def test_code_rejected_after_expiry(self) -> None:
        server = start_server(self.db, code_ttl_seconds=1)
        try:
            code = self._issue_code(server)
            time.sleep(1.2)
            status, body = post_json(server.base_url, "/oauth/token", {"client_id": "client-a", "code": code})
            self.assertEqual(status, 403)
            self.assertEqual(body, {"error": "invalid_code"})
        finally:
            server.close()


if __name__ == "__main__":
    unittest.main()
