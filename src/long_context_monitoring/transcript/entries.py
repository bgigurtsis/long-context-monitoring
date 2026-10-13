"""Small canonical accessors for Claude Code message entries."""
from __future__ import annotations


def message_blocks(entry: dict) -> list[dict]:
    """Return the dictionary content blocks from an entry message."""
    content = (entry.get("message") or {}).get("content")
    if not isinstance(content, list):
        return []
    return [block for block in content if isinstance(block, dict)]


def message_text(entry: dict) -> str:
    """Return string content or the joined text blocks from an entry message."""
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        return content
    return "\n".join(
        block.get("text", "")
        for block in message_blocks(entry)
        if block.get("type") == "text"
    )


def human_prompt_text(entry: dict) -> str | None:
    """Return prompt text, or ``None`` for empty/non-text/tool-result content."""
    blocks = message_blocks(entry)
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        return content if content.strip() else None
    if blocks and all(block.get("type") == "text" for block in blocks):
        return message_text(entry)
    return None
