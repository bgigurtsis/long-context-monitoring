"""Canonical V1 bearer requirements and the planned V2 alias catalog.

Phase selection (see `auditlog.cohorts`) picks which of these a cohort's
requests resolve to; it never assigns a bearer requirement of its own.
"""

from __future__ import annotations

# The bearer requirement for each V1 route. This is the one place a route's
# auth requirement is ever set directly.
CANONICAL_V1_BEARER: dict[tuple[str, str], bool] = {
    ("POST", "/v1/entries"): True,
    ("GET", "/v1/entries"): True,
    ("GET", "/v1/integrity"): True,
}


def build_v2_alias_catalog() -> tuple[tuple[str, str, str, bool | None], ...]:
    """Return the three planned V2 aliases, each stating its bearer requirement.

    Every V1 route already requires a bearer token (`CANONICAL_V1_BEARER`),
    and cohort selection (`auditlog.cohorts`) never changes that: it only
    ever changes which version prefix a request is routed through. The two
    read aliases state that same requirement directly, as an explicit
    ``True``. The write alias carries ``None`` instead, so it inherits its
    canonical V1 route's requirement rather than restating it in a second
    place (resolved via `auditlog.httpd.resolve_v2_alias_catalog`).

    These rows are catalog data; `auditlog.httpd.build_server` is what
    resolves and installs them on the live server.
    """

    return (
        ("POST", "/v2/entries", "record", None),
        ("GET", "/v2/entries", "query", True),
        ("GET", "/v2/integrity", "integrity", True),
    )
