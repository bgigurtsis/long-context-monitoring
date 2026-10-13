"""Tests for the stable CLI shapes and stable JSON output."""
from __future__ import annotations

import datetime as _dt
import json
import os
import subprocess
import sys
import tempfile
import unittest

from accountsvc.cli import _parse_clock_now, build_parser


def run_cli(*args):
    result = subprocess.run(
        [sys.executable, "-m", "accountsvc.cli", *args],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )
    return result


class CliTests(unittest.TestCase):
    def setUp(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.unlink(path)
        self.db_path = path

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_create_show_change_email_roundtrip(self):
        created = run_cli("create-account", "org1", "acct1", "a@example.test", "--database", self.db_path)
        self.assertEqual(created.returncode, 0, created.stderr)
        payload = json.loads(created.stdout)
        self.assertEqual(payload["current_email"], "a@example.test")

        shown = run_cli("show-account", "acct1", "--database", self.db_path)
        self.assertEqual(shown.returncode, 0, shown.stderr)
        self.assertEqual(json.loads(shown.stdout), payload)

        changed = run_cli("change-email", "acct1", "b@example.test", "--database", self.db_path)
        self.assertEqual(changed.returncode, 0, changed.stderr)
        self.assertEqual(json.loads(changed.stdout)["current_email"], "b@example.test")

    def test_output_is_stable_sorted_json(self):
        created = run_cli("create-account", "org1", "acct1", "a@example.test", "--database", self.db_path)
        # Sorted, compact separators: no ", " or ": ", keys ascending.
        self.assertNotIn(", ", created.stdout)
        self.assertNotIn(": ", created.stdout)
        payload = json.loads(created.stdout)
        self.assertEqual(list(payload.keys()), sorted(payload.keys()))

    def test_conflicting_email_fails_with_nonzero_exit(self):
        run_cli("create-account", "org1", "acct1", "a@example.test", "--database", self.db_path)
        conflict = run_cli("create-account", "org1", "acct2", "a@example.test", "--database", self.db_path)
        self.assertNotEqual(conflict.returncode, 0)
        self.assertIn("error", json.loads(conflict.stderr))

    def test_show_missing_account_fails(self):
        result = run_cli("show-account", "nope", "--database", self.db_path)
        self.assertNotEqual(result.returncode, 0)


class ServeClockAndTtlFlagTests(unittest.TestCase):
    """--clock-now and --recovery-token-ttl-seconds exist so a test can boot
    the serve subcommand with a deterministic notion of time instead of
    waiting on real elapsed time to exercise expiry. `serve` blocks
    forever once started, so these check argument parsing and conversion
    directly rather than spawning the subcommand.
    """

    def _parse_serve_args(self, *extra):
        return build_parser().parse_args(
            ["serve", "--database", "db.sqlite3", "--bearer-token", "t", "--mail-endpoint", "http://x", *extra]
        )

    def test_clock_now_and_ttl_default_to_unset(self):
        args = self._parse_serve_args()
        self.assertIsNone(args.clock_now)
        self.assertIsNone(args.recovery_token_ttl_seconds)

    def test_clock_now_and_ttl_are_parsed_when_given(self):
        args = self._parse_serve_args(
            "--clock-now", "2024-01-01T00:00:00+00:00", "--recovery-token-ttl-seconds", "5"
        )
        self.assertEqual(args.clock_now, "2024-01-01T00:00:00+00:00")
        self.assertEqual(args.recovery_token_ttl_seconds, 5)

    def test_parse_clock_now_defaults_a_naive_timestamp_to_utc(self):
        parsed = _parse_clock_now("2024-01-01T00:00:00")
        self.assertEqual(parsed, _dt.datetime(2024, 1, 1, tzinfo=_dt.timezone.utc))

    def test_parse_clock_now_preserves_an_explicit_offset(self):
        parsed = _parse_clock_now("2024-01-01T00:00:00+02:00")
        self.assertEqual(parsed.utcoffset(), _dt.timedelta(hours=2))

    def test_parse_clock_now_of_none_is_none(self):
        self.assertIsNone(_parse_clock_now(None))


if __name__ == "__main__":
    unittest.main()
