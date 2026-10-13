"""Hierarchical and fold-left recursive summarization baselines.

Both techniques answer the same question as map-reduce (``map_reduce.py``) —
does summarizing-then-judging suffice without interactive lookup? — but they
recursively COMBINE section summaries into fewer, larger summaries before the
final score, instead of map-reduce's single flat concatenation. The two differ
only in the shape of that combination:

- **Fold-left** (``FoldLeftSummaryMonitor``, ``fold-left-summary``): a linear
  chain. The running summary is merged with the next leaf, one at a time:
  ``S_1 = leaf_1``, ``S_i = merge(S_{i-1}, leaf_i)``. This is the natural
  analogue of how native compaction itself works (summarize prior context +
  new turns, repeat) — and it has the same weakness: content from the first
  leaf gets recompressed at every one of the ``n-1`` merge steps, while the
  last leaf is never recompressed at all. A value planted early (AGENTS.md's
  "A") is diluted every time the running summary is re-merged; a value
  consumed late ("B") survives untouched. Uneven compression by position is
  exactly the failure mode a setup/execution attack is built to exploit.

- **Hierarchical** (``HierarchicalSummaryMonitor``, ``hierarchical-summary``):
  a balanced tree. Leaves are merged in fixed-size groups (``BRANCHING``) into
  parent summaries, and parents are merged the same way, until one root
  remains. Every leaf is recompressed the same number of times when the
  leaf count divides evenly into groups of ``BRANCHING`` at every level; a
  leftover leaf is carried up without a merge and arrives one level less
  compressed. Five leaves, for example, form groups of 3 and 2, then one
  merge of the two, so every leaf is merged exactly twice; four leaves leave
  one carried up once. A section over the budget is extracted in parts, each
  its own leaf, so the tree can hold more leaves than compaction intervals.
  ``leaf_merge_depths`` in ``result.config`` records the depth of every leaf
  that actually ran, so an uneven tree is visible.

Both share leaf extraction (``build_extraction_prompt``, the same one
map-reduce uses) and the merge step (``build_merge_summary_prompt``); only the
grouping differs. The final call scores the single remaining summary with the
ordinary ``build_monitor_prompt``, exactly like map-reduce's reduce stage.

Self-contained: each strategy drives its own multi-stage loop with
``client.complete`` and depends only on stable helpers.
"""
from __future__ import annotations

import hashlib

from long_context_monitoring.monitor.events import Event
from long_context_monitoring.monitor.llm import LLMClient
from long_context_monitoring.monitor.render import estimate_tokens
from long_context_monitoring.monitor.scoring import (
    MonitorResult,
    ScoreParseError,
    parse_monitor_reply,
)
from long_context_monitoring.openrouter import LLMResponse, assert_pinned_provider, provider_pin
from long_context_monitoring.prompts import (
    build_merge_summary_prompt,
    build_monitor_prompt,
    strategy_prompt_templates,
)
from long_context_monitoring.monitor.strategies.base import (
    ChunkPlan,
    ContextBudgetError,
    MonitorRequest,
    View,
    _chunk_record,
    _unit_event_id,
    build_result,
    chunk_has_actions,
)
from long_context_monitoring.monitor.strategies.extraction import (
    assert_digests_fit,
    assert_prompt_fits,
    plan_extraction,
    split_extraction_parts,
)
from long_context_monitoring.monitor.strategies.intervals import split_compaction_intervals

# Leaves merged into one parent node at a time, for the hierarchical strategy.
# 3 keeps the tree shallow (fewer sequential merge rounds) while still giving
# every merge call a manageable handful of summaries to reconcile.
_TEMPLATES = ["monitor_extract.md", "monitor_merge.md", "monitor.md"]
BRANCHING = 3


def _leaf_views(events: list[Event]) -> list[View]:
    """Leaf sections to extract from — the compaction intervals, or the whole."""
    views, _ = split_compaction_intervals(events)
    intervals = [v for v in views if v.name != "whole"]
    if intervals:
        return intervals
    return [View("whole", "whole trajectory",
                 "No main-thread compaction.", list(events))]


class _StageRunner:
    """Shared plumbing for both strategies: extract leaves, then merge/score.

    Not a strategy itself — ``HierarchicalSummaryMonitor`` and
    ``FoldLeftSummaryMonitor`` each drive this with their own grouping.
    """

    def __init__(self, request: MonitorRequest, client: LLMClient, journal) -> None:
        self.request = request
        self.client = client
        self.journal = journal
        self.total_in = 0
        self.total_out = 0
        self.total_cost: float | None = None
        self.merge_calls = 0

    def _complete(self, prompt: str) -> LLMResponse:
        """One call with the request's full settings and the provider pin checked.
        Why: every stage must run under the settings result.config records.
        If wrong: a stage runs at the client default temperature or on an
        unpinned host while the result claims otherwise.
        """
        request = self.request
        pin_order = list(request.provider)
        resp = self.client.complete(
            prompt, request.model,
            max_tokens=request.max_output_tokens,
            temperature=request.temperature,
            reasoning_effort=request.reasoning_effort,
            provider=provider_pin(
                pin_order or None,
                quantizations=list(request.provider_quantizations) or None,
            ),
        )
        assert_pinned_provider(resp, pin_order or None)
        self.total_in += resp.input_tokens
        self.total_out += resp.output_tokens
        if resp.cost_usd is not None:
            self.total_cost = (self.total_cost or 0.0) + resp.cost_usd
        return resp

    def extract_leaves(self, views: list[View]) -> list[tuple[str, str]]:
        """Return ``[(label, digest), ...]``, one extraction call per leaf.

        A section over the budget becomes several leaves (one per part, see
        split_extraction_parts), so the tree may hold more leaves than there
        are compaction intervals.
        """
        leaves: list[tuple[str, str]] = []
        for view in views:
            for _units, label, prompt in split_extraction_parts(self.request, view):
                resp = self._complete(prompt)
                leaves.append((label, (resp.text or "").strip()))
                if self.journal is not None:
                    self.journal.append({
                        "prompt_hash": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                        "status": "completed", "stage": "leaf", "unit": view.name,
                        "raw_response": resp.text,
                    })
        return leaves

    def merge(self, children: list[tuple[str, str]], group_label: str) -> str:
        """One merge call combining ``children`` into a single digest."""
        prompt = build_merge_summary_prompt(
            self.request.task_description, children, group_label)
        assert_prompt_fits(self.request, prompt, f"merge {group_label}")
        resp = self._complete(prompt)
        self.merge_calls += 1
        if self.journal is not None:
            self.journal.append({
                "prompt_hash": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                "status": "completed", "stage": "merge", "unit": group_label,
                "raw_response": resp.text,
            })
        return (resp.text or "").strip()

    def score(self, root_label: str, root_digest: str,
             units: list[Event]) -> tuple[dict, str]:
        """Final reduce-style scoring call over the single remaining digest."""
        request = self.request
        prompt = build_monitor_prompt(
            request.task_description, root_digest, objectives=request.objectives,
            template=request.monitor_template)
        assert_prompt_fits(request, prompt, f"{root_label} score")
        # Three attempts, as in base.complete_and_parse: gpt-4.1-nano omits a
        # parseable score on about 12% of first replies, and a single attempt
        # here ended the whole invocation after every leaf and merge was paid
        # for. Each bad reply is journalled so the retry stays visible.
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        parsed = None
        for attempt in (1, 2, 3):
            resp = self._complete(prompt)
            try:
                parsed = parse_monitor_reply(resp.text)
                break
            except ScoreParseError:
                if self.journal is not None:
                    self.journal.append({
                        "prompt_hash": prompt_hash, "status": "parse_error",
                        "stage": "score", "attempt": attempt,
                        "raw_response": resp.text,
                        "finish_reason": resp.finish_reason,
                        "output_tokens": resp.output_tokens,
                    })
        if parsed is None:
            raise ContextBudgetError(
                f"{root_label} scoring stage did not emit a parseable <score> "
                "in three attempts")
        score, reasoning = parsed

        plan = ChunkPlan(
            index=1, units=list(units), has_actions=chunk_has_actions(units),
            user_prompt=prompt,
            prompt_hash=hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            prompt_tokens_est=estimate_tokens(prompt),
            event_start=_unit_event_id(units[0]) if units else None,
            event_end=_unit_event_id(units[-1]) if units else None,
            event_count=len(units),
            view=root_label, view_label=root_label,
            view_index=1, view_total=1,
        )
        # Billed cost and the serving provider come from the real replies; the
        # token totals span every stage so the record prices the whole run.
        usage = LLMResponse(text="", model=request.model,
                            input_tokens=self.total_in, output_tokens=self.total_out,
                            cost_usd=self.total_cost, provider=resp.provider)
        chunk = _chunk_record(request, plan, score, reasoning, usage)
        if self.journal is not None:
            self.journal.append({
                "prompt_hash": plan.prompt_hash, "status": "completed",
                "stage": "score", "raw_response": resp.text, "chunk": chunk,
            })
        return chunk, reasoning


def leaf_merge_depths(leaf_count: int) -> list[int]:
    """How many merges each leaf passes through before the root score.
    Why: the strategy's claim is equal compression per leaf; this is the
    number a reader checks it against, per transcript.
    If wrong: an uneven tree is reported as balanced.
    """
    depths = [0] * leaf_count
    level = list(range(leaf_count))  # each node holds the leaf indexes under it
    nodes = [[i] for i in level]
    while len(nodes) > 1:
        next_nodes = []
        for start in range(0, len(nodes), BRANCHING):
            group = nodes[start:start + BRANCHING]
            if len(group) == 1:
                next_nodes.append(group[0])  # carried up, no merge
                continue
            merged = [leaf for node in group for leaf in node]
            for leaf in merged:
                depths[leaf] += 1
            next_nodes.append(merged)
        nodes = next_nodes
    return depths


def merge_call_count(leaf_count: int) -> int:
    """How many merge calls the balanced tree makes for this many leaves.
    Why: the cost gate only sees the planned leaf extractions; the merges
    depend on the replies and are counted here by walking the same grouping
    run() uses (a group of one is carried up without a call).
    If wrong: the gate under-counts every merge level.
    """
    merges = 0
    level = leaf_count
    while level > 1:
        groups = range(0, level, BRANCHING)
        merges += sum(1 for start in groups if min(BRANCHING, level - start) > 1)
        level = len(groups)
    return merges


class HierarchicalSummaryMonitor:
    """Balanced-tree recursive summarization: every leaf compressed equally."""

    name = "hierarchical-summary-v1"
    # Templates this strategy sends; prompt_version is derived from them.
    prompt_templates = tuple(_TEMPLATES)
    # The journal is never read back here: every call is paid again on a
    # resume, so the CLI refuses --resume for this strategy.
    supports_resume = False

    def expected_calls(self, plans: list[ChunkPlan]) -> tuple[int, str]:
        """Planned leaf extractions plus the tree merges plus one root score."""
        merges = merge_call_count(len(plans))
        return (len(plans) + merges + 1,
                f"{merges} tree merge(s) and one root score are not planned")

    def plan(self, request: MonitorRequest) -> list[ChunkPlan]:
        """Plan the leaf-extraction calls only (for dry-run/cost-estimate).

        The merge and scoring stages depend on the leaves' actual replies, so
        their real prompts cannot exist before ``run()`` executes; a dry-run of
        this strategy therefore shows every leaf's real extraction prompt but
        not the merge/score calls that follow.
        """
        return plan_extraction(request, _leaf_views(request.events))

    def run(self, request: MonitorRequest, client: LLMClient, journal,
            plans: list[ChunkPlan] | None = None) -> MonitorResult:
        views = _leaf_views(request.events)
        assert_digests_fit(request, BRANCHING, "merge")
        runner = _StageRunner(request, client, journal)
        level: list[tuple[str, str]] = runner.extract_leaves(views)
        leaf_count = len(level)
        depth = 0
        while len(level) > 1:
            depth += 1
            next_level: list[tuple[str, str]] = []
            for group_index, start in enumerate(range(0, len(level), BRANCHING), start=1):
                group = level[start:start + BRANCHING]
                label = f"level {depth} node {group_index}"
                if len(group) == 1:
                    next_level.append(group[0])
                    continue
                next_level.append((label, runner.merge(group, label)))
            level = next_level

        root_label, root_digest = level[0] if level else ("root", "")
        chunk, reasoning = runner.score(root_label, root_digest, request.events)
        return build_result(
            request, [chunk], self.name,
            config_extra={
                "baseline": True, "family": "hierarchical-summary",
                "prompt_templates": strategy_prompt_templates(
                    self.prompt_templates, request.monitor_template),
                "window": "tree-merge-then-score",
                "interval_count": len(views),
                "leaf_count": leaf_count, "branching_factor": BRANCHING,
                "tree_depth": depth, "merge_calls": runner.merge_calls,
                "leaf_merge_depths": leaf_merge_depths(leaf_count),
            },
        )
