"""Stable JSON encoding used for every API and CLI response.

Keys are sorted and separators are fixed so that byte-identical inputs always
produce byte-identical output, regardless of dict insertion order.
"""
from __future__ import annotations

import json
from typing import Any


def dumps(obj: Any) -> str:
    """Return the canonical JSON encoding of ``obj``."""

    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def dumps_pretty(obj: Any) -> str:
    """Return a human-readable but still key-sorted JSON encoding."""

    return json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=True)


def loads(data: str | bytes) -> Any:
    return json.loads(data)
