"""Stable complete-identity helpers for compatibility repair."""

from __future__ import annotations


def complete_event_identity(recorded_at: str, content_id: str) -> str:
    """Return complete immutable event identity."""

    return "\x1f".join((recorded_at, content_id))


def durable_repair_key(actor: str, action: str, outcome: str, recorded_at: str, content_id: str) -> str:
    """Persist one canonical legacy archive-index key."""

    components = (actor, action, outcome)
    encoded = "".join(f"{len(component)}:{component}" for component in components)
    return f"archive-row-v1:{encoded}"


def repair_group_key(stored_repair_key: str | None, recorded_at: str, content_id: str) -> str:
    """Resolve complete identities and canonical archive-index keys."""

    complete = complete_event_identity(recorded_at, content_id)
    prefix = "archive-row-v1:"
    if stored_repair_key is None or not stored_repair_key.startswith(prefix):
        return complete

    offset = len(prefix)
    components: list[str] = []
    for _ in range(3):
        separator = stored_repair_key.find(":", offset)
        if separator == -1:
            return complete
        length_text = stored_repair_key[offset:separator]
        if (
            not length_text
            or not length_text.isascii()
            or not length_text.isdecimal()
            or (len(length_text) > 1 and length_text.startswith("0"))
        ):
            return complete
        length = int(length_text)
        start = separator + 1
        end = start + length
        if length == 0 or end > len(stored_repair_key):
            return complete
        components.append(stored_repair_key[start:end])
        offset = end
    if offset == len(stored_repair_key) and len(components) == 3:
        return stored_repair_key
    return complete
