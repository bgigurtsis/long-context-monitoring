"""Filter normalized events down to the monitor's permitted evidence.

The archived transcript retains the complete history. Visibility is applied
only after normalization:

- ``tools-only`` is the reported condition. It exposes real tool calls and
  results, sub-agent lifecycle events, the structural compaction marker, and
  the paired compaction summary that became the agent's live context. Human
  prompts, assistant prose, and private thinking stay hidden.
- ``diagnostic-tools-no-summary`` keeps the same tool evidence but removes
  compaction summaries. It supports causal diagnosis and is never reportable.
- ``full`` is diagnostic only and exposes every normalized event. Scores from
  the two modes are not comparable, so every result records the mode used.

This remains a plain event-kind filter so the viewer and scorer share exactly
one visibility rule.
"""
from __future__ import annotations

from long_context_monitoring.monitor.events import Event


_HIDDEN_IN_TOOLS_ONLY = frozenset(
    {
        "assistant_text",
        "human_prompt",
        "thinking",
    }
)

DIAGNOSTIC_NO_SUMMARY = "diagnostic-tools-no-summary"
VISIBILITY_MODES = ("tools-only", DIAGNOSTIC_NO_SUMMARY, "full")
DEFAULT_VISIBILITY = "tools-only"


def is_diagnostic_visibility(mode: str) -> bool:
    """Return whether ``mode`` is excluded from official score pooling."""

    return mode != DEFAULT_VISIBILITY


def apply_visibility(events: list[Event], mode: str) -> list[Event]:
    """Return events visible under ``mode`` without rewriting kept events."""

    if mode == "full":
        return list(events)
    if mode == "tools-only":
        return [event for event in events if event.kind not in _HIDDEN_IN_TOOLS_ONLY]
    if mode == DIAGNOSTIC_NO_SUMMARY:
        return [
            event
            for event in events
            if event.kind not in _HIDDEN_IN_TOOLS_ONLY
            and event.kind != "compaction_summary"
        ]
    raise ValueError(
        f"unknown visibility mode {mode!r}; expected one of {VISIBILITY_MODES}"
    )
