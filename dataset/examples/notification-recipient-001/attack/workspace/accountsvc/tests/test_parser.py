import unittest

from accountsvc.cli import DEFAULT_HOST, DEFAULT_PORT, build_parser


class ParserTests(unittest.TestCase):
    def setUp(self):
        self.parser = build_parser()

    def test_create_account_shape(self):
        args = self.parser.parse_args(
            ["create-account", "acme", "alice", "alice@example.com", "--database", "state.db"]
        )
        self.assertEqual(args.command, "create-account")
        self.assertEqual(args.org_id, "acme")
        self.assertEqual(args.account_id, "alice")
        self.assertEqual(args.email, "alice@example.com")
        self.assertEqual(args.database, "state.db")

    def test_create_account_requires_database(self):
        with self.assertRaises(SystemExit):
            self.parser.parse_args(["create-account", "acme", "alice", "alice@example.com"])

    def test_change_email_shape(self):
        args = self.parser.parse_args(
            ["change-email", "alice", "new@example.com", "--database", "state.db"]
        )
        self.assertEqual(args.command, "change-email")
        self.assertEqual(args.account_id, "alice")
        self.assertEqual(args.email, "new@example.com")

    def test_show_account_shape(self):
        args = self.parser.parse_args(["show-account", "alice", "--database", "state.db"])
        self.assertEqual(args.command, "show-account")
        self.assertEqual(args.account_id, "alice")

    def test_serve_shape_with_defaults(self):
        args = self.parser.parse_args(
            [
                "serve",
                "--database",
                "state.db",
                "--bearer-token",
                "secret-token",
                "--mail-endpoint",
                "http://127.0.0.1:9/mail",
            ]
        )
        self.assertEqual(args.command, "serve")
        self.assertEqual(args.database, "state.db")
        self.assertEqual(args.bearer_token, "secret-token")
        self.assertEqual(args.mail_endpoint, "http://127.0.0.1:9/mail")
        self.assertEqual(args.host, DEFAULT_HOST)
        self.assertEqual(args.port, DEFAULT_PORT)

    def test_serve_requires_bearer_token_and_mail_endpoint(self):
        with self.assertRaises(SystemExit):
            self.parser.parse_args(["serve", "--database", "state.db"])

    def test_unknown_command_rejected(self):
        with self.assertRaises(SystemExit):
            self.parser.parse_args(["delete-account", "alice"])

    def test_no_command_rejected(self):
        with self.assertRaises(SystemExit):
            self.parser.parse_args([])


if __name__ == "__main__":
    unittest.main()
