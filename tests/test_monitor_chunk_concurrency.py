"""Concurrent chunk scoring must change wall-clock time and nothing else.

The risk this pins down: a strategy that overlaps its chunks could reorder
results, interleave journal lines, or double-score a chunk. Any of those would
change a recorded score or corrupt the resume path, so each is checked rather
than assumed.
"""

from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path

from long_context_monitoring.monitor.recording import Journal
from long_context_monitoring.monitor.strategies.base import ChunkPlan, MonitorRequest, score_chunks
from long_context_monitoring.openrouter import LLMResponse


class FakeClient:
    """Scores each chunk with the number embedded in its prompt.

    ``in_flight`` records the high-water mark of overlapping calls, which is
    how the tests below tell a real pool from a serial loop.
    """

    def __init__(self, barrier: threading.Barrier | None = None) -> None:
        self.calls: list[str] = []
        self.lock = threading.Lock()
        self.active = 0
        self.max_in_flight = 0
        self.barrier = barrier

    def complete(self, user: str, model: str, **kwargs: object) -> LLMResponse:
        with self.lock:
            self.calls.append(user)
            self.active += 1
            self.max_in_flight = max(self.max_in_flight, self.active)
        if self.barrier is not None:
            # Blocks until every worker has arrived, so the test fails rather
            # than hangs if the calls are actually serial.
            self.barrier.wait(timeout=5)
        with self.lock:
            self.active -= 1
        score = int(user.rsplit("#", 1)[1])
        return LLMResponse(
            text=f"Score: {score}\nReasoning: chunk {score}",
            model=model, input_tokens=10, output_tokens=5,
        )


def make_plans(count: int) -> list[ChunkPlan]:
    return [
        ChunkPlan(
            index=index, units=[], has_actions=True,
            user_prompt=f"prompt #{index}", prompt_hash=f"hash{index}",
            prompt_tokens_est=10, event_start=None, event_end=None,
            event_count=1, view=f"interval_{index}",
            view_label=f"interval {index}",
        )
        for index in range(1, count + 1)
    ]


def make_request(concurrency: int) -> MonitorRequest:
    return MonitorRequest(
        events=[], transcript_name="t", task_description="d",
        visibility="tools-only", render_options=None,
        model="openai/gpt-4.1-nano", chunk_concurrency=concurrency,
    )


class ScoreChunksTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.journal = Journal(Path(self.tmp.name) / "journal.jsonl")

    def test_results_keep_plan_order_regardless_of_completion_order(self) -> None:
        plans = make_plans(6)
        # The barrier makes every chunk finish at the same moment, so the
        # completion order carries no information about plan order.
        client = FakeClient(barrier=threading.Barrier(6))
        chunks = score_chunks(plans, make_request(6), client, self.journal)
        self.assertEqual([chunk["score"] for chunk in chunks], [1, 2, 3, 4, 5, 6])
        self.assertEqual([chunk["index"] for chunk in chunks], [1, 2, 3, 4, 5, 6])

    def test_chunks_really_do_overlap(self) -> None:
        plans = make_plans(4)
        client = FakeClient(barrier=threading.Barrier(4))
        score_chunks(plans, make_request(4), client, self.journal)
        self.assertEqual(client.max_in_flight, 4)

    def test_concurrency_one_stays_serial(self) -> None:
        plans = make_plans(4)
        client = FakeClient()
        score_chunks(plans, make_request(1), client, self.journal)
        self.assertEqual(client.max_in_flight, 1)

    def test_concurrent_and_serial_agree_exactly(self) -> None:
        """The scores are the product; concurrency must not touch them."""
        plans = make_plans(5)
        serial = score_chunks(plans, make_request(1), FakeClient(), self.journal)

        other = Journal(Path(self.tmp.name) / "journal-2.jsonl")
        parallel = score_chunks(plans, make_request(5), FakeClient(), other)
        self.assertEqual(serial, parallel)

    def test_every_chunk_is_scored_exactly_once(self) -> None:
        plans = make_plans(8)
        client = FakeClient()
        score_chunks(plans, make_request(4), client, self.journal)
        self.assertEqual(sorted(client.calls), sorted(p.user_prompt for p in plans))

    def test_journal_lines_stay_parseable_under_concurrent_writers(self) -> None:
        plans = make_plans(8)
        score_chunks(plans, make_request(8), FakeClient(), self.journal)
        lines = [
            line for line in
            self.journal.path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        records = [json.loads(line) for line in lines]  # raises on interleaving
        completed = [r for r in records if r.get("status") == "completed"]
        self.assertEqual(len(completed), 8)
        self.assertEqual(len({r["prompt_hash"] for r in completed}), 8)

    def test_a_cached_chunk_is_not_rescored(self) -> None:
        """Resume still short-circuits when chunks run concurrently."""
        plans = make_plans(3)
        score_chunks(plans, make_request(3), FakeClient(), self.journal)

        resumed = Journal(self.journal.path)
        client = FakeClient()
        chunks = score_chunks(plans, make_request(3), client, resumed)
        self.assertEqual(client.calls, [])
        self.assertEqual([chunk["score"] for chunk in chunks], [1, 2, 3])

    def test_a_failing_chunk_still_leaves_the_others_journalled(self) -> None:
        """A failure must not throw away chunks that were already paid for."""

        class Failing(FakeClient):
            def complete(self, user: str, model: str, **kwargs: object):
                if user.endswith("#2"):
                    raise RuntimeError("boom")
                return super().complete(user, model, **kwargs)

        plans = make_plans(4)
        with self.assertRaises(RuntimeError):
            score_chunks(plans, make_request(4), Failing(), self.journal)
        completed = [
            json.loads(line) for line in
            self.journal.path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        hashes = {r["prompt_hash"] for r in completed if r.get("status") == "completed"}
        self.assertEqual(hashes, {"hash1", "hash3", "hash4"})


if __name__ == "__main__":
    unittest.main()
