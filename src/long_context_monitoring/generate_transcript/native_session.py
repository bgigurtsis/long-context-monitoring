"""Canonical file access for generated native Claude Code sessions."""

from __future__ import annotations

import json
from pathlib import Path


PROJECTS_DIR = Path.home() / ".claude" / "projects"


class SessionFormatError(ValueError):
    """A generated session archive is missing or malformed."""


def find_session_file(
    session_id: str, projects_dir: Path = PROJECTS_DIR
) -> Path | None:
    """Locate a globally unique Claude session without guessing its project slug."""

    return next(projects_dir.glob(f"*/{session_id}.jsonl"), None)


def main_jsonl(transcript_dir: Path) -> Path:
    """Return the sole main JSONL in an archived transcript."""

    candidates = sorted(transcript_dir.glob("*.jsonl"))
    if len(candidates) != 1:
        raise SessionFormatError(
            f"expected exactly one main JSONL in {transcript_dir}; "
            f"found {len(candidates)}"
        )
    return candidates[0]


def read_jsonl(path: Path) -> tuple[list[str], list[dict[str, object]]]:
    """Read a strict JSONL file while retaining untouched source lines."""

    raw_lines = path.read_text(encoding="utf-8", errors="strict").splitlines()
    entries: list[dict[str, object]] = []
    for line_number, line in enumerate(raw_lines, start=1):
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SessionFormatError(f"invalid JSONL at {path}:{line_number}") from exc
        if not isinstance(value, dict):
            raise SessionFormatError(
                f"JSONL entry at {path}:{line_number} must be an object"
            )
        entries.append(value)
    return raw_lines, entries
