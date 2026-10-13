"""Small viewer annotations derived from native records; source text stays authoritative."""

from __future__ import annotations

import json
from long_context_monitoring.transcript.entries import human_prompt_text, message_blocks

# Tool names whose tool_use blocks spawn sub-agents. "Task" is the older name
# used by earlier Claude Code versions; keep it as a fallback.
AGENT_TOOL_NAMES = ("Agent", "Task")

# Entry types that are part of the conversation proper (everything else is
# bookkeeping the page renders collapsed). Only conversation entries take part
# in the compaction preserved-set logic.
CONVERSATION_TYPES = ("user", "assistant", "system")

# These are presentation-only categories. They deliberately live in the
# viewer package rather than the future normalized-event parser/monitor
# contract. A raw JSONL line may have several categories (for example an
# assistant line can contain prose and a tool call); ``category`` is only the
# most useful label for navigation.
PRESET_CATEGORIES = {
    "narrative": {
        "prompt",
        "assistant",
        "agent",
        "compaction",
        "compaction_summary",
        "error",
    },
    "tools": {
        "prompt",
        "assistant",
        "agent",
        "compaction",
        "compaction_summary",
        "error",
        "tool_call",
        "tool_result",
    },
    "all": None,
}

# Landmark filters are deliberately narrower than presentation presets. A
# preset decides how much transcript detail is visible; a landmark selection
# asks for only the source rows represented by those navigation landmarks.
LANDMARK_KINDS = {"edit", "compaction", "turn", "error"}


def _text_preview(value: object, limit: int = 120) -> str:
    """Return a compact single-line title without changing the source value."""
    if value is None:
        return ""
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False)
    return " ".join(value.split())[:limit]


def _edit_landmark(line_no: int, entry: dict, presentation: dict) -> dict:
    """Describe one authored tool call for the outline and timeline.

    The transcript records the edit as an ordinary ``Edit`` call, so the
    target path and the replaced text are read straight from its input. The
    function name is not in the transcript; the viewer joins these rows to
    the run's ``result.json`` by order to name it.
    """
    target = None
    tool_name = None
    old_string = None
    new_string = None
    for block in message_blocks(entry):
        if block.get("type") != "tool_use":
            continue
        tool_name = block.get("name") or tool_name
        tool_input = block.get("input")
        if not isinstance(tool_input, dict):
            continue
        target = target or tool_input.get("file_path")
        old_string = old_string or tool_input.get("old_string")
        new_string = new_string or tool_input.get("new_string")
    return {
        "line": line_no,
        "phase": presentation.get("injected_phase") or "injected",
        "turn": presentation.get("turn"),
        "tool": tool_name or "Edit",
        "path": target,
        "tool_use_id": presentation.get("tool_use_id"),
        "old_chars": len(old_string) if isinstance(old_string, str) else None,
        "new_chars": len(new_string) if isinstance(new_string, str) else None,
    }


def _presentation(self, line_no: int, entry: dict) -> dict:
    """Build small, non-authoritative metadata for one raw source line."""
    etype = entry.get("type") or "<untyped>"
    if isinstance(entry.get("payload"), dict) and etype in {
        "session_meta",
        "response_item",
        "event_msg",
        "turn_context",
        "world_state",
        "compacted",
        "inter_agent_communication_metadata",
    }:
        return self._codex_presentation(line_no, entry)
    subtype = entry.get("subtype")
    message = entry.get("message") or {}
    content = message.get("content")
    blocks = message_blocks(entry)
    block_types = [block.get("type") for block in blocks]

    tool_blocks = [block for block in blocks if block.get("type") == "tool_use"]
    result_blocks = [block for block in blocks if block.get("type") == "tool_result"]
    tool_ids = []
    for block in tool_blocks:
        if block.get("id"):
            tool_ids.append(block["id"])
    for block in result_blocks:
        if block.get("tool_use_id"):
            tool_ids.append(block["tool_use_id"])

    # The post-compaction summary is a synthetic ``user`` entry, but it is
    # not a human turn — it is the model-written continuation context. Detect
    # it first so it is neither counted as a turn nor styled like a prompt.
    is_compact_summary = entry.get("isCompactSummary") is True

    prompt_text = None
    if etype == "user" and not is_compact_summary:
        prompt_text = human_prompt_text(entry)
    is_prompt = prompt_text is not None
    if is_prompt:
        self.current_turn += 1

    is_error = any(bool(block.get("is_error")) for block in result_blocks)
    categories, title = _claude_categories(
        self,
        line_no,
        entry,
        etype,
        subtype,
        content,
        blocks,
        block_types,
        tool_blocks,
        result_blocks,
        is_compact_summary,
        is_prompt,
        prompt_text,
        is_error,
    )

    if is_error:
        categories.append("error")
    # The first category is deliberately the most useful navigation label.
    category = categories[0]

    # Synthetic tool pairs carry a stable id, so both the call and its
    # result can be flagged as authored rather than generated:
    #   ``toolu_lcm_<phase>_...``  legacy injector (generate_transcript);
    #   ``toolu_manual_<hash>``    manual pair (src/manual_pair.py), whose
    #                              entry uuids also start ``manual-edit-``.
    # ``injected_phase`` names the phase where the source records one.
    injected_phase = _injected_phase(entry, tool_ids)

    return {
        "category": category,
        "categories": categories,
        "turn": self.current_turn or None,
        "title": title,
        "is_error": is_error,
        "tool_use_id": tool_ids[0] if tool_ids else None,
        "tool_use_ids": tool_ids,
        "uuid": entry.get("uuid"),
        "injected": injected_phase is not None,
        "injected_phase": injected_phase,
    }


def _codex_presentation(self, line_no: int, entry: dict) -> dict:
    """Build viewer navigation metadata for one native Codex rollout line."""

    etype = entry.get("type") or "<untyped>"
    payload = entry.get("payload") or {}
    ptype = payload.get("type")
    categories = ["bookkeeping"]
    title = f"{etype}{'/' + str(ptype) if ptype else ''}"
    tool_use_id = payload.get("call_id")

    if etype == "compacted":
        categories = ["compaction", "compaction_summary"]
        title = "Context compacted (Codex native)"
    elif etype == "response_item" and ptype == "message":
        role = payload.get("role")
        content = payload.get("content")
        text = _codex_message_text(content)
        if role == "user":
            self.current_turn += 1
            categories = ["prompt"]
            title = _text_preview(text) or "Human prompt"
            self.turn_lines.append(
                {
                    "line": line_no,
                    "turn": self.current_turn,
                    "title": title,
                }
            )
        elif role == "assistant":
            categories = ["assistant"]
            title = _text_preview(text) or "Assistant response"
    elif etype == "response_item" and ptype == "reasoning":
        categories = ["thinking"]
        title = "Reasoning"
    elif etype == "response_item" and ptype in (
        "function_call",
        "custom_tool_call",
    ):
        name = str(payload.get("name") or "Tool")
        namespace = payload.get("namespace")
        if namespace:
            name = f"{namespace}.{name}"
        categories = ["agent" if name.endswith(".spawn_agent") else "tool_call"]
        title = f"{name} call"
    elif etype == "response_item" and ptype in (
        "function_call_output",
        "custom_tool_call_output",
    ):
        categories = ["tool_result"]
        title = "Tool result"

    return {
        "category": categories[0],
        "categories": categories,
        "turn": self.current_turn or None,
        "title": title,
        "is_error": False,
        "tool_use_id": tool_use_id,
        "tool_use_ids": [tool_use_id] if tool_use_id else [],
        "uuid": payload.get("id") or payload.get("window_id"),
        "duplicate": False,
        "injected": False,
        "injected_phase": None,
    }


def _claude_categories(
    self,
    line_no,
    entry,
    etype,
    subtype,
    content,
    blocks,
    block_types,
    tool_blocks,
    result_blocks,
    is_compact_summary,
    is_prompt,
    prompt_text,
    is_error,
):
    """Choose the navigation label in precedence order and index human turns."""
    categories: list[str] = []
    title = f"{etype}{'/' + subtype if subtype else ''}"

    if etype == "system" and subtype == "compact_boundary":
        categories.append("compaction")
        compact = entry.get("compactMetadata") or {}
        title = "Context compacted"
        if compact.get("trigger"):
            title += f" ({compact['trigger']})"
    elif is_compact_summary:
        categories.append("compaction_summary")
        title = "Compaction summary (post-compaction context)"
    elif is_prompt:
        categories.append("prompt")
        title = _text_preview(prompt_text) or "Human prompt"
        self.turn_lines.append(
            {
                "line": line_no,
                "turn": self.current_turn,
                "title": title,
            }
        )
    elif tool_blocks:
        categories, title = _tool_call_label(tool_blocks, blocks)
    elif result_blocks:
        categories.append("tool_result")
        title = "Tool error" if is_error else "Tool result"
    elif etype == "assistant":
        if "text" in block_types or isinstance(content, str):
            categories.append("assistant")
            text = (
                content
                if isinstance(content, str)
                else "\n".join(
                    block.get("text", "")
                    for block in blocks
                    if block.get("type") == "text"
                )
            )
            title = _text_preview(text) or "Assistant response"
        elif "thinking" in block_types:
            categories.append("thinking")
            title = "Thinking"
        else:
            categories.append("assistant")
            title = "Assistant event"
    elif etype == "system":
        categories.append("system")
    elif etype in CONVERSATION_TYPES:
        categories.append("assistant")
    else:
        categories.append("bookkeeping")

    return categories, title


def _tool_call_label(
    tool_blocks: list[dict], blocks: list[dict]
) -> tuple[list[str], str]:
    """Prefer agent navigation and describe the first tool's meaningful input."""
    categories = []
    for block in tool_blocks:
        if block.get("name") in AGENT_TOOL_NAMES:
            if "agent" not in categories:
                categories.append("agent")
        elif "tool_call" not in categories:
            categories.append("tool_call")
    first = tool_blocks[0]
    summary = ""
    tool_input = first.get("input") or {}
    for key in ("command", "file_path", "pattern", "query", "description", "prompt"):
        if tool_input.get(key):
            summary = _text_preview(tool_input[key])
            break
    title = f"{first.get('name') or 'Tool'} call"
    if summary:
        title += f": {summary}"
    if any(block.get("type") == "text" for block in blocks):
        categories.append("assistant")
    return categories, title


def _injected_phase(entry: dict, tool_ids: list) -> str | None:
    """Recognize authored call/result pairs from their stable native IDs."""
    injected_phase = None
    for tid in tool_ids:
        text = str(tid)
        if text.startswith("toolu_lcm_setup_"):
            injected_phase = "setup"
            break
        if text.startswith("toolu_lcm_execution_"):
            injected_phase = "execution"
            break
        if text.startswith("toolu_manual_"):
            injected_phase = "manual edit"
            break
        if text.startswith("toolu_lcm_"):
            injected_phase = "injected"
            break
    if injected_phase is None and str(entry.get("uuid", "")).startswith("manual-edit-"):
        injected_phase = "manual edit"

    return injected_phase


def _codex_message_text(content: object) -> str:
    """Join text-bearing Codex blocks without interpreting non-text content."""
    text_parts = []
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("text"):
                text_parts.append(str(block["text"]))
    return "\n".join(text_parts)
