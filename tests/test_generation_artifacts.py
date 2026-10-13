"""Characterize generation artifacts before separating their implementation."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from long_context_monitoring.generate_transcript import delivery, live


class GenerationArtifactTests(unittest.TestCase):
    def test_workspace_archive_replaces_snapshot_and_records_cache_exclusions(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "working"
            workspace.mkdir()
            (workspace / "service.py").write_bytes(b"pass\n")
            cache = workspace / "__pycache__"
            cache.mkdir()
            (cache / "cached.pyc").write_bytes(b"cache")
            destination = root / "arm"
            old = destination / "workspace"
            old.mkdir(parents=True)
            (old / "stale.py").write_bytes(b"stale")

            result = live.archive_workspace(workspace, destination)

            self.assertEqual(
                result,
                {
                    "path": "workspace",
                    "archived": True,
                    "files": 1,
                    "bytes": 5,
                    "excluded": list(live.WORKSPACE_ARCHIVE_EXCLUDES),
                },
            )
            self.assertEqual((old / "service.py").read_bytes(), b"pass\n")
            self.assertFalse((old / "stale.py").exists())
            self.assertFalse((old / "__pycache__").exists())
            self.assertEqual(list(destination.glob(".workspace.staging-*")), [])

    def test_archive_copy_failure_keeps_previous_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            existing = root / "arm" / "workspace"
            existing.mkdir(parents=True)
            (existing / "old.py").write_bytes(b"old")
            with mock.patch.object(
                live.shutil, "copytree", side_effect=OSError("copy failed")
            ):
                with self.assertRaisesRegex(OSError, "copy failed"):
                    live.archive_workspace(root / "source", root / "arm")
            self.assertEqual((existing / "old.py").read_bytes(), b"old")
            self.assertEqual(list((root / "arm").glob(".workspace.staging-*")), [])

    def test_resume_round_trip_redacts_side_task_and_rejects_model_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "workspace"
            workspace.mkdir()
            spec = {
                "compaction_mode": "manual",
                "configured_compact_after": [1],
                "side_task": "PRIVATE_REGISTRATION_TEXT",
            }
            plan = [("turn 1", "one"), ("turn 2", "two")]
            segments = [delivery.Segment(label="all", start_turn=1, messages=plan)]
            live.write_resume_state(
                root,
                name="example",
                arm="honest",
                session_id="native",
                workspace=workspace,
                fingerprint="seed-hash",
                plan=plan,
                plan_segments=segments,
                spec=spec,
                completed=1,
                policy_model="test-model",
                policy_effort="high",
            )
            marker = (root / "resume.json").read_text(encoding="utf-8")
            self.assertNotIn("PRIVATE_REGISTRATION_TEXT", marker)
            state = live.load_resume_state(
                root, plan, segments, spec, "test-model", "high"
            )
            self.assertEqual(state, json.loads(marker))
            self.assertEqual(state["completed_segments"], [])
            self.assertFalse((root / "resume.json.tmp").exists())
            with self.assertRaisesRegex(live.SessionError, "policy model changed"):
                live.load_resume_state(
                    root, plan, segments, spec, "other-model", "high"
                )

    def test_compaction_pairing_ignores_duplicates_and_preserves_line_numbers(
        self,
    ) -> None:
        rows = [
            {
                "type": "system",
                "subtype": "compact_boundary",
                "uuid": "b",
                "compactMetadata": {
                    "trigger": "manual",
                    "preTokens": 100,
                    "postTokens": 10,
                },
            },
            {"type": "user", "uuid": "summary", "isCompactSummary": True},
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "native.jsonl"
            path.write_text(
                "".join(json.dumps(row) + "\n" for row in rows + rows), encoding="utf-8"
            )
            self.assertEqual(
                live.compaction_boundaries(path),
                [
                    {
                        "line": 1,
                        "summary_line": 2,
                        "boundary_event_id": "b",
                        "summary_event_id": "summary",
                        "trigger": "manual",
                        "pre_tokens": 100,
                        "post_tokens": 10,
                    }
                ],
            )
            path.write_text(json.dumps(rows[0]) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(
                live.SessionError, "has no paired main-thread compact summary"
            ):
                live.compaction_boundaries(path)

    def test_manual_compaction_validation_preserves_exception_text(self) -> None:
        spec = {"compaction_mode": "manual", "configured_compact_after": [1]}
        live.validate_compaction_boundaries(spec, [{"trigger": "manual"}])
        with self.assertRaises(live.SessionError) as raised:
            live.validate_compaction_boundaries(spec, [{"trigger": "auto"}])
        self.assertEqual(
            str(raised.exception),
            "expected 1 manual compaction boundaries; observed 1 with triggers ['auto']",
        )


if __name__ == "__main__":
    unittest.main()
