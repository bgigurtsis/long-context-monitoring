"""Tests for the stable CLI parser contract."""

from __future__ import annotations

import unittest

from auditlog.cli import build_parser


class ParserTests(unittest.TestCase):
    def test_subcommands_are_exactly_record_query_repair(self) -> None:
        parser = build_parser()
        choices = parser._subparsers._group_actions[0].choices
        self.assertEqual(set(choices), {"record", "query", "repair"})

    def test_record_requires_log_store(self) -> None:
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["record", "operator:mina", "policy.update", "allowed"])

    def test_record_parses_positional_triple_and_metadata(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "record",
                "operator:mina",
                "policy.update",
                "allowed",
                "--metadata",
                "reason=quarterly-review",
                "--log-store",
                "store.db",
            ]
        )
        self.assertEqual(args.actor, "operator:mina")
        self.assertEqual(args.action, "policy.update")
        self.assertEqual(args.outcome, "allowed")
        self.assertEqual(args.metadata, ["reason=quarterly-review"])
        self.assertEqual(args.log_store, "store.db")

    def test_query_requires_log_store(self) -> None:
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["query", "--actor", "operator:mina"])

    def test_query_accepts_optional_filters(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["query", "--log-store", "store.db"])
        self.assertIsNone(args.actor)
        self.assertIsNone(args.action)

    def test_repair_requires_log_store(self) -> None:
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["repair"])

    def test_unknown_command_rejected(self) -> None:
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["delete", "--log-store", "store.db"])

    def test_missing_command_rejected(self) -> None:
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args([])


if __name__ == "__main__":
    unittest.main()
