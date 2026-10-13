"""Reconcile copied source observations and reject contradictory downstream native edits."""

from __future__ import annotations

import copy
import re
from typing import Sequence
from .models import ManualPairError, SourceReplayRecord
from .native_rows import (
    _is_manual_edit_entry,
    _tool_use_items,
    _normalized_tool_text,
    _same_workspace_path,
    _native_result_strings,
    _manual_edit_sources,
)


def _replace_source_observation(
    value: str, old_string: str, new_string: str
) -> tuple[str, int]:
    """Replace one observed function while retaining Claude Read line numbers."""

    direct_count = value.count(old_string)
    if direct_count:
        return value.replace(old_string, new_string), direct_count

    normalized_value = value.replace("\r\n", "\n").replace("\r", "\n")
    normalized_old = old_string.replace("\r\n", "\n").replace("\r", "\n")
    normalized_new = new_string.replace("\r\n", "\n").replace("\r", "\n")
    normalized_count = normalized_value.count(normalized_old)
    if normalized_count:
        replaced = normalized_value.replace(normalized_old, normalized_new)
        first_ending = re.search(r"\r\n|\r|\n", value)
        if first_ending is not None and first_ending.group(0) != "\n":
            replaced = replaced.replace("\n", first_ending.group(0))
        return replaced, normalized_count

    lines = value.splitlines()
    numbered = [re.match(r"^(\s*)(\d+)\t(.*)$", line) for line in lines]
    if not lines or any(match is None for match in numbered):
        return value, 0
    normalized = "\n".join(match.group(3) for match in numbered if match is not None)
    normalized_old = normalized_old.strip()
    replacement_count = normalized.count(normalized_old)
    if not replacement_count:
        return value, 0
    replaced = normalized.replace(normalized_old, normalized_new.strip())
    first = numbered[0]
    assert first is not None
    leading = first.group(1)
    start = int(first.group(2))
    rebuilt = "\n".join(
        f"{leading}{start + offset}\t{line}"
        for offset, line in enumerate(replaced.splitlines())
    )
    if value.endswith("\n"):
        rebuilt += "\n"
    return rebuilt, replacement_count


def _replay_value(
    value: object, replacements: Sequence[tuple[str, str]]
) -> tuple[object, int]:
    """Replay registered source replacements through one nested result value."""

    if isinstance(value, str):
        updated = value
        total = 0
        for old_string, new_string in replacements:
            updated, count = _replace_source_observation(
                updated, old_string, new_string
            )
            total += count
        return updated, total
    if isinstance(value, list):
        updated_list = []
        total = 0
        for child in value:
            updated_child, count = _replay_value(child, replacements)
            updated_list.append(updated_child)
            total += count
        return updated_list, total
    if isinstance(value, dict):
        updated_dict = {}
        total = 0
        for key, child in value.items():
            updated_child, count = _replay_value(child, replacements)
            updated_dict[key] = updated_child
            total += count
        return updated_dict, total
    return value, 0


def replay_native_source_results(
    entries: Sequence[dict],
) -> tuple[list[dict], list[SourceReplayRecord]]:
    """Replay copied source observations against the manual-edit timeline."""

    updated = copy.deepcopy(list(entries))
    active_edits: dict[str, list[tuple[str, str]]] = {}
    pending_tools: dict[str, str] = {}
    records: list[SourceReplayRecord] = []

    for entry in updated:
        if _is_manual_edit_entry(entry):
            for path, old_string, new_string in _manual_edit_sources(entry):
                active_edits.setdefault(path, []).append((old_string, new_string))
            continue

        for item in _tool_use_items(entry):
            tool_use_id = item.get("id")
            tool_name = item.get("name")
            if isinstance(tool_use_id, str) and isinstance(tool_name, str):
                pending_tools[tool_use_id] = tool_name

        content = entry.get("message", {}).get("content", [])
        if not isinstance(content, list):
            continue
        for item in content:
            if not isinstance(item, dict) or item.get("type") != "tool_result":
                continue
            tool_use_id = item.get("tool_use_id")
            if not isinstance(tool_use_id, str) or tool_use_id not in pending_tools:
                continue
            tool_name = pending_tools.pop(tool_use_id)
            records.extend(
                _replay_tool_result(entry, item, tool_use_id, tool_name, active_edits)
            )
    return updated, records


def _validate_no_direct_native_contradictions(entries: Sequence[dict]) -> None:
    """Reject copied native evidence that directly contradicts a manual edit."""

    manual_calls: list[tuple[int, str, str, str]] = []
    for index, entry in enumerate(entries):
        if not _is_manual_edit_entry(entry):
            continue
        for path, old_string, new_string in _manual_edit_sources(entry):
            manual_calls.append((index, path, old_string, new_string))

    for call_index, path, old_string, new_string in manual_calls:
        expected_old = _normalized_tool_text(old_string)
        function_headers = {
            source.strip().splitlines()[0]
            for source in (old_string, new_string)
            if source.strip()
        }
        for entry in entries[call_index + 1 :]:
            _validate_following_native_entry(
                entry, path, expected_old, function_headers
            )


def _replay_tool_result(
    entry: dict,
    item: dict,
    tool_use_id: str,
    tool_name: str,
    active_edits: dict,
) -> list[SourceReplayRecord]:
    """Update displayed and structured copies together, recording each changed path."""
    records = []
    for path, replacements in active_edits.items():
        replayed_content, content_count = _replay_value(
            item.get("content"), replacements
        )
        item["content"] = replayed_content
        result_count = 0
        native_result = entry.get("toolUseResult")
        if native_result is not None:
            replayed_result, result_count = _replay_value(native_result, replacements)
            entry["toolUseResult"] = replayed_result
        replacement_count = content_count + result_count
        if replacement_count:
            records.append(
                SourceReplayRecord(
                    entry_uuid=str(entry.get("uuid", "<unknown>")),
                    tool_use_id=tool_use_id,
                    tool_name=tool_name,
                    path=path,
                    replacement_count=replacement_count,
                )
            )
    return records


def _validate_following_native_entry(
    entry: dict,
    path: str,
    expected_old: str,
    function_headers: set[str],
) -> None:
    """Reject later writes, overlapping edits, and unreconciled direct reads."""
    if _is_manual_edit_entry(entry):
        return
    for item in _tool_use_items(entry):
        if item.get("name") not in {"Edit", "Write"}:
            continue
        tool_input = item.get("input")
        if isinstance(tool_input, dict) and _same_workspace_path(
            tool_input.get("file_path"), path
        ):
            if item.get("name") == "Write":
                raise ManualPairError(
                    "native transcript writes an edited path after its manual edit: "
                    f"{path} at {entry.get('uuid', '<unknown>')}"
                )
            changed_source = "\n".join(
                str(tool_input.get(key, "")) for key in ("old_string", "new_string")
            )
            if any(header in changed_source for header in function_headers):
                raise ManualPairError(
                    "native transcript edits a registered function after its "
                    f"manual edit: {path} at "
                    f"{entry.get('uuid', '<unknown>')}"
                )
    for result_text in _native_result_strings(entry):
        if expected_old and expected_old in _normalized_tool_text(result_text):
            raise ManualPairError(
                "native tool result contradicts a registered manual edit: "
                f"{path} at {entry.get('uuid', '<unknown>')}"
            )
