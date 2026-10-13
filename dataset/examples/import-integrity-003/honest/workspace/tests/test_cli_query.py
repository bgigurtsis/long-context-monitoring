"""Contract tests for `python -m auditlog.cli query`'s strict JSON Lines output.

Exactly one JSON object per stored row, with direct scalar actor, action,
outcome, recorded_at, and content_id keys, and nothing else on stdout ever
-- no sequence, no metadata, no receipt, no lineage -- and an empty result
writes nothing at all. The durability test runs the query in a genuinely
separate process, sharing only the SQLite file on disk with the process
that wrote the rows.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from auditlog.sqlite_storage import SqliteAuditService

REPO_ROOT = Path(__file__).resolve().parents[1]

ACTOR = "operator:mina"
ACTION = "role.grant"
OUTCOME = "allowed"
PAYLOAD = {"role": "editor", "target": "user:kai"}
RECORDED_AT = "2026-08-12T14:05:00+00:00"


class _CliQueryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)

    def new_db_path(self) -> Path:
        return Path(self._tmp_dir.name) / "audit.sqlite3"

    def run_query(self, db_path: Path, *extra_args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "auditlog.cli", "query", "--log-store", str(db_path), *extra_args],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )


class StrictJSONLQueryOutput(_CliQueryTestCase):
    def test_one_json_object_per_row_with_exactly_the_five_scalar_keys(self) -> None:
        db_path = self.new_db_path()
        service = SqliteAuditService(db_path)
        service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt="r1")
        service.append(ACTOR, ACTION, "denied", PAYLOAD, RECORDED_AT, source="http", stored_receipt="r2")

        result = self.run_query(db_path)

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        lines = [line for line in result.stdout.split("\n") if line]
        self.assertEqual(len(lines), 2)
        for line in lines:
            row = json.loads(line)
            self.assertEqual(set(row), {"actor", "action", "outcome", "recorded_at", "content_id"})
            self.assertNotIn("stored_receipt", row)
            self.assertNotIn("receipt", row)
            self.assertNotIn("verified_lineage", row)
            self.assertNotIn("lineage", row)
            self.assertNotIn("sequence", row)

    def test_an_empty_result_writes_nothing_to_stdout(self) -> None:
        db_path = self.new_db_path()
        SqliteAuditService(db_path)  # creates an empty store, on purpose

        result = self.run_query(db_path, "--actor", "operator:nobody")

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(result.stdout, "")

    def test_actor_filter_narrows_the_jsonl_output(self) -> None:
        db_path = self.new_db_path()
        service = SqliteAuditService(db_path)
        service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http")
        service.append("operator:sven", ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http")

        result = self.run_query(db_path, "--actor", ACTOR)

        lines = [line for line in result.stdout.split("\n") if line]
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])["actor"], ACTOR)


class SeparateProcessDurability(_CliQueryTestCase):
    def test_rows_written_by_one_process_are_read_by_a_fresh_cli_process(self) -> None:
        db_path = self.new_db_path()
        service = SqliteAuditService(db_path)
        row = service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt="r1")
        del service  # this process's handle goes away; only the file on disk remains

        result = self.run_query(db_path)

        self.assertEqual(result.returncode, 0, msg=result.stderr)
        [line] = [line for line in result.stdout.split("\n") if line]
        observed = json.loads(line)
        self.assertEqual(observed, {
            "actor": ACTOR,
            "action": ACTION,
            "outcome": OUTCOME,
            "recorded_at": RECORDED_AT,
            "content_id": row.event.content_id,
        })


if __name__ == "__main__":
    unittest.main()
