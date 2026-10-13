"""Deterministic offline rollout manifest for the V2 compatibility catalog.

``auditlog.policy.build_v2_alias_catalog`` is the stable, offline catalog of
planned V2 route aliases from turn 3. This module renders that catalog into
a manifest for change review -- serialized deterministically, with each
stored row preserved exactly as the catalog returned it. Nothing here is
imported by ``auditlog.httpd`` or ``auditlog.cli``: rendering a manifest
does not install routes, and it never touches the live server.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional, Tuple

from .policy import build_v2_alias_catalog

CatalogRow = Tuple[str, str, str, Optional[bool]]


@dataclass(frozen=True)
class ManifestRow:
    method: str
    path: str
    permission: str
    requires_auth: bool | None


class DuplicateManifestRowError(ValueError):
    """Raised when two catalog rows collide on the same (method, path)."""


def _reject_duplicates(rows: tuple[CatalogRow, ...]) -> None:
    seen: set[tuple[str, str]] = set()
    for method, path, _permission, _requires_auth in rows:
        key = (method, path)
        if key in seen:
            raise DuplicateManifestRowError(f"duplicate route in catalog: {method} {path}")
        seen.add(key)


def build_rollout_manifest(rows: tuple[CatalogRow, ...] | None = None) -> tuple[ManifestRow, ...]:
    """Render catalog rows into a manifest, preserving order and content exactly.

    Defaults to the turn 3 compatibility catalog. Raises
    ``DuplicateManifestRowError`` rather than silently dropping or merging a
    colliding row.
    """

    if rows is None:
        rows = build_v2_alias_catalog()
    _reject_duplicates(rows)
    return tuple(ManifestRow(method, path, permission, requires_auth) for method, path, permission, requires_auth in rows)


def render_manifest(manifest: tuple[ManifestRow, ...]) -> str:
    """Serialize a manifest deterministically: stable row order, stable key order."""

    payload = [
        {
            "method": row.method,
            "path": row.path,
            "permission": row.permission,
            "requires_auth": row.requires_auth,
        }
        for row in manifest
    ]
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def parse_manifest(text: str) -> tuple[ManifestRow, ...]:
    """Parse a manifest previously produced by ``render_manifest``.

    Re-validates for duplicates rather than trusting the serialized form, so
    a hand-edited or corrupted manifest cannot smuggle in a collision.
    """

    payload = json.loads(text)
    rows = tuple(
        (item["method"], item["path"], item["permission"], item["requires_auth"]) for item in payload
    )
    return build_rollout_manifest(rows)
