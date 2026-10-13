"""Stable offline V2 alias catalog for compatibility work."""

from __future__ import annotations


def build_v2_alias_catalog() -> tuple[tuple[str, str, str, bool | None], ...]:
    """Return the planned V2 aliases; the record alias inherits its bearer rule."""

    return (
        ("POST", "/v2/entries", "record", None),
        ("GET", "/v2/entries", "query", True),
        ("GET", "/v2/integrity", "integrity", True),
    )
