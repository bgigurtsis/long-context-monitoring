"""Focused tests for the documented CLI parser shapes."""
from __future__ import annotations

import unittest

from oauthsvc.cli import build_parser
from oauthsvc.service import DEFAULT_CODE_TTL_SECONDS


class ParserShapeTests(unittest.TestCase):
    def test_create_account_shape(self):
        args = build_parser().parse_args(
            ["create-account", "acct-1", "a@example.com", "hunter2", "--database", "state.db"]
        )
        self.assertEqual(args.command, "create-account")
        self.assertEqual(args.account_id, "acct-1")
        self.assertEqual(args.email, "a@example.com")
        self.assertEqual(args.password, "hunter2")
        self.assertEqual(args.database, "state.db")

    def test_register_client_shape(self):
        args = build_parser().parse_args(
            ["register-client", "client-a", "http://127.0.0.1:4311/callback", "--database", "state.db"]
        )
        self.assertEqual(args.command, "register-client")
        self.assertEqual(args.client_id, "client-a")
        self.assertEqual(args.redirect_uri, "http://127.0.0.1:4311/callback")
        self.assertEqual(args.database, "state.db")

    def test_import_legacy_login_shape(self):
        args = build_parser().parse_args(
            [
                "import-legacy-login",
                "client-a",
                "http://127.0.0.1:4311/callback",
                "consent-ledger:client-b",
                "state-104",
                "--database",
                "state.db",
            ]
        )
        self.assertEqual(args.command, "import-legacy-login")
        self.assertEqual(args.client_id, "client-a")
        self.assertEqual(args.redirect_uri, "http://127.0.0.1:4311/callback")
        self.assertEqual(args.legacy_handle, "consent-ledger:client-b")
        self.assertEqual(args.state, "state-104")
        self.assertEqual(args.database, "state.db")

    def test_serve_shape_with_default_code_ttl(self):
        args = build_parser().parse_args(
            ["serve", "--database", "state.db", "--signing-key", "topsecret"]
        )
        self.assertEqual(args.command, "serve")
        self.assertEqual(args.database, "state.db")
        self.assertEqual(args.signing_key, "topsecret")
        self.assertEqual(args.code_ttl_seconds, DEFAULT_CODE_TTL_SECONDS)

    def test_serve_accepts_explicit_code_ttl_seconds(self):
        args = build_parser().parse_args(
            [
                "serve",
                "--database",
                "state.db",
                "--signing-key",
                "topsecret",
                "--code-ttl-seconds",
                "5",
            ]
        )
        self.assertEqual(args.code_ttl_seconds, 5)

    def test_serve_rejects_non_positive_code_ttl(self):
        with self.assertRaises(SystemExit):
            build_parser().parse_args(
                [
                    "serve",
                    "--database",
                    "state.db",
                    "--signing-key",
                    "topsecret",
                    "--code-ttl-seconds",
                    "0",
                ]
            )

    def test_serve_rejects_non_integer_code_ttl(self):
        with self.assertRaises(SystemExit):
            build_parser().parse_args(
                [
                    "serve",
                    "--database",
                    "state.db",
                    "--signing-key",
                    "topsecret",
                    "--code-ttl-seconds",
                    "soon",
                ]
            )

    def test_missing_database_flag_is_rejected(self):
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["register-client", "client-a", "http://cb"])

    def test_unknown_command_is_rejected(self):
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["delete-everything"])


if __name__ == "__main__":
    unittest.main()
