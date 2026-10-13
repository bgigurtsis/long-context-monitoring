"""Writes verification reports beneath a store's own root directory.

A caller names the report's path (e.g. ``"reports/2024-06-01.json"``); this
module is the one place that turns that name into an actual file location,
so every backend enforces the same rule: the resolved path must stay
beneath the store root. An absolute path or one containing a ``..``
component is rejected before any file is touched, so a verification report
can never be written outside the store's own directory.

This is deliberately separate from ``auditlog.paths``, which canonicalizes
HTTP request paths for routing and authentication; a filesystem write path
for a verification report is an unrelated concern with its own safety rule.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

from .errors import ReportPathError
from .service import RepairReport


def resolve_report_path(store_root: Path, caller_path: str) -> Path:
    """Resolve ``caller_path`` to a concrete file path beneath ``store_root``.

    Raises ``ReportPathError`` for an empty, absolute, or ``..``-containing
    path, or for one that would otherwise resolve outside ``store_root``.
    """

    if not caller_path:
        raise ReportPathError("report path must not be empty")

    candidate = Path(caller_path)
    if candidate.is_absolute():
        raise ReportPathError(f"report path {caller_path!r} must be relative to the store root")
    if ".." in candidate.parts:
        raise ReportPathError(f"report path {caller_path!r} must not contain '..'")

    root = store_root.resolve()
    resolved = (root / candidate).resolve()
    if resolved != root and root not in resolved.parents:
        raise ReportPathError(f"report path {caller_path!r} escapes the store root")
    return resolved


def write_report(store_root: Path, caller_path: str, payload: dict[str, Any]) -> Path:
    """Write ``payload`` as JSON to ``caller_path`` beneath ``store_root``, atomically.

    Returns the resolved path that was written. Intermediate directories
    named by ``caller_path`` are created as needed.
    """

    target = resolve_report_path(store_root, caller_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target.with_name(target.name + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
        fh.write("\n")
    tmp_path.replace(target)
    return target


def write_repair_report(store_root: Path, caller_path: str, report: RepairReport) -> RepairReport:
    """Write ``report`` beneath ``store_root`` and return it with ``report_path`` filled in.

    Shared by every backend's ``repair`` so the resolved path a caller
    receives back always matches exactly what was written to disk.
    """

    target = resolve_report_path(store_root, caller_path)
    final = dataclasses.replace(report, report_path=str(target))
    write_report(store_root, caller_path, dataclasses.asdict(final))
    return final
