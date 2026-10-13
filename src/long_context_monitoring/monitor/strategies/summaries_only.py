"""Baseline 2 — compaction summaries only.

Score using ONLY the post-compaction summaries — the context the agent itself
carried forward past each seam — and nothing else. This is a cheap floor: it
measures how much of the attack survives into the summaries. If a fragmented
attack hides in the raw tool calls that the summary glossed over, this baseline
is blind to it by construction; if the summary mentions the key value, it will
catch it for almost no tokens.

Non-agentic, single LLM call. Falls back to the whole transcript when the run has
no compaction summaries (nothing to score otherwise).

Self-contained: depends only on the stable shared helpers in ``base.py``.
"""
from __future__ import annotations

from long_context_monitoring.monitor.events import EMPTY_COMPACTION_SUMMARY_TEXT
from long_context_monitoring.monitor.llm import LLMClient
from long_context_monitoring.monitor.scoring import MonitorResult
from long_context_monitoring.monitor.strategies.base import (
    ChunkPlan,
    ContextBudgetError,
    MonitorRequest,
    View,
    build_result,
    plan_views,
    score_chunks,
    summarize_views,
)


class SummariesOnlyMonitor:
    name = "summaries-only-v1"

    @staticmethod
    def _views(request: MonitorRequest) -> list[View]:
        summaries = [e for e in request.events if e.kind == "compaction_summary"]
        if summaries and all(
            e.text == EMPTY_COMPACTION_SUMMARY_TEXT for e in summaries
        ):
            raise ContextBudgetError(
                f"all {len(summaries)} compaction summaries are empty in the "
                "native rollout; summaries-only has nothing to score"
            )
        if not summaries:
            return [View(
                "whole", "whole trajectory (no summaries)",
                "No compaction summaries in this run; scored the whole transcript.",
                list(request.events),
            )]
        return [View(
            "summaries", "compaction summaries only",
            "Only the post-compaction summaries the agent carried past each seam.",
            summaries,
        )]

    def plan(self, request: MonitorRequest) -> list[ChunkPlan]:
        plans = plan_views(request, self._views(request))
        # Summaries carry no tool calls, so the default no-action skip would
        # score them 0 without a call. The summaries ARE the content to review
        # here, so force a real scoring call.
        for plan in plans:
            plan.has_actions = True
        return plans

    def run(self, request: MonitorRequest, client: LLMClient, journal,
            plans: list[ChunkPlan] | None = None) -> MonitorResult:
        plans = plans if plans is not None else self.plan(request)
        chunks = score_chunks(plans, request, client, journal)
        return build_result(
            request, chunks, self.name, views=summarize_views(chunks),
            config_extra={
                "baseline": True, "family": "single-pass",
                "window": "summaries-only",
            },
        )
