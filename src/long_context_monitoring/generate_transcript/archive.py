"""Snapshot native sessions and workspaces without changing their evidence bytes."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from long_context_monitoring.hashing import ordered_tree_files
from . import codex_session
from .session import SessionError

WORKSPACE_DIRNAME = "workspace"
# Derived test caches are explicitly listed in each archived workspace record.
WORKSPACE_ARCHIVE_EXCLUDES = (
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
)


def workspace_fingerprint(root: Path) -> str:
    """One sha256 over sorted relative paths plus each file's content hash.

    Nothing is excluded, including ``.git``. The hash pins the honest seed used
    by every later manual derivative.
    """
    digest = hashlib.sha256()
    for path in ordered_tree_files(root):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def copy_workspace(source: Path) -> Path:
    """Copy the starting state to a fresh temp dir; never mutate ``source``.

    ``symlinks=True`` keeps a symlink a symlink instead of inlining its target,
    so the agent sees the tree shape the operator prepared.
    """
    destination = Path(tempfile.mkdtemp(prefix="lcm-live-")) / source.name
    shutil.copytree(source, destination, symlinks=True)
    return destination


def _archive_session_with_finder(
    session_id: str,
    destination: Path,
    backend: str = "claude",
    native_home: Path | None = None,
    *,
    find_claude_session,
) -> Path:
    """Copy the session JSONL and any sub-agent files out of the live store.

    The live session dir keeps mutating, so the dataset needs an immutable
    snapshot. ``shutil.copy`` follows symlinks, so a resumed session's symlinked
    sub-agent entries archive as real bytes.
    """
    if backend == "codex":
        if native_home is None:
            raise SessionError("Codex archive needs its isolated native home")
        source = codex_session.find_session_file(session_id, native_home)
    else:
        source = find_claude_session(session_id)
        # Claude can report the new session id just before its JSONL directory
        # becomes visible. Give that filesystem write a short bounded window so
        # the initialization checkpoint does not turn a healthy first turn into
        # an unresumable generation.
        deadline = time.monotonic() + 5.0
        while source is None and time.monotonic() < deadline:
            time.sleep(0.1)
            source = find_claude_session(session_id)
    if source is None:
        raise SessionError(f"could not locate the JSONL for session {session_id}")
    destination.mkdir(parents=True, exist_ok=True)
    archived = destination / source.name
    shutil.copy(source, archived)

    subagents = source.parent / session_id / "subagents"
    if backend == "claude" and subagents.is_dir():
        target = destination / "subagents"
        target.mkdir(exist_ok=True)
        for path in sorted(subagents.rglob("*")):
            if path.is_file():
                shutil.copy(path, target / path.name)
    if backend == "codex":
        target = destination / "subagents"
        target.mkdir(exist_ok=True)
        for child, metadata in codex_session.child_session_files(
            session_id, native_home
        ):
            thread_id = metadata["id"]
            shutil.copy(child, target / f"agent-{thread_id}.jsonl")
            meta = {
                "format": "codex",
                "threadId": thread_id,
                "parentThreadId": metadata.get("parent_thread_id"),
                "agentPath": metadata.get("agent_path"),
                "description": metadata.get("agent_nickname"),
            }
            (target / f"agent-{thread_id}.meta.json").write_text(
                json.dumps(meta, indent=2) + "\n", encoding="utf-8"
            )
    return archived


def archive_workspace(workspace: Path, destination: Path) -> dict:
    """Copy the finished workspace into the run dir and describe what landed.

    Why this exists: the session runs in a temp dir that the OS eventually reaps,
    so without this the code the agent actually built is gone the moment the
    machine cleans up, and anything that reads the end state - a side-task probe,
    a human diffing against the seed - has nothing to read. The transcript records
    every edit, but reconstructing a tree from a transcript is not a thing you want
    standing between you and a verdict.

    Staged into a sibling dir and renamed, so an interrupted copy never leaves a
    half-written ``workspace/`` that looks complete. ``symlinks=True`` matches
    ``copy_workspace``: a symlink stays a symlink, which the containment-rule seeds
    depend on.

    Returns a description for the manifest. Raises ``OSError`` on failure; the
    caller decides whether that is fatal (it is not - see ``_run``).
    """
    target = destination / WORKSPACE_DIRNAME
    staging = destination / f".{WORKSPACE_DIRNAME}.staging-{os.getpid()}"
    destination.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(staging, ignore_errors=True)
    try:
        shutil.copytree(
            workspace,
            staging,
            symlinks=True,
            ignore=shutil.ignore_patterns(*WORKSPACE_ARCHIVE_EXCLUDES),
        )
        files = [path for path in staging.rglob("*") if path.is_file()]
        described = {
            "path": WORKSPACE_DIRNAME,
            "archived": True,
            "files": len(files),
            "bytes": sum(path.stat().st_size for path in files),
            "excluded": list(WORKSPACE_ARCHIVE_EXCLUDES),
        }
        # Replace only once the copy is complete, so the previous archive survives
        # a failure rather than being deleted before its replacement exists.
        if target.exists():
            shutil.rmtree(target)
        staging.replace(target)
        return described
    finally:
        shutil.rmtree(staging, ignore_errors=True)
