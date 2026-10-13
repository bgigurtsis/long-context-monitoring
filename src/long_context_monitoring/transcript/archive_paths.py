"""Resolve legacy and generated archive names without reading transcript bodies."""

from __future__ import annotations

from pathlib import Path
from long_context_monitoring.artifact_layout import evidence_file


def _archive_manifest_path(archive_dir: Path) -> Path:
    """Prefer native embedded metadata, then legacy or grouped arm evidence."""
    inside = archive_dir / "manifest.json"
    if inside.exists():
        return inside
    return evidence_file(archive_dir.parent, "manifest.json")


def _archive_logical_name(archive_dir: Path) -> str:
    """``<task>/<condition>`` for an archive dir, used when no manifest names it.

    In the ``runs/<task>/<condition>/transcript/`` layout the dir stem is the
    useless literal ``transcript``, which would misfile a manifest-less run under
    ``runs/transcript/monitor/``. Recovering the two parent dir names reproduces
    the name the manifest would have produced.
    """
    if archive_dir.name != "transcript":
        return archive_dir.name
    task = archive_dir.parent.parent.name
    condition = archive_dir.parent.name
    if task and condition:
        return f"{task}/{condition}"
    return archive_dir.name
