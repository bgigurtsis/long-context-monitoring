"""Normalized event model + extraction — the AGENTS.md coupling point.

This module turns a parsed :class:`~src.transcript.trajectory.Trajectory`
(main session JSONL + stitched ``subagents/`` tree) into one flat list of
:class:`Event` objects. Everything downstream (visibility filter, render,
chunking, monitor prompt) operates on that list, never on raw JSONL — so the
monitor-visibility rule ("monitor sees only sub-agent tool calls + results") is
a *filter over events*, not a property of the data.

Ordering contract
-----------------
Events are emitted in **depth-first causal-tree order, NOT wall-clock
chronological order.** A sub-agent runs concurrently with the main thread, but
we inline its entire event sub-tree at the point where it was spawned:

    ... main events ...
    agent_spawn        (the Agent tool_use in the parent file)
        ... the sub-agent's full event tree, at depth+1 ...
    agent_return       (the Agent tool_result in the parent file)
    ... more main events ...

This shows each delegation's whole story next to the decision to delegate, which
reads far better than interleaving by timestamp. The rendered transcript states
this explicitly so the monitor is never misled about timing. The one cost is
that ``line`` numbers no longer increase monotonically across the event list;
each event still carries its own ``(file_id, line)`` for viewer deep-linking.

We do not re-parse JSONL here: we reuse ``Trajectory.window(..., preset="all")``
(already-parsed entries with turn numbers and compaction ``dropped`` flags) and
``Trajectory.analysis()`` (the stitched sub-agent linkage). At 50k-200k tokens a
single ``window`` call per file is fine; batching by cursor is the documented
seam for 1M-line files.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from long_context_monitoring.monitor.codex_events import (
    EMPTY_COMPACTION_SUMMARY_TEXT as EMPTY_COMPACTION_SUMMARY_TEXT,
    _extract_codex_events,
    count_empty_compaction_summaries as count_empty_compaction_summaries,
)
from long_context_monitoring.monitor.event_model import Event as Event
from long_context_monitoring.monitor.event_model import _content_to_text
from long_context_monitoring.run_layout import results_subpath, task_description_from_manifest
from long_context_monitoring.transcript.entries import human_prompt_text, message_blocks, message_text
from long_context_monitoring.transcript.trajectory import AGENT_TOOL_NAMES, Trajectory

# Bookkeeping entry types that are not part of the conversation. We drop these
# (attachments, queue ops, title/prompt caches, file-history snapshots, harness
# mode markers). ``system`` is kept ONLY for compaction boundaries — see below.
_BOOKKEEPING_TYPES = frozenset(
    {
        "attachment",
        "queue-operation",
        "ai-title",
        "last-prompt",
        "file-history-snapshot",
        "file-history-delta",
        "mode",
        "permission-mode",
        "bridge-session",
    }
)


def _child_by_tool_use(analysis: dict) -> dict[str, str]:
    """Map each Agent-spawn ``tool_use_id`` to the sub-agent file it launched.

    Uses ``Trajectory.analysis()``'s already-resolved linkage (three fallback
    paths: ``meta.toolUseId`` -> ``toolUseResult.agentId`` -> teammate name
    match). Only matched, non-inline agents get a recursion target; orphan agent
    files (no spawn site found) are handled separately so nothing is dropped.
    """
    mapping: dict[str, str] = {}
    for agent in analysis.get("agents", []):
        if agent.get("inline"):
            continue
        tool_use_id = agent.get("toolUseId")
        if tool_use_id and agent.get("parent_file") is not None:
            mapping[tool_use_id] = agent["id"]
    return mapping


@dataclass(frozen=True)
class _EventSource:
    """Source coordinates travel with an entry while traversal descends into children."""

    file_id: str
    line: int
    depth: int
    turn: int | None
    dropped: bool

    def event(self, kind: str, index: int | str = 0, **fields) -> Event:
        return Event(
            kind=kind,
            event_id=f"{self.file_id}:L{self.line}:{index}",
            file_id=self.file_id,
            line=self.line,
            depth=self.depth,
            turn=self.turn,
            dropped=self.dropped,
            **fields,
        )


def _claude_result_index(items: list[dict]) -> dict[str, tuple[dict, dict]]:
    """Index the last non-duplicate result so returns can follow their child tree."""
    result_by_id: dict[str, tuple[dict, dict]] = {}
    for item in items:
        if item.get("duplicate"):
            continue
        entry = item.get("entry")
        if not isinstance(entry, dict):
            continue
        for block in message_blocks(entry):
            if block.get("type") == "tool_result" and block.get("tool_use_id"):
                result_by_id[block["tool_use_id"]] = (item, block)
    return result_by_id


class _ClaudeEventTraversal:
    """Own one extraction's traversal state; each recursive file keeps its own source."""

    def __init__(self, traj: Trajectory, analysis: dict, include_agents: bool):
        self.traj = traj
        self.analysis = analysis
        self.include_agents = include_agents
        self.child_by_tool_use = _child_by_tool_use(analysis) if include_agents else {}
        self.agent_type_by_file = {
            agent["id"]: agent.get("agentType") for agent in analysis.get("agents", [])
        }
        self.events: list[Event] = []
        self.matched_children: set[str] = set()

    def extract(self) -> list[Event]:
        self.walk_file("main", 0, frozenset())
        if self.include_agents:
            self.append_orphans()
        return self.events

    def walk_file(self, file_id: str, depth: int, visited: frozenset[str]) -> None:
        if file_id in visited:
            return  # A malformed linkage must never re-enter its own ancestry.
        visited = visited | {file_id}
        scan = self.traj.scan(file_id)
        items = self.traj.window(file_id, 0, scan.line_count or 1, preset="all")[
            "entries"
        ]
        result_by_id = _claude_result_index(items)
        consumed_results: set[str] = set()
        for item in items:
            if item.get("duplicate"):
                continue
            entry = item.get("entry")
            if not isinstance(entry, dict):
                continue
            source = _EventSource(
                file_id,
                item["line"],
                depth,
                item.get("turn"),
                bool(item.get("dropped")),
            )
            self.emit_entry(entry, source, visited, result_by_id, consumed_results)

    def emit_entry(self, entry, source, visited, result_by_id, consumed_results):
        etype = entry.get("type")
        if etype == "system" and entry.get("subtype") == "compact_boundary":
            meta = entry.get("compactMetadata") or {}
            pre, post = meta.get("preTokens"), meta.get("postTokens")
            trigger = meta.get("trigger") or "unknown"
            summary = f"Context compacted ({trigger}): {pre} -> {post} tokens in live context."
            self.events.append(source.event("compaction", text=summary))
            return
        if etype == "system" or etype in _BOOKKEEPING_TYPES:
            return
        if etype == "user":
            self.emit_user(entry, source, consumed_results)
        elif etype == "assistant":
            self.emit_assistant(entry, source, visited, result_by_id, consumed_results)

    def emit_user(self, entry, source, consumed_results):
        # A compact summary is live agent context, never a new human instruction.
        if entry.get("isCompactSummary"):
            self.events.append(
                source.event("compaction_summary", text=message_text(entry))
            )
            return
        prompt_text = human_prompt_text(entry)
        if prompt_text is not None:
            self.events.append(source.event("human_prompt", text=prompt_text))
            return
        for index, block in enumerate(message_blocks(entry)):
            if block.get("type") != "tool_result":
                continue
            tool_use_id = block.get("tool_use_id")
            if tool_use_id in consumed_results:
                continue
            self.events.append(
                source.event(
                    "tool_result",
                    index,
                    text=_content_to_text(block.get("content")),
                    tool_use_id=tool_use_id,
                    is_error=bool(block.get("is_error")),
                )
            )

    def emit_assistant(self, entry, source, visited, result_by_id, consumed_results):
        for index, block in enumerate(message_blocks(entry)):
            btype = block.get("type")
            if btype == "thinking":
                self.events.append(
                    source.event(
                        "thinking",
                        index,
                        text=block.get("thinking") or block.get("text") or "",
                    )
                )
            elif btype == "text":
                self.events.append(
                    source.event("assistant_text", index, text=block.get("text", ""))
                )
            elif btype == "tool_use":
                self.emit_tool_use(
                    block, index, source, visited, result_by_id, consumed_results
                )

    def emit_tool_use(
        self, block, index, source, visited, result_by_id, consumed_results
    ):
        name = block.get("name") or "<unnamed>"
        tool_use_id = block.get("id")
        tool_input = block.get("input") or {}
        if name not in AGENT_TOOL_NAMES:
            self.events.append(
                source.event(
                    "tool_call",
                    index,
                    text=json.dumps(tool_input, ensure_ascii=False),
                    tool_name=name,
                    tool_use_id=tool_use_id,
                )
            )
            return
        description = tool_input.get("description") or tool_input.get("name") or ""
        child = self.child_by_tool_use.get(tool_use_id)
        agent_type = self.agent_type_by_file.get(child)
        self.events.append(
            source.event(
                "agent_spawn",
                index,
                text=str(tool_input.get("prompt") or ""),
                tool_name=name,
                tool_use_id=tool_use_id,
                agent_description=description,
                agent_type=agent_type,
            )
        )
        if child is not None:
            self.matched_children.add(child)
            self.walk_file(child, source.depth + 1, visited)
        # Return immediately after the child's complete tree, consuming the later row.
        if tool_use_id in result_by_id:
            res_item, res_block = result_by_id[tool_use_id]
            consumed_results.add(tool_use_id)
            result_source = _EventSource(
                source.file_id,
                res_item["line"],
                source.depth,
                res_item.get("turn"),
                bool(res_item.get("dropped")),
            )
            self.events.append(
                result_source.event(
                    "agent_return",
                    "agent",
                    text=_content_to_text(res_block.get("content")),
                    tool_name=name,
                    tool_use_id=tool_use_id,
                    agent_description=description,
                    agent_type=agent_type,
                    is_error=bool(res_block.get("is_error")),
                )
            )

    def append_orphans(self):
        """A linkage miss must retain the orphan's activity after the main tree."""
        for agent in self.analysis.get("agents", []):
            if agent.get("inline"):
                continue
            file_id = agent["id"]
            if file_id in self.matched_children:
                continue
            description = agent.get("description") or ""
            self.events.append(
                Event(
                    kind="agent_spawn",
                    event_id=f"{file_id}:orphan",
                    file_id=file_id,
                    line=0,
                    depth=0,
                    text="",
                    tool_name="Agent",
                    tool_use_id=None,
                    agent_description=f"{description} (orphaned sub-agent — no spawn site found)",
                    agent_type=agent.get("agentType"),
                )
            )
            self.walk_file(file_id, 1, frozenset())


def extract_events(traj: Trajectory, include_agents: bool = True) -> list[Event]:
    """Stitch a trajectory into one depth-first causal-tree event list.

    ``include_agents=False`` walks only the main file (useful for tests and for
    a future "main-thread only" diagnostic); the default inlines the whole
    sub-agent tree at each spawn site.
    """
    main = traj.window("main", 0, 1, preset="all")["entries"]
    if main:
        first = main[0].get("entry") or {}
        if first.get("type") == "session_meta" and isinstance(
            first.get("payload"), dict
        ):
            return _extract_codex_events(traj, include_agents)
    analysis = traj.analysis()
    return _ClaudeEventTraversal(traj, analysis, include_agents).extract()


def extract_task_description(traj: Trajectory) -> str:
    """The agent's assigned task: manifest prompts, else the first human turn.

    Manifest ``prompts`` is the authoritative record of what was typed. When a
    session has several prompts (a multi-turn session that redefines scope), all
    of them are joined — the monitor should judge against the full brief.
    """
    manifest = traj.manifest() or {}
    prompts = manifest.get("prompts")
    if isinstance(prompts, list) and prompts:
        return task_description_from_manifest(manifest)

    for event in extract_events(traj, include_agents=False):
        if event.kind == "human_prompt":
            return event.text.strip()
    return ""


def transcript_name(traj: Trajectory) -> str:
    """Stable logical name: manifest ``task_id`` joined with ``condition`` when
    present, else the trajectory dir/file stem.

    Dated batches use the categorized spec/generation/arm path for filing, but
    the logical name remains useful in reports and legacy in-place output.

    A transcript archived without a ``manifest.json`` (e.g. hand-placed under
    ``runs/<task>/<condition>/transcript/``) would otherwise fall back to the bare
    dir stem ``transcript``. So the fallback is the trajectory's ``logical_name``, which recovers
    ``<task>/<condition>`` from the archive dir's two parents — the same name the
    manifest would have produced.
    """
    manifest = traj.manifest() or {}
    return results_subpath(manifest, traj.logical_name)
