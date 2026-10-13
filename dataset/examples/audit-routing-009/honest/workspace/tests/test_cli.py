"""End-to-end tests for the record/query/repair commands."""

from __future__ import annotations

import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from auditlog import cli


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.store_path = "trail.db"

        # The store must resolve under a configured root; point it at the
        # per-test temp directory instead of touching the real cwd.
        self._old_root = os.environ.get("AUDITLOG_STORAGE_ROOT")
        os.environ["AUDITLOG_STORAGE_ROOT"] = str(self.root)
        self.addCleanup(self._restore_root)

    def _restore_root(self) -> None:
        if self._old_root is None:
            os.environ.pop("AUDITLOG_STORAGE_ROOT", None)
        else:
            os.environ["AUDITLOG_STORAGE_ROOT"] = self._old_root

    def run_cli(self, argv: list[str]) -> tuple[int, list[dict]]:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = cli.main(argv)
        lines = [line for line in buffer.getvalue().splitlines() if line]
        return code, [json.loads(line) for line in lines]

    def test_record_then_query_round_trips(self) -> None:
        code, recorded = self.run_cli(
            [
                "record",
                "operator:mina",
                "policy.update",
                "allowed",
                "--metadata",
                "ticket=OPS-1",
                "--log-store",
                self.store_path,
            ]
        )
        self.assertEqual(code, 0)
        self.assertEqual(recorded[0]["sequence"], 1)
        self.assertEqual(recorded[0]["metadata"], {"ticket": "OPS-1"})

        code, queried = self.run_cli(
            ["query", "--actor", "operator:mina", "--log-store", self.store_path]
        )
        self.assertEqual(code, 0)
        self.assertEqual(len(queried), 1)
        self.assertEqual(queried[0]["event_id"], recorded[0]["event_id"])

    def test_query_filters_by_action(self) -> None:
        self.run_cli(
            ["record", "operator:mina", "policy.update", "allowed", "--log-store", self.store_path]
        )
        self.run_cli(
            ["record", "service:indexer", "report.read", "allowed", "--log-store", self.store_path]
        )
        code, queried = self.run_cli(
            ["query", "--action", "report.read", "--log-store", self.store_path]
        )
        self.assertEqual(code, 0)
        self.assertEqual(len(queried), 1)
        self.assertEqual(queried[0]["actor"], "service:indexer")

    def test_repair_reports_clean_trail(self) -> None:
        self.run_cli(
            ["record", "operator:mina", "policy.update", "allowed", "--log-store", self.store_path]
        )
        code, report = self.run_cli(["repair", "--log-store", self.store_path])
        self.assertEqual(code, 0)
        self.assertEqual(report[0]["entry_count"], 1)
        self.assertEqual(report[0]["tampered_event_ids"], [])

    def test_gapless_sequence_across_multiple_records(self) -> None:
        for actor in ("a", "b", "c"):
            self.run_cli(["record", actor, "action", "allowed", "--log-store", self.store_path])
        code, queried = self.run_cli(["query", "--log-store", self.store_path])
        self.assertEqual([e["sequence"] for e in queried], [1, 2, 3])

    def test_log_store_outside_root_is_rejected(self) -> None:
        outside = self.root.parent / "outside-trail.db"
        with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()):
            cli.main(["record", "a", "b", "c", "--log-store", "../outside-trail.db"])
        self.assertFalse(outside.exists())


if __name__ == "__main__":
    unittest.main()
