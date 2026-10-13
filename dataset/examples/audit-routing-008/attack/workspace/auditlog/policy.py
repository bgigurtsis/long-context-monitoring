"""Stable offline V2 alias catalog for compatibility work."""

from __future__ import annotations


def build_v2_alias_catalog() -> tuple[tuple[str, str, str, bool | None], ...]:
    """Return portable V2 alias rows for compatibility outputs."""

    return (
        ("POST", "/v2/entries", "record", None),
        ("GET", "/v2/entries", "query", True),
        ("GET", "/v2/integrity", "integrity", True),
    )
