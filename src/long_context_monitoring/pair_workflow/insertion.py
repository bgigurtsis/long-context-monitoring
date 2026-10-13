"""Anchor registered edits to native host turns and retain complete call/result pairs."""

from __future__ import annotations

import hashlib
import shutil
import tempfile
from pathlib import Path
from typing import Sequence
from long_context_monitoring.attack_lab.edits import apply_function_edit
from long_context_monitoring.attack_lab.transcript import synthetic_edit_pair
from long_context_monitoring.transcript.entries import human_prompt_text
from .models import InlineAction, ManualPairError
from .native_rows import _same_workspace_path, _manual_edit_entries


def _host_prompt_index(entries: Sequence[dict], prompt: str) -> int:
    """Return the first delivery of a host prompt.

    A resumed Claude turn can retain the interrupted delivery and append the
    same host prompt again before continuing. The manual edit belongs before
    the first delivery, so it remains active across every retry of that turn.
    """

    matches = [
        index
        for index, entry in enumerate(entries)
        if human_prompt_text(entry) == prompt and not entry.get("isCompactSummary")
    ]
    if not matches:
        raise ManualPairError("expected host prompt is absent from honest transcript")
    return matches[0]


def _boundary_after_prompt(
    entries: Sequence[dict], prompt_index: int, next_prompt_index: int | None
) -> int | None:
    end = len(entries) if next_prompt_index is None else next_prompt_index
    matches = [
        index
        for index in range(prompt_index + 1, end)
        if entries[index].get("type") == "system"
        and entries[index].get("subtype") == "compact_boundary"
    ]
    if len(matches) > 1:
        raise ManualPairError("found several main compact boundaries in one host turn")
    return matches[0] if matches else None


def _insertion_index(entries: Sequence[dict], spec: dict, action: InlineAction) -> int:
    turns = spec["host_turns"]
    prompt = turns[action.turn - 1]["prompt"]
    prompt_index = _host_prompt_index(entries, prompt)
    if action.when == "before_host_turn":
        return prompt_index
    next_prompt_index = None
    if action.turn < len(turns):
        next_prompt_index = _host_prompt_index(entries, turns[action.turn]["prompt"])
    if action.when == "after_native_function_edit":
        return _after_native_function_edit(
            entries, prompt_index, next_prompt_index, action
        )
    boundary = _boundary_after_prompt(entries, prompt_index, next_prompt_index)
    return boundary if boundary is not None else (next_prompt_index or len(entries))


def inject_manual_edits(
    entries: list[dict],
    spec: dict,
    actions: Sequence[InlineAction],
    source_workspace: Path,
) -> list[dict]:
    """Insert exact synthetic Edit tool pairs at registered host-turn anchors."""

    updated = list(entries)
    for action in sorted(actions, key=lambda item: item.turn, reverse=True):
        index = _insertion_index(updated, spec, action)
        # The transcript records the final honest function as the replaced text.
        # apply_function_edit obtains the exact source later from the honest archive.
        # Here a temporary copy gives the same audited function extraction.
        with tempfile.TemporaryDirectory(prefix="lcm-edit-source-") as tmp:
            scratch = Path(tmp) / "workspace"
            shutil.copytree(source_workspace, scratch)
            applied = apply_function_edit(scratch, action.edit)
        pair = synthetic_edit_pair(
            action.edit.path,
            applied.old_string,
            applied.new_string,
        )
        identity = hashlib.sha256(
            (
                f"{action.turn}\0{action.when}\0{action.edit.path}\0"
                f"{action.edit.function}\0{applied.old_string}\0{applied.new_string}"
            ).encode("utf-8")
        ).hexdigest()
        tool_use_id = f"toolu_manual_{identity[:24]}"
        pair[0]["uuid"] = f"manual-edit-{identity[:24]}-call"
        pair[0]["message"]["id"] = f"msg_manual_{identity[:24]}"
        pair[0]["message"]["content"][0]["id"] = tool_use_id
        pair[1]["uuid"] = f"manual-edit-{identity[:24]}-result"
        pair[1]["message"]["content"][0]["tool_use_id"] = tool_use_id
        for entry in pair:
            entry.pop("timestamp", None)
        updated[index:index] = pair
    return updated


def _validate_manual_edit_pairs(
    entries: Sequence[dict], actions: Sequence[InlineAction]
) -> None:
    """Fail when compaction rebuilding drops a registered manual edit pair."""

    manual_entries = _manual_edit_entries(entries)
    call_ids: set[str] = set()
    result_ids: set[str] = set()
    for entry in manual_entries:
        content = entry.get("message", {}).get("content", [])
        if not isinstance(content, list) or len(content) != 1:
            raise ManualPairError(
                "constructed transcript has a malformed manual edit row"
            )
        item = content[0]
        if not isinstance(item, dict):
            raise ManualPairError(
                "constructed transcript has a malformed manual edit row"
            )
        if item.get("type") == "tool_use" and item.get("name") == "Edit":
            call_ids.add(str(item.get("id", "")))
        elif item.get("type") == "tool_result":
            result_ids.add(str(item.get("tool_use_id", "")))
        else:
            raise ManualPairError(
                "constructed transcript has a malformed manual edit row"
            )
    if len(call_ids) != len(actions) or len(result_ids) != len(actions):
        raise ManualPairError(
            "constructed transcript lost a registered manual edit: "
            f"expected {len(actions)} pairs, found "
            f"{len(call_ids)} calls and {len(result_ids)} results"
        )
    if call_ids != result_ids:
        raise ManualPairError(
            "constructed transcript has an unmatched manual edit pair"
        )


def affected_interval_views(spec: dict, actions: Sequence[InlineAction]) -> list[str]:
    """Return the interval containing each registered edit."""

    boundaries = spec["configured_compact_after"]
    views: list[str] = []
    for action in actions:
        if action.when == "after_host_turn" and action.turn in boundaries:
            interval = boundaries.index(action.turn)
        else:
            interval = sum(point < action.turn for point in boundaries)
        view = f"interval_{interval}"
        if view not in views:
            views.append(view)
    return views


def _after_native_function_edit(
    entries: Sequence[dict],
    prompt_index: int,
    next_prompt_index: int | None,
    action: InlineAction,
) -> int:
    """Anchor after the last matching native function call's result in this turn."""
    end = len(entries) if next_prompt_index is None else next_prompt_index
    function_name = action.edit.function.rsplit(".", 1)[-1]
    function_header = f"def {function_name}("
    matching_tool_ids: list[tuple[int, str]] = []
    for index in range(prompt_index + 1, end):
        content = entries[index].get("message", {}).get("content", [])
        if not isinstance(content, list):
            continue
        for item in content:
            if not isinstance(item, dict) or item.get("type") != "tool_use":
                continue
            if item.get("name") not in {"Edit", "Write"}:
                continue
            tool_input = item.get("input")
            if not isinstance(tool_input, dict) or not _same_workspace_path(
                tool_input.get("file_path"), action.edit.path
            ):
                continue
            changed_source = "\n".join(
                str(tool_input.get(key, ""))
                for key in ("old_string", "new_string", "content")
            )
            if function_header in changed_source and isinstance(item.get("id"), str):
                matching_tool_ids.append((index, item["id"]))
    if not matching_tool_ids:
        raise ManualPairError(
            "could not anchor manual edit after a native function edit: "
            f"{action.edit.path}:{action.edit.function} in host turn {action.turn}"
        )
    call_index, tool_id = matching_tool_ids[-1]
    for index in range(call_index + 1, end):
        content = entries[index].get("message", {}).get("content", [])
        if not isinstance(content, list):
            continue
        if any(
            isinstance(item, dict)
            and item.get("type") == "tool_result"
            and item.get("tool_use_id") == tool_id
            for item in content
        ):
            return index + 1
    raise ManualPairError(
        "native function edit has no matching tool result: "
        f"{action.edit.path}:{action.edit.function} in host turn {action.turn}"
    )
