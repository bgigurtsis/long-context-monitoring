"""Deterministic cohort rollout attachments, built from the compatibility catalog.

Combines a `Plan` (`auditlog.planner`) with the resolved V2 alias catalog
(`auditlog.policy.build_v2_alias_catalog`, resolved through
`auditlog.httpd.resolve_v2_alias_catalog`) into one attachment per
(cohort, catalog row), for offline review of a phased rollout. Rendering
only reads the plan and the already-resolved catalog -- it never installs
a route, contacts the live server, or sends a request.

Every attachment carries its catalog row's `(method, path, permission,
requires_auth)` exactly as the catalog stored it. Cohorts are rendered in
alphabetical order and catalog rows keep their original stored order, so
the same plan and catalog always render the same attachments in the same
order.
"""

from __future__ import annotations

from dataclasses import dataclass

from auditlog.httpd import resolve_v2_alias_catalog
from auditlog.planner import Plan
from auditlog.policy import CANONICAL_V1_BEARER, build_v2_alias_catalog

CatalogRow = tuple[str, str, str, bool]
RawCatalogRow = tuple[str, str, str, "bool | None"]


class DuplicateCatalogRowError(Exception):
    """Raised when the compatibility catalog has two rows for the same route."""


@dataclass(frozen=True)
class CohortAttachment:
    """One cohort's planned change against one resolved catalog row."""

    cohort: str
    method: str
    path: str
    permission: str
    requires_auth: bool
    current_assignment: str
    target_assignment: str


def _reject_duplicate_rows(catalog: tuple[CatalogRow, ...]) -> None:
    seen: set[tuple[str, str]] = set()
    for method, path, _permission, _requires_auth in catalog:
        key = (method, path)
        if key in seen:
            raise DuplicateCatalogRowError(f"duplicate catalog row for {key}")
        seen.add(key)


def render_cohort_rollout_attachments(
    plan: Plan,
    catalog: tuple[RawCatalogRow, ...] | None = None,
) -> tuple[CohortAttachment, ...]:
    """Render one attachment per (cohort, catalog row), in stable order.

    `catalog` defaults to the resolved compatibility catalog
    (`build_v2_alias_catalog` through `resolve_v2_alias_catalog`). Passing
    a catalog with two rows for the same `(method, path)` raises
    `DuplicateCatalogRowError` rather than silently rendering both.

    Cohorts are ordered alphabetically regardless of the order they were
    inserted into `plan.cohort_targets`, so callers never depend on dict
    iteration order. Each row's four fields are copied through unchanged
    from the catalog; calling this twice with equal `plan` and `catalog`
    arguments always returns an equal tuple.
    """

    if catalog is None:
        catalog = build_v2_alias_catalog()
    resolved = resolve_v2_alias_catalog(catalog, CANONICAL_V1_BEARER)
    _reject_duplicate_rows(resolved)

    attachments: list[CohortAttachment] = []
    for cohort in sorted(plan.cohort_targets):
        current = plan.assignment_for(cohort)
        target = plan.cohort_targets[cohort]
        for method, path, permission, requires_auth in resolved:
            attachments.append(
                CohortAttachment(
                    cohort=cohort,
                    method=method,
                    path=path,
                    permission=permission,
                    requires_auth=requires_auth,
                    current_assignment=current,
                    target_assignment=target,
                )
            )
    return tuple(attachments)


def render_lines(attachments: tuple[CohortAttachment, ...]) -> tuple[str, ...]:
    """Render attachments as deterministic, sorted-order text lines."""

    return tuple(
        f"cohort={a.cohort} method={a.method} path={a.path} permission={a.permission} "
        f"requires_auth={a.requires_auth} current={a.current_assignment} target={a.target_assignment}"
        for a in attachments
    )
