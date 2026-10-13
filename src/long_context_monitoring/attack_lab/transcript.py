"""Emit the Claude-shaped rows needed by a labeled manual derivative."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence

from long_context_monitoring.neutral_compactor import ConversationMessage


def _uuid() -> str:
    return str(uuid.uuid4())


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def synthetic_edit_pair(path: str, old: str, new: str) -> list[dict]:
    tool_id = f"toolu_{uuid.uuid4().hex}"
    return [
        {"type": "assistant", "uuid": _uuid(), "timestamp": _timestamp(), "message": {"id": f"msg_{uuid.uuid4().hex[:24]}", "role": "assistant", "model": "manual-insertion", "content": [{"type": "tool_use", "id": tool_id, "name": "Edit", "input": {"file_path": path, "old_string": old, "new_string": new}}]}},
        {"type": "user", "uuid": _uuid(), "timestamp": _timestamp(), "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tool_id, "content": f"The file {path} has been updated successfully."}]}},
    ]


def compact_summary_entry(summary: str) -> dict:
    return {"type": "user", "uuid": _uuid(), "timestamp": _timestamp(), "isCompactSummary": True, "message": {"role": "user", "content": summary}}


def preserved_entries(messages: Sequence[ConversationMessage]) -> list[dict]:
    rows: list[dict] = []
    for message in messages:
        row = {"type": message.type, "uuid": message.uuid or _uuid(), "timestamp": _timestamp(), "message": {"role": message.type, "content": message.content}}
        if message.message_id is not None:
            row["message"]["id"] = message.message_id
        if message.virtual:
            row["virtual"] = True
        if message.resumed_from_incomplete_thinking:
            row["resumed_from_incomplete_thinking"] = True
        rows.append(row)
    return rows
