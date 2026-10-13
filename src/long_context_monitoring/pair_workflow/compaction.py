"""Rebuild configured compactions in order without moving registered edit anchors."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from long_context_monitoring.neutral_compactor import CompactorClient, backend_identity
from .models import CompactionRecord, ManualPairError
from .insertion import _host_prompt_index, _boundary_after_prompt
from .native_rows import _is_manual_edit_entry
from .source import _write_jsonl
from .compaction_cache import _CompactionCache, _Summary


def rebuild_compactions(
    entries: list[dict],
    spec: dict,
    client: CompactorClient | None,
    model: str,
    reasoning_effort: str | None,
    cache_root: Path,
    max_cost_usd: float,
    backend: str = "openrouter",
) -> tuple[list[dict], list[CompactionRecord]]:
    """Regenerate every configured compact summary from the edited prefix."""

    updated = list(entries)
    records: list[CompactionRecord] = []
    boundaries = spec["configured_compact_after"]
    original_tokens = max(
        1,
        (len(json.dumps(entries, ensure_ascii=False).encode("utf-8")) + 3) // 4,
    )
    backend_name, endpoint = backend_identity(backend)
    cache = _CompactionCache(
        client,
        model,
        reasoning_effort,
        cache_root,
        max_cost_usd,
        backend,
        backend_name,
        endpoint,
        boundaries,
        original_tokens,
    )
    for position, after_turn in enumerate(boundaries):
        turns = spec["host_turns"]
        prompt_index = _host_prompt_index(updated, turns[after_turn - 1]["prompt"])
        next_prompt_index = _host_prompt_index(updated, turns[after_turn]["prompt"])
        boundary_index = _boundary_after_prompt(
            updated, prompt_index, next_prompt_index
        )
        if boundary_index is None:
            raise ManualPairError(f"no compact boundary follows host turn {after_turn}")
        with tempfile.TemporaryDirectory(prefix="lcm-compact-prefix-") as tmp:
            prefix = Path(tmp) / "prefix.jsonl"
            _write_jsonl(prefix, updated[:boundary_index])
            summary = cache.for_prefix(prefix, after_turn, position)
        # Keep edits anchored immediately before the next host turn. They sit in
        # the same slice as the old honest summary but are not part of the prefix
        # sent to the compactor.
        replacement_end = next_prompt_index
        while replacement_end > boundary_index + 1 and _is_manual_edit_entry(
            updated[replacement_end - 1]
        ):
            replacement_end -= 1
        # Replace the old honest summary and preserved suffix. The next exact host
        # prompt starts the next interval and remains untouched.
        updated[boundary_index + 1 : replacement_end] = summary.replacement
        records.append(_compaction_record(after_turn, summary))
    return updated, records


def _compaction_record(after_turn: int, summary: _Summary) -> CompactionRecord:
    """Decode cached provenance with the same legacy conversions and defaults."""
    return CompactionRecord(
        after_turn=after_turn,
        prefix_sha256=summary.prefix_sha256,
        request_sha256=str(summary.payload["request_sha256"]),
        result_sha256=str(summary.payload["result_sha256"]),
        parsed_summary=summary.parsed_summary,
        compaction_backend=str(summary.payload["compaction_backend"]),
        compaction_endpoint=str(summary.payload["compaction_endpoint"]),
        requested_model=str(summary.payload["requested_model"]),
        observed_model=str(summary.payload["model"]),
        response_id=(
            str(summary.payload["response_id"])
            if summary.payload.get("response_id") is not None
            else None
        ),
        reasoning_effort=(
            str(summary.payload["reasoning_effort"])
            if summary.payload.get("reasoning_effort") is not None
            else None
        ),
        requested_provider=tuple(summary.payload["requested_provider"]),
        provider=(
            str(summary.payload["provider"])
            if summary.payload.get("provider") is not None
            else None
        ),
        input_tokens=int(summary.payload["input_tokens"]),
        output_tokens=int(summary.payload["output_tokens"]),
        cached_input_tokens=int(summary.payload["cached_input_tokens"]),
        estimated_cost_usd=float(summary.payload["estimated_cost_usd"]),
        response_status=(
            str(summary.payload["response_status"])
            if summary.payload.get("response_status") is not None
            else None
        ),
        incomplete_details=(
            dict(summary.payload["incomplete_details"])
            if isinstance(summary.payload.get("incomplete_details"), dict)
            else None
        ),
        cache_hit=summary.cache_hit,
    )
