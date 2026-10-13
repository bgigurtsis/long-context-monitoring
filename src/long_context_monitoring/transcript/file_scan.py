"""Incremental native JSONL scanning with stable byte offsets and shared cache state."""

from __future__ import annotations

import json
import os
import re
import threading
from pathlib import Path
from long_context_monitoring.transcript.entries import message_blocks
from .presentation import (
    AGENT_TOOL_NAMES,
    CONVERSATION_TYPES,
    _edit_landmark,
    _presentation,
    _codex_presentation,
)


class FileScan:
    """Incremental scan state for one JSONL file.

    Append-only files let us keep a byte offset of how far we have scanned and
    only parse newly appended complete lines on refresh() — this is what makes
    live-tailing a generation run cheap.
    """

    def __init__(self, path: str):
        self.path = path
        self.lock = threading.Lock()
        self.offsets: list[int] = []  # byte offset of each line start
        self.scanned_bytes = 0  # we have ingested complete lines up to here
        # Derived stats, updated per ingested line:
        self.entry_types: dict[str, int] = {}
        self.tools: dict[str, int] = {}
        self.attachments: dict[str, int] = {}
        self.tokens_out = 0
        self.context_peak = 0  # max(input + cache tokens) seen in any usage
        self.context_last = 0  # same sum, from the most recent usage seen
        self.synthetic_padding_tokens = 0  # Explicit additions, never API usage.
        self.models: list[str] = []
        self.version: str | None = None
        self.session_id: str | None = None
        self.inline_sidechain = 0  # isSidechain entries in a *main* file (old format)
        self.parse_errors = 0
        # Claude Code may repeat earlier native history when a resumed process
        # appends to the same session. UUIDs identify those copied entries.
        self.seen_entry_uuids: set[str] = set()
        # (line_no, uuid) for conversation entries, in file order — needed for
        # the compaction dropped-set computation.
        self.conv_entries: list[tuple[int, str]] = []
        # tool_use_id -> spawn site info, for Agent/Task calls in this file.
        self.agent_spawns: dict[str, dict] = {}
        # tool_use_id -> agentId, from toolUseResult sidecars on result entries
        # (second linkage path — teammate metas have no toolUseId).
        self.agent_results: dict[str, str] = {}
        # Compaction boundaries found in this file.
        self.boundaries: list[dict] = []
        # Post-compaction summary entries (isCompactSummary), in file order.
        # Only the line + char count are kept here; the (large) summary text is
        # left in the JSONL and rendered from the event stream, so the viewer
        # always shows the *live* reconstructed summary rather than a manifest
        # copy that neutral-compaction may have left stale.
        self.compaction_summaries: list[dict] = []
        # Viewer-only line annotations. Keeping these small lets entry windows,
        # outlines, and filtered cursors avoid reparsing the full transcript.
        self.line_meta: dict[int, dict] = {}
        self.turn_lines: list[dict] = []
        self.error_lines: list[dict] = []
        # Authored tool calls spliced into a derived attack transcript, in file
        # order. One row per call (never its result), so the count equals the
        # number of registered edits.
        self.edit_lines: list[dict] = []
        self.tool_calls: dict[str, dict] = {}
        self.tool_results: dict[str, dict] = {}
        self.inline_agents: dict[str, dict] = {}
        self.current_turn = 0

    def refresh(self) -> None:
        """Ingest any lines appended since the last refresh."""
        with self.lock:
            try:
                size = os.path.getsize(self.path)
            except OSError:
                return
            if size < self.scanned_bytes:
                # File shrank (should not happen for session logs) — rescan.
                self.__init__(self.path)
                size = os.path.getsize(self.path)
            if size == self.scanned_bytes:
                return
            with open(self.path, "rb") as f:
                f.seek(self.scanned_bytes)
                chunk = f.read(size - self.scanned_bytes)
            end = chunk.rfind(b"\n")
            if end == -1:
                return  # only a partial line so far (file mid-write)
            pos = self.scanned_bytes
            for raw in chunk[: end + 1].split(b"\n")[:-1]:
                self.offsets.append(pos)
                self._ingest(len(self.offsets) - 1, raw)
                pos += len(raw) + 1
            self.scanned_bytes = pos

    def _ingest(self, line_no: int, raw: bytes) -> None:
        """Apply one complete native row in source order to the scan indexes."""
        entry = self._parse_entry(line_no, raw)
        if entry is None:
            return
        etype = entry.get("type") or "<untyped>"
        # Count system entries per subtype — the subtypes (turn_duration,
        # compact_boundary, …) are the interesting part.
        key = etype
        if etype == "system" and entry.get("subtype"):
            key = f"system/{entry['subtype']}"
        self.entry_types[key] = self.entry_types.get(key, 0) + 1

        if etype == "synthetic_padding":
            # This non-conversation record contributes only its declared padding.
            tokens = entry.get("token_count")
            if type(tokens) is not int or tokens < 0:
                raise ValueError("synthetic padding requires a nonnegative token_count")
            self.synthetic_padding_tokens += tokens
            return

        self._record_codex_metadata(line_no, entry, etype)
        self._record_session_metadata(line_no, entry, etype)
        self._record_presentation(line_no, entry)
        self._record_compactions(line_no, entry, etype)
        if etype == "assistant":
            self._record_assistant(line_no, entry)
        if etype == "user":
            self._record_agent_results(entry)
        for block in message_blocks(entry):
            if block.get("type") == "tool_result" and block.get("tool_use_id"):
                self.tool_results[block["tool_use_id"]] = {
                    "line": line_no,
                    "is_error": bool(block.get("is_error")),
                }

    def _parse_entry(self, line_no: int, raw: bytes) -> dict | None:
        """Keep invalid rows navigable and suppress only repeated native UUIDs."""
        try:
            entry = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.parse_errors += 1
            self.entry_types["<unparseable>"] = (
                self.entry_types.get("<unparseable>", 0) + 1
            )
            meta = {
                "category": "error",
                "categories": ["error"],
                "turn": self.current_turn or None,
                "title": "Unparseable JSONL data",
                "is_error": True,
                "tool_use_id": None,
                "tool_use_ids": [],
                "uuid": None,
            }
            self.line_meta[line_no] = meta
            self.error_lines.append({"line": line_no, "title": meta["title"]})
            return None
        if not isinstance(entry, dict):
            self.entry_types["<non-object>"] = (
                self.entry_types.get("<non-object>", 0) + 1
            )
            self.line_meta[line_no] = {
                "category": "bookkeeping",
                "categories": ["bookkeeping"],
                "turn": self.current_turn or None,
                "title": "Non-object JSON value",
                "is_error": False,
                "tool_use_id": None,
                "tool_use_ids": [],
                "uuid": None,
            }
            return None

        entry_uuid = entry.get("uuid")
        if entry_uuid is not None:
            if entry_uuid in self.seen_entry_uuids:
                self.line_meta[line_no] = {
                    "category": "bookkeeping",
                    "categories": ["bookkeeping"],
                    "turn": self.current_turn or None,
                    "title": "Repeated native history entry",
                    "is_error": False,
                    "tool_use_id": None,
                    "tool_use_ids": [],
                    "uuid": entry_uuid,
                    "duplicate": True,
                    "injected": False,
                    "injected_phase": None,
                }
                return None
            self.seen_entry_uuids.add(entry_uuid)

        return entry

    def _record_codex_metadata(self, line_no: int, entry: dict, etype: str) -> None:
        """Retain native Codex compaction and tool-call identities."""
        payload = entry.get("payload") if isinstance(entry.get("payload"), dict) else {}
        if etype == "session_meta" and payload:
            self.version = self.version or payload.get("cli_version")
            self.session_id = self.session_id or payload.get("id")
        if etype == "turn_context" and payload:
            model = payload.get("model")
            if model and model not in self.models:
                self.models.append(model)
        if etype == "compacted" and payload:
            preserved = [
                item.get("id")
                for item in payload.get("replacement_history", [])
                if isinstance(item, dict) and item.get("id")
            ]
            self.boundaries.append(
                {
                    "line": line_no,
                    "uuid": payload.get("window_id"),
                    "trigger": "native",
                    "preTokens": None,
                    "postTokens": None,
                    "preserved_uuids": preserved,
                }
            )
            self.compaction_summaries.append(
                {
                    "line": line_no,
                    "uuid": payload.get("window_id"),
                    "chars": len(str(payload.get("message") or "")),
                }
            )
        if etype == "response_item" and payload:
            ptype = payload.get("type")
            if ptype in ("function_call", "custom_tool_call"):
                name = payload.get("name") or "<unnamed>"
                namespace = payload.get("namespace")
                if namespace:
                    name = f"{namespace}.{name}"
                self.tools[name] = self.tools.get(name, 0) + 1
                call_id = payload.get("call_id")
                if call_id:
                    self.tool_calls[call_id] = {
                        "line": line_no,
                        "name": name,
                        "is_agent": name.endswith(".spawn_agent"),
                    }
            elif ptype in ("function_call_output", "custom_tool_call_output"):
                call_id = payload.get("call_id")
                if call_id:
                    self.tool_results[call_id] = {
                        "line": line_no,
                        "is_error": False,
                    }

    def _record_session_metadata(self, line_no: int, entry: dict, etype: str) -> None:
        """Accumulate session identity, attachment counts, and legacy sidechains."""
        if etype == "attachment":
            att = entry.get("attachment") or {}
            atype = att.get("type") or "<untyped>"
            self.attachments[atype] = self.attachments.get(atype, 0) + 1

        if self.version is None and entry.get("version"):
            self.version = entry["version"]
        if self.session_id is None and entry.get("sessionId"):
            self.session_id = entry["sessionId"]
        if entry.get("isSidechain") is True:
            self.inline_sidechain += 1
            inline_id = entry.get("agentId") or "inline-sidechain"
            record = self.inline_agents.setdefault(
                inline_id,
                {
                    "id": inline_id,
                    "first_line": line_no,
                    "last_line": line_no,
                    "lines": 0,
                },
            )
            record["last_line"] = line_no
            record["lines"] += 1

    def _record_presentation(self, line_no: int, entry: dict) -> None:
        """Index navigation metadata without replacing the authoritative source."""
        presentation = self._presentation(line_no, entry)
        self.line_meta[line_no] = presentation
        if presentation["is_error"]:
            self.error_lines.append(
                {
                    "line": line_no,
                    "title": presentation["title"],
                    "tool_use_id": presentation["tool_use_id"],
                }
            )

        # Authored (non-generated) tool calls: the manual-pair Edit pairs and
        # the legacy injector's pairs. Only the *call* side is recorded, so one
        # landmark exists per edit rather than two.
        if presentation.get("injected") and any(
            block.get("type") == "tool_use" for block in message_blocks(entry)
        ):
            self.edit_lines.append(self._edit_landmark(line_no, entry, presentation))

    def _record_compactions(self, line_no: int, entry: dict, etype: str) -> None:
        """Keep preserved UUIDs and summary positions in native file order."""
        if etype in CONVERSATION_TYPES and entry.get("uuid"):
            self.conv_entries.append((line_no, entry["uuid"]))

        if etype == "system" and entry.get("subtype") == "compact_boundary":
            meta = entry.get("compactMetadata") or {}
            preserved = (meta.get("preservedMessages") or {}).get("uuids") or []
            self.boundaries.append(
                {
                    "line": line_no,
                    "uuid": entry.get("uuid"),
                    "trigger": meta.get("trigger"),
                    "preTokens": meta.get("preTokens"),
                    "postTokens": meta.get("postTokens"),
                    "preserved_uuids": list(preserved),
                }
            )

        if entry.get("isCompactSummary") is True:
            summary_content = (entry.get("message") or {}).get("content")
            summary_text = summary_content if isinstance(summary_content, str) else ""
            self.compaction_summaries.append(
                {
                    "line": line_no,
                    "uuid": entry.get("uuid"),
                    "chars": len(summary_text),
                }
            )

    def _record_assistant(self, line_no: int, entry: dict) -> None:
        """Account for API usage before indexing the assistant's tool calls."""
        message = entry.get("message") or {}
        model = message.get("model")
        if model and model not in self.models:
            self.models.append(model)
        usage = message.get("usage") or {}
        self.tokens_out += usage.get("output_tokens") or 0
        context = (
            (usage.get("input_tokens") or 0)
            + (usage.get("cache_read_input_tokens") or 0)
            + (usage.get("cache_creation_input_tokens") or 0)
        )
        self.context_peak = max(self.context_peak, context)
        if context:
            self.context_last = context
        self._record_tool_calls(line_no, entry, message)

    def _record_tool_calls(self, line_no: int, entry: dict, message: dict) -> None:
        """Record call sites and all native agent-linkage keys."""
        content = message.get("content")
        if not isinstance(content, list):
            return
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            name = block.get("name") or "<unnamed>"
            self.tools[name] = self.tools.get(name, 0) + 1
            if name in AGENT_TOOL_NAMES and block.get("id"):
                tool_input = block.get("input") or {}
                self.agent_spawns[block["id"]] = {
                    "line": line_no,
                    "uuid": entry.get("uuid"),
                    "description": tool_input.get("description")
                    or str(tool_input.get("prompt") or "")[:120],
                    "subagent_type": tool_input.get("subagent_type"),
                    # Teammate spawns carry a name; it is the only
                    # linkage key for in-process teammates.
                    "name": tool_input.get("name"),
                }

            if block.get("id"):
                self.tool_calls[block["id"]] = {
                    "line": line_no,
                    "name": name,
                    "is_agent": name in AGENT_TOOL_NAMES,
                }

    def _record_agent_results(self, entry: dict) -> None:
        """Resolve result-side agent IDs when spawn metadata has no toolUseId."""
        sidecar = entry.get("toolUseResult")
        if not isinstance(sidecar, dict) or not sidecar.get("agentId"):
            return
        content = (entry.get("message") or {}).get("content")
        if not isinstance(content, list):
            return
        for block in content:
            if (
                isinstance(block, dict)
                and block.get("type") == "tool_result"
                and block.get("tool_use_id")
            ):
                self.agent_results[block["tool_use_id"]] = sidecar["agentId"]

    @staticmethod
    def _edit_landmark(line_no: int, entry: dict, presentation: dict) -> dict:
        return _edit_landmark(line_no, entry, presentation)

    def _presentation(self, line_no: int, entry: dict) -> dict:
        return _presentation(self, line_no, entry)

    def _codex_presentation(self, line_no: int, entry: dict) -> dict:
        return _codex_presentation(self, line_no, entry)

    @property
    def line_count(self) -> int:
        return len(self.offsets)

    def read_entries(self, start: int, limit: int) -> list[dict]:
        """Read and parse lines [start, start+limit) from disk.

        Returns wrapper dicts ``{"line": N, "entry": {...}}``. Unparseable
        lines come back as ``{"line": N, "raw": "..."}`` so nothing is dropped.
        """
        with self.lock:
            start = max(0, start)
            end = min(start + max(0, limit), len(self.offsets))
            if start >= end:
                return []
            begin = self.offsets[start]
            stop = self.offsets[end] if end < len(self.offsets) else self.scanned_bytes
        with open(self.path, "rb") as f:
            f.seek(begin)
            data = f.read(stop - begin)
        out = []
        for i, raw in enumerate(data.split(b"\n")[: end - start]):
            line_no = start + i
            raw_text = raw.decode("utf-8", "replace")
            try:
                out.append(
                    {
                        "line": line_no,
                        "entry": json.loads(raw),
                        # Exact source text powers Raw JSONL mode and exports. The
                        # parsed entry remains for backward-compatible callers.
                        "raw": raw_text,
                    }
                )
            except (json.JSONDecodeError, UnicodeDecodeError):
                out.append({"line": line_no, "raw": raw_text})
        return out

    def search(
        self,
        query: str,
        use_regex: bool,
        categories: set[str] | None = None,
        limit: int = 200,
    ) -> list[dict]:
        """Search raw lines while returning stable source locators."""
        pattern = None
        if use_regex:
            pattern = re.compile(query, re.IGNORECASE)
        needle = query.lower()
        hits = []
        with self.lock:
            count = len(self.offsets)
            scanned = self.scanned_bytes
        with open(self.path, "rb") as f:
            data = f.read(scanned)
        for line_no, raw in enumerate(data.split(b"\n")[:count]):
            meta = self.line_meta.get(line_no, {})
            if categories and not categories.intersection(meta.get("categories", [])):
                continue
            text = raw.decode("utf-8", "replace")
            if pattern is not None:
                match = pattern.search(text)
                if not match:
                    continue
                at = match.start()
            else:
                at = text.lower().find(needle)
                if at == -1:
                    continue
            snippet = text[max(0, at - 60) : at + 120]
            hits.append(
                {
                    "line": line_no,
                    "type": meta.get("category", "?"),
                    "category": meta.get("category", "?"),
                    "categories": meta.get("categories", []),
                    "title": meta.get("title", ""),
                    "uuid": meta.get("uuid"),
                    "snippet": snippet,
                }
            )
            if len(hits) >= limit:
                break
        return hits


# One FileScan per real path, shared across requests and trajectories (a live
# session's subagent files can be symlinked from a resumed session — realpath
# keying is also what dedupes those).
_scan_cache: dict[str, FileScan] = {}
_scan_cache_lock = threading.Lock()


def get_scan(path: str | Path) -> FileScan:
    real = os.path.realpath(path)
    with _scan_cache_lock:
        scan = _scan_cache.get(real)
        if scan is None:
            scan = FileScan(real)
            _scan_cache[real] = scan
    scan.refresh()
    return scan
