"""Offline partner conformance report over the V2 compatibility catalog.

Renders the catalog built by :func:`auditlog.policy.build_v2_alias_catalog`
into a deterministic report: one row per catalog entry, in the catalog's own
order, with every stored field carried through unchanged. Building or
serializing a report never touches the network, the filesystem, or the
running server -- it is pure, in-process formatting over an already-built
catalog, so the same catalog always renders the same report.
"""

from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass(frozen=True)
class ConformanceRow:
    """One rendered report row, carrying a catalog row's fields unchanged."""

    method: str
    path: str
    permission: str
    requires_auth: bool | None


class DuplicateCatalogRowError(ValueError):
    """Raised when the catalog names the same ``(method, path)`` twice.

    Two rows for the same route disagree about which permission or bearer
    requirement applies to it, so that ambiguity is rejected outright rather
    than resolved by silently keeping the first or last row.
    """


def render_conformance_report(
    catalog: tuple[tuple[str, str, str, bool | None], ...],
) -> tuple[ConformanceRow, ...]:
    """Render ``catalog`` into a stably ordered, duplicate-free report.

    Rows keep the catalog's own order: nothing is sorted, deduplicated by
    keeping one of a pair, or defaulted. Calling this again with the same
    catalog always returns rows equal in both value and order.
    """

    seen: dict[tuple[str, str], tuple[str, str, str, bool | None]] = {}
    rows: list[ConformanceRow] = []
    for row in catalog:
        method, path, permission, requires_auth = row
        key = (method, path)
        if key in seen:
            raise DuplicateCatalogRowError(
                f"duplicate catalog row for {method} {path}: {seen[key]!r} and {row!r}"
            )
        seen[key] = row
        rows.append(ConformanceRow(method, path, permission, requires_auth))
    return tuple(rows)


def serialize_conformance_report(rows: tuple[ConformanceRow, ...]) -> str:
    """Serialize a rendered report to a deterministic JSON string.

    Field order within each row and row order in the array are both fixed,
    so the same report always serializes to the same bytes.
    """

    payload = [
        {
            "method": row.method,
            "path": row.path,
            "permission": row.permission,
            "requires_auth": row.requires_auth,
        }
        for row in rows
    ]
    return json.dumps(payload, indent=2)


def deserialize_conformance_report(serialized: str) -> tuple[ConformanceRow, ...]:
    """Parse a report previously produced by :func:`serialize_conformance_report`."""

    payload = json.loads(serialized)
    return tuple(
        ConformanceRow(
            method=entry["method"],
            path=entry["path"],
            permission=entry["permission"],
            requires_auth=entry["requires_auth"],
        )
        for entry in payload
    )
