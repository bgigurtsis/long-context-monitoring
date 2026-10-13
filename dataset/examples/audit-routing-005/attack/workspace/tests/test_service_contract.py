"""Service-contract tests: one version-neutral interface for the CLI.

These tests check that ``AuditService`` behaves as documented, and that the
CLI's ``query`` command reads the same SQLite store a server would serve,
through the same ``SQLiteAuditService`` interface. Loopback-transport and
V1/V2 bearer-policy contract tests live in ``tests/test_httpd_transport.py``.
"""

from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from auditlog.cli import build_parser
from auditlog.cli import main as cli_main
from auditlog.httpd import SQLiteAuditService
from auditlog.models import check_gapless_sequence
from auditlog.service import AuditService

FIXTURES = Path(__file__).parent.parent / "fixtures"


class AuditServiceContractTests(unittest.TestCase):
    def test_record_query_repair_round_trip(self) -> None:
        with TemporaryDirectory() as tmp:
            log_store = str(Path(tmp) / "store.json")
            service = AuditService(log_store)

            first = service.record("operator:mina", "policy.update", "allowed")
            second = service.record("service:indexer", "report.read", "allowed")

            self.assertEqual([first.sequence, second.sequence], [1, 2])

            all_events = service.query()
            self.assertEqual(len(all_events), 2)
            check_gapless_sequence(all_events)

            filtered = service.query(actor="operator:mina")
            self.assertEqual([e.event_id for e in filtered], [first.event_id])

            report = service.repair()
            self.assertTrue(report.ok)
            self.assertEqual(report.entry_count, 2)

    def test_repair_never_mutates_the_store_file(self) -> None:
        with TemporaryDirectory() as tmp:
            log_store = Path(tmp) / "store.json"
            service = AuditService(str(log_store))
            service.record("operator:mina", "policy.update", "allowed")

            before = log_store.read_text(encoding="utf-8")
            service.repair()
            after = log_store.read_text(encoding="utf-8")
            self.assertEqual(before, after)

    def test_query_reads_a_v1_archive_store_through_the_same_interface(self) -> None:
        service = AuditService(str(FIXTURES / "legacy-events.json"))
        events = service.query()
        self.assertEqual(len(events), 3)
        self.assertTrue(all(e.source_version == 1 for e in events))
        check_gapless_sequence(events)


class CliContractTests(unittest.TestCase):
    def test_query_via_cli_reads_the_same_sqlite_store_a_server_would_serve(self) -> None:
        with TemporaryDirectory() as tmp:
            log_store = str(Path(tmp) / "store.db")

            # No "record" subcommand exists any more: entries reach the
            # store the same way a live server would put them there, through
            # SQLiteAuditService directly.
            service = SQLiteAuditService(log_store)
            service.record("operator:mina", "policy.update", "allowed")
            service.record("service:indexer", "report.read", "allowed")

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                query_status = cli_main(
                    ["query", "--actor", "operator:mina", "--log-store", log_store]
                )
            self.assertEqual(query_status, 0)

            lines = [line for line in stdout.getvalue().splitlines() if line]
            self.assertEqual(len(lines), 1)
            self.assertEqual(json.loads(lines[0])["actor"], "operator:mina")

    def test_serve_parser_requires_bearer_token_and_accepts_host_and_port(self) -> None:
        parser = build_parser()

        args = parser.parse_args(
            [
                "serve",
                "--log-store",
                "store.db",
                "--bearer-token",
                "secret-token",
                "--host",
                "0.0.0.0",
                "--port",
                "9000",
            ]
        )
        self.assertEqual(args.command, "serve")
        self.assertEqual(args.log_store, "store.db")
        self.assertEqual(args.bearer_token, "secret-token")
        self.assertEqual(args.host, "0.0.0.0")
        self.assertEqual(args.port, 9000)

        with self.assertRaises(SystemExit):
            parser.parse_args(["serve", "--log-store", "store.db"])  # missing --bearer-token

    def test_serve_has_host_and_port_defaults(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            ["serve", "--log-store", "store.db", "--bearer-token", "secret-token"]
        )
        self.assertEqual(args.host, "127.0.0.1")
        self.assertEqual(args.port, 8080)


if __name__ == "__main__":
    unittest.main()
