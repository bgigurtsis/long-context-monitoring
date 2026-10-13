"""CLI surface tests for the ``serve`` subcommand."""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr

from auditlog.cli import build_parser, main


class ServeParserSurfaceTests(unittest.TestCase):
    def test_serve_is_a_subcommand(self) -> None:
        parser = build_parser()
        choices = parser._subparsers._group_actions[0].choices
        self.assertIn("serve", choices)

    def test_serve_requires_log_store_and_bearer_token(self) -> None:
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["serve"])

    def test_serve_accepts_all_four_documented_options(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "serve",
                "--log-store",
                "store.sqlite3",
                "--bearer-token",
                "tok",
                "--host",
                "127.0.0.1",
                "--port",
                "9999",
            ]
        )
        self.assertEqual(args.log_store, "store.sqlite3")
        self.assertEqual(args.bearer_token, "tok")
        self.assertEqual(args.host, "127.0.0.1")
        self.assertEqual(args.port, 9999)

    def test_serve_defaults_host_and_port(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["serve", "--log-store", "store.sqlite3", "--bearer-token", "tok"])
        self.assertEqual(args.host, "127.0.0.1")
        self.assertEqual(args.port, 8765)


class ServeRefusesNonLoopbackHostsTests(unittest.TestCase):
    def test_non_loopback_host_is_refused_without_starting_a_server(self) -> None:
        with redirect_stderr(io.StringIO()) as captured:
            with self.assertRaises(SystemExit) as ctx:
                main(
                    [
                        "serve",
                        "--log-store",
                        "unused.sqlite3",
                        "--bearer-token",
                        "tok",
                        "--host",
                        "192.168.1.5",
                    ]
                )
        self.assertEqual(ctx.exception.code, 2)
        self.assertIn("loopback", captured.getvalue())

    def test_refused_host_never_creates_the_log_store_file(self) -> None:
        import os

        path = "unused-refused.sqlite3"
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                main(["serve", "--log-store", path, "--bearer-token", "tok", "--host", "0.0.0.0"])
        self.assertFalse(os.path.exists(path))


if __name__ == "__main__":
    unittest.main()
