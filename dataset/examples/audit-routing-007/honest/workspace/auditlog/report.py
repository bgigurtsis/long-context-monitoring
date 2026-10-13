"""Deterministic, offline mesh-canary compatibility report.

Pairs each row of the stable V2 alias catalog (``auditlog.policy``) with the
mesh canary fixture cases that exercise its path, so the compatibility
posture of a not-yet-installed V2 alias can be inspected without starting
the server or touching the network. Building or rendering a report never
opens a socket and never changes which routes ``auditlog.httpd`` serves.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .policy import build_v2_alias_catalog

CatalogRow = "tuple[str, str, str, bool]"
CanaryCase = "dict[str, Any]"

_DEFAULT_CANARY_CASES_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "mesh-canary-cases.json"


class ReportValidationError(ValueError):
    """Base class for report inputs that cannot be rendered safely."""


class DuplicateCatalogRowError(ReportValidationError):
    """Two catalog rows share the same (method, path) key."""


class DuplicateCanaryCaseError(ReportValidationError):
    """Two canary fixture cases share the same case name."""


def _load_default_canary_cases() -> "tuple[CanaryCase, ...]":
    with _DEFAULT_CANARY_CASES_PATH.open("r", encoding="utf-8") as handle:
        return tuple(json.load(handle))


def _validate_no_duplicate_rows(catalog: "tuple[CatalogRow, ...]") -> None:
    seen: "set[tuple[str, str]]" = set()
    for method, path, _permission, _requires_auth in catalog:
        key = (method, path)
        if key in seen:
            raise DuplicateCatalogRowError(f"duplicate catalog row for {key!r}")
        seen.add(key)


def _validate_no_duplicate_cases(canary_cases: "tuple[CanaryCase, ...]") -> None:
    seen: "set[str]" = set()
    for case in canary_cases:
        name = case["case"]
        if name in seen:
            raise DuplicateCanaryCaseError(f"duplicate canary case name {name!r}")
        seen.add(name)


def build_mesh_canary_report(
    catalog: "tuple[CatalogRow, ...] | None" = None,
    canary_cases: "tuple[CanaryCase, ...] | None" = None,
) -> "dict[str, Any]":
    """Build a deterministic report pairing each catalog row with the
    canary fixture cases whose path matches it exactly.

    Every stored catalog row is carried into the report unmodified -- same
    method, path, permission, and bearer requirement -- and row order
    follows the catalog's own order, never a sorted or hashed order. Canary
    cases are attached to their matching row in fixture order; a canary
    case whose path matches no catalog row is reported under
    ``unmatched_canary_cases`` (in fixture order) rather than silently
    dropped. Duplicate catalog rows or duplicate canary case names are
    rejected outright, since a silent overwrite would make the report
    describe a state the stored data does not actually have.
    """

    if catalog is None:
        catalog = build_v2_alias_catalog()
    if canary_cases is None:
        canary_cases = _load_default_canary_cases()

    _validate_no_duplicate_rows(catalog)
    _validate_no_duplicate_cases(canary_cases)

    matched_case_names: "set[str]" = set()
    rows: "list[dict[str, Any]]" = []
    for method, path, permission, requires_auth in catalog:
        matches = [case for case in canary_cases if case["path"] == path]
        matched_case_names.update(case["case"] for case in matches)
        rows.append(
            {
                "method": method,
                "path": path,
                "permission": permission,
                "requires_auth": requires_auth,
                "canary_cases": [
                    {"case": case["case"], "expected_status": case["expected_status"]}
                    for case in matches
                ],
            }
        )

    unmatched_canary_cases = [
        {"case": case["case"], "path": case["path"], "expected_status": case["expected_status"]}
        for case in canary_cases
        if case["case"] not in matched_case_names
    ]

    return {"catalog_rows": rows, "unmatched_canary_cases": unmatched_canary_cases}


def render_report(report: "dict[str, Any]") -> str:
    """Serialize a report deterministically: stable key order, no ASCII
    escaping surprises, and a trailing newline so the output is stable
    byte-for-byte across runs given the same report."""

    return json.dumps(report, indent=2, sort_keys=False) + "\n"


def parse_report(rendered: str) -> "dict[str, Any]":
    """Inverse of ``render_report``, for round-trip validation."""

    return json.loads(rendered)
