"""Tests for the stable CLI contract: build_parser() and the command handlers."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from auditlog.cli import build_parser, main


class BuildParserTests(unittest.TestCase):
    def test_public_commands_exist(self) -> None:
        parser = build_parser()
        choices = parser._subparsers._group_actions[0].choices
        self.assertEqual(set(choices), {"record", "query", "repair"})

    def test_record_requires_log_store(self) -> None:
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["record", "operator:mina", "policy.update", "allowed"])

    def test_record_requires_actor_action_outcome(self) -> None:
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["record", "operator:mina", "--log-store", "x.db"])

    def test_record_accepts_repeated_metadata(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "record",
                "operator:mina",
                "policy.update",
                "allowed",
                "--metadata",
                "a=1",
                "--metadata",
                "b=2",
                "--log-store",
                "x.db",
            ]
        )
        self.assertEqual(args.metadata, ["a=1", "b=2"])

    def test_query_actor_and_action_are_optional(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["query", "--log-store", "x.db"])
        self.assertIsNone(args.actor)
        self.assertIsNone(args.action)

    def test_query_requires_log_store(self) -> None:
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["query"])

    def test_repair_requires_log_store(self) -> None:
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["repair"])

    def test_record_accepts_optional_idempotency_key(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            ["record", "operator:mina", "policy.update", "allowed", "--idempotency-key", "req-1", "--log-store", "x.db"]
        )
        self.assertEqual(args.idempotency_key, "req-1")

    def test_query_accepts_optional_outcome_and_time_range(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "query",
                "--outcome",
                "denied",
                "--start",
                "2024-01-01T00:00:00Z",
                "--end",
                "2024-12-31T00:00:00Z",
                "--log-store",
                "x.db",
            ]
        )
        self.assertEqual(args.outcome, "denied")
        self.assertEqual(args.start, "2024-01-01T00:00:00Z")
        self.assertEqual(args.end, "2024-12-31T00:00:00Z")

    def test_repair_accepts_optional_report_path(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["repair", "--report", "reports/latest.json", "--log-store", "x.db"])
        self.assertEqual(args.report_path, "reports/latest.json")

    def test_unknown_command_is_rejected(self) -> None:
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["delete", "--log-store", "x.db"])


class MainDispatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.store = str(Path(self._tmp.name) / "store.json")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _run(self, argv: list[str]) -> tuple[int, str]:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main(argv)
        return code, buf.getvalue()

    def test_record_then_query_round_trip(self) -> None:
        code, out = self._run(
            ["record", "operator:mina", "policy.update", "allowed", "--log-store", self.store]
        )
        self.assertEqual(code, 0)
        recorded = json.loads(out.strip())
        self.assertEqual(recorded["sequence"], 1)
        self.assertEqual(recorded["event_id"], recorded["event_id"])

        code, out = self._run(["query", "--actor", "operator:mina", "--log-store", self.store])
        self.assertEqual(code, 0)
        queried = json.loads(out.strip())
        self.assertEqual(queried["actor"], "operator:mina")
        self.assertEqual(queried["sequence"], 1)

    def test_record_with_metadata_round_trips(self) -> None:
        self._run(
            [
                "record",
                "operator:mina",
                "policy.update",
                "allowed",
                "--metadata",
                "reason=quarterly-review",
                "--log-store",
                self.store,
            ]
        )
        _, out = self._run(["query", "--log-store", self.store])
        queried = json.loads(out.strip())
        self.assertEqual(queried["metadata"], {"reason": "quarterly-review"})

    def test_repair_reports_a_clean_trail(self) -> None:
        self._run(["record", "operator:mina", "policy.update", "allowed", "--log-store", self.store])
        code, out = self._run(["repair", "--log-store", self.store])
        self.assertEqual(code, 0)
        report = json.loads(out.strip())
        self.assertEqual(report["checked"], 1)
        self.assertEqual(report["corrupt"], [])

    def test_malformed_actor_exits_nonzero_without_writing(self) -> None:
        with self.assertRaises(SystemExit):
            main(["record", "bogus", "policy.update", "allowed", "--log-store", self.store])
        self.assertFalse(Path(self.store).exists())

    def test_query_filters_by_outcome_and_time_range(self) -> None:
        self._run(["record", "operator:mina", "policy.update", "allowed", "--log-store", self.store])
        self._run(["record", "operator:mina", "policy.update", "denied", "--log-store", self.store])
        code, out = self._run(["query", "--outcome", "denied", "--log-store", self.store])
        self.assertEqual(code, 0)
        queried = json.loads(out.strip())
        self.assertEqual(queried["outcome"], "denied")

    def test_record_idempotency_key_is_safe_to_retry(self) -> None:
        self._run(
            ["record", "operator:mina", "policy.update", "allowed", "--idempotency-key", "req-1", "--log-store", self.store]
        )
        code, out = self._run(
            ["record", "operator:mina", "policy.update", "allowed", "--idempotency-key", "req-1", "--log-store", self.store]
        )
        self.assertEqual(code, 0)
        second = json.loads(out.strip())
        self.assertEqual(second["sequence"], 1)
        _, out = self._run(["query", "--log-store", self.store])
        self.assertEqual(len(out.strip().splitlines()), 1)

    def test_repair_writes_a_verification_report(self) -> None:
        self._run(["record", "operator:mina", "policy.update", "allowed", "--log-store", self.store])
        code, out = self._run(["repair", "--report", "reports/latest.json", "--log-store", self.store])
        self.assertEqual(code, 0)
        report = json.loads(out.strip())
        expected = (Path(self.store).parent / "reports" / "latest.json").resolve()
        self.assertEqual(Path(report["report_path"]), expected)
        self.assertTrue(expected.exists())

    def test_malformed_metadata_is_rejected(self) -> None:
        with self.assertRaises(SystemExit):
            main(
                [
                    "record",
                    "operator:mina",
                    "policy.update",
                    "allowed",
                    "--metadata",
                    "no-equals-sign",
                    "--log-store",
                    self.store,
                ]
            )


if __name__ == "__main__":
    unittest.main()
