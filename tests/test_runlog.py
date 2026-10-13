"""Tests for the run-tree console log.

The properties that matter are ordering (output printed before a sink exists
still lands in the file), fan-out (one invocation, several run trees, identical
content), and redaction (a registered secret never reaches disk).
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from long_context_monitoring.runlog import REDACTED, RunLog, log_file_name


FIXED_NOW = datetime(2026, 7, 24, 9, 30, 15, tzinfo=timezone.utc)


class LogFileNameTests(unittest.TestCase):
    """The name sorts by time and stays unique under concurrency.

    The pid is part of it because the timestamp only resolves to the second and
    a concurrent sweep starts several invocations inside one: they shared a log
    file and overwrote each other, leaving failed runs with no error text.
    """

    def test_name_is_sortable_and_labelled(self) -> None:
        self.assertEqual(
            log_file_name(FIXED_NOW, "generate", "attack"),
            f"2026-07-24_09-30-15Z_p{os.getpid()}_generate_attack.log",
        )

    def test_label_is_optional(self) -> None:
        self.assertEqual(
            log_file_name(FIXED_NOW, "monitor", None),
            f"2026-07-24_09-30-15Z_p{os.getpid()}_monitor.log",
        )

    def test_the_timestamp_still_leads_so_names_sort_by_time(self) -> None:
        name = log_file_name(FIXED_NOW, "monitor", None)
        self.assertTrue(name.startswith("2026-07-24_09-30-15Z_"))

    def test_two_processes_would_not_collide(self) -> None:
        """The property that matters: same second, same command, same label."""
        from unittest import mock
        with mock.patch("long_context_monitoring.runlog.os.getpid", return_value=111):
            first = log_file_name(FIXED_NOW, "monitor", "batch")
        with mock.patch("long_context_monitoring.runlog.os.getpid", return_value=222):
            second = log_file_name(FIXED_NOW, "monitor", "batch")
        self.assertNotEqual(first, second)


class RunLogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.saved = (sys.stdout, sys.stderr)

    def tearDown(self) -> None:
        # Guard against a failing assertion leaving the tee installed, which
        # would silently swallow the rest of the suite's output.
        sys.stdout, sys.stderr = self.saved

    def _log(self, command: str = "generate") -> RunLog:
        runlog = RunLog(command, ["--spec", "runs/x/spec.yaml"], now_utc=FIXED_NOW)
        self.addCleanup(runlog.close)
        return runlog

    def test_output_before_open_is_flushed_into_the_sink(self) -> None:
        # This is the whole point: a run that dies before its dir exists must
        # still have its early output on disk.
        runlog = self._log()
        runlog.install()
        print("early line")
        path = runlog.open_in(self.tmp / "runs" / "task", "attack")
        print("late line")
        runlog.close()

        assert path is not None
        text = path.read_text(encoding="utf-8")
        self.assertIn("early line", text)
        self.assertIn("late line", text)
        self.assertLess(text.index("early line"), text.index("late line"))

    def test_creates_the_logs_dir_under_the_run_root(self) -> None:
        runlog = self._log()
        runlog.install()
        path = runlog.open_in(self.tmp / "runs" / "task", "honest")
        runlog.close()

        assert path is not None
        self.assertEqual(path.parent, self.tmp / "runs" / "task" / "logs")
        self.assertTrue(path.exists())

    def test_header_records_argv_and_command(self) -> None:
        runlog = self._log()
        runlog.install()
        path = runlog.open_in(self.tmp / "runs" / "task", "honest")
        runlog.close()

        assert path is not None
        text = path.read_text(encoding="utf-8")
        self.assertIn("lcm generate --spec runs/x/spec.yaml", text)
        self.assertIn("commit  :", text)

    def test_registered_secret_never_reaches_disk(self) -> None:
        runlog = self._log()
        runlog.install()
        runlog.register_secret("private monitor input")
        print("monitor failed while reading private monitor input")
        path = runlog.open_in(self.tmp / "runs" / "task", "monitor")
        runlog.close()

        assert path is not None
        text = path.read_text(encoding="utf-8")
        self.assertNotIn("private monitor input", text)
        self.assertIn(REDACTED, text)

    def test_colour_is_stripped_on_disk_only(self) -> None:
        runlog = self._log()
        runlog.install()
        print("\x1b[31mred\x1b[0m")
        path = runlog.open_in(self.tmp / "runs" / "task", "honest")
        runlog.close()

        assert path is not None
        text = path.read_text(encoding="utf-8")
        self.assertNotIn("\x1b", text)
        self.assertIn("red", text)

    def test_several_sinks_all_receive_the_whole_stream(self) -> None:
        # ``lcm monitor runs/<name>`` can expand to several run trees; none of
        # their logs should be missing the shared planning prefix.
        runlog = self._log("monitor")
        runlog.install()
        print("shared prefix")
        first = runlog.open_in(self.tmp / "runs" / "a", "honest")
        second = runlog.open_in(self.tmp / "runs" / "b", "attack")
        print("after both")
        runlog.close()

        assert first is not None and second is not None
        for path in (first, second):
            text = path.read_text(encoding="utf-8")
            self.assertIn("shared prefix", text)
            self.assertIn("after both", text)

    def test_stderr_is_captured_too(self) -> None:
        runlog = self._log()
        runlog.install()
        path = runlog.open_in(self.tmp / "runs" / "task", "honest")
        print("boom", file=sys.stderr)
        runlog.close()

        assert path is not None
        self.assertIn("boom", path.read_text(encoding="utf-8"))

    def test_never_opened_writes_nothing(self) -> None:
        # The ``--dry-run`` path: capture, then discard, leaving no run tree.
        runlog = self._log()
        runlog.install()
        print("plan output including a side task")
        runlog.close()

        self.assertEqual(runlog.paths, [])
        self.assertEqual(list(self.tmp.rglob("*.log")), [])

    def test_isatty_reflects_the_real_stream(self) -> None:
        # console._colour_enabled() gates on isatty(); the tee must not lie.
        runlog = self._log()
        expected = bool(getattr(sys.stdout, "isatty", lambda: False)())
        runlog.install()
        self.assertEqual(sys.stdout.isatty(), expected)
        runlog.close()

    def test_close_restores_the_console_streams(self) -> None:
        runlog = self._log()
        original = sys.stdout
        runlog.install()
        self.assertIsNot(sys.stdout, original)
        runlog.close()
        self.assertIs(sys.stdout, original)

    def test_unwritable_run_root_degrades_to_no_log(self) -> None:
        # A filesystem problem must never be the reason a generation run fails.
        blocker = self.tmp / "blocked"
        blocker.write_text("not a directory", encoding="utf-8")
        runlog = self._log()
        runlog.install()
        path = runlog.open_in(blocker, "honest")
        runlog.close()

        self.assertIsNone(path)
        self.assertEqual(runlog.paths, [])


class MonitorLogGroupingTests(unittest.TestCase):
    """``_open_run_logs`` keys logs by run tree, not by scored condition.

    ``transcript_name`` is patched rather than fixtured: the behaviour under test
    is the grouping, and building two real archives would only re-test the name.
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.saved = (sys.stdout, sys.stderr)

    def tearDown(self) -> None:
        sys.stdout, sys.stderr = self.saved

    def _open(self, names: list[str]) -> RunLog:
        from unittest import mock

        from long_context_monitoring.monitor import __main__ as monitor_main

        runlog = RunLog("monitor", ["runs/x"], now_utc=FIXED_NOW)
        self.addCleanup(runlog.close)
        targets = [object() for _ in names]
        lookup = dict(zip(targets, names, strict=True))
        with mock.patch("long_context_monitoring.monitor.events.transcript_name", lookup.get):
            monitor_main._open_run_logs(runlog, targets, str(self.tmp))
        return runlog

    def test_both_arms_of_one_task_share_one_log(self) -> None:
        runlog = self._open(["widget-run/attack", "widget-run/honest"])
        self.assertEqual(
            [p.name for p in runlog.paths],
            [f"2026-07-24_09-30-15Z_p{os.getpid()}_monitor_attack+honest.log"],
        )
        self.assertEqual(runlog.paths[0].parent, self.tmp / "widget-run" / "logs")

    def test_cross_task_sweep_gets_one_log_per_task(self) -> None:
        runlog = self._open(["task-a/honest", "task-b/honest"])
        self.assertEqual(
            sorted(p.relative_to(self.tmp).as_posix() for p in runlog.paths),
            [
                f"task-a/logs/2026-07-24_09-30-15Z_p{os.getpid()}_monitor_honest.log",
                f"task-b/logs/2026-07-24_09-30-15Z_p{os.getpid()}_monitor_honest.log",
            ],
        )

    def test_name_without_a_condition_is_unlabelled(self) -> None:
        runlog = self._open(["bare-session"])
        self.assertEqual(
            [p.name for p in runlog.paths],
            [f"2026-07-24_09-30-15Z_p{os.getpid()}_monitor.log"])


if __name__ == "__main__":
    unittest.main()
