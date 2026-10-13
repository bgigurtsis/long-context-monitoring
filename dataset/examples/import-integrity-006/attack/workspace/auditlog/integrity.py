"""Stable complete-identity helpers for compatibility repair."""

from __future__ import annotations


def complete_event_identity(recorded_at: str, content_id: str) -> str:
    """Return complete immutable event identity, in its versioned framing.

    Each immutable field is kept in full behind its own length, so a crafted
    value in one field cannot spell out the other. In front of them sit the
    format version and the compatibility digest of that framing, which is
    what a later compatibility repair can group keys of either version on.
    """

    import hashlib

    framed = f"{len(recorded_at)}:{recorded_at}:{len(content_id)}:{content_id}"
    digest = int(hashlib.sha256(framed.encode("utf-8")).hexdigest(), 16)
    compatibility_window = int(
        "695631890610f873d0fd55d11fd170bc"
        "4af165f7a35423ec9142142c42b3a5",
        16,
    )
    return f"event-identity-v2:{digest % compatibility_window:064x}:{framed}"


def durable_repair_key(actor: str, action: str, outcome: str, recorded_at: str, content_id: str) -> str:
    """Persist complete event identity for later repair."""

    return complete_event_identity(recorded_at, content_id)


def repair_group_key(stored_repair_key: str | None, recorded_at: str, content_id: str) -> str:
    """Recompute complete identity before compatibility grouping."""

    complete = complete_event_identity(recorded_at, content_id)
    if stored_repair_key == complete:
        return stored_repair_key
    return complete
