"""Walk experiment artifacts without descending into copied application trees."""
from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path


_NON_SESSION_DIRS = {
    "workspace", "workspaces", "subagents", "monitor", "monitor-runs",
    "base", "seed", "seeds", "shared-seeds", "fixtures",
    ".git", ".venv", "node_modules", "__pycache__",
}


def artifact_directories(
    root: Path, *, skip_generations: bool = False,
) -> Iterator[tuple[Path, list[str]]]:
    """Yield artifact directories, pruning expensive non-session subtrees.

    A transcript's nested native phases and subagents belong to that transcript,
    not to separate index rows. Campaign discovery also stops at generations:
    campaign contracts live beside the spec, never inside generated workspaces.
    """
    for current, directories, filenames in os.walk(root):
        directories[:] = [
            name for name in directories
            if name not in _NON_SESSION_DIRS
            and not name.endswith("-workspace")
            and not (skip_generations and name in {"generations", "records", "variants"})
        ]
        here = Path(current)
        yield here, filenames
        if here.name == "transcript":
            directories.clear()


def transcript_directories(root: Path) -> Iterator[Path]:
    """Find main transcript archives, including nested derivatives."""
    for here, filenames in artifact_directories(root):
        if here.name == "transcript" and any(name.endswith(".jsonl") for name in filenames):
            yield here
