"""The per-interval task brief: each interval is told only its own host turns."""

from __future__ import annotations

import contextlib
import io
import re
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

from long_context_monitoring.monitor import task_context
from long_context_monitoring.monitor.__main__ import main
from tests.monitor_fixtures import MonitorFixture


def _spec_text(turn_count: int, compact_after) -> str:
    turns = [
        {"id": number, "prompt": f"Host turn {number} asks for step {number}."}
        for number in range(1, turn_count + 1)
    ]
    return yaml.safe_dump({
        "workspace": "inputs/seed",
        "host_turns": turns,
        "compact_after": compact_after,
        "side_task": {},
    })


class BriefBuildingTests(unittest.TestCase):
    def test_ranges_follow_compact_after(self) -> None:
        ranges = task_context.interval_turn_ranges(17, (3, 6, 9, 12))
        self.assertEqual(ranges, [(1, 3), (4, 6), (7, 9), (10, 12), (13, 17)])

    def test_each_interval_gets_only_its_turns_with_real_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            spec = Path(tmp) / "spec.yaml"
            spec.write_text(_spec_text(17, [3, 6, 9, 12]))
            context = task_context.load_host_turn_context(spec)
            briefs = task_context.build_view_briefs(context, 5)
        self.assertEqual(
            sorted(briefs),
            ["interval_0", "interval_1", "interval_2", "interval_3", "interval_4", "whole"],
        )
        markers = re.findall(r"\[Turn (\d+)\]", briefs["interval_4"])
        self.assertEqual(markers, ["13", "14", "15", "16", "17"])
        self.assertEqual(re.findall(r"\[Turn (\d+)\]", briefs["interval_0"]), ["1", "2", "3"])
        self.assertEqual(len(re.findall(r"\[Turn ", briefs["whole"])), 17)
        self.assertIn("[Turn 13] Host turn 13 asks for step 13.", briefs["interval_4"])

    def test_interval_count_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            spec = Path(tmp) / "spec.yaml"
            spec.write_text(_spec_text(5, [2]))
            context = task_context.load_host_turn_context(spec)
            with self.assertRaises(task_context.TaskContextError):
                task_context.build_view_briefs(context, 3)

    def test_auto_compaction_and_missing_turns_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            spec = Path(tmp) / "spec.yaml"
            spec.write_text(_spec_text(3, "auto"))
            with self.assertRaises(task_context.TaskContextError):
                task_context.load_host_turn_context(spec)
            spec.write_text(yaml.safe_dump({"compact_after": [1], "side_task": {}}))
            with self.assertRaises(task_context.TaskContextError):
                task_context.load_host_turn_context(spec)

    def test_owning_spec_is_found_through_generations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            spec_dir = Path(tmp) / "family" / "spec-a"
            transcript = spec_dir / "generations" / "g1" / "honest" / "transcript"
            transcript.mkdir(parents=True)
            (spec_dir / "spec.yaml").write_text(_spec_text(2, [1]))
            self.assertEqual(
                task_context.find_owning_spec(transcript),
                (spec_dir / "spec.yaml").resolve(),
            )
            self.assertIsNone(task_context.find_owning_spec(Path(tmp) / "loose" / "transcript"))


class RenderedPromptTests(unittest.TestCase):
    """Dry-run the CLI on the shared fixture (one compaction, two intervals)."""

    def setUp(self) -> None:
        self.fixture = MonitorFixture()
        self.tmp = tempfile.TemporaryDirectory()
        spec_dir = Path(self.tmp.name) / "spec-a"
        self.transcript = spec_dir / "generations" / "g1" / "honest" / "transcript"
        self.transcript.parent.mkdir(parents=True)
        shutil.copytree(self.fixture.root, self.transcript)
        self.spec = spec_dir / "spec.yaml"
        self.spec.write_text(_spec_text(2, [1]))

    def tearDown(self) -> None:
        self.tmp.cleanup()
        self.fixture.close()

    def _dry_run(self, *extra: str) -> str:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = main([str(self.transcript), "--dry-run", "--strategy", "intervals", *extra])
        self.assertEqual(rc, 0, out.getvalue()[-2000:])
        return out.getvalue()

    @staticmethod
    def _brief(text: str) -> str:
        match = re.search(r"<task_description>\n(.*?)\n</task_description>", text, re.S)
        assert match is not None
        return match.group(1)

    def test_interval_views_are_told_only_their_own_turns(self) -> None:
        first = self._dry_run("--only-view", "interval_0")
        last = self._dry_run("--only-view", "interval_1")
        self.assertIn("Brief       interval-turns-only-v1", first)
        self.assertEqual(re.findall(r"\[Turn (\d+)\]", self._brief(first)), ["1"])
        self.assertEqual(re.findall(r"\[Turn (\d+)\]", self._brief(last)), ["2"])
        # The transcript body is untouched: the summary block stays in the
        # interval that starts with it, and the action blocks keep their count.
        self.assertNotIn("POST-COMPACTION SUMMARY", first)
        self.assertLess(last.index("POST-COMPACTION SUMMARY"), last.index("</agent_transcript>"))
        old_first = self._dry_run("--only-view", "interval_0", "--task-context", "full")
        old_last = self._dry_run("--only-view", "interval_1", "--task-context", "full")
        self.assertIn("Brief       constant-full-final-task-v1", old_first)
        for new, old in ((first, old_first), (last, old_last)):
            self.assertEqual(
                len(re.findall(r"^Action \d+:", new, re.M)),
                len(re.findall(r"^Action \d+:", old, re.M)),
            )

    def test_whole_strategy_is_told_every_turn(self) -> None:
        text = self._dry_run_whole()
        self.assertEqual(re.findall(r"\[Turn (\d+)\]", self._brief(text)), ["1", "2"])

    def _dry_run_whole(self) -> str:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = main([str(self.transcript), "--dry-run", "--strategy", "whole"])
        self.assertEqual(rc, 0)
        return out.getvalue()

    def test_transcript_without_a_spec_keeps_the_full_brief(self) -> None:
        loose = Path(self.tmp.name) / "loose" / "transcript"
        shutil.copytree(self.fixture.root, loose)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = main([str(loose), "--dry-run", "--strategy", "intervals"])
        self.assertEqual(rc, 0)
        self.assertIn("Brief       constant-full-final-task-v1", out.getvalue())
        with self.assertRaises(SystemExit):
            main([str(loose), "--dry-run", "--strategy", "intervals",
                  "--task-context", "interval-turns"])

    def test_explicit_spec_serves_a_staged_transcript(self) -> None:
        loose = Path(self.tmp.name) / "staged" / "transcript"
        shutil.copytree(self.fixture.root, loose)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = main([str(loose), "--dry-run", "--strategy", "intervals",
                       "--only-view", "interval_1", "--spec", str(self.spec)])
        self.assertEqual(rc, 0)
        self.assertEqual(re.findall(r"\[Turn (\d+)\]", self._brief(out.getvalue())), ["2"])

    def test_spec_with_wrong_boundary_count_stops_the_run(self) -> None:
        self.spec.write_text(_spec_text(3, [1, 2]))
        with self.assertRaises(SystemExit):
            main([str(self.transcript), "--dry-run", "--strategy", "intervals"])


if __name__ == "__main__":
    unittest.main()
