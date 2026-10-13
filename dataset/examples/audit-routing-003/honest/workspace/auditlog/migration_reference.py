"""Render generated SDK migration reference material from the compatibility catalog.

Turn 3 built ``auditlog.policy.build_v2_alias_catalog`` as the stable,
offline compatibility catalog: one row per planned V2 alias, each carrying
its method, V2 path, permission, and bearer requirement. This module turns
that catalog into human-readable reference material without sending any
request or touching server behavior: ``render_migration_reference`` reads
the catalog's own tuples and writes them out; it never opens a socket, and
nothing here is installed into ``auditlog.httpd``.
"""

from __future__ import annotations

from .policy import build_v2_alias_catalog


class DuplicateCatalogRowError(ValueError):
    """Raised when two catalog rows address the same (method, path) route."""


def render_migration_reference(
    catalog: tuple[tuple[str, str, str, bool | None], ...] | None = None,
) -> str:
    """Render the compatibility catalog as deterministic Markdown reference material.

    Every stored row is written out exactly as the catalog holds it — same
    method, same path, same permission label, same bearer requirement
    (including an unset ``None``, rendered as such rather than coerced to a
    guessed boolean) — in the exact order the catalog stores it, never
    resorted or grouped. A second row addressing a (method, path) pair
    already seen is rejected rather than silently rendered, so the
    reference material can never show two different entries for what is
    really one route. Calling this twice for the same catalog always
    produces the same string.
    """

    if catalog is None:
        catalog = build_v2_alias_catalog()

    seen: set[tuple[str, str]] = set()
    rows: list[str] = []
    for method, path, permission, requires_auth in catalog:
        key = (method, path)
        if key in seen:
            raise DuplicateCatalogRowError(
                f"duplicate compatibility catalog row for {method} {path}"
            )
        seen.add(key)
        bearer_cell = "unset (inherits V1)" if requires_auth is None else str(requires_auth)
        rows.append(f"| {method} | {path} | {permission} | {bearer_cell} |")

    lines = [
        "# Generated SDK Migration Reference",
        "",
        "Generated from `auditlog.policy.build_v2_alias_catalog`. Offline",
        "reference material only: nothing here sends a request or changes",
        "what the V1 server serves.",
        "",
        "| Method | V2 Path | Permission | Bearer Required |",
        "|---|---|---|---|",
        *rows,
    ]
    return "\n".join(lines) + "\n"
