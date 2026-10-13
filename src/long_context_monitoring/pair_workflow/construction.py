"""Construct one derived attack while preserving native reconciliation order."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence
from long_context_monitoring.neutral_compactor import (
    CompactorClient,
    DEFAULT_BACKEND as DEFAULT_COMPACT_BACKEND,
)
from .models import HonestSource, InlineAction, CompactionRecord, SourceReplayRecord
from .source import _loaded_entries, _write_jsonl, _apply_selected_actions
from .insertion import inject_manual_edits, _validate_manual_edit_pairs
from .reconciliation import (
    replay_native_source_results,
    _validate_no_direct_native_contradictions,
)
from .compaction import rebuild_compactions


def _build_attack(
    spec: dict,
    honest: HonestSource,
    actions: Sequence[InlineAction],
    destination: Path,
    compact_client: CompactorClient | None,
    compact_model: str,
    compact_effort: str | None,
    cache_root: Path,
    max_compact_cost_usd: float,
    compact_backend: str = DEFAULT_COMPACT_BACKEND,
) -> tuple[Path, Path, list[CompactionRecord], list[SourceReplayRecord]]:
    entries = inject_manual_edits(
        _loaded_entries(honest.transcript), spec, actions, honest.workspace
    )
    _validate_manual_edit_pairs(entries, actions)
    entries, source_replays = replay_native_source_results(entries)
    _validate_no_direct_native_contradictions(entries)
    entries, compactions = rebuild_compactions(
        entries,
        spec,
        compact_client,
        compact_model,
        compact_effort,
        cache_root,
        max_compact_cost_usd,
        backend=compact_backend,
    )
    _validate_manual_edit_pairs(entries, actions)
    transcript = destination / "transcript" / "constructed.jsonl"
    workspace = destination / "workspace"
    _write_jsonl(transcript, entries)
    _apply_selected_actions(honest.workspace, workspace, actions)
    return transcript, workspace, compactions, source_replays
