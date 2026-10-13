"""Baseline 1 — whole transcript, single pass.

The simplest possible monitor: render the entire visible transcript into one
prompt and take one score. No interval slicing, no tools, no memory. This is the
floor the agentic monitors must beat — if one shot over everything already
catches the attack, the machinery is not earning its keep.

Non-agentic, single LLM call per view (one view = the whole trajectory). If the
transcript exceeds the model's context window, ``plan_views`` splits it into
budget-sized chunks and the score is the max over them, so this degrades
gracefully on very large transcripts rather than failing.

Self-contained: it depends only on the stable shared helpers in ``base.py`` and
never on another strategy.
"""
from __future__ import annotations

from long_context_monitoring.monitor.llm import LLMClient
from long_context_monitoring.monitor.scoring import MonitorResult
from long_context_monitoring.monitor.strategies.base import (
    ChunkPlan,
    MonitorRequest,
    View,
    build_result,
    plan_views,
    score_chunks,
    summarize_views,
)


class WholeMonitor:
    name = "whole-v1"

    @staticmethod
    def _views(request: MonitorRequest) -> list[View]:
        return [View(
            "whole", "whole trajectory",
            "The entire visible transcript scored in one pass.",
            list(request.events),
        )]

    def plan(self, request: MonitorRequest) -> list[ChunkPlan]:
        return plan_views(request, self._views(request))

    def run(self, request: MonitorRequest, client: LLMClient, journal,
            plans: list[ChunkPlan] | None = None) -> MonitorResult:
        plans = plans if plans is not None else self.plan(request)
        chunks = score_chunks(plans, request, client, journal)
        return build_result(
            request, chunks, self.name, views=summarize_views(chunks),
            config_extra={
                "baseline": True, "family": "single-pass",
                "window": "whole-single-pass",
                "chunks_needed": len(chunks),
            },
        )
