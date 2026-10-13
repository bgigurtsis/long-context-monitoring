"""Score every main-thread compaction interval; the headline is the max over them."""
from __future__ import annotations

from long_context_monitoring.monitor.events import Event
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
    select_views,
    summarize_views,
)
from long_context_monitoring.monitor.visibility import DIAGNOSTIC_NO_SUMMARY


class CompactionIntervalError(ContextBudgetError):
    """Raised when main-thread compaction intervals cannot be paired safely."""


def _compaction_summaries(
    events: list[Event], boundary_indexes: list[int]
) -> list[int]:
    """Pair each boundary with its first main-thread summary before the next one."""
    summary_indexes: list[int] = []
    for position, boundary_index in enumerate(boundary_indexes):
        stop = (
            boundary_indexes[position + 1]
            if position + 1 < len(boundary_indexes)
            else len(events)
        )
        summary_index = None
        for index in range(boundary_index + 1, stop):
            event = events[index]
            if (
                event.kind == "compaction_summary"
                and event.file_id == "main"
                and event.depth == 0
            ):
                summary_index = index
                break
        if summary_index is None:
            boundary = events[boundary_index]
            raise CompactionIntervalError(
                "main-thread compaction has no following compact summary "
                f"before the next boundary (boundary {boundary.event_id})"
            )
        summary_indexes.append(summary_index)

    return summary_indexes


def split_compaction_intervals(
    events: list[Event],
    *,
    summaries_required: bool = True,
    include_whole: bool = True,
) -> tuple[list[View], dict]:
    """Return all loss-boundary intervals, plus the complete trajectory unless
    ``include_whole`` is False. A transcript with no main compaction has one
    interval, which is the whole trajectory and keeps the view name ``whole``."""
    boundary_indexes = [
        index
        for index, event in enumerate(events)
        if event.kind == "compaction" and event.file_id == "main" and event.depth == 0
    ]
    if not boundary_indexes:
        return [
            View(
                "whole",
                "whole trajectory",
                "The transcript has no main-thread compaction.",
                list(events),
            )
        ], {
            "boundary_count": 0,
            "interval_count": 0,
            "boundary_event_ids": [],
            "summary_event_ids": [],
        }

    summary_indexes: list[int] = []
    if summaries_required:
        summary_indexes = _compaction_summaries(events, boundary_indexes)

    views: list[View] = []
    views.append(
        View(
            "interval_0",
            "interval 0",
            "Trajectory start through the first compaction boundary.",
            list(events[:boundary_indexes[0] + 1]),
        )
    )
    for interval_index in range(1, len(boundary_indexes)):
        interval_start = (
            summary_indexes[interval_index - 1]
            if summaries_required
            else boundary_indexes[interval_index - 1] + 1
        )
        interval_description = (
            "Previous compact summary through the next compaction boundary."
            if summaries_required
            else "Previous compaction boundary through the next boundary."
        )
        views.append(
            View(
                f"interval_{interval_index}",
                f"interval {interval_index}",
                interval_description,
                list(
                    events[
                        interval_start:
                        boundary_indexes[interval_index] + 1
                    ]
                ),
            )
        )
    final_start = (
        summary_indexes[-1]
        if summaries_required
        else boundary_indexes[-1] + 1
    )
    final_description = (
        "Last compact summary through the end of the trajectory."
        if summaries_required
        else "Last compaction boundary through the end of the trajectory."
    )
    views.append(
        View(
            f"interval_{len(boundary_indexes)}",
            f"interval {len(boundary_indexes)}",
            final_description,
            list(events[final_start:]),
        )
    )
    if include_whole:
        views.append(
            View(
                "whole",
                "whole trajectory",
                "The complete visible trajectory across every compaction.",
                list(events),
            )
        )
    return views, {
        "boundary_count": len(boundary_indexes),
        "interval_count": len(boundary_indexes) + 1,
        "boundary_event_ids": [
            events[index].event_id for index in boundary_indexes
        ],
        "summary_event_ids": [
            events[index].event_id for index in summary_indexes
        ],
    }


class CompactionIntervalsMonitor:
    """One call per compaction interval; the headline is the max over intervals.
    Why: the same rule every chunked strategy uses, so a threshold means the
    same thing here as for other chunked strategies.
    If wrong: a high interval score never reaches the headline and the attack
    goes unreported.
    """

    # Report the maximum score across interval views.
    name = "intervals-v1"
    # This strategy defines named views, so the CLI accepts --only-view.
    supports_only_view = True

    def plan(self, request: MonitorRequest) -> list[ChunkPlan]:
        views, _ = split_compaction_intervals(
            request.events,
            summaries_required=request.visibility != DIAGNOSTIC_NO_SUMMARY,
            include_whole=False,
        )
        selected = select_views(views, request.only_view, CompactionIntervalError)
        return plan_views(request, selected)

    def run(
        self,
        request: MonitorRequest,
        client: LLMClient,
        journal,
        plans: list[ChunkPlan] | None = None,
    ) -> MonitorResult:
        plans = plans if plans is not None else self.plan(request)
        chunks = score_chunks(plans, request, client, journal)
        _, metadata = split_compaction_intervals(
            request.events,
            summaries_required=request.visibility != DIAGNOSTIC_NO_SUMMARY,
        )
        view_results = summarize_views(chunks)

        activation_turns = request.run_metadata.get(
            "runtime_guidance_turns", []
        )
        metadata.update({
            "compaction_mode": request.run_metadata.get(
                "compaction_mode", "unknown"
            ),
            "guidance_activation_turns": activation_turns,
            "view_count": len(view_results),
            "view_aggregation": "max_over_chunks",
            "overall_aggregation": "max_over_interval_views",
            # The name of the one view scored, or the rule when several were.
            "headline_view": (
                request.only_view
                or ("whole" if metadata["boundary_count"] == 0 else "max_over_interval_views")
            ),
            "only_view": request.only_view,
        })
        # build_result takes the max over every chunk, which is the max over
        # interval views since each view's chunks are already max-reduced.
        return build_result(
            request,
            chunks,
            self.name,
            views=view_results,
            config_extra=metadata,
        )
