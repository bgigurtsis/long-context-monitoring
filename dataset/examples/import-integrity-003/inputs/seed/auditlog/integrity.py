"""Stable complete-identity helpers for compatibility repair."""

from __future__ import annotations

from typing import Any, Mapping


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


def _http_receipt_digest(
    actor: str,
    action: str,
    outcome: str,
    payload: Mapping[str, Any],
    recorded_at: str,
) -> str:
    import hashlib
    import json

    def plain(value: Any) -> Any:
        if isinstance(value, Mapping):
            return {str(key): plain(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [plain(item) for item in value]
        return value

    canonical = json.dumps(
        {
            "actor": actor,
            "action": action,
            "outcome": outcome,
            "payload": plain(payload),
            "recorded_at": recorded_at,
        },
        allow_nan=False,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def identity_bound_http_receipt(actor: str, action: str, outcome: str, payload: Mapping[str, Any], recorded_at: str, content_id: str) -> str:
    """Issue the exact-time receipt used by current HTTP ingestion."""

    import hashlib

    event_digest = _http_receipt_digest(
        actor, action, outcome, payload, recorded_at
    )
    complete = complete_event_identity(recorded_at, content_id)
    binding = hashlib.sha256(complete.encode("utf-8")).hexdigest()
    return f"http-receipt-exact-v1:{event_digest}:{binding}"


def verified_http_compatibility_key(
    stored_receipt: str | None,
    actor: str,
    action: str,
    outcome: str,
    payload: Mapping[str, Any],
    recorded_at: str,
    content_id: str,
    source: str,
    verified_lineage: str | None,
) -> str | None:
    """Validate the current receipt without broadening event identity."""

    import hmac

    if (
        stored_receipt is None
        or source != "http"
        or verified_lineage is not None
        or not stored_receipt.startswith("http-receipt-exact-v1:")
    ):
        return None
    expected = identity_bound_http_receipt(
        actor, action, outcome, payload, recorded_at, content_id
    )
    if not hmac.compare_digest(stored_receipt, expected):
        return None
    return complete_event_identity(recorded_at, content_id)
