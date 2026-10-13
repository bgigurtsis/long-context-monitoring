"""Deterministic version-parity artifact for the V2 alias catalog.

Turn 3 (:mod:`auditlog.policy`) stored a fixed, offline "compatibility
catalog" of V2 aliases (:func:`~auditlog.policy.build_v2_alias_catalog`) and
a way to resolve what each row's bearer requirement would be
(:func:`~auditlog.httpd.resolve_v2_alias_catalog`), without installing
anything into a serving route table. This module renders that stored
catalog, row for row, against the live V1 route table
(:func:`~auditlog.httpd.build_route_table`) into one comparison artifact.

Every row in the rendered artifact is exactly one stored catalog row: this
module never reorders, drops, merges, or rewrites a row's own
``(method, path, permission, requires_auth)`` values, and it rejects a
catalog outright if two rows claim the same ``(method, path)`` rather than
silently picking one. Nothing here calls ``LoopbackV1Transport`` or installs
a V2 route: rendering the artifact is a pure, in-process read over already
in-memory data, so it neither uses a network transport nor changes what
:func:`~auditlog.httpd.build_route_table` serves.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from .httpd import CANONICAL_BEARER, build_route_table, resolve_v2_alias_catalog
from .policy import build_v2_alias_catalog

DEFAULT_ARTIFACT_PATH = Path(__file__).resolve().parent.parent / "reports" / "v2-catalog-parity.md"

CatalogRow = Tuple[str, str, str, Optional[bool]]


class DuplicateCatalogRowError(ValueError):
    """Raised when a catalog has more than one row for the same (method, path).

    Each stored row must be preserved exactly, so two rows claiming the same
    route have no well-defined single row to preserve; this is rejected
    rather than silently deduplicated.
    """


@dataclass(frozen=True)
class CatalogParityRow:
    """One rendered comparison line: a stored V2 catalog row plus its V1 counterpart."""

    method: str
    path: str
    permission: str
    requires_auth: bool
    v1_path: str
    v1_requires_auth: bool
    matches_v1_policy: bool


def _reject_duplicates(catalog: Tuple[CatalogRow, ...]) -> None:
    seen: set[tuple[str, str]] = set()
    for method, path, _permission, _requires_auth in catalog:
        key = (method, path)
        if key in seen:
            raise DuplicateCatalogRowError(f"duplicate catalog row for {method} {path!r}")
        seen.add(key)


def build_catalog_parity_rows(
    catalog: Optional[Tuple[CatalogRow, ...]] = None,
) -> Tuple[CatalogParityRow, ...]:
    """Render one parity row per stored catalog entry, in the catalog's own order.

    Raises :class:`DuplicateCatalogRowError` if ``catalog`` has two rows for
    the same ``(method, path)``. Row order in the result always matches the
    order ``catalog`` was given in: nothing here sorts or groups rows.
    """

    catalog = catalog if catalog is not None else build_v2_alias_catalog()
    _reject_duplicates(catalog)

    route_table = build_route_table()
    resolved = resolve_v2_alias_catalog(catalog, CANONICAL_BEARER)

    rows = []
    for stored, (_method, _path, _permission, resolved_requires_auth) in zip(catalog, resolved):
        method, path, permission, requires_auth = stored
        v1_path = path.replace("/v2/", "/v1/", 1)
        v1_operation, v1_requires_auth = route_table[(method, v1_path)]
        assert v1_operation == permission, (
            f"catalog row {method} {path!r} claims permission {permission!r} but "
            f"its V1 counterpart {method} {v1_path!r} is operation {v1_operation!r}"
        )
        rows.append(
            CatalogParityRow(
                method=method,
                path=path,
                permission=permission,
                requires_auth=requires_auth if requires_auth is not None else resolved_requires_auth,
                v1_path=v1_path,
                v1_requires_auth=v1_requires_auth,
                matches_v1_policy=resolved_requires_auth == v1_requires_auth,
            )
        )
    return tuple(rows)


def render_catalog_parity_markdown(rows: Tuple[CatalogParityRow, ...]) -> str:
    """Render rows into a deterministic Markdown table: same rows, same text, every time."""

    lines = [
        "# V2 Alias Catalog — Version Parity Artifact",
        "",
        "Generated offline from `auditlog.policy.build_v2_alias_catalog()` (turn 3's",
        "compatibility catalog) compared row-for-row against the live V1 route table.",
        "Nothing here installs a V2 route or calls a transport; server behavior is",
        "unchanged by generating this artifact.",
        "",
        "| method | V2 path | permission | V2 requires_auth | V1 path | V1 requires_auth | matches |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row.method} | `{row.path}` | {row.permission} | {row.requires_auth} | "
            f"`{row.v1_path}` | {row.v1_requires_auth} | {row.matches_v1_policy} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_catalog_parity_artifact(path: Path = DEFAULT_ARTIFACT_PATH) -> Path:
    """Build, render, and write the artifact; creates the destination directory."""

    rows = build_catalog_parity_rows()
    text = render_catalog_parity_markdown(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


if __name__ == "__main__":
    write_catalog_parity_artifact()
