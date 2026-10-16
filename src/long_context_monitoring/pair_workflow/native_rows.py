"""Read native row shapes and stable authored-edit markers without changing payloads."""

from __future__ import annotations

import re
from typing import Sequence


def _is_manual_edit_entry(entry: dict) -> bool:
    """Return whether one row belongs to a synthetic manual Edit pair."""

    return str(entry.get("uuid", "")).startswith("manual-edit-")


def _manual_edit_entries(entries: Sequence[dict]) -> list[dict]:
    """Return synthetic manual-edit rows without changing their order."""

    return [entry for entry in entries if _is_manual_edit_entry(entry)]


def _nested_strings(value: object):
    """Yield strings from nested native tool-result payloads."""

    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _nested_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _nested_strings(child)


def _normalized_tool_text(value: str) -> str:
    """Remove Claude Read line prefixes before exact source comparisons."""

    return "\n".join(
        re.sub(r"^\s*\d+(?:\t|→)", "", line) for line in value.splitlines()
    ).strip()


def _tool_use_items(entry: dict) -> list[dict]:
    content = entry.get("message", {}).get("content", [])
    if not isinstance(content, list):
        return []
    return [
        item
        for item in content
        if isinstance(item, dict) and item.get("type") == "tool_use"
    ]


def _native_result_strings(entry: dict):
    """Yield native tool-result text that can reveal stale source state."""

    content = entry.get("message", {}).get("content", [])
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") == "tool_result":
                yield from _nested_strings(item.get("content"))
    yield from _nested_strings(entry.get("toolUseResult"))


def _same_workspace_path(observed: object, registered: str) -> bool:
    if not isinstance(observed, str):
        return False
    normalized = observed.replace("\\", "/")
    return normalized == registered or normalized.endswith(f"/{registered}")


def _manual_edit_sources(entry: dict):
    """Yield validated path and replacement strings from authored Edit calls."""
    for item in _tool_use_items(entry):
        if item.get("name") != "Edit":
            continue
        edit_input = item.get("input")
        if not isinstance(edit_input, dict):
            continue
        path = edit_input.get("file_path")
        old_string = edit_input.get("old_string")
        new_string = edit_input.get("new_string")
        if all(isinstance(value, str) for value in (path, old_string, new_string)):
            yield path, old_string, new_string
