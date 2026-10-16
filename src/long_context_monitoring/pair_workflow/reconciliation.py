"""Reconcile copied source observations and reject contradictory downstream native edits."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Sequence
from .models import ManualPairError, SourceReplayRecord
from .evidence_tools import tool_read_path
from .native_rows import (
    _is_manual_edit_entry,
    _tool_use_items,
    _normalized_tool_text,
    _manual_edit_sources,
    _nested_strings,
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

    return _replace_numbered_source(value, normalized_old, normalized_new)


def _replace_numbered_source(value: str, old: str, new: str) -> tuple[str, int]:
    """Preserve native read headings/reminders outside numbered source spans."""
    lines = value.splitlines(keepends=True)
    output: list[str] = []
    count = 0
    index = 0
    pattern = re.compile(r"^(\s*)(\d+)(\t|→)([^\r\n]*)(\r?\n)?$")
    while index < len(lines):
        first = pattern.match(lines[index])
        if first is None:
            output.append(lines[index])
            index += 1
            continue
        start = index
        source: list[str] = []
        last = first
        while index < len(lines) and (match := pattern.match(lines[index])) is not None:
            source.append(match.group(4))
            last = match
            index += 1
        observed = "\n".join(source)
        occurrences = observed.count(old.rstrip("\n"))
        if not occurrences:
            output.extend(lines[start:index])
            continue
        replaced = observed.replace(old.rstrip("\n"), new.rstrip("\n"))
        ending = first.group(5) or "\n"
        rebuilt = ending.join(
            f"{first.group(1)}{int(first.group(2)) + offset}{first.group(3)}{line}"
            for offset, line in enumerate(replaced.splitlines())
        )
        output.append(rebuilt + (last.group(5) or ""))
        count += occurrences
    return "".join(output), count


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


def _result_items(entry: dict) -> list[dict]:
    content = entry.get("message", {}).get("content", [])
    if not isinstance(content, list):
        return []
    return [item for item in content if isinstance(item, dict) and item.get("type") == "tool_result"]


def _result_hash(entry: dict, item: dict) -> str:
    evidence = {"content": item.get("content"), "toolUseResult": entry.get("toolUseResult")}
    text = json.dumps(evidence, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _activate(entry: dict, active: dict[str, list[tuple[str, str]]]) -> None:
    for path, old, new in _manual_edit_sources(entry):
        active.setdefault(path, []).append((old, new))


def _pending_reads(entry: dict, active: dict, pending: dict, completed: set[str] | None = None) -> None:
    for tool in _tool_use_items(entry):
        path = tool_read_path(tool, entry, active) if active else None
        if isinstance(tool.get("id"), str):
            pending[tool["id"]] = (tool.get("name"), path)
            if completed is not None:
                completed.discard(tool["id"])
        elif active:
            raise ManualPairError("native tool call has no tool ID after insertion")


def _known_read(item: dict, known: dict, active: dict) -> tuple[str | None, str | None]:
    tool_id = item.get("tool_use_id")
    if not isinstance(tool_id, str):
        raise ManualPairError("native tool result has no tool ID")
    if tool_id not in known:
        if active:
            raise ManualPairError("cannot attribute native tool result after insertion")
        return None, None
    return known[tool_id]


def _require_updated_read(entry: dict, item: dict, replacements: list[tuple[str, str]]) -> None:
    """A partial or unrecognized affected read must never silently retain old code."""
    displayed = list(_nested_strings(item.get("content")))
    structured = list(_nested_strings(entry.get("toolUseResult")))
    for old, new in replacements:
        for values in (displayed, structured) if structured else (displayed,):
            normalized = [_normalized_tool_text(value) for value in values]
            if any(_normalized_tool_text(old) in value for value in normalized):
                raise ManualPairError(f"unreconciled source read at {entry.get('uuid')}")
            if not any(_normalized_tool_text(new) in value for value in normalized):
                raise ManualPairError(f"cannot reconcile partial or unrecognized source read at {entry.get('uuid')}")


def replay_native_source_results(entries: Sequence[dict]) -> tuple[list[dict], list[SourceReplayRecord]]:
    """Change only established reads of the currently edited workspace files."""
    updated = copy.deepcopy(list(entries))
    active: dict[str, list[tuple[str, str]]] = {}
    pending: dict[str, tuple[str, str | None]] = {}
    records: list[SourceReplayRecord] = []
    for entry in updated:
        if _is_manual_edit_entry(entry):
            _activate(entry, active)
            continue
        _pending_reads(entry, active, pending)
        for item in _result_items(entry):
            tool_id = item.get("tool_use_id")
            # Native compaction can retain the same result again without its call.
            # Keep the original call provenance so every retained copy is reconciled.
            name, path = _known_read(item, pending, active)
            if path is None:
                continue
            if item.get("is_error"):
                raise ManualPairError(f"cannot reconcile failed source read at {entry.get('uuid')}")
            before = _result_hash(entry, item)
            item["content"], count = _replay_value(item.get("content"), active[path])
            native = entry.get("toolUseResult")
            if native is not None:
                if len(_result_items(entry)) != 1:
                    raise ManualPairError("cannot attribute a shared structured result to one tool call")
                entry["toolUseResult"], native_count = _replay_value(native, active[path])
                count += native_count
                _update_read_line_counts(native, entry["toolUseResult"])
            _require_updated_read(entry, item, active[path])
            if count:
                records.append(SourceReplayRecord(
                    entry_uuid=str(entry.get("uuid", "<unknown>")), tool_use_id=tool_id,
                    tool_name=name, path=path, replacement_count=count,
                    before_sha256=before, after_sha256=_result_hash(entry, item),
                ))
    return updated, records


def _update_read_line_counts(before: object, after: object) -> None:
    if not isinstance(before, dict) or not isinstance(after, dict):
        return
    old_file, new_file = before.get("file"), after.get("file")
    if not isinstance(old_file, dict) or not isinstance(new_file, dict):
        return
    old_source, new_source = old_file.get("content"), new_file.get("content")
    if isinstance(old_source, str) and isinstance(new_source, str):
        delta = len(new_source.splitlines()) - len(old_source.splitlines())
        for key in ("numLines", "totalLines"):
            if isinstance(new_file.get(key), int):
                new_file[key] += delta


def _validate_no_direct_native_contradictions(
    entries: Sequence[dict], *, require_updated_reads: bool = True,
) -> None:
    """Validate call provenance before rewriting; then check affected reads only."""
    active: dict[str, list[tuple[str, str]]] = {}
    pending: dict[str, tuple[str, str | None]] = {}
    completed: set[str] = set()
    for entry in entries:
        if _is_manual_edit_entry(entry):
            _activate(entry, active)
            continue
        _pending_reads(entry, active, pending, completed)
        for item in _result_items(entry):
            _name, path = _known_read(item, pending, active)
            completed.add(item.get("tool_use_id"))
            if path is not None and require_updated_reads:
                _require_updated_read(entry, item, active[path])
    if any(path is not None and tool_id not in completed
           for tool_id, (_name, path) in pending.items()):
        raise ManualPairError("affected source read has no matching tool result")


def reconcile_native_entries(entries: Sequence[dict]) -> tuple[list[dict], list[SourceReplayRecord]]:
    """Perform all free consistency checks before any compactor call."""
    _validate_no_direct_native_contradictions(entries, require_updated_reads=False)
    updated, records = replay_native_source_results(entries)
    _validate_no_direct_native_contradictions(updated)
    return updated, records
