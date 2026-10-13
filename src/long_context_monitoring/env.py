"""Load a repo-local ``.env`` into ``os.environ`` without extra dependencies."""

from __future__ import annotations

import os
from pathlib import Path

from long_context_monitoring.run_layout import REPO_ROOT


def find_dotenv(start: Path | None = None) -> Path | None:
    """Return the first existing ``.env`` under ``start`` or the repo root."""

    candidates: list[Path] = []
    if start is not None:
        candidates.append(start.resolve() / ".env")
    repo_env = REPO_ROOT / ".env"
    if repo_env not in candidates:
        candidates.append(repo_env)
    for path in candidates:
        if path.is_file():
            return path
    return None


def _parse_assignment(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if stripped.startswith("export "):
        stripped = stripped[len("export ") :].lstrip()
    if "=" not in stripped:
        return None
    key, value = stripped.split("=", 1)
    key = key.strip()
    if not key:
        return None
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return key, value


def load_dotenv(path: Path | None = None, *, override: bool = False) -> bool:
    """Load ``KEY=VALUE`` pairs from ``.env``; return False when no file exists.

    Existing process environment variables are preserved unless ``override`` is
    True. This keeps explicit shell exports authoritative over the file.
    """

    dotenv_path = path if path is not None else find_dotenv()
    if dotenv_path is None or not dotenv_path.is_file():
        return False
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        parsed = _parse_assignment(raw_line)
        if parsed is None:
            continue
        key, value = parsed
        if override or key not in os.environ:
            os.environ[key] = value
    return True
