"""Deterministic, offline renderer for the turn-3 V2 alias compatibility catalog.

The catalog built by :func:`auditlog.policy.build_v2_alias_catalog` is fixed,
offline data -- see that module's docstring. Rendering it into a report never
resolves an inherited (``None``) bearer requirement; that resolution is
:func:`auditlog.httpd.resolve_v2_alias_catalog`'s job, and it needs a live
canonical-route table this module has no business consulting. This module
only ever reads the catalog tuple it is given and writes text -- it installs
no route and opens no socket, so rendering a report never changes what the
server does.
"""

from __future__ import annotations

import json


class DuplicateCatalogRowError(ValueError):
    """Two catalog rows declared the same ``(method, path)``."""


def render_compatibility_report(catalog: tuple[tuple[str, str, str, bool | None], ...]) -> str:
    """Render ``catalog`` to a deterministic JSON report, one row per declared entry.

    Each stored row is carried through unchanged and in its original
    declaration order -- this is a transcription, not a summary or a sort. A
    row whose ``(method, path)`` repeats an earlier row is rejected outright
    rather than merged or silently overwritten, since two differing
    declarations for the same route are a policy disagreement, not a
    redundant restatement.
    """

    seen: set[tuple[str, str]] = set()
    rows = []
    for method, path, permission, requires_auth in catalog:
        key = (method, path)
        if key in seen:
            raise DuplicateCatalogRowError(f"duplicate catalog row for {method} {path}")
        seen.add(key)
        rows.append(
            {
                "method": method,
                "path": path,
                "permission": permission,
                "requires_auth": requires_auth,
            }
        )
    return json.dumps({"rows": rows}, indent=2) + "\n"


def parse_compatibility_report(text: str) -> tuple[tuple[str, str, str, bool | None], ...]:
    """Invert :func:`render_compatibility_report`, recovering the original rows."""

    payload = json.loads(text)
    return tuple(
        (row["method"], row["path"], row["permission"], row["requires_auth"])
        for row in payload["rows"]
    )
