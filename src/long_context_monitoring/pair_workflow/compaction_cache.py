"""Immutable neutral-summary caching with provider identity and a run-wide cost gate."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence
from long_context_monitoring.attack_lab.transcript import compact_summary_entry, preserved_entries
from long_context_monitoring.neutral_compactor import (
    COMPACTION_PROMPT_SHA256,
    MAX_OUTPUT_TOKENS,
    CompactorClient,
    ConversationMessage,
    compact,
    estimate_compaction_cost_usd,
    read_claude_messages,
    render_request,
    select_for_compaction,
)
from long_context_monitoring.openrouter import default_provider_order
from .models import CompactionCacheMiss, ManualPairError
from .source import _sha256_file


def _conversation_message(raw: dict) -> ConversationMessage:
    return ConversationMessage(
        type=str(raw["type"]),
        content=raw["content"],
        uuid=raw.get("uuid"),
        message_id=raw.get("message_id"),
        virtual=raw.get("virtual") is True,
        resumed_from_incomplete_thinking=(
            raw.get("resumed_from_incomplete_thinking") is True
        ),
    )


def _cache_path(cache_root: Path, key: str) -> Path:
    return cache_root / key[:2] / f"{key}.json"


def _load_cached_compaction(
    path: Path,
) -> tuple[str, tuple[ConversationMessage, ...], dict] | None:
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        preserved = tuple(_conversation_message(item) for item in raw["preserved"])
        return raw["parsed_summary"], preserved, raw
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        return None


def _store_cached_compaction(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _replacement_entries(
    parsed_summary: str,
    preserved: Sequence[ConversationMessage],
    cache_key: str,
) -> list[dict]:
    """Build stable replacement rows so later prefix hashes can hit the cache."""

    replacement = [
        compact_summary_entry(parsed_summary),
        *preserved_entries(preserved),
    ]
    for index, entry in enumerate(replacement):
        if index == 0 or not entry.get("uuid"):
            entry["uuid"] = f"manual-compact-{cache_key[:24]}-{index}"
        entry.pop("timestamp", None)
    return replacement


@dataclass
class _Summary:
    """Replacement rows and the exact cache provenance used for one boundary."""

    replacement: list[dict]
    payload: dict
    parsed_summary: str
    prefix_sha256: str
    cache_hit: bool


@dataclass
class _CompactionCache:
    """Share one conservative budget preflight across a reconstruction run."""

    client: CompactorClient | None
    model: str
    reasoning_effort: str | None
    cache_root: Path
    max_cost_usd: float
    backend: str
    backend_name: str
    endpoint: str
    boundaries: list[int]
    original_tokens: int
    budget_preflight_done: bool = False

    def for_prefix(self, prefix: Path, after_turn: int, position: int) -> _Summary:
        """Reuse an exact identity or construct and persist its neutral summary."""
        prefix_sha256 = _sha256_file(prefix)
        requested_provider = (
            default_provider_order(self.model, None)
            if self.backend == "openrouter"
            else ()
        )
        cache_key = hashlib.sha256(
            (
                f"{self.backend_name}\0{self.endpoint}\0{self.model}\0"
                f"{self.reasoning_effort or ''}\0{COMPACTION_PROMPT_SHA256}\0"
                f"{prefix_sha256}\0{','.join(requested_provider)}"
            ).encode("utf-8")
        ).hexdigest()
        cache_path = _cache_path(self.cache_root, cache_key)
        cached = _load_cached_compaction(cache_path)
        if cached is None:
            if self.client is None:
                raise CompactionCacheMiss(
                    f"neutral summary after turn {after_turn} is not cached"
                )
            self._preflight_budget(position)
            cache_payload, replacement = self._generate(prefix, cache_key, cache_path)
            parsed_summary = cache_payload["parsed_summary"]
        else:
            parsed_summary, preserved, cache_payload = cached
            raw_replacement = cache_payload.get("replacement")
            if isinstance(raw_replacement, list) and all(
                isinstance(item, dict) for item in raw_replacement
            ):
                replacement = [dict(item) for item in raw_replacement]
            else:
                replacement = _replacement_entries(parsed_summary, preserved, cache_key)
        return _Summary(
            replacement,
            cache_payload,
            parsed_summary,
            prefix_sha256,
            cached is not None,
        )

    def _preflight_budget(self, position: int) -> None:
        """Check all possible remaining misses before the first paid call."""
        if self.budget_preflight_done:
            return
        remaining_calls = len(self.boundaries) - position
        worst_input_tokens = (
            self.original_tokens + len(self.boundaries) * MAX_OUTPUT_TOKENS
        )
        remaining_estimate = remaining_calls * estimate_compaction_cost_usd(
            self.backend,
            self.model,
            worst_input_tokens,
            MAX_OUTPUT_TOKENS,
        )
        if remaining_estimate > self.max_cost_usd:
            raise ManualPairError(
                "neutral compaction estimate "
                f"${remaining_estimate:.4f} exceeds "
                f"--max-compact-cost-usd ${self.max_cost_usd:.4f}"
            )
        self.budget_preflight_done = True

    def _generate(
        self, prefix: Path, cache_key: str, cache_path: Path
    ) -> tuple[dict, list[dict]]:
        """Create the original cache schema and stable replacement-row identities."""
        # Preserve the preliminary request rendering and its possible failures,
        # even though compact() renders its own request afterward.
        messages = read_claude_messages(prefix)
        _request = render_request(select_for_compaction(messages))
        result = compact(
            messages,
            prefix,
            self.client,
            self.model,
            reasoning_effort=self.reasoning_effort,
            backend=self.backend,
        )
        parsed_summary = result.parsed_summary
        preserved = result.preserved
        cache_payload = {
            "parsed_summary": parsed_summary,
            "preserved": [asdict(message) for message in preserved],
            "compaction_backend": result.compaction_backend,
            "compaction_endpoint": result.compaction_endpoint,
            "requested_model": result.requested_model,
            "model": result.model,
            "response_id": result.response_id,
            "reasoning_effort": result.reasoning_effort,
            "requested_provider": list(result.requested_provider),
            "provider": result.provider,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "cached_input_tokens": result.cached_input_tokens,
            "estimated_cost_usd": result.estimated_cost_usd,
            "request_sha256": result.request_sha256,
            "result_sha256": result.result_sha256,
            "response_status": result.response_status,
            "incomplete_details": result.incomplete_details,
        }
        replacement = _replacement_entries(parsed_summary, preserved, cache_key)
        cache_payload["replacement"] = replacement
        _store_cached_compaction(cache_path, cache_payload)
        return cache_payload, replacement
