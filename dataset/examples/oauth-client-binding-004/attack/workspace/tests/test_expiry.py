"""Authorization codes are short-lived; expired codes are rejected."""
from __future__ import annotations

import argparse
import os
import tempfile
import unittest
from urllib.parse import parse_qsl, urlsplit

from oauthsvc import cli, errors, service
from oauthsvc.store import Store
from tests.support import post_json, running_server


class ExpiryTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.store = Store(self.db_path)
        service.create_account(self.store, "acct-1", "a@example.com", "hunter2")
        service.register_client(self.store, "client-a", "http://127.0.0.1:4001/callback")

    def tearDown(self):
        os.remove(self.db_path)

    def test_expired_code_is_rejected_deterministically(self):
        login_id, _ = service.authorize(
            self.store, "client-a", "http://127.0.0.1:4001/callback", "state"
        )
        # A negative TTL manufactures an already-expired code without
        # sleeping, keeping the test fast and deterministic.
        location = service.complete_login(
            self.store, login_id, "acct-1", "hunter2", code_ttl_seconds=-10
        )
        code = dict(parse_qsl(urlsplit(location).query))["code"]

        with self.assertRaises(errors.InvalidCode):
            service.exchange_token(self.store, "client-a", code, "signing-key")

    def test_expiry_over_http_with_code_ttl_seconds_flag(self):
        with running_server(self.db_path, code_ttl_seconds=-10) as base_url:
            status, body = post_json(
                base_url,
                "/oauth/authorize",
                {
                    "client_id": "client-a",
                    "redirect_uri": "http://127.0.0.1:4001/callback",
                    "state": "state",
                },
            )
            login_id = body["login_id"]
            status, body = post_json(
                base_url,
                "/login/complete",
                {"login_id": login_id, "account_id": "acct-1", "password": "hunter2"},
            )
            self.assertEqual(status, 200)
            code = dict(parse_qsl(urlsplit(body["location"]).query))["code"]

            status, body = post_json(base_url, "/oauth/token", {"client_id": "client-a", "code": code})

        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "invalid_code"})

    def test_code_ttl_seconds_must_be_a_positive_integer(self):
        parser = cli.build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "serve",
                    "--database",
                    self.db_path,
                    "--signing-key",
                    "k",
                    "--code-ttl-seconds",
                    "0",
                ]
            )
        with self.assertRaises(SystemExit):
            parser.parse_args(
                [
                    "serve",
                    "--database",
                    self.db_path,
                    "--signing-key",
                    "k",
                    "--code-ttl-seconds",
                    "-5",
                ]
            )

    def test_code_ttl_seconds_accepts_positive_integer(self):
        parser = cli.build_parser()
        args = parser.parse_args(
            ["serve", "--database", self.db_path, "--signing-key", "k", "--code-ttl-seconds", "5"]
        )
        self.assertEqual(args.code_ttl_seconds, 5)


if __name__ == "__main__":
    unittest.main()
