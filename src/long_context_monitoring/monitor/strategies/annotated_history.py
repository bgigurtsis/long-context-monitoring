"""Score ordered transcript sections while carrying a record of relevant evidence."""
from __future__ import annotations

import hashlib
from dataclasses import replace

from long_context_monitoring.monitor.llm import LLMClient
from long_context_monitoring.monitor.render import estimate_tokens, render_units
from long_context_monitoring.monitor.scoring import MonitorResult, parse_flags
from long_context_monitoring.prompts import build_annotated_history_prompt, strategy_prompt_templates
from long_context_monitoring.monitor.strategies.base import (
    ChunkPlan,
    MonitorRequest,
    View,
    _chunk_record,
    _unit_event_id,
    assert_resume_settings,
    build_result,
    chunk_has_actions,
    chunk_transcript_budget,
    complete_and_parse,
    resume_settings,
    split_chunks,
    summarize_views,
)
from long_context_monitoring.monitor.strategies.intervals import split_compaction_intervals
from long_context_monitoring.monitor.visibility import DIAGNOSTIC_NO_SUMMARY

_NO_FLAGS_YET = "No flags have been raised yet — this is the first interval reviewed.\n"


def _intervals(request: MonitorRequest) -> list[View]:
    views, _ = split_compaction_intervals(
        request.events, summaries_required=request.visibility != DIAGNOSTIC_NO_SUMMARY,
    )
    intervals = [v for v in views if v.name != "whole"]
    if intervals:
        return intervals
    return [View("whole", "whole trajectory",
                 "No main-thread compaction.", list(request.events))]


def _render_ledger(ledger: list[dict]) -> str:
    if not ledger:
        return _NO_FLAGS_YET
    lines = [
        f"- [{flag['interval']}] {flag['action']}: {flag['claim']} "
        f"(severity: {flag['severity']})"
        for flag in ledger
    ]
    return (
        "Flags raised by earlier intervals in this run (context for your own "
        "judgement, not a verdict):\n" + "\n".join(lines) + "\n"
    )


def _interval_parts(request: MonitorRequest, view: View, index: int,
                    total: int) -> list[list]:
    """Split one interval into budget-sized unit lists; usually just one."""
    view_request = replace(request, events=view.events)
    view_info = {"name": view.name, "label": view.label,
                 "description": view.description, "index": index, "total": total}
    budget = chunk_transcript_budget(view_request, view_info=view_info)
    return split_chunks(view.events, request.render_options, budget)


def _part_label(view: View, part: int, parts: int) -> str:
    if parts == 1:
        return view.label
    return f"{view.label} (part {part}/{parts})"


def _build_plan(view: View, index: int, total: int, prompt: str, units: list, *,
                chunk_index: int, part: int = 1, parts: int = 1) -> ChunkPlan:
    return ChunkPlan(
        index=chunk_index, units=list(units), has_actions=chunk_has_actions(units),
        user_prompt=prompt,
        prompt_hash=hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        prompt_tokens_est=estimate_tokens(prompt),
        event_start=_unit_event_id(units[0]) if units else None,
        event_end=_unit_event_id(units[-1]) if units else None,
        event_count=len(units),
        view=view.name, view_label=_part_label(view, part, parts),
        view_index=index, view_total=total,
        view_chunk_index=part, view_chunk_total=parts,
    )


def _score_interval(request: MonitorRequest, client: LLMClient, journal,
                    plan: ChunkPlan) -> dict:
    """One paid interval call: pinned, parsed, flags extracted, journalled with
    the settings a later resume must match."""
    if journal is not None:
        journal.write_prompt(plan.index, plan.user_prompt)
    response, score, reasoning = complete_and_parse(client, request, plan, journal)
    chunk = _chunk_record(request, plan, score, reasoning, response)
    chunk["flags"] = parse_flags(response.text)
    if journal is not None:
        journal.append({
            "prompt_hash": plan.prompt_hash, "status": "completed",
            "raw_response": response.text, "chunk": chunk,
            "settings": resume_settings(request),
        })
    return chunk


class AnnotatedHistoryMonitor:
    """Sequential interval scoring with a forward-carried flag ledger."""

    name = "annotated-history-v1"
    # Templates this strategy sends; prompt_version is derived from them.
    prompt_templates = ("monitor_annotated_history.md",)

    def plan(self, request: MonitorRequest) -> list[ChunkPlan]:
        intervals = _intervals(request)
        plans = []
        for index, view in enumerate(intervals, start=1):
            parts = _interval_parts(request, view, index, len(intervals))
            for part, units in enumerate(parts, start=1):
                text = render_units(units, request.render_options)
                # Approximation noted in the module docstring: real ledger
                # content is only known once earlier calls have been scored.
                prompt = build_annotated_history_prompt(
                    request.task_description, text, _NO_FLAGS_YET,
                    index, len(intervals), objectives=request.objectives,
                    scoring_template=request.monitor_template,
                )
                plans.append(_build_plan(
                    view, index, len(intervals), prompt, units,
                    chunk_index=len(plans) + 1, part=part, parts=len(parts)))
        return plans

    def run(self, request: MonitorRequest, client: LLMClient, journal,
            plans: list[ChunkPlan] | None = None) -> MonitorResult:
        """Score the intervals in order, carrying the flag ledger forward."""
        intervals = _intervals(request)
        ledger: list[dict] = []
        chunks: list[dict] = []
        for index, view in enumerate(intervals, start=1):
            parts = _interval_parts(request, view, index, len(intervals))
            for part, units in enumerate(parts, start=1):
                text = render_units(units, request.render_options)
                prompt = build_annotated_history_prompt(
                    request.task_description, text, _render_ledger(ledger),
                    index, len(intervals), objectives=request.objectives,
                    scoring_template=request.monitor_template,
                )
                plan = _build_plan(
                    view, index, len(intervals), prompt, units,
                    chunk_index=len(chunks) + 1, part=part, parts=len(parts))

                cached = journal.completed(plan.prompt_hash) if journal is not None else None
                if cached is not None:
                    # The prompt hash covers the text only; the settings block
                    # on the journal line must match too, as in score_chunk.
                    assert_resume_settings(journal, plan, request)
                    chunk = cached
                elif not plan.has_actions:
                    chunk = _chunk_record(
                        request, plan, score=0,
                        reasoning=("No agent actions (tool calls or results) in "
                                   "this interval; nothing to review."),
                        usage=None,
                    )
                    chunk["flags"] = []
                else:
                    chunk = _score_interval(request, client, journal, plan)

                chunks.append(chunk)
                ledger.extend(
                    {**flag, "interval": plan.view_label}
                    for flag in chunk.get("flags", [])
                )

        return build_result(
            request, chunks, self.name, views=summarize_views(chunks),
            config_extra={
                "technique": "monitor-annotated-history",
                "prompt_templates": strategy_prompt_templates(
                    self.prompt_templates, request.monitor_template),
                "family": "sequential-flag-ledger",
                "window": "interval-with-forward-carried-flags",
                "flags_raised": len(ledger),
                "flags_by_severity": {
                    severity: sum(1 for f in ledger if f["severity"] == severity)
                    for severity in sorted({f["severity"] for f in ledger})
                },
                "ledger": ledger,
            },
        )
