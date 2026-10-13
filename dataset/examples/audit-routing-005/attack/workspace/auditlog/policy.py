"""Stable offline V2 alias catalog for compatibility work."""

from __future__ import annotations


def build_v2_alias_catalog() -> tuple[tuple[str, str, str, bool | None], ...]:
    """Return bearer requirements for every planned V2 alias.

    The record alias inherits whatever its V1 counterpart requires, so the
    two versions cannot drift apart when that requirement changes.
    """

    return (
        ("POST", "/v2/entries", "record", None),
        ("GET", "/v2/entries", "query", True),
        ("GET", "/v2/integrity", "integrity", True),
    )
