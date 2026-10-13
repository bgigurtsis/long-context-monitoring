"""Tests for the CLI surface, focused on the ``serve`` subcommand."""

from __future__ import annotations

import io
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from auditlog import httpd
from auditlog.cli import build_parser, main
from auditlog.service import AuditService
from auditlog.storage import SqliteStore


class ServeParserTests(unittest.TestCase):
    def test_serve_is_a_subcommand(self) -> None:
        parser = build_parser()
        choices = parser._subparsers._group_actions[0].choices
        self.assertIn("serve", choices)

    def test_serve_requires_log_store_and_bearer_token(self) -> None:
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["serve"])

    def test_serve_defaults_host_and_port(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            ["serve", "--log-store", "store.db", "--bearer-token", "secret"]
        )
        self.assertEqual(args.host, "127.0.0.1")
        self.assertEqual(args.port, 8080)

    def test_serve_accepts_explicit_host_and_port(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "serve",
                "--log-store",
                "store.db",
                "--bearer-token",
                "secret",
                "--host",
                "::1",
                "--port",
                "9090",
            ]
        )
        self.assertEqual(args.host, "::1")
        self.assertEqual(args.port, 9090)


class CliAndHttpShareOneSqliteStoreTests(unittest.TestCase):
    """``record``/``query``/``repair`` and ``serve`` use one SQLite store format
    and path, so entries recorded through one surface are immediately visible
    through the other."""

    def setUp(self) -> None:
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmpdir, ignore_errors=True)
        self.log_store = str(Path(tmpdir) / "store.db")

    def test_cli_record_is_visible_through_a_direct_sqlite_query(self) -> None:
        main(["record", "operator:mina", "policy.update", "allowed", "--log-store", self.log_store])

        events = AuditService(SqliteStore(self.log_store)).query()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].actor, "operator:mina")
        self.assertEqual(events[0].sequence, 1)

    def test_cli_query_sees_an_entry_recorded_through_a_direct_sqlite_store(self) -> None:
        AuditService(SqliteStore(self.log_store)).record("operator:mina", "policy.update", "allowed")

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            main(["query", "--log-store", self.log_store])
        self.assertIn("operator:mina", buffer.getvalue())

    def test_cli_recording_then_serving_over_the_same_path_sees_the_entry(self) -> None:
        main(["record", "operator:mina", "policy.update", "allowed", "--log-store", self.log_store])

        server = httpd.build_server(self.log_store, "secret", host="127.0.0.1", port=0)
        try:
            events = server.service.query()
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].actor, "operator:mina")
        finally:
            server.server_close()


class ServeRefusesNonLoopbackHostTests(unittest.TestCase):
    def test_main_rejects_a_non_loopback_host_before_binding(self) -> None:
        with self.assertRaises(SystemExit):
            main(
                [
                    "serve",
                    "--log-store",
                    "store.db",
                    "--bearer-token",
                    "secret",
                    "--host",
                    "0.0.0.0",
                ]
            )


if __name__ == "__main__":
    unittest.main()
