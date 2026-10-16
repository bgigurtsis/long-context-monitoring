"""Regression checks for the publication review; no transcript command is executed."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from long_context_monitoring.attack_lab.transcript import synthetic_edit_pair
from long_context_monitoring.pair_workflow.models import ManualPairError
from long_context_monitoring.pair_workflow.reconciliation import (
    _validate_no_direct_native_contradictions,
    replay_native_source_results,
)
from long_context_monitoring.pair_workflow.source import _sha256_tree


DATASET = Path(__file__).resolve().parents[1] / "dataset"
OLD_SOURCE = "def value():\n    return 'safe'\n"
NEW_SOURCE = "def value():\n    return 'inserted'\n"


def windows_order_hash(root: Path) -> str:
    """Reproduce Windows Path ordering without requiring a Windows host."""
    files = [path for path in root.rglob("*") if path.is_file()]
    files.sort(key=lambda path: tuple(part.lower() for part in path.relative_to(root).parts))
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def manual_edit_rows() -> list[dict]:
    rows = synthetic_edit_pair("app.py", OLD_SOURCE, NEW_SOURCE)
    rows[0]["uuid"] = "manual-edit-review-call"
    rows[1]["uuid"] = "manual-edit-review-result"
    return rows


def later_tool_rows(name: str, tool_input: dict, content: str) -> list[dict]:
    return [
        {
            "type": "assistant",
            "uuid": "later-call",
            "message": {
                "role": "assistant",
                "content": [{
                    "type": "tool_use", "id": "later-tool", "name": name,
                    "input": tool_input,
                }],
            },
        },
        {
            "type": "user",
            "uuid": "later-result",
            "message": {
                "role": "user",
                "content": [{
                    "type": "tool_result", "tool_use_id": "later-tool",
                    "content": content,
                }],
            },
            "toolUseResult": {"stdout": content},
        },
    ]


def test_all_published_workspace_hashes_match_windows_path_order():
    index = json.loads((DATASET / "index.json").read_text(encoding="utf-8"))
    checked = 0
    for example in index["examples"]:
        for arm in ("honest", "attack"):
            metadata = example[arm]
            manifest = json.loads((DATASET / metadata["manifest"]).read_text(encoding="utf-8"))
            actual = windows_order_hash(DATASET / metadata["workspace"])
            assert actual == metadata["workspace_sha256"], (example["id"], arm)
            assert actual == manifest["workspace_sha256"], (example["id"], arm)
            checked += 1
    assert checked == 60


def test_released_hash_function_verifies_published_workspace():
    arm = DATASET / "examples/import-integrity-002/honest"
    manifest = json.loads((arm / "manifest.json").read_text(encoding="utf-8"))
    assert _sha256_tree(arm / "workspace") == manifest["workspace_sha256"]


def test_validator_rejects_shell_overwrite_of_registered_function():
    rows = manual_edit_rows() + later_tool_rows(
        "Bash", {"command": "printf \"def value():\\n    return 'safe'\\n\" > app.py"}, "",
    )
    with pytest.raises(ManualPairError):
        _validate_no_direct_native_contradictions(rows)


def test_validator_rejects_body_only_edit_of_registered_function():
    # This copied honest edit would no longer apply after the inserted change.
    rows = manual_edit_rows() + later_tool_rows(
        "Edit",
        {"file_path": "app.py", "old_string": "return 'safe'", "new_string": "return 'later'"},
        "The file app.py has been updated successfully.",
    )
    with pytest.raises(ManualPairError):
        _validate_no_direct_native_contradictions(rows)


@pytest.mark.parametrize(
    ("name", "tool_input"),
    [
        ("Read", {"file_path": "other.py"}),
        ("Bash", {"command": "git show HEAD:other.py"}),
    ],
    ids=["different-file-read", "historical-command-output"],
)
def test_reconciliation_preserves_unrelated_results(name: str, tool_input: dict):
    rows = manual_edit_rows() + later_tool_rows(name, tool_input, OLD_SOURCE)
    before = copy.deepcopy(rows)
    updated, records = replay_native_source_results(rows)
    assert rows == before
    assert updated[-1] == before[-1]
    assert records == []
    _validate_no_direct_native_contradictions(updated)


def test_reconciliation_updates_a_registered_file_read():
    rows = manual_edit_rows() + later_tool_rows("Read", {"file_path": "app.py"}, OLD_SOURCE)
    updated, records = replay_native_source_results(rows)
    assert updated[-1]["message"]["content"][0]["content"] == NEW_SOURCE
    assert updated[-1]["toolUseResult"]["stdout"] == NEW_SOURCE
    assert len(records) == 1
    assert records[0].path == "app.py"
