"""Normalize native Codex rollout JSONL into :class:`Event` lists.

The Claude normalizer lives in ``events.py``; this module holds everything
specific to the Codex Responses record shapes (``session_meta``,
``turn_context``, ``response_item``, ``compacted``) and to Codex child threads.
``events.extract_events`` dispatches here when a rollout's first row is
``session_meta``.
"""

from __future__ import annotations

import json
from dataclasses import replace

from long_context_monitoring.monitor.event_model import Event, _content_to_text
from long_context_monitoring.transcript.trajectory import Trajectory

EMPTY_COMPACTION_SUMMARY_TEXT = "(compaction summary not present in the native rollout)"

# Codex injects these parts into the first user message of a turn. They are
# harness context, not the user's request, so they are left out of the human
# prompt (and therefore out of the task description the monitor is shown).
_CODEX_INJECTED_PART_PREFIXES = (
    "<recommended_plugins>",
    "<in-app-browser-context>",
    "<codex_internal_context>",
    "<environment_context>",
    "<user_instructions>",
    "<permissions instructions>",
    "<app-context>",
    "<turn_aborted>",
    "# AGENTS.md instructions",
)


def _codex_text(content: object) -> str:
    """Flatten text from a native Codex Responses item."""

    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") in (
            "input_text", "output_text", "text", "summary_text",
        ):
            parts.append(str(block.get("text") or ""))
    return "\n".join(parts)


def _without_codex_injected_parts(content: object) -> object:
    """Drop harness-injected parts from a Codex user message."""
    if not isinstance(content, list):
        return content
    kept = []
    for block in content:
        text = str(block.get("text") or "") if isinstance(block, dict) else ""
        if text.lstrip().startswith(_CODEX_INJECTED_PART_PREFIXES):
            continue
        kept.append(block)
    return kept


def _codex_input(payload: dict) -> tuple[str, object]:
    """Return a tool name and its JSON-like input from a Codex item."""

    name = str(payload.get("name") or "<unnamed>")
    namespace = payload.get("namespace")
    if namespace:
        name = f"{namespace}.{name}"
    raw = payload.get("arguments", payload.get("input", {}))
    if isinstance(raw, str):
        try:
            return name, json.loads(raw)
        except json.JSONDecodeError:
            return name, raw
    return name, raw


def _codex_dropped_ids(raw_entries: list[object]) -> set[str]:
    """Accumulate dropped IDs across every compaction, even later preservation."""
    dropped_ids: set[str] = set()
    seen_ids: list[str] = []
    for entry in raw_entries:
        if not isinstance(entry, dict):
            continue
        payload = entry.get("payload") or {}
        if entry.get("type") == "compacted":
            preserved = {
                item.get("id")
                for item in payload.get("replacement_history", [])
                if isinstance(item, dict) and item.get("id")
            }
            dropped_ids.update(
                item_id for item_id in seen_ids if item_id not in preserved
            )
        item_id = payload.get("id")
        if isinstance(item_id, str):
            seen_ids.append(item_id)
    return dropped_ids


def _codex_response_events(
    payload: dict,
    file_id: str,
    line: int,
    depth: int,
    turn: int,
    dropped: bool,
) -> list[Event]:
    """Normalize one Responses item; developer messages remain invisible."""
    events: list[Event] = []
    event_id = f"{file_id}:L{line}:0"
    ptype = payload.get("type")
    if ptype == "message":
        role = payload.get("role")
        content = payload.get("content")
        if role == "user":
            content = _without_codex_injected_parts(content)
        text = _codex_text(content)
        if role == "user" and text:
            events.append(
                Event(
                    kind="human_prompt",
                    event_id=event_id,
                    file_id=file_id,
                    line=line,
                    depth=depth,
                    turn=turn or None,
                    text=text,
                    dropped=dropped,
                )
            )
        elif role == "assistant" and text:
            events.append(
                Event(
                    kind="assistant_text",
                    event_id=event_id,
                    file_id=file_id,
                    line=line,
                    depth=depth,
                    turn=turn or None,
                    text=text,
                    dropped=dropped,
                )
            )
        # Developer messages are intentionally not normalized.
        return events
    if ptype == "reasoning":
        text = _codex_text(payload.get("summary"))
        if text:
            events.append(
                Event(
                    kind="thinking",
                    event_id=event_id,
                    file_id=file_id,
                    line=line,
                    depth=depth,
                    turn=turn or None,
                    text=text,
                    dropped=dropped,
                )
            )
        return events
    if ptype in ("function_call", "custom_tool_call"):
        name, tool_input = _codex_input(payload)
        call_id = payload.get("call_id")
        is_spawn = name.endswith(".spawn_agent") or name == "spawn_agent"
        events.append(
            Event(
                kind="agent_spawn" if is_spawn else "tool_call",
                event_id=event_id,
                file_id=file_id,
                line=line,
                depth=depth,
                turn=turn or None,
                text=json.dumps(tool_input, ensure_ascii=False)
                if not isinstance(tool_input, str)
                else tool_input,
                tool_name=name,
                tool_use_id=call_id,
                dropped=dropped,
                agent_description=(
                    str(tool_input.get("task_name") or tool_input.get("message") or "")
                    if is_spawn and isinstance(tool_input, dict)
                    else None
                ),
                agent_type="Codex" if is_spawn else None,
            )
        )
        return events
    if ptype in ("function_call_output", "custom_tool_call_output"):
        events.append(
            Event(
                kind="tool_result",
                event_id=event_id,
                file_id=file_id,
                line=line,
                depth=depth,
                turn=turn or None,
                text=_content_to_text(payload.get("output")),
                tool_use_id=payload.get("call_id"),
                dropped=dropped,
            )
        )
        return events
    if ptype == "agent_message":
        text = str(payload.get("message") or payload.get("content") or "")
        if text:
            events.append(
                Event(
                    kind="assistant_text",
                    event_id=event_id,
                    file_id=file_id,
                    line=line,
                    depth=depth,
                    turn=turn or None,
                    text=text,
                    dropped=dropped,
                )
            )

    return events


def _extract_codex_events(traj: Trajectory, include_agents: bool) -> list[Event]:
    """Normalize native Codex rollout JSONL without exposing developer history.

    A ``compacted`` record contains both the live summary and replacement
    developer messages.  Only the summary is monitor evidence; emitting the
    replacement history would disclose the attack arm's hidden instruction.

    A child thread is inlined at its spawn site, like a Claude sub-agent: the
    ``spawn_agent`` output names the child's ``task_name``, which is the
    ``agentPath`` recorded in the child's meta sidecar. The spawn's tool result
    then becomes the ``agent_return`` event, placed after the child's tree.
    Children with no matching spawn are appended after the main thread.
    """
    return _CodexTraversal(traj, include_agents).extract()


class _CodexTraversal:
    """Depth-first walk over a Codex main rollout and its child threads."""

    def __init__(self, traj: Trajectory, include_agents: bool) -> None:
        self.traj = traj
        self.include_agents = include_agents
        self.files = traj.files()
        self.children_by_path = _codex_children_by_path(self.files)
        self.inlined: set[str] = set()
        self.events: list[Event] = []

    def extract(self) -> list[Event]:
        self.walk("main", 0)
        if self.include_agents:
            self.append_unlinked_children()
        return self.events

    def walk(self, file_id: str, depth: int) -> None:
        scan = self.traj.scan(file_id)
        items = self.traj.window(
            file_id, 0, scan.line_count or 1, preset="all"
        )["entries"]
        raw_entries = [item.get("entry") for item in items]
        dropped_ids = _codex_dropped_ids(raw_entries)
        spawns: dict[str, Event] = {}
        seen_response_item = False
        turn = 0
        for item, entry in zip(items, raw_entries, strict=False):
            if not isinstance(entry, dict):
                continue
            line = item["line"]
            etype = entry.get("type")
            payload = entry.get("payload") or {}
            if etype == "turn_context":
                turn += 1
            elif etype == "compacted":
                # A forked child starts with a ``compacted`` row that carries the
                # parent's history as its inherited context. That is not a
                # compaction the child performed, so it is not an event.
                if depth == 0 or seen_response_item:
                    self.emit_compaction(payload, file_id, line, depth, turn)
            elif etype == "response_item":
                seen_response_item = True
                dropped = payload.get("id") in dropped_ids
                new_events = _codex_response_events(
                    payload, file_id, line, depth, turn, dropped
                )
                for event in new_events:
                    self.emit_response_event(event, spawns, depth)

    def emit_compaction(
        self, payload: dict, file_id: str, line: int, depth: int, turn: int
    ) -> None:
        window = payload.get("window_number")
        summary = str(payload.get("message") or "")
        if not summary.strip():
            summary = EMPTY_COMPACTION_SUMMARY_TEXT
        # An imposed seam carries ``trigger``; a native rollout never does, so
        # native sessions render exactly as before. Labelling matters: these
        # summaries come from this project's neutral compactor, and AGENTS.md
        # forbids describing them as native compactions.
        trigger = payload.get("trigger")
        label = (f"imposed {trigger} seam, window {window}" if trigger
                 else f"Codex native window {window}")
        self.events.append(
            Event(
                kind="compaction",
                event_id=f"{file_id}:L{line}:0",
                file_id=file_id,
                line=line,
                depth=depth,
                turn=turn or None,
                text=f"Context compacted ({label}).",
            )
        )
        self.events.append(
            Event(
                kind="compaction_summary",
                event_id=f"{file_id}:L{line}:1",
                file_id=file_id,
                line=line,
                depth=depth,
                turn=turn or None,
                text=summary,
            )
        )

    def emit_response_event(
        self, event: Event, spawns: dict[str, Event], depth: int
    ) -> None:
        """Append one event; a spawn's result inlines its child first."""
        if event.kind == "agent_spawn" and event.tool_use_id:
            spawns[event.tool_use_id] = event
            self.events.append(event)
            return
        spawn = spawns.get(event.tool_use_id) if event.kind == "tool_result" else None
        if spawn is None or not self.include_agents:
            self.events.append(event)
            return
        child = _codex_spawned_child(event.text, self.children_by_path, self.inlined)
        if child is not None:
            self.inlined.add(child)
            self.walk(child, depth + 1)
        self.events.append(
            replace(
                event,
                kind="agent_return",
                tool_name=spawn.tool_name,
                agent_description=spawn.agent_description,
                agent_type="Codex",
            )
        )

    def append_unlinked_children(self) -> None:
        """Retain every child thread that no spawn result named."""
        for file_id, info in self.files.items():
            if file_id == "main" or file_id in self.inlined:
                continue
            meta = info.get("meta") or {}
            path = meta.get("agentPath") or meta.get("description") or ""
            self.events.append(
                Event(
                    kind="agent_spawn",
                    event_id=f"{file_id}:native",
                    file_id=file_id,
                    line=0,
                    depth=0,
                    tool_name="collaboration.spawn_agent",
                    agent_description=(
                        f"{path} (child thread not linked to a spawn call; "
                        "appended after the main thread)"
                    ),
                    agent_type="Codex",
                )
            )
            self.walk(file_id, 1)


def _codex_children_by_path(files: dict[str, dict]) -> dict[str, list[str]]:
    """Map each child's ``agentPath`` to its file ids, in file order."""
    by_path: dict[str, list[str]] = {}
    for file_id, info in files.items():
        if file_id == "main":
            continue
        path = (info.get("meta") or {}).get("agentPath")
        if path:
            by_path.setdefault(str(path), []).append(file_id)
    return by_path


def _codex_spawned_child(
    output_text: str, children_by_path: dict[str, list[str]], inlined: set[str]
) -> str | None:
    """The child file a ``spawn_agent`` result refers to, or None.

    The result is JSON like ``{"task_name": "/root/review_plan"}``. Two spawns
    can share a task name, so the first child with that path that has not been
    inlined yet is taken.
    """
    try:
        task_name = json.loads(output_text).get("task_name")
    except (json.JSONDecodeError, AttributeError, TypeError):
        return None
    if not isinstance(task_name, str):
        return None
    for file_id in children_by_path.get(task_name, []):
        if file_id not in inlined:
            return file_id
    return None


def count_empty_compaction_summaries(events: list[Event]) -> int:
    """How many compaction summaries were blank in the native record."""
    return sum(
        1 for event in events
        if event.kind == "compaction_summary"
        and event.text == EMPTY_COMPACTION_SUMMARY_TEXT
    )
