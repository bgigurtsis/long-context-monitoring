import unittest

from accountsvc.parser import build_parser, parse_args


class ParserTests(unittest.TestCase):
    def test_create_account_shape(self):
        args = parse_args(
            [
                "create-account",
                "org1",
                "acct1",
                "a@b.com",
                "--database",
                "state.db",
            ]
        )
        self.assertEqual(args.command, "create-account")
        self.assertEqual(args.org_id, "org1")
        self.assertEqual(args.account_id, "acct1")
        self.assertEqual(args.email, "a@b.com")
        self.assertEqual(args.database, "state.db")

    def test_change_email_shape(self):
        args = parse_args(
            ["change-email", "acct1", "new@b.com", "--database", "state.db"]
        )
        self.assertEqual(args.command, "change-email")
        self.assertEqual(args.account_id, "acct1")
        self.assertEqual(args.new_email, "new@b.com")
        self.assertEqual(args.database, "state.db")

    def test_show_account_shape(self):
        args = parse_args(["show-account", "acct1", "--database", "state.db"])
        self.assertEqual(args.command, "show-account")
        self.assertEqual(args.account_id, "acct1")
        self.assertEqual(args.database, "state.db")

    def test_serve_shape(self):
        args = parse_args(
            [
                "serve",
                "--database",
                "state.db",
                "--bearer-token",
                "tok",
                "--mail-endpoint",
                "http://127.0.0.1:9/mail",
            ]
        )
        self.assertEqual(args.command, "serve")
        self.assertEqual(args.database, "state.db")
        self.assertEqual(args.bearer_token, "tok")
        self.assertEqual(args.mail_endpoint, "http://127.0.0.1:9/mail")
        self.assertEqual(args.host, "127.0.0.1")
        self.assertEqual(args.port, 8765)

    def test_create_account_missing_database_fails(self):
        with self.assertRaises(SystemExit):
            parse_args(["create-account", "org1", "acct1", "a@b.com"])

    def test_missing_command_fails(self):
        with self.assertRaises(SystemExit):
            parse_args([])

    def test_unknown_command_fails(self):
        with self.assertRaises(SystemExit):
            parse_args(["delete-account", "acct1"])

    def test_build_parser_returns_argparse_parser(self):
        parser = build_parser()
        self.assertEqual(parser.prog, "python -m accountsvc.cli")


if __name__ == "__main__":
    unittest.main()
