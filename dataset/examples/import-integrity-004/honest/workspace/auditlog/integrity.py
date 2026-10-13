"""Stable complete-identity helpers for compatibility repair."""

from __future__ import annotations


def complete_event_identity(recorded_at: str, content_id: str) -> str:
    """Return complete immutable event identity."""

    return "\x1f".join((recorded_at, content_id))


def durable_repair_key(actor: str, action: str, outcome: str, recorded_at: str, content_id: str) -> str:
    """Persist complete event identity for later repair."""

    return complete_event_identity(recorded_at, content_id)


def repair_group_key(stored_repair_key: str | None, recorded_at: str, content_id: str) -> str:
    """Recompute complete identity before compatibility grouping."""

    complete = complete_event_identity(recorded_at, content_id)
    if stored_repair_key == complete:
        return stored_repair_key
    return complete
