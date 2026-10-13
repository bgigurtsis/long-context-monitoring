"""Cohort-to-API-version selection for the phased upgrade.

Selecting a cohort's phase (see fixtures/upgrade-cohorts.csv) only ever
changes which route version -- v1 or v2 -- a request is dispatched to.
It never changes whether the route requires a bearer token: that
requirement is canonical to the underlying permission
(`auditlog.policy.CANONICAL_V1_BEARER`) and is inherited by every version
alias (`auditlog.httpd.resolve_v2_alias_catalog`). `bearer_required` below
is the assertion that both phases resolve to the same answer.
"""

from __future__ import annotations

import csv
from pathlib import Path

from auditlog.httpd import resolve_v2_alias_catalog
from auditlog.policy import CANONICAL_V1_BEARER, build_v2_alias_catalog

# Route each action resolves to within a phase; only the version prefix
# changes between phases. Matches fixtures/phase-route-expectations.yaml.
ACTION_ROUTES: dict[str, tuple[str, str]] = {
    "record": ("POST", "/entries"),
    "query": ("GET", "/entries"),
    "integrity": ("GET", "/integrity"),
}


def load_cohort_phases(csv_path: Path) -> dict[str, str]:
    """Return {cohort: phase} for enabled rows of an upgrade-cohorts.csv file."""

    phases: dict[str, str] = {}
    with csv_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["enabled"].strip().lower() == "true":
                phases[row["cohort"]] = row["phase"]
    return phases


def route_for(action: str, phase: str) -> tuple[str, str]:
    """The (method, path) a cohort in `phase` uses for `action`."""

    method, suffix = ACTION_ROUTES[action]
    return method, f"/{phase}{suffix}"


def bearer_table() -> dict[tuple[str, str], bool]:
    """Canonical bearer requirements for every V1 route plus every V2 alias."""

    table = dict(CANONICAL_V1_BEARER)
    resolved = resolve_v2_alias_catalog(build_v2_alias_catalog(), CANONICAL_V1_BEARER)
    for method, path, _permission, requires_auth in resolved:
        table[(method, path)] = requires_auth
    return table


def bearer_required(action: str, phase: str) -> bool:
    """Whether `action` requires a bearer token when routed through `phase`.

    Cohort selection picks `phase`, which changes only the resolved path.
    It never changes this answer: `bearer_required(action, "v1")` and
    `bearer_required(action, "v2")` always agree for the same action.
    """

    method, path = route_for(action, phase)
    return bearer_table()[(method, path)]
