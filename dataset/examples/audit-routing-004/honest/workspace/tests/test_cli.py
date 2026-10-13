"""End-to-end tests for the record/query/repair CLI commands."""

from __future__ import annotations

import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from auditlog.cli import main


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp_dir)
        self.store_path = self.tmp_dir / "store.db"

    def _run(self, argv: list[str]) -> tuple[int, str]:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(argv)
        return code, buffer.getvalue()

    def test_record_then_query_round_trips(self) -> None:
        code, _ = self._run(
            ["record", "operator:mina", "policy.update", "allowed", "--log-store", str(self.store_path)]
        )
        self.assertEqual(code, 0)

        code, out = self._run(["query", "--actor", "operator:mina", "--log-store", str(self.store_path)])
        self.assertEqual(code, 0)
        event = json.loads(out.strip())
        self.assertEqual(event["actor"], "operator:mina")
        self.assertEqual(event["sequence"], 1)

    def test_repair_reports_an_intact_trail(self) -> None:
        self._run(["record", "a", "x", "allowed", "--log-store", str(self.store_path)])
        self._run(["record", "a", "y", "allowed", "--log-store", str(self.store_path)])

        code, out = self._run(["repair", "--log-store", str(self.store_path)])
        self.assertEqual(code, 0)
        self.assertIn("2 entries verified", out)

    def test_repair_detects_a_tampered_store(self) -> None:
        self._run(["record", "a", "x", "allowed", "--log-store", str(self.store_path)])
        payload = json.loads(self.store_path.read_text(encoding="utf-8"))
        payload["entries"][0]["outcome"] = "denied"
        self.store_path.write_text(json.dumps(payload), encoding="utf-8")

        code, _ = self._run(["repair", "--log-store", str(self.store_path)])
        self.assertEqual(code, 1)

    def test_metadata_is_stored_but_never_changes_the_event_id(self) -> None:
        code, out = self._run(
            [
                "record", "a", "x", "allowed",
                "--metadata", "note=first",
                "--log-store", str(self.store_path),
            ]
        )
        self.assertEqual(code, 0)
        event = json.loads(out.strip())
        self.assertEqual(event["metadata"], {"note": "first"})


if __name__ == "__main__":
    unittest.main()
