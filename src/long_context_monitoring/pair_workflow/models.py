"""Shared value records, failures, and pinned identities for manual-pair stages."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from long_context_monitoring.attack_lab.edits import FunctionEdit


class ManualPairError(RuntimeError):
    """The honest source or insertion contract is invalid."""


class CompactionCacheMiss(ManualPairError):
    """An exact prompt preview needs a neutral summary not yet in the cache."""


@dataclass(frozen=True)
class InlineAction:
    """One exact edit and its transcript insertion point."""

    turn: int
    when: str
    edit: FunctionEdit


@dataclass(frozen=True)
class HonestSource:
    """The native transcript and archived workspace reused by the lab."""

    arm: Path
    transcript: Path
    workspace: Path


@dataclass(frozen=True)
class CompactionRecord:
    """One regenerated summary and its cache/provenance identity."""

    after_turn: int
    prefix_sha256: str
    request_sha256: str
    result_sha256: str
    parsed_summary: str
    compaction_backend: str
    compaction_endpoint: str
    requested_model: str
    observed_model: str
    response_id: str | None
    reasoning_effort: str | None
    requested_provider: tuple[str, ...]
    provider: str | None
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int
    estimated_cost_usd: float
    response_status: str | None
    incomplete_details: dict[str, object] | None
    cache_hit: bool


@dataclass(frozen=True)
class SourceReplayRecord:
    """One copied tool result updated for the derived workspace state."""

    entry_uuid: str
    tool_use_id: str
    tool_name: str
    path: str
    replacement_count: int
    before_sha256: str
    after_sha256: str
