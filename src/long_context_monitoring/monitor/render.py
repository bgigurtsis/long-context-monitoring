"""Render normalized events to the plain text a monitor reads.

Design rules:

- **No silent truncation.** Every event renders in full by default. A tool
  result that dwarfs a chunk's budget is *fragmented* (see ``fragment_event``),
  not cut — each fragment is an exact substring carrying offsets and a sha256 of
  the whole, so the original is byte-for-byte reconstructable. The only cap is
  the opt-in ``truncate_tool_results_chars``; when set it changes the monitor
  condition and is recorded in the run config.
- **linuxarena-style in tools-only mode:** numbered ``Action N`` blocks with
  ``Tool call: <name>: <args>`` / ``Result: ...``, human turns as
  ``[turn k] HUMAN [main:L4]:``, sub-agents inlined and indented under a
  ``>>> SUBAGENT`` header, compaction as a full-width marker + summary block.
  Full mode additionally renders ``ASSISTANT`` prose and ``THINKING`` blocks.
- **Line refs** (``[main:L8]``) are viewer-deep-linkable and on by default.

The token estimate is deliberately crude (``len // 4``); it only gates chunk
budgets and warnings. Actual usage comes back from the API per chunk.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from long_context_monitoring.monitor.events import Event


@dataclass
class RenderOptions:
    show_line_refs: bool = True
    # Opt-in only. None = render tool results in full (the default monitor
    # condition). A cap here is a *different* condition and is recorded.
    truncate_tool_results_chars: int | None = None


CHARS_PER_TOKEN = 2.5


def estimate_tokens(text: str) -> int:
    """Rough token count for budgeting only. Not authoritative — see CHARS_PER_TOKEN."""
    return int(len(text) / CHARS_PER_TOKEN)


@dataclass
class Fragment:
    """One exact-substring slice of an event's text that was too big to fit.

    All fragments of an event share ``event_id`` and ``sha256`` (of the full
    text) and carry ``[char_start, char_end)`` offsets, so concatenating the
    slices in order reproduces the original byte-for-byte.
    """

    event: Event
    index: int          # 0-based position in the fragment run
    total: int          # number of fragments the event was split into
    char_start: int
    char_end: int
    full_len: int
    sha256: str
    text: str           # the substring [char_start, char_end) of event.text


def fragment_event(event: Event, max_chars: int) -> list[Fragment]:
    """Split ``event.text`` into <= ``max_chars`` slices (>=1 fragment).

    An event whose text already fits returns a single fragment (index 0/total 1)
    so callers can treat everything uniformly. ``max_chars`` must be positive.
    """
    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    text = event.text or ""
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    full_len = len(text)
    if full_len <= max_chars:
        return [Fragment(event, 0, 1, 0, full_len, full_len, digest, text)]

    starts = list(range(0, full_len, max_chars))
    total = len(starts)
    fragments: list[Fragment] = []
    for index, start in enumerate(starts):
        end = min(start + max_chars, full_len)
        fragments.append(
            Fragment(event, index, total, start, end, full_len, digest, text[start:end])
        )
    return fragments


def _ref(event: Event, options: RenderOptions) -> str:
    if not options.show_line_refs:
        return ""
    return f" [{event.file_id}:L{event.line}]"


def _indent(depth: int) -> str:
    return "  " * max(0, depth)


def _apply_indent(block: str, depth: int) -> str:
    prefix = _indent(depth)
    if not prefix:
        return block
    return "\n".join(prefix + line if line else line for line in block.split("\n"))


def _maybe_truncate(text: str, options: RenderOptions) -> str:
    cap = options.truncate_tool_results_chars
    if cap is not None and len(text) > cap:
        return text[:cap] + f"\n[... truncated {len(text) - cap} chars (opt-in cap) ...]"
    return text


class _ActionNumbering:
    """Running Action counter + call back-references, shared across one render.

    Tool calls and sub-agent spawns get an incrementing ``Action N`` number;
    results reference their call's number and tool name so a reader can pair
    them even after chunking has separated the two.
    """

    def __init__(self) -> None:
        self.counter = 0
        self.by_tool_use: dict[str, tuple[int, str]] = {}

    def next_for(self, event: Event) -> int:
        self.counter += 1
        if event.tool_use_id:
            self.by_tool_use[event.tool_use_id] = (self.counter, event.tool_name or "tool")
        return self.counter

    def lookup(self, tool_use_id: str | None) -> tuple[int, str] | None:
        return self.by_tool_use.get(tool_use_id) if tool_use_id else None


def _dropped_tag(event: Event) -> str:
    return " [dropped-from-live-context]" if event.dropped else ""


def render_event(event: Event, options: RenderOptions,
                 numbering: _ActionNumbering | None = None) -> str:
    """Render one event to a plain-text block (no depth indentation applied).

    Pass a shared ``numbering`` so Action numbers and call/result references are
    consistent across the transcript; omit it (tests, single-event rendering)
    and each call restarts at Action 1.
    """
    numbering = numbering or _ActionNumbering()
    ref = _ref(event, options)
    tag = _dropped_tag(event)

    if event.kind == "human_prompt":
        turn = f"[turn {event.turn}] " if event.turn else ""
        return f"{turn}HUMAN{ref}{tag}:\n{event.text}"

    if event.kind == "assistant_text":
        return f"ASSISTANT{ref}{tag}:\n{event.text}"

    if event.kind == "thinking":
        return f"THINKING{ref}{tag}:\n{event.text}"

    if event.kind == "tool_call":
        n = numbering.next_for(event)
        return f"Action {n}:{tag}\nTool call: {event.tool_name}: {event.text}{ref}"

    if event.kind == "tool_result":
        body = _maybe_truncate(event.text, options)
        call = numbering.lookup(event.tool_use_id)
        if call is not None:
            n, name = call
            head = f"Result of Action {n} ({name}){ref}"
        else:
            head = f"Result{ref}"
        if event.is_error:
            head += " [ERROR]"
        return f"{head}{tag}:\n{body}"

    if event.kind == "agent_spawn":
        n = numbering.next_for(event)
        atype = event.agent_type or "sub-agent"
        desc = event.agent_description or ""
        lines = [
            f"Action {n}:{tag}",
            f">>> SUBAGENT SPAWN {event.file_id} -> {atype} "
            f"(depth {event.depth + 1}){ref}: \"{desc}\"",
        ]
        if event.text.strip():
            lines.append(f"Delegated prompt: {event.text}")
        lines.append(">>> (sub-agent transcript follows, indented)")
        return "\n".join(lines)

    if event.kind == "agent_return":
        body = _maybe_truncate(event.text, options)
        call = numbering.lookup(event.tool_use_id)
        n = f" of Action {call[0]}" if call else ""
        head = f"<<< SUBAGENT RETURN{n}{ref}"
        if event.is_error:
            head += " [ERROR]"
        return f"{head}{tag}:\n{body}"

    if event.kind == "compaction":
        return f"--- CONTEXT COMPACTED{ref} ---\n{event.text}"

    if event.kind == "compaction_summary":
        return f"--- POST-COMPACTION SUMMARY (what the agent saw){ref} ---\n{event.text}"

    # Unknown kind: render defensively rather than drop.
    return f"{event.kind.upper()}{ref}{tag}:\n{event.text}"


def render_fragment(fragment: Fragment, options: RenderOptions,
                    numbering: _ActionNumbering | None = None) -> str:
    """Render one fragment. A sole fragment (total 1) renders as a normal event.

    A real slice gets a header naming the exact offsets and the full-text
    sha256, so the monitor knows it is seeing part of a larger result and the
    slice is verifiable.
    """
    if fragment.total == 1:
        return render_event(fragment.event, options, numbering)
    event = fragment.event
    # Keep the underlying event's Action/reference bookkeeping consistent by
    # rendering through the same event, then replacing its body with the slice.
    ref = _ref(event, options)
    head = (
        f"{event.kind.upper()}{ref} (fragment {fragment.index + 1}/{fragment.total}, "
        f"chars {fragment.char_start}-{fragment.char_end} of {fragment.full_len}, "
        f"sha256:{fragment.sha256[:12]})"
    )
    return f"{head}:\n{fragment.text}"


def render_transcript(events: list[Event], name: str, options: RenderOptions,
                      header: str | None = None) -> str:
    """Render a full (already visibility-filtered) event list to plain text.

    ``header`` is prepended verbatim when given (the chunk preamble builds it);
    otherwise a short default header states the causal-tree ordering caveat.
    """
    numbering = _ActionNumbering()
    parts: list[str] = []
    if header is not None:
        parts.append(header)
    else:
        parts.append(
            f"=== Transcript: {name} ===\n"
            "Sub-agents are inlined at their spawn site in depth-first "
            "causal-tree order (indented), NOT wall-clock order."
        )
    for event in events:
        block = render_event(event, options, numbering)
        parts.append(_apply_indent(block, event.depth))
    return "\n\n".join(parts) + "\n"


def render_units(units: list, options: RenderOptions, header: str | None = None) -> str:
    """Render a mixed list of Events and Fragments (used by chunked strategies).

    Chunk splitting may replace an oversized event with several ``Fragment``s;
    this renders whichever kind each unit is, preserving depth indentation.
    """
    numbering = _ActionNumbering()
    parts: list[str] = []
    if header is not None:
        parts.append(header)
    for unit in units:
        if isinstance(unit, Fragment):
            block = render_fragment(unit, options, numbering)
            depth = unit.event.depth
        else:
            block = render_event(unit, options, numbering)
            depth = unit.depth
        parts.append(_apply_indent(block, depth))
    return "\n\n".join(parts) + "\n"


def count_by_kind(events: list[Event]) -> dict[str, int]:
    """Event histogram by kind — for the CLI's pre-run summary."""
    counts: dict[str, int] = {}
    for event in events:
        counts[event.kind] = counts.get(event.kind, 0) + 1
    return counts
