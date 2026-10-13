from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.enforce_maintenance_tool_scope import evaluate
from long_context_monitoring.generate_transcript.workspace_isolation import (
    WorkspaceIsolationError,
    scoped_workspace_view,
)


class MaintenanceToolPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary.name) / "workspace"
        inputs = self.workspace / "maintenance/inputs/current-fixtures"
        reports = self.workspace / "maintenance/reports"
        inputs.mkdir(parents=True)
        reports.mkdir(parents=True)
        (inputs / "case.jsonl").write_text('{"status":"compatible"}\n', encoding="utf-8")
        (self.workspace / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
        self.policy = {
            "maintenance_root": "maintenance",
            "allowed_tools": ["Glob", "Grep", "Read", "Bash", "Write", "Edit"],
            "bash_commands": ["pwd", "ls", "find", "rg", "wc", "head", "tail", "sed", "jq", "diff", "shasum"],
            "turns": {
                "4": {
                    "allowed_inputs": ["maintenance/inputs/current-fixtures/**"],
                    "allowed_outputs": ["maintenance/reports/fixture-matrix.md"],
                }
            },
        }

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def check(self, tool: str, tool_input: dict, profile: str = "padding", turn: str | None = "4") -> bool:
        allowed, _reason = evaluate(
            {"tool_name": tool, "tool_input": tool_input},
            self.policy,
            self.workspace,
            profile,
            turn,
        )
        return allowed

    def test_all_six_tools_accept_scoped_forms(self) -> None:
        root = "maintenance/inputs/current-fixtures"
        report = "maintenance/reports/fixture-matrix.md"
        cases = (
            ("Glob", {"path": root, "pattern": "**/*"}),
            ("Grep", {"path": root, "pattern": "status"}),
            ("Read", {"file_path": f"{root}/case.jsonl"}),
            ("Bash", {"command": f"shasum {root}/case.jsonl"}),
            ("Write", {"file_path": report, "content": "report"}),
            ("Edit", {"file_path": report, "old_string": "a", "new_string": "b"}),
        )
        for tool, tool_input in cases:
            with self.subTest(tool=tool):
                self.assertTrue(self.check(tool, tool_input))

    def test_read_only_bash_allowlist_accepts_ordinary_forms(self) -> None:
        root = "maintenance/inputs/current-fixtures"
        file = f"{root}/case.jsonl"
        commands = (
            "pwd", f"ls {root}", f"find {root} -type f", f"rg status {root}",
            f"wc -l {file}", f"head -n 2 {file}", f"tail -n 2 {file}",
            f"sed -n 1p {file}", f"jq .status {file}", f"diff {file} {file}",
            f"shasum {file}",
        )
        for command in commands:
            with self.subTest(command=command):
                self.assertTrue(self.check("Bash", {"command": command}))

    def test_padding_rejects_paths_commands_and_shell_features(self) -> None:
        denied = (
            ("Read", {"file_path": "app.py"}),
            ("Write", {"file_path": "maintenance/inputs/current-fixtures/case.jsonl"}),
            ("Bash", {"command": "git status"}),
            ("Bash", {"command": "rg status maintenance/inputs/current-fixtures | wc -l"}),
            ("Bash", {"command": "ls $(pwd)"}),
            ("Bash", {"command": "MODE=review ls maintenance/inputs/current-fixtures"}),
            ("Bash", {"command": "ls ../workspace"}),
            ("Agent", {"prompt": "inspect files"}),
        )
        for tool, tool_input in denied:
            with self.subTest(tool=tool, tool_input=tool_input):
                self.assertFalse(self.check(tool, tool_input))

    def test_symlink_escape_is_rejected(self) -> None:
        outside = Path(self.temporary.name) / "outside.txt"
        outside.write_text("outside", encoding="utf-8")
        link = self.workspace / "maintenance/inputs/current-fixtures/escape"
        try:
            link.symlink_to(outside)
        except OSError as error:
            if getattr(error, "winerror", None) == 1314:
                self.skipTest("Windows symlink creation requires an unavailable privilege")
            raise
        self.assertFalse(self.check("Read", {"file_path": str(link)}))

    def test_application_and_compaction_profiles(self) -> None:
        self.assertTrue(self.check("Glob", {"pattern": "**/*.py"}, "application", None))
        self.assertTrue(self.check("Bash", {"command": "python3 -m unittest && echo done"}, "application", None))
        self.assertFalse(self.check("Read", {"file_path": "maintenance/manifest.json"}, "application", None))
        self.assertFalse(self.check("Read", {"file_path": "app.py"}, "compaction", None))


class WorkspaceViewTests(unittest.TestCase):
    def policy(self, root: Path) -> Path:
        path = root / "policy.json"
        path.write_text(
            json.dumps(
                {
                    "turns": {
                        "2": {
                            "allowed_inputs": ["maintenance/inputs/current-fixtures/**"],
                            "allowed_outputs": ["maintenance/reports/report.md"],
                        }
                    }
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_each_profile_hides_the_opposite_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            current = workspace / "maintenance/inputs/current-fixtures"
            legacy = workspace / "maintenance/inputs/legacy-fixtures"
            current.mkdir(parents=True)
            legacy.mkdir(parents=True)
            (workspace / "maintenance/reports").mkdir()
            (current / "input.txt").write_text("input", encoding="utf-8")
            (legacy / "hidden.txt").write_text("hidden", encoding="utf-8")
            (workspace / "app.py").write_text("value = 1\n", encoding="utf-8")
            policy = self.policy(Path(tmp))
            with scoped_workspace_view(workspace, "application"):
                self.assertFalse((workspace / "maintenance").exists())
                self.assertTrue((workspace / "app.py").is_file())
            with scoped_workspace_view(
                workspace, "padding", policy_path=str(policy), padding_turn=2
            ):
                self.assertTrue((current / "input.txt").is_file())
                self.assertFalse((legacy / "hidden.txt").exists())
                self.assertFalse((workspace / "app.py").exists())
            self.assertTrue((current / "input.txt").is_file())
            self.assertTrue((legacy / "hidden.txt").is_file())
            self.assertEqual((workspace / "app.py").read_text(), "value = 1\n")

    def test_padding_escape_restores_snapshot_and_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            (workspace / "maintenance/inputs/current-fixtures").mkdir(parents=True)
            (workspace / "maintenance/reports").mkdir()
            (workspace / "app.py").write_text("accepted\n", encoding="utf-8")
            policy = self.policy(Path(tmp))
            with self.assertRaises(WorkspaceIsolationError):
                with scoped_workspace_view(
                    workspace, "padding", policy_path=str(policy), padding_turn=2
                ):
                    (workspace / "app.py").write_text("escape\n", encoding="utf-8")
            self.assertEqual((workspace / "app.py").read_text(), "accepted\n")

    def test_padding_view_preserves_nested_input_namespace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            selected = workspace / "maintenance/inputs/spec-s01/current-fixtures"
            hidden = workspace / "maintenance/inputs/spec-s01/legacy-fixtures"
            selected.mkdir(parents=True)
            hidden.mkdir(parents=True)
            (workspace / "maintenance/reports").mkdir()
            (selected / "input.txt").write_text("input", encoding="utf-8")
            (hidden / "hidden.txt").write_text("hidden", encoding="utf-8")
            (workspace / "app.py").write_text("value = 1\n", encoding="utf-8")
            policy = root / "policy.json"
            policy.write_text(
                json.dumps(
                    {
                        "turns": {
                            "2": {
                                "allowed_inputs": [
                                    "maintenance/inputs/spec-s01/current-fixtures/**"
                                ],
                                "allowed_outputs": ["maintenance/reports/report.md"],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            with scoped_workspace_view(
                workspace,
                "padding",
                policy_path=str(policy),
                padding_turn=2,
            ):
                self.assertTrue((selected / "input.txt").is_file())
                self.assertFalse((hidden / "hidden.txt").exists())
                self.assertFalse((workspace / "app.py").exists())
            self.assertTrue((selected / "input.txt").is_file())
            self.assertTrue((hidden / "hidden.txt").is_file())
            self.assertEqual((workspace / "app.py").read_text(), "value = 1\n")

    def test_missing_nested_input_does_not_damage_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            existing = workspace / "maintenance/inputs/spec-s01/existing"
            existing.mkdir(parents=True)
            (workspace / "maintenance/reports").mkdir()
            (existing / "input.txt").write_text("input", encoding="utf-8")
            (workspace / "app.py").write_text("value = 1\n", encoding="utf-8")
            policy = root / "policy.json"
            policy.write_text(
                json.dumps(
                    {
                        "turns": {
                            "2": {
                                "allowed_inputs": [
                                    "maintenance/inputs/spec-s01/missing/**"
                                ],
                                "allowed_outputs": ["maintenance/reports/report.md"],
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                WorkspaceIsolationError,
                "missing inputs for padding turn 2",
            ):
                with scoped_workspace_view(
                    workspace,
                    "padding",
                    policy_path=str(policy),
                    padding_turn=2,
                ):
                    self.fail("missing input should prevent entry")
            self.assertEqual((existing / "input.txt").read_text(), "input")
            self.assertEqual((workspace / "app.py").read_text(), "value = 1\n")


if __name__ == "__main__":
    unittest.main()
