"""Public native-transcript API and bounded navigation over focused data-layer modules."""

from __future__ import annotations

import hashlib as hashlib
from concurrent.futures import ThreadPoolExecutor as ThreadPoolExecutor
import json
import os
import re
import threading as threading
import time
from pathlib import Path

from long_context_monitoring.run_layout import (
    DEFAULT_RUNS_ROOT as DEFAULT_RUNS_ROOT,
    results_subpath as results_subpath,
    resolve_repo_path,
    experiment_roots as experiment_roots,
)
from long_context_monitoring.transcript.entries import (
    human_prompt_text as human_prompt_text,
    message_blocks as message_blocks,
)
from long_context_monitoring.transcript.discovery import artifact_directories as artifact_directories


from .presentation import (
    AGENT_TOOL_NAMES as AGENT_TOOL_NAMES,
    CONVERSATION_TYPES as CONVERSATION_TYPES,
    PRESET_CATEGORIES as PRESET_CATEGORIES,
    LANDMARK_KINDS as LANDMARK_KINDS,
    _text_preview as _text_preview,
)
from .file_scan import (
    FileScan as FileScan,
    get_scan as get_scan,
    _scan_cache as _scan_cache,
    _scan_cache_lock as _scan_cache_lock,
)
from .archive_paths import (
    _archive_manifest_path as _archive_manifest_path,
    _archive_logical_name as _archive_logical_name,
)
from .catalog import (
    discover as discover,
    deduplicate_trajectories as deduplicate_trajectories,
    _probe_head as _probe_head,
    _count_subagents as _count_subagents,
    _manifest_had_compaction as _manifest_had_compaction,
    _archive_index_row as _archive_index_row,
    _deduplication_arm as _deduplication_arm,
)
from .analysis import analyze


class Trajectory:
    """One trajectory = a main session JSONL plus its subagents directory.

    Accepts either a generated arm's ``transcript/`` archive or a bare
    ``.jsonl`` path (e.g. a live ``~/.claude/projects/<slug>/<sid>.jsonl``,
    whose subagents live in the sibling ``<sid>/subagents/`` dir).
    """

    def __init__(self, path: str | Path):
        self.path = resolve_repo_path(path)
        if self.path.is_dir():
            self.kind = "archive"
            mains = sorted(p for p in self.path.glob("*.jsonl"))
            if not mains:
                raise FileNotFoundError(f"no .jsonl in archive dir {self.path}")
            self.manifest_path = _archive_manifest_path(self.path)
            manifest = self.manifest()
            session_id = (manifest or {}).get("session_id")
            preferred = (
                self.path / f"{session_id}.jsonl"
                if isinstance(session_id, str) and session_id
                else None
            )
            self.main_path = preferred if preferred and preferred.is_file() else mains[0]
            self.subagents_dir = self.path / "subagents"
            self.name = self.path.name
            self.logical_name = _archive_logical_name(self.path)
        elif self.path.suffix == ".jsonl":
            self.kind = "session"
            self.main_path = self.path
            # Live-session layout: <slug>/<session-id>.jsonl with sub-agents
            # in <slug>/<session-id>/subagents/.
            self.subagents_dir = self.path.parent / self.path.stem / "subagents"
            self.manifest_path = None
            self.name = self.path.stem
            self.logical_name = self.name
        else:
            raise FileNotFoundError(f"not a trajectory: {self.path}")

    def manifest(self) -> dict | None:
        if self.manifest_path and self.manifest_path.exists():
            try:
                return json.loads(self.manifest_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return None
        return None

    def is_live(self) -> bool:
        """Heuristic: written to in the last 5 minutes."""
        try:
            return time.time() - os.path.getmtime(self.main_path) < 300
        except OSError:
            return False

    def agent_files(self) -> list[dict]:
        """Enumerate subagent JSONL files with their meta sidecars.

        Follows symlinks (resumed sessions symlink agents back to the original
        session) and dedupes by agentId — first occurrence wins.

        Two layouts are read: the flat ``subagents/agent-*.jsonl`` a spawned
        sub-agent writes, and ``subagents/workflows/<run>/agent-*.jsonl``, which
        is where the Workflow tool puts the agents one workflow run spawned.
        Those are real delegated work, so leaving them out would hide it from
        the monitor; each still carries its own ``.meta.json``.
        """
        out = []
        seen_ids = set()
        if not self.subagents_dir.is_dir():
            return out
        flat = sorted(self.subagents_dir.glob("agent-*.jsonl"))
        workflow = sorted(self.subagents_dir.glob("workflows/*/agent-*.jsonl"))
        for path in flat + workflow:
            agent_id = path.stem  # "agent-<id>"
            if agent_id in seen_ids:
                continue
            seen_ids.add(agent_id)
            meta = None
            meta_path = path.with_suffix(".meta.json")
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    meta = None
            out.append({"id": agent_id, "path": str(path), "meta": meta})
        return out

    def files(self) -> dict[str, dict]:
        """All JSONL files in this trajectory, keyed by file id.

        The main file has id "main"; agents use their "agent-<id>" filename stem.
        """
        files = {"main": {"id": "main", "path": str(self.main_path), "meta": None}}
        for agent in self.agent_files():
            files[agent["id"]] = {"id": agent["id"], "path": agent["path"], "meta": agent["meta"]}
        return files

    def scan(self, file_id: str) -> FileScan:
        info = self.files().get(file_id)
        if info is None:
            raise KeyError(f"unknown file id {file_id!r}")
        return get_scan(info["path"])

    def dropped_uuids(self, scan: FileScan) -> set[str]:
        """Uuids of conversation entries dropped from context at a compaction.

        For each boundary: everything before it (and after the previous
        boundary) whose uuid is not in that boundary's preservedMessages list
        is out of live context. This is the exact mechanism the monitor
        visibility filter can use without depending on viewer presentation.
        """
        dropped: set[str] = set()
        prev_line = -1
        for boundary in scan.boundaries:
            preserved = set(boundary["preserved_uuids"])
            for line, uuid in scan.conv_entries:
                if prev_line < line < boundary["line"] and uuid not in preserved:
                    dropped.add(uuid)
            prev_line = boundary["line"]
        return dropped

    @staticmethod
    def _cumulative_context_from_scans(scans: dict[str, FileScan]) -> int:
        """Return native cumulative context plus explicitly labeled padding.

        Each compaction contributes only the context it discarded; the final
        live context is then added once.  This is the canonical cumulative
        token definition used by both the detail view and the trajectory index.
        Synthetic padding is counted separately without changing API usage.
        """
        total = 0
        for scan in scans.values():
            total += scan.context_last
            total += scan.synthetic_padding_tokens
            for boundary in scan.boundaries:
                total += (
                    (boundary["preTokens"] or 0)
                    - (boundary["postTokens"] or 0)
                )
        return total

    def cumulative_context_tokens(self) -> int:
        """Return cumulative context and explicit padding without full metadata."""
        scans = {
            file_id: get_scan(info["path"])
            for file_id, info in self.files().items()
        }
        return self._cumulative_context_from_scans(scans)

    def analysis(self, results_root: str | Path | None = None) -> dict:
        """Everything the page header needs: files, histograms, agent tree,
        compaction boundaries, token totals. Cheap after the first scan —
        FileScans are incremental and cached.

        ``results_root`` contains dated monitor batches and any legacy in-place
        results; it decides the ``scores`` capability. It must match the root the
        Context tab reads (the server's ``--results``), so ``--results`` and the
        reported ``scores`` capability stay in agreement. Defaults to
        DEFAULT_RUNS_ROOT for internal callers (window/search) that ignore it."""
        return analyze(self, results_root)

    def window(
        self,
        file_id: str,
        start: int,
        limit: int,
        preset: str | None = None,
        landmark_kinds: set[str] | None = None,
    ) -> dict:
        """Return a raw-cursor window with viewer-only presentation metadata.

        ``start`` and all returned cursors are source-line offsets even when a
        preset filters noisy entries. This keeps old callers and deep links
        stable and prevents bookkeeping from shifting tool call/result links.
        """
        if preset not in PRESET_CATEGORIES and preset is not None:
            raise KeyError(f"unknown preset {preset!r}")
        self._validate_landmark_kinds(landmark_kinds)
        scan = self.scan(file_id)
        dropped = self.dropped_uuids(scan)
        wanted = PRESET_CATEGORIES.get(preset)
        breadcrumb = self.analysis()["agent_breadcrumbs"].get(
            file_id, ["main", file_id] if file_id != "main" else ["main"]
        )
        cursor = max(0, start)
        items: list[dict] = []
        # Read bounded chunks. Filtering may skip many bookkeeping lines, but
        # never requires holding the entire trajectory as parsed objects.
        while cursor < scan.line_count and len(items) < max(0, limit):
            batch_size = min(max(limit * 3, 100), 2000)
            batch = scan.read_entries(cursor, batch_size)
            if not batch:
                break
            for item in batch:
                cursor = item["line"] + 1
                presented = self._window_item(
                    file_id, scan, item, wanted, landmark_kinds, dropped,
                    breadcrumb,
                )
                if presented is None:
                    continue
                items.append(presented)
                if len(items) >= limit:
                    break
        return {
            "file": file_id,
            "entries": items,
            "total": scan.line_count,
            "cursor": max(0, start),
            "next_cursor": cursor,
            "prev_cursor": max(0, start - max(limit * 3, 100)),
            "preset": preset,
            "landmark_kinds": sorted(landmark_kinds or []),
        }

    def window_before(
        self,
        file_id: str,
        before: int,
        limit: int,
        preset: str | None = None,
        landmark_kinds: set[str] | None = None,
    ) -> dict:
        """Return the last ``limit`` visible entries strictly before a line.

        The viewer uses this for upward virtual scrolling.  A real reverse
        window prevents gaps when presentation presets skip raw JSONL lines;
        guessing a forward start from ``before - N`` cannot provide that
        guarantee for differently dense transcript regions.
        """
        if preset not in PRESET_CATEGORIES and preset is not None:
            raise KeyError(f"unknown preset {preset!r}")
        self._validate_landmark_kinds(landmark_kinds)
        scan = self.scan(file_id)
        dropped = self.dropped_uuids(scan)
        wanted = PRESET_CATEGORIES.get(preset)
        breadcrumb = self.analysis()["agent_breadcrumbs"].get(
            file_id, ["main", file_id] if file_id != "main" else ["main"]
        )
        boundary = min(max(0, before), scan.line_count)
        cursor = boundary
        reverse_items: list[dict] = []
        batch_size = min(max(limit * 3, 100), 2000)
        while cursor > 0 and len(reverse_items) < max(0, limit):
            batch_start = max(0, cursor - batch_size)
            batch = scan.read_entries(batch_start, cursor - batch_start)
            cursor = batch_start
            for item in reversed(batch):
                presented = self._window_item(
                    file_id, scan, item, wanted, landmark_kinds, dropped,
                    breadcrumb,
                )
                if presented is None:
                    continue
                reverse_items.append(presented)
                if len(reverse_items) >= limit:
                    break
        items = list(reversed(reverse_items))
        previous = items[0]["line"] if items else cursor
        return {
            "file": file_id,
            "entries": items,
            "total": scan.line_count,
            "cursor": previous,
            "next_cursor": boundary,
            "prev_cursor": previous,
            "preset": preset,
            "landmark_kinds": sorted(landmark_kinds or []),
        }

    @staticmethod
    def _validate_landmark_kinds(landmark_kinds: set[str] | None) -> None:
        if landmark_kinds is None:
            return
        unknown = landmark_kinds - LANDMARK_KINDS
        if unknown:
            names = ", ".join(sorted(unknown))
            raise KeyError(f"unknown landmark kind(s): {names}")

    @staticmethod
    def _matches_landmark_kind(meta: dict, kinds: set[str]) -> bool:
        """Return whether a source row belongs to a selected landmark kind.

        Authored edits are native call/result pairs. Both rows are injected,
        so retaining both shows the action and its result while the outline
        continues to expose one landmark per pair.
        """
        categories = set(meta.get("categories", []))
        for kind in kinds:
            if kind == "edit" and meta.get("injected"):
                return True
            if kind == "compaction" and {
                "compaction", "compaction_summary"
            }.intersection(categories):
                return True
            if kind == "turn" and "prompt" in categories:
                return True
            if kind == "error" and meta.get("is_error"):
                return True
        return False

    @staticmethod
    def _window_item(
        file_id: str,
        scan: FileScan,
        item: dict,
        wanted: set[str] | None,
        landmark_kinds: set[str] | None,
        dropped: set[str],
        breadcrumb: list[str],
    ) -> dict | None:
        """Attach presentation metadata to one raw entry, or filter it out."""
        meta = dict(scan.line_meta.get(item["line"], {}))
        if wanted is not None and not wanted.intersection(meta.get("categories", [])):
            return None
        if landmark_kinds is not None and not Trajectory._matches_landmark_kind(
            meta, landmark_kinds
        ):
            return None
        entry = item.get("entry")
        item["dropped"] = bool(
            isinstance(entry, dict) and entry.get("uuid") in dropped
        )
        item.update(meta)
        item["file"] = file_id
        item["agent_breadcrumb"] = breadcrumb
        item["related"] = None
        tool_use_id = meta.get("tool_use_id")
        if tool_use_id in scan.tool_calls and tool_use_id in scan.tool_results:
            if item["line"] == scan.tool_calls[tool_use_id]["line"]:
                item["related"] = {
                    "file": file_id,
                    "line": scan.tool_results[tool_use_id]["line"],
                    "kind": "result",
                }
            else:
                item["related"] = {
                    "file": file_id,
                    "line": scan.tool_calls[tool_use_id]["line"],
                    "kind": "call",
                }
        return item

    def search(
        self,
        query: str,
        use_regex: bool = False,
        scope: str = "all",
        file_id: str = "main",
        categories: set[str] | None = None,
        limit: int = 200,
    ) -> dict:
        """Search the main session and agent tree with stable locators."""
        if not query:
            return {"hits": [], "error": None}
        if use_regex:
            try:
                re.compile(query)
            except re.error as error:
                return {"hits": [], "error": str(error)}

        meta = self.analysis()
        file_ids = [row["id"] for row in meta["files"]]
        if scope == "file":
            file_ids = [file_id]
        elif scope == "branch":
            children: dict[str, list[str]] = {}
            for agent in meta["agents"]:
                if agent.get("inline"):
                    continue
                children.setdefault(agent.get("parent_file") or "main", []).append(agent["id"])
            selected = []
            stack = [file_id]
            while stack:
                current = stack.pop()
                if current in selected:
                    continue
                selected.append(current)
                stack.extend(children.get(current, []))
            file_ids = selected

        hits = []
        for fid in file_ids:
            remaining = limit - len(hits)
            if remaining <= 0:
                break
            try:
                file_hits = self.scan(fid).search(
                    query, use_regex, categories=categories, limit=remaining
                )
            except re.error as error:
                return {"hits": [], "error": str(error)}
            breadcrumb = meta["agent_breadcrumbs"].get(
                fid, ["main", fid] if fid != "main" else ["main"]
            )
            for hit in file_hits:
                hit["file"] = fid
                hit["agent_breadcrumb"] = breadcrumb
                hits.append(hit)
        return {"hits": hits, "error": None}
