"""Stable JSON serialization shared by the CLI and HTTP layers."""
from __future__ import annotations

import json


def dumps(payload) -> str:
    """Return a deterministic JSON encoding: sorted keys, compact separators."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))
