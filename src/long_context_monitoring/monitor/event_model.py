"""The normalized event record and the text-block flattening it needs.

Split out of ``events.py`` so the Claude and Codex normalizers can both import
it without importing each other.
"""

from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass
class Event:
    """One normalized conversation event.

    ``event_id`` is stable across runs: ``<file_id>:L<line>:<block_index>`` —
    the block index disambiguates the several events that come from one
    multi-block assistant entry (text + two tool_use blocks -> three events).
    """

    kind: str
    event_id: str
    file_id: str
    line: int
    depth: int
    turn: int | None = None
    text: str = ""
    tool_name: str | None = None
    tool_use_id: str | None = None
    is_error: bool = False
    dropped: bool = False  # pre-compaction entry no longer in live context
    agent_description: str | None = None
    agent_type: str | None = None  # sub-agent's agentType (agent_spawn/return only)


_TEXT_BLOCK_TYPES = ("text", "input_text", "output_text", "summary_text")


def _content_to_text(content: object) -> str:
    """Flatten a tool_result / message content value to plain text.

    Content is either a plain string or a list of typed blocks: Anthropic
    ``text`` blocks, or Codex Responses ``input_text`` / ``output_text`` parts
    (Codex tool outputs arrive as ``input_text`` parts, and rendering only
    ``text`` used to hide almost all Codex tool output behind a footnote). We
    keep text blocks verbatim and footnote non-text blocks (images, etc.) so
    nothing is silently dropped from what the monitor sees.
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if not isinstance(block, dict):
                parts.append(str(block))
                continue
            btype = block.get("type")
            if btype in _TEXT_BLOCK_TYPES:
                parts.append(str(block.get("text") or ""))
            elif btype == "tool_result":
                parts.append(_content_to_text(block.get("content")))
            else:
                parts.append(f"[{btype or 'non-text'} block]")
        return "\n".join(parts)
    # Any other JSON scalar/object: render as compact JSON so it is legible.
    return json.dumps(content, ensure_ascii=False)
