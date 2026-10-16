"""Reconciliation must preserve unrelated evidence and reject ambiguous source state."""

from __future__ import annotations

import copy
import hashlib
import json

import pytest

from long_context_monitoring.pair_workflow.models import ManualPairError
from long_context_monitoring.pair_workflow.reconciliation import reconcile_native_entries
from tests.test_publication_review import (
    NEW_SOURCE,
    OLD_SOURCE,
    later_tool_rows,
    manual_edit_rows,
)


@pytest.mark.parametrize("name", ["Write", "Edit"])
def test_writes_to_another_file_preserve_their_inputs_and_results(name):
    tools = later_tool_rows(name, {
        "file_path": "other.py", "old_string": OLD_SOURCE,
        "new_string": NEW_SOURCE, "content": OLD_SOURCE,
    }, OLD_SOURCE)
    rows = manual_edit_rows() + tools
    updated, records = reconcile_native_entries(rows)
    assert updated == rows
    assert records == []


@pytest.mark.parametrize("command", [
    "cat other.py", "git show HEAD:app.py", "git show HEAD:other.py",
    "python3 -m unittest tests.test_app -v", "pytest tests/test_app.py -q",
])
def test_unrelated_and_historical_shell_output_is_preserved(command):
    rows = manual_edit_rows() + later_tool_rows("Bash", {"command": command}, OLD_SOURCE)
    updated, records = reconcile_native_entries(rows)
    assert updated == rows
    assert records == []


@pytest.mark.parametrize("command", [
    "sed -i s/safe/changed/ app.py", "python3 -c 'open(\"app.py\",\"w\").write(\"changed\")'",
    "cp other.py app.py", "mv app.py other.py", "cat other.py > app.py",
    "cat app.py; cp other.py app.py", "cat $(printf app.py)",
    "bash script.sh", "env python3 -m unittest", "git show --output=app.py HEAD:other.py",
    "cat *.py", "cat app.?y", "cat ~user/app.py",
])
def test_unverifiable_shell_commands_are_rejected(command):
    rows = manual_edit_rows() + later_tool_rows("Bash", {"command": command}, "")
    with pytest.raises(ManualPairError, match="shell"):
        reconcile_native_entries(rows)


@pytest.mark.parametrize(("file_path", "cwd"), [
    ("/workspace/app.py", "/workspace"),
    ("C:\\work\\app.py", "C:\\work"),
    (".\\APP.py", "C:\\work"),
    ("./app.py", "/workspace"),
])
def test_read_paths_resolve_against_native_cwd(file_path, cwd):
    tools = later_tool_rows("Read", {"file_path": file_path}, OLD_SOURCE)
    tools[0]["cwd"] = cwd
    rows = manual_edit_rows() + tools
    updated, records = reconcile_native_entries(rows)
    assert updated[-1]["message"]["content"][0]["content"] == NEW_SOURCE
    assert len(records) == 1
    assert records[0].before_sha256 != records[0].after_sha256


def test_absolute_file_with_same_suffix_outside_workspace_is_not_rewritten():
    tools = later_tool_rows("Read", {"file_path": "/elsewhere/app.py"}, OLD_SOURCE)
    tools[0]["cwd"] = "/workspace"
    rows = manual_edit_rows() + tools
    updated, records = reconcile_native_entries(rows)
    assert updated == rows
    assert records == []


def test_absolute_affected_path_without_cwd_is_rejected():
    rows = manual_edit_rows() + later_tool_rows("Read", {"file_path": "/workspace/app.py"}, OLD_SOURCE)
    with pytest.raises(ManualPairError, match="native cwd"):
        reconcile_native_entries(rows)


def test_full_file_cat_is_reconciled():
    rows = manual_edit_rows() + later_tool_rows("Bash", {"command": "cat -- app.py"}, OLD_SOURCE)
    updated, records = reconcile_native_entries(rows)
    assert updated[-1]["toolUseResult"]["stdout"] == NEW_SOURCE
    assert len(records) == 1


@pytest.mark.parametrize("content", ["def value():\n", "    return 'safe'\n", "unexpected output"])
def test_partial_or_unrecognized_affected_reads_fail_closed(content):
    rows = manual_edit_rows() + later_tool_rows("Read", {"file_path": "app.py"}, content)
    with pytest.raises(ManualPairError, match="partial or unrecognized"):
        reconcile_native_entries(rows)


def test_missing_read_result_is_rejected():
    tools = later_tool_rows("Read", {"file_path": "app.py"}, OLD_SOURCE)
    with pytest.raises(ManualPairError, match="no matching tool result"):
        reconcile_native_entries(manual_edit_rows() + tools[:1])


def test_retained_result_copy_reuses_its_original_call_provenance():
    tools = later_tool_rows("Read", {"file_path": "app.py"}, OLD_SOURCE)
    rows = manual_edit_rows() + tools + [copy.deepcopy(tools[-1])]
    updated, records = reconcile_native_entries(rows)
    assert updated[-1] == updated[-2]
    assert updated[-1]["toolUseResult"]["stdout"] == NEW_SOURCE
    assert len(records) == 2


def test_result_without_known_call_fails_closed():
    tools = later_tool_rows("Read", {"file_path": "app.py"}, OLD_SOURCE)
    with pytest.raises(ManualPairError, match="cannot attribute"):
        reconcile_native_entries(manual_edit_rows() + tools[1:])


def test_failed_read_is_rejected():
    tools = later_tool_rows("Read", {"file_path": "app.py"}, OLD_SOURCE)
    tools[-1]["message"]["content"][0]["is_error"] = True
    with pytest.raises(ManualPairError, match="failed source read"):
        reconcile_native_entries(manual_edit_rows() + tools)


def test_numbered_native_read_updates_payload_metadata_and_audit_hashes():
    new_source = "def value():\n    marker = 'inserted'\n    return marker\n"
    manual = manual_edit_rows()
    manual[0]["message"]["content"][0]["input"]["new_string"] = new_source
    before_source = OLD_SOURCE + "\nNEXT = 1\n"
    display = "Read result:\n" + "".join(
        f"{i}→{line}\n" for i, line in enumerate(before_source.splitlines(), 1)
    ) + "<system-reminder>Unchanged native reminder.</system-reminder>\n"
    tools = later_tool_rows("Read", {"file_path": "app.py"}, display)
    tools[-1]["toolUseResult"] = {
        "type": "text", "file": {
            "filePath": "app.py", "content": before_source,
            "numLines": 4, "totalLines": 4, "startLine": 1,
        },
    }
    original = copy.deepcopy(manual + tools)
    updated, records = reconcile_native_entries(original)
    assert original == manual + tools
    result = updated[-1]
    assert "5→NEXT = 1" in result["message"]["content"][0]["content"]
    assert result["message"]["content"][0]["content"].endswith(
        "<system-reminder>Unchanged native reminder.</system-reminder>\n"
    )
    assert result["toolUseResult"]["file"]["content"] == new_source + "\nNEXT = 1\n"
    assert result["toolUseResult"]["file"]["numLines"] == 5
    assert result["toolUseResult"]["file"]["totalLines"] == 5
    assert records[0].replacement_count == 2
    for entry, expected in [(original[-1], records[0].before_sha256),
                            (result, records[0].after_sha256)]:
        payload = {"content": entry["message"]["content"][0]["content"],
                   "toolUseResult": entry["toolUseResult"]}
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        assert hashlib.sha256(raw.encode()).hexdigest() == expected
