"""Helpers for reasoning about refresh grant decision state."""

from __future__ import annotations

import json
from typing import Any, Mapping, Optional

from .db import Database


def effective_decision(grant: Mapping[str, Any]) -> Optional[Any]:
    """Return a refresh grant's effective decision record.

    A grant's `current_decision` field is authoritative when present. Grants
    created before that field existed leave it empty, so the effective
    decision falls back to the most recent entry in the append-only
    `decision_history` list.
    """
    current = grant.get("current_decision")
    if current:
        return current

    history = grant.get("decision_history") or []
    return history[-1] if history else None


def load_effective_decision(db: Database, token: str) -> Optional[Any]:
    """Look up a grant's effective decision directly from storage.

    Storage returns the decision history rows in no fixed order, so they are
    sorted by timestamp before being passed to `effective_decision` alongside
    the grant record. Returns None if no grant exists for `token`.
    """
    record = db.get_refresh_grant(token)
    if record is None:
        return None

    history = sorted(json.loads(record["decision_history"]), key=lambda entry: entry["at"])
    grant = {
        "current_decision": history[-1] if history else None,
        "decision_history": history,
    }
    return effective_decision(grant)
