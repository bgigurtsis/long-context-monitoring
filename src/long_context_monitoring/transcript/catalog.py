"""Discover native sessions and group aliases while preserving distinct attack arms."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import os
import time
from pathlib import Path
from long_context_monitoring.run_layout import experiment_roots
from .discovery import artifact_directories
from .archive_paths import _archive_manifest_path


def _probe_head(path: Path, cap: int = 65536) -> dict:
    """Cheaply read the first `cap` bytes of a session file for index-page
    metadata (model, CC version). Deliberately does NOT scan the whole file —
    the viewer page computes accurate stats on open."""
    info: dict = {"model": None, "version": None, "session_id": None, "native": False}
    try:
        with open(path, "rb") as f:
            head = f.read(cap)
    except OSError:
        return info
    for raw in head.split(b"\n"):
        try:
            entry = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(entry, dict):
            continue
        if entry.get("type") in {
            "user",
            "assistant",
            "system",
            "session_meta",
            "turn_context",
            "response_item",
            "compacted",
        }:
            info["native"] = True
        payload = entry.get("payload")
        if isinstance(payload, dict):
            if entry.get("type") == "session_meta":
                info["session_id"] = info["session_id"] or payload.get("id")
                info["version"] = info["version"] or payload.get("cli_version")
            elif entry.get("type") == "turn_context":
                info["model"] = info["model"] or payload.get("model")
        if info["version"] is None and entry.get("version"):
            info["version"] = entry["version"]
        if info["session_id"] is None and entry.get("sessionId"):
            info["session_id"] = entry["sessionId"]
        if info["model"] is None and entry.get("type") == "assistant":
            message = entry.get("message")
            if isinstance(message, dict):
                info["model"] = message.get("model")
        if info["model"] and info["version"] and info["session_id"]:
            break
    return info


def _count_subagents(subagents_dir: Path) -> int:
    if not subagents_dir.is_dir():
        return 0
    return len(list(subagents_dir.glob("agent-*.jsonl")))


def _manifest_had_compaction(manifest: dict | None) -> bool | None:
    """Read compaction state from both legacy and current manifests."""
    if not manifest:
        return None
    explicit = manifest.get("had_compaction")
    if isinstance(explicit, bool):
        return explicit
    boundaries = manifest.get("compaction_boundaries")
    if isinstance(boundaries, list):
        return bool(boundaries)
    return None


def _archive_index_row(candidate: tuple[Path, list[str], Path]) -> dict | None:
    """Read one archive's small metadata files; tolerate a disappearing live run."""
    here, jsonls, transcripts_root = candidate
    try:
        manifest = None
        manifest_path = _archive_manifest_path(here)
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                manifest = None
        if not isinstance(manifest, dict):
            manifest = None
        session_id = (manifest or {}).get("session_id")
        preferred = (
            here / f"{session_id}.jsonl"
            if isinstance(session_id, str) and session_id
            else None
        )
        main = preferred if preferred and preferred.is_file() else here / jsonls[0]
        # Generated JSONL lives in an arm's ``transcript/``, so the logical
        # unit name is the parent dir. Older flat archives are used as-is.
        logical = here.parent if here.name == "transcript" else here
        rel = logical.relative_to(transcripts_root)
        probe = _probe_head(main)
        if here.name != "transcript" and not manifest and not any(probe.values()):
            return None
        stat = main.stat()
        cost = None
        tokens = None
        if manifest:
            stats = manifest.get("turn_stats") or []
            cost = sum(t.get("total_cost_usd") or 0 for t in stats) or None
            tokens = sum(t.get("output_tokens") or 0 for t in stats) or None
        return {
            "path": str(here),
            "name": str(rel),
            "source": "transcripts",
            "mtime": stat.st_mtime,
            "bytes": stat.st_size,
            "model": probe["model"],
            "version": (manifest or {}).get("claude_version") or probe["version"],
            "subagents": _count_subagents(here / "subagents"),
            "had_compaction": _manifest_had_compaction(manifest),
            "tokens_out": tokens,
            "cost_usd": cost,
            "live": time.time() - stat.st_mtime < 300,
            "session_id": probe["session_id"] or main.stem,
            "resolved_path": os.path.realpath(here),
            "project": str(rel.parent),
        }
    except OSError:
        return None


def discover(transcripts_root: Path, projects_root: Path) -> list[dict]:
    """List every trajectory for the index page.

    Archives: each ``transcript/`` directory under transcripts_root directly
    containing a .jsonl. We skip ``subagents/`` (stitched into their parent),
    monitor scorings, and ``workspace/`` (the agent's archived cwd, which can
    hold unrelated .jsonl files). Live/plain
    sessions: top-level .jsonl files in each ~/.claude/projects/<slug>/ dir.
    """
    rows = []

    roots = [transcripts_root, *experiment_roots(transcripts_root)[1:]]
    candidates = []
    for scan_root in roots:
        # Label sibling archive roots relative to their shared parent.
        label_root = (
            transcripts_root
            if scan_root == transcripts_root
            else transcripts_root.parent
        )
        for here, filenames in artifact_directories(scan_root):
            jsonls = sorted(name for name in filenames if name.endswith(".jsonl"))
            if jsonls:
                candidates.append((here, jsonls, label_root))
    with ThreadPoolExecutor(max_workers=8) as pool:
        rows.extend(
            row for row in pool.map(_archive_index_row, candidates) if row is not None
        )

    rows.extend(_project_index_rows(projects_root))

    rows.sort(key=lambda r: r["mtime"], reverse=True)
    return rows


def deduplicate_trajectories(rows: list[dict]) -> list[dict]:
    """Group path aliases, then copies with the same exact session ID.

    Resumed Claude sessions have distinct IDs and therefore remain separate,
    even when their human-readable names or project paths are similar.
    Constructed attack arms intentionally retain the honest source's session
    ID, so attack and honest archive conditions must remain separate rows.
    Archived files take precedence over copied live-session representations.
    """
    if not rows:
        return []

    parents = list(range(len(rows)))

    def root(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def union(left: int, right: int) -> None:
        left_root = root(left)
        right_root = root(right)
        if left_root != right_root:
            parents[right_root] = left_root

    by_path: dict[str, int] = {}
    by_session: dict[tuple[str, str], int] = {}
    for index, row in enumerate(rows):
        resolved = row.get("resolved_path") or os.path.realpath(row["path"])
        if resolved in by_path:
            union(index, by_path[resolved])
        else:
            by_path[resolved] = index
        session_id = row.get("session_id")
        if session_id:
            session_key = (session_id, _deduplication_arm(row))
            if session_key in by_session:
                union(index, by_session[session_key])
            else:
                by_session[session_key] = index

    groups: dict[int, list[dict]] = {}
    for index, row in enumerate(rows):
        groups.setdefault(root(index), []).append(row)

    source_rank = {"transcripts": 0, "cli-arg": 1, "projects": 2}
    output = []
    for members in groups.values():
        members.sort(
            key=lambda row: (
                source_rank.get(row.get("source"), 9),
                -row.get("mtime", 0),
            )
        )
        canonical = dict(members[0])
        canonical["aliases"] = []
        for alias in members[1:]:
            canonical["aliases"].append(
                {
                    "path": alias["path"],
                    "source": alias.get("source"),
                    "name": alias.get("name"),
                    "live": alias.get("live", False),
                }
            )
        sources = {member.get("source") for member in members}
        canonical["scope"] = "research" if "transcripts" in sources else "all"
        canonical["live"] = any(member.get("live", False) for member in members)
        output.append(canonical)

    output.sort(key=lambda row: row.get("mtime", 0), reverse=True)
    return output


def _deduplication_arm(row: dict) -> str:
    """Partition attacks while keeping ordinary/live aliases with honest arms.

    Every attack derived from one honest session keeps that session's ID, so
    attacks are also split by the folders between ``generations`` and
    ``attack``. Two derivatives of one honest source then stay separate rows,
    while copies of the same generation in different roots still group.
    """
    path = Path(str(row.get("path") or ""))
    parts = [part.lower() for part in path.parts]
    if "attack" not in parts:
        return "honest"
    attack_at = parts.index("attack")
    if "generations" in parts[:attack_at]:
        generation = "/".join(parts[parts.index("generations") + 1:attack_at])
        return f"attack:{generation}"
    return "attack"


def _project_index_rows(projects_root: Path) -> list[dict]:
    """Read live-session metadata while tolerating files removed during discovery."""
    rows = []
    if not projects_root.is_dir():
        return rows
    for slug_dir in sorted(projects_root.iterdir()):
        if not slug_dir.is_dir():
            continue
        for jsonl in sorted(slug_dir.glob("*.jsonl")):
            try:
                stat = jsonl.stat()
            except OSError:
                continue
            probe = _probe_head(jsonl)
            rows.append(
                {
                    "path": str(jsonl),
                    "name": f"{slug_dir.name}/{jsonl.stem}",
                    "source": "projects",
                    "mtime": stat.st_mtime,
                    "bytes": stat.st_size,
                    "model": probe["model"],
                    "version": probe["version"],
                    "subagents": _count_subagents(slug_dir / jsonl.stem / "subagents"),
                    "had_compaction": None,  # unknown without a full scan
                    "tokens_out": None,
                    "cost_usd": None,
                    "live": time.time() - stat.st_mtime < 300,
                    "session_id": probe["session_id"] or jsonl.stem,
                    "resolved_path": os.path.realpath(jsonl),
                    "project": slug_dir.name,
                }
            )

    return rows
