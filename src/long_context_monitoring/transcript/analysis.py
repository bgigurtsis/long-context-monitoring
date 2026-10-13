"""Aggregate file scans into trajectory statistics, agent linkage, and navigation landmarks."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from long_context_monitoring.artifact_layout import evidence_file
from long_context_monitoring.run_layout import DEFAULT_RUNS_ROOT, results_subpath
from .file_scan import get_scan


def analyze(self, results_root: str | Path | None = None) -> dict:
    """Everything the page header needs: files, histograms, agent tree,
    compaction boundaries, token totals. Cheap after the first scan —
    FileScans are incremental and cached.

    ``results_root`` contains dated monitor batches and any legacy in-place
    results; it decides the ``scores`` capability. It must match the root the
    Context tab reads (the server's ``--results``), so ``--results`` and the
    reported ``scores`` capability stay in agreement. Defaults to
    DEFAULT_RUNS_ROOT for internal callers (window/search) that ignore it."""
    files = self.files()
    scans = {fid: get_scan(info["path"]) for fid, info in files.items()}

    # API-reported discarded context plus final live context, never a size estimate.
    content_tokens = self._cumulative_context_from_scans(scans)
    totals = _scan_totals(self, files, scans)
    agents, matched_ids = _linked_agents(files, scans, totals.spawn_sites)
    _append_inline_agents(agents, scans)
    orphan_spawns = _orphan_spawns(totals.spawn_sites, matched_ids)
    breadcrumbs = _agent_breadcrumbs(agents)
    agent_tree = _agent_tree(agents, breadcrumbs)
    outline = _outline(scans, breadcrumbs, totals.boundaries, agent_tree)

    main_scan = scans["main"]
    # Read the manifest once and reuse it for the capability probes below —
    # it also decides where monitor results for this trajectory would live.
    manifest = self.manifest()
    labels_present = (
        self.kind == "archive" and evidence_file(self.path.parent, "labels.yaml").exists()
    )
    # ``results_subpath`` (from long_context_monitoring.run_layout) resolves the same
    # ``<task_id>/<condition>`` the monitor writes under, so this capability
    # probe points at exactly ``runs/<task_id>/<condition>/monitor/``.
    root = Path(results_root) if results_root else DEFAULT_RUNS_ROOT
    scores_present = (
        root / results_subpath(manifest, self.logical_name) / "monitor" / "index.json"
    ).exists()
    # A generated arm sits at <spec>/generations/<id>/<arm>/transcript, so
    # the authoring spec is three levels up. Its presence is what lets the
    # viewer render the plain-English briefing without a manifest, which
    # manual pairs do not write.
    parents = self.path.parents
    overview_present = (
        self.kind == "archive"
        and len(parents) > 3
        and (
            (parents[3] / "spec.yaml").exists() or evidence_file(parents[1], "result.json").exists()
        )
    )
    return {
        "name": self.name,
        "path": str(self.path),
        "kind": self.kind,
        "live": self.is_live(),
        "manifest": manifest,
        "session_id": main_scan.session_id,
        "version": main_scan.version,
        "models": totals.models,
        "files": totals.file_rows,
        "entry_types": totals.entry_types,
        "tools": totals.tools,
        "attachments": totals.attachments,
        "agents": agents,
        "orphan_spawns": orphan_spawns,
        "boundaries": totals.boundaries,
        "inline_sidechain": main_scan.inline_sidechain,
        "tokens_out_total": totals.tokens_out,
        "context_peak": totals.context_peak,
        "content_tokens_total": content_tokens,
        "agent_breadcrumbs": breadcrumbs,
        "outline": outline,
        "capabilities": {
            "live": self.is_live(),
            "export": True,
            "normalized": False,
            "labels": labels_present,
            "scores": scores_present,
            "overview": overview_present,
        },
    }


@dataclass
class _ScanTotals:
    """One ordered pass over scan counters and filesystem metadata."""

    entry_types: dict[str, int]
    tools: dict[str, int]
    attachments: dict[str, int]
    tokens_out: int
    context_peak: int
    models: list[str]
    file_rows: list[dict]
    boundaries: list[dict]
    spawn_sites: dict[str, tuple[str, dict]]


def _scan_totals(self, files: dict, scans: dict) -> _ScanTotals:
    """Aggregate every native file in order, tolerating disappearing files."""
    entry_types: dict[str, int] = {}
    tools: dict[str, int] = {}
    attachments: dict[str, int] = {}
    tokens_out = 0
    context_peak = 0
    models: list[str] = []
    file_rows = []
    boundaries = []
    # tool_use_id -> file that contains the spawn site (for parent lookup)
    spawn_sites: dict[str, tuple[str, dict]] = {}

    for fid, info in files.items():
        scan = scans[fid]
        for counter, mine in (
            (entry_types, scan.entry_types),
            (tools, scan.tools),
            (attachments, scan.attachments),
        ):
            for key, count in mine.items():
                counter[key] = counter.get(key, 0) + count
        tokens_out += scan.tokens_out
        context_peak = max(context_peak, scan.context_peak)
        for model in scan.models:
            if model not in models:
                models.append(model)
        for tool_use_id, site in scan.agent_spawns.items():
            spawn_sites[tool_use_id] = (fid, site)
        boundaries.extend(_compaction_rows(self, fid, scan))
        try:
            mtime = os.path.getmtime(info["path"])
            size = os.path.getsize(info["path"])
        except OSError:
            mtime, size = 0, 0
        file_rows.append(
            {
                "id": fid,
                "path": info["path"],
                "lines": scan.line_count,
                "bytes": size,
                "mtime": mtime,
                "tokens_out": scan.tokens_out,
                "parse_errors": scan.parse_errors,
                "meta": info["meta"],
            }
        )

    return _ScanTotals(
        entry_types,
        tools,
        attachments,
        tokens_out,
        context_peak,
        models,
        file_rows,
        boundaries,
        spawn_sites,
    )


def _compaction_rows(trajectory, fid: str, scan) -> list[dict]:
    """Pair boundaries with the first following live summary, including its own row."""
    boundaries = []
    for boundary in scan.boundaries:
        dropped = trajectory.dropped_uuids(scan)
        # Pair this boundary with the post-compaction summary that
        # follows it (the first isCompactSummary entry after its line),
        # so the viewer can jump straight to the live summary text.
        summary_line = None
        summary_chars = None
        for summary in scan.compaction_summaries:
            if summary["line"] >= boundary["line"]:
                summary_line = summary["line"]
                summary_chars = summary["chars"]
                break
        boundaries.append(
            {
                "file": fid,
                "line": boundary["line"],
                "trigger": boundary["trigger"],
                "preTokens": boundary["preTokens"],
                "postTokens": boundary["postTokens"],
                "dropped_count": len(dropped),
                "summary_line": summary_line,
                "summary_chars": summary_chars,
            }
        )
    return boundaries


def _linked_agents(files: dict, scans: dict, spawn_sites: dict) -> tuple[list, set]:
    """Resolve native agent IDs, result-side IDs, then unmatched teammate names."""
    # Reverse map for linkage path 2: agentId -> the tool_use_id whose
    # result reported it (toolUseResult.agentId).
    result_tool_use: dict[str, str] = {}
    for scan in scans.values():
        for tool_use_id, agent_id in scan.agent_results.items():
            result_tool_use[agent_id] = tool_use_id

    # Agent tree: link each agent file to its spawn site in the main file
    # OR another agent file (that is how nesting is discovered). Three
    # linkage paths, in order (all verified against real sessions):
    #   1. meta.toolUseId — headless / general-purpose agents;
    #   2. toolUseResult.agentId on the result entry — fallback;
    #   3. spawn input.name == meta.name — in-process teammates, whose
    #      meta has NO toolUseId and whose results carry no agentId.
    # Anything unmatched — either direction — is an orphan and gets
    # surfaced loudly, never dropped.
    agents = []
    matched_ids = set()
    for fid, info in files.items():
        if fid == "main":
            continue
        meta = info["meta"] or {}
        agent_id = fid.removeprefix("agent-")
        tool_use_id = meta.get("toolUseId") or result_tool_use.get(agent_id)
        if tool_use_id is None and meta.get("name"):
            tool_use_id = _teammate_spawn(meta["name"], spawn_sites, matched_ids)
        parent_file, site = spawn_sites.get(tool_use_id, (None, None))
        if tool_use_id and parent_file is not None:
            matched_ids.add(tool_use_id)
        agents.append(
            {
                "id": fid,
                "agentType": meta.get("agentType"),
                "description": meta.get("description"),
                "spawnDepth": meta.get("spawnDepth"),
                "toolUseId": tool_use_id,
                "parent_file": parent_file,
                "spawn_line": site["line"] if site else None,
                "tokens_out": scans[fid].tokens_out,
                "lines": scans[fid].line_count,
                "orphan": parent_file is None,
                "inline": False,
            }
        )

    return agents, matched_ids


def _append_inline_agents(agents: list, scans: dict) -> None:
    """Keep legacy inline sidechains visible without inventing separate files."""
    # Claude Code used to inline sidechains in the parent JSONL. Preserve
    # those as outline branches when no sibling file exists. They remain in
    # exact main-file order in Raw JSONL mode.
    for inline_id, record in scans["main"].inline_agents.items():
        fid = "main"
        synthetic_id = f"inline-{inline_id}"
        if any(agent["id"] == synthetic_id for agent in agents):
            continue
        agents.append(
            {
                "id": synthetic_id,
                "agentType": "inline-sidechain",
                "description": "Legacy inline sidechain entries",
                "spawnDepth": None,
                "toolUseId": None,
                "parent_file": fid,
                "spawn_line": record["first_line"],
                "tokens_out": 0,
                "lines": record["lines"],
                "orphan": False,
                "inline": True,
                "inline_agent_id": inline_id,
                "last_line": record["last_line"],
            }
        )


def _orphan_spawns(spawn_sites: dict, matched_ids: set) -> list[dict]:
    """Surface authored spawn sites that have no matching native agent file."""
    orphan_spawns = []
    for tool_use_id, (fid, site) in spawn_sites.items():
        if tool_use_id not in matched_ids:
            orphan_spawns.append(
                {
                    "file": fid,
                    "line": site["line"],
                    "tool_use_id": tool_use_id,
                    "description": site["description"],
                }
            )

    return orphan_spawns


def _agent_breadcrumbs(agents: list[dict]) -> dict[str, list[str]]:
    """Follow parents with cycle protection and keep the main-file fallback."""
    parent_by_file = {
        agent["id"]: agent["parent_file"]
        for agent in agents
        if not agent.get("inline") and agent.get("parent_file")
    }
    breadcrumbs: dict[str, list[str]] = {"main": ["main"]}
    for agent in agents:
        if agent.get("inline"):
            continue
        trail = [agent["id"]]
        parent = agent.get("parent_file")
        seen = {agent["id"]}
        while parent and parent not in seen:
            trail.append(parent)
            seen.add(parent)
            parent = parent_by_file.get(parent)
        if trail[-1] != "main":
            trail.append("main")
        breadcrumbs[agent["id"]] = list(reversed(trail))

    return breadcrumbs


def _agent_tree(agents: list[dict], breadcrumbs: dict) -> list[dict]:
    """Link outline nodes in source order, retaining orphan branches."""
    agent_nodes: dict[str, dict] = {}
    for agent in agents:
        node = dict(agent)
        node["children"] = []
        node["breadcrumb"] = breadcrumbs.get(
            agent["id"], [agent.get("parent_file") or "main", agent["id"]]
        )
        agent_nodes[agent["id"]] = node
    agent_tree = []
    for agent in agents:
        node = agent_nodes[agent["id"]]
        parent = agent.get("parent_file")
        if parent in agent_nodes and parent != agent["id"]:
            agent_nodes[parent]["children"].append(node)
        else:
            agent_tree.append(node)

    return agent_tree


def _outline(
    scans: dict, breadcrumbs: dict, boundaries: list, agent_tree: list
) -> dict:
    """Collect landmarks and number authored edits in their established file order."""
    turns = []
    errors = []
    edits = []
    for fid, scan in scans.items():
        breadcrumb = breadcrumbs.get(fid, ["main", fid] if fid != "main" else ["main"])
        for turn in scan.turn_lines:
            turns.append({"file": fid, "breadcrumb": breadcrumb, **turn})
        for error in scan.error_lines:
            errors.append({"file": fid, "breadcrumb": breadcrumb, **error})
        for edit in scan.edit_lines:
            edits.append({"file": fid, "breadcrumb": breadcrumb, **edit})
    # Number the edits in file order so the viewer, the outline, and the
    # run's registered edit list all refer to the same "edit 1 / edit 2".
    edits.sort(key=lambda item: (item["file"] != "main", item["line"]))
    for index, edit in enumerate(edits, start=1):
        edit["index"] = index

    landmarks = []
    for turn in turns:
        landmarks.append({"kind": "turn", **turn})
    for boundary in boundaries:
        landmarks.append({"kind": "compaction", **boundary})
    for error in errors:
        landmarks.append({"kind": "error", **error})
    for edit in edits:
        landmarks.append({"kind": "edit", **edit})

    return {
        "turns": turns,
        "agents": agent_tree,
        "compactions": boundaries,
        "errors": errors,
        "edits": edits,
        "landmarks": landmarks,
    }


def _teammate_spawn(name: str, spawn_sites: dict, matched_ids: set) -> str | None:
    """Use the first unmatched spawn with the recorded teammate name."""
    for candidate, (_, site) in spawn_sites.items():
        if site.get("name") == name and candidate not in matched_ids:
            return candidate
    return None
