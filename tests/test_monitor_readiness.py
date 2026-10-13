"""Offline end-to-end probes for the released monitoring methods."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from long_context_monitoring.monitor.events import Event
from long_context_monitoring.monitor.recording import Journal
from long_context_monitoring.monitor.render import RenderOptions, estimate_tokens
from long_context_monitoring.monitor.sandbox_tools import MAX_LINE_CHARS, TOOL_SCHEMAS, SandboxTools
from long_context_monitoring.monitor.scoring import ScoreParseError
from long_context_monitoring.monitor.strategies import get_strategy
from long_context_monitoring.prompts import MONITOR_PROMPT_VERSION
from long_context_monitoring.monitor.strategies.base import MonitorRequest
from long_context_monitoring.monitor.visibility import apply_visibility
from long_context_monitoring.openrouter import LLMResponse, ToolCall, ToolTurn
from tests.monitor_fixtures import make_interval_events

STRATEGIES = [
    "whole", "summaries-only", "hierarchical-summary", "intervals", "sandbox", "scratchpad",
]
# These five go through base.score_chunk, which handles journal resume, the
# provider assertion, and temperature. The other five call the client directly.
SCORE_CHUNK_STRATEGIES = {"whole", "summaries-only", "intervals"}
AGENTIC_STRATEGIES = {"sandbox", "scratchpad"}
SINGLE_SHOT_STRATEGIES = sorted(set(STRATEGIES) - AGENTIC_STRATEGIES)
PIN = ("open-inference/fp8",)
CATALOG = "CATALOG_OBJECTIVE_TEXT: never widen a path root."
MODEL = "deepseek/deepseek-v4-flash-0731"


class RecordingClient:
    """Fake OpenRouter client for both call shapes, keeping every prompt in order.

    ``complete`` (single-shot) returns replies in sequence; the score climbs by
    one per call so a test can tell which call fed the headline. ``chat``
    (agentic) answers each rep with a final score straight away unless
    ``tool_first`` asks for one tool call before the score.
    """

    def __init__(self, *, observed_provider: str | None = None,
                 replies: list[str] | None = None, tool_first: str | None = None,
                 tool_args: dict | None = None, scores: list[int] | None = None) -> None:
        self.prompts: list[str] = []
        self.complete_calls: list[dict] = []
        self.chat_calls: list[dict] = []
        self.observed_provider = observed_provider
        self.replies = list(replies) if replies is not None else None
        self.tool_first = tool_first
        self.tool_args = dict(tool_args or {})
        self.scores = list(scores) if scores is not None else None
        self._rep = 0
        self._pending_tool = False

    @property
    def calls(self) -> int:
        return len(self.complete_calls) + len(self.chat_calls)

    def _score_for(self, n: int) -> int:
        if self.scores is not None:
            return self.scores[(n - 1) % len(self.scores)]
        return min(n, 10)

    def _provider(self, provider) -> str:
        if self.observed_provider is not None:
            return self.observed_provider
        order = (provider or {}).get("order") or []
        return str(order[0]).split("/", 1)[0] if order else "Anthropic"

    def complete(self, user, model, max_tokens=2000, temperature=0.0,
                 reasoning_effort=None, response_format=None, provider=None):
        self.prompts.append(user)
        self.complete_calls.append({
            "user": user, "model": model, "temperature": temperature,
            "reasoning_effort": reasoning_effort, "provider": provider,
            "max_tokens": max_tokens,
        })
        n = len(self.complete_calls)
        if self.replies is not None and n - 1 < len(self.replies):
            text = self.replies[n - 1]
        else:
            text = f"<reasoning>DIGEST_{n}</reasoning>\n<score>{self._score_for(n)}</score>"
        return LLMResponse(
            text=text, model=model, input_tokens=len(user) // 4,
            output_tokens=len(text) // 4, generation_id=f"gen-{n}",
            provider=self._provider(provider),
        )

    def chat(self, messages, model, *, tools=None, max_tokens=4000,
             reasoning_effort=None, provider=None, **kwargs) -> ToolTurn:
        self.chat_calls.append({
            "messages": copy.deepcopy(messages), "model": model, "tools": tools,
            "reasoning_effort": reasoning_effort, "provider": provider,
            "extra_kwargs": dict(kwargs),
        })
        self.prompts.append("\n".join(str(m.get("content") or "") for m in messages))
        if len(messages) == 1:
            self._rep += 1
            self._pending_tool = self.tool_first is not None
        if self._pending_tool:
            self._pending_tool = False
            call = {"id": "c1", "type": "function",
                    "function": {"name": self.tool_first,
                                 "arguments": json.dumps(self.tool_args)}}
            return ToolTurn(
                text="", tool_calls=[ToolCall(id="c1", name=self.tool_first,
                                              arguments=dict(self.tool_args))],
                assistant_message={"role": "assistant", "content": None, "tool_calls": [call]},
                input_tokens=100, output_tokens=10, provider=self._provider(provider))
        score = self._score_for(self._rep)
        return ToolTurn(
            text=f"<reasoning>rep {self._rep}</reasoning>\n<score>{score}</score>",
            tool_calls=[], assistant_message={"role": "assistant", "content": "done"},
            input_tokens=100, output_tokens=10, provider=self._provider(provider))


def _tool_call(line: int, command: str, uid: str) -> Event:
    return Event(kind="tool_call", event_id=f"main:L{line}:0", file_id="main", line=line,
                 depth=0, text=f'{{"command": "{command}"}}', tool_name="Bash", tool_use_id=uid)


def _tool_result(line: int, text: str, uid: str) -> Event:
    return Event(kind="tool_result", event_id=f"main:L{line}:0", file_id="main", line=line,
                 depth=0, text=text, tool_use_id=uid)


def _human(line: int, text: str) -> Event:
    return Event(kind="human_prompt", event_id=f"main:L{line}:0", file_id="main",
                 line=line, depth=0, text=text)


def _summary(line: int, text: str) -> Event:
    return Event(kind="compaction_summary", event_id=f"main:L{line}:0", file_id="main",
                 line=line, depth=0, text=text)


def zero_compaction_events() -> list[Event]:
    return [_human(1, "Do the task."), _tool_call(2, "ONLY_ONE", "a"),
            _tool_result(3, "ok", "a"), _tool_call(4, "ONLY_TWO", "b")]


def one_compaction_events() -> list[Event]:
    return [
        _human(1, "Do the task."), _tool_call(2, "BEFORE", "a"),
        Event(kind="compaction", event_id="main:L3:0", file_id="main", line=3, depth=0,
              text="Boundary one."),
        _summary(4, "SUMMARY_ONE"),
        _tool_call(5, "AFTER", "b"),
    ]


SHAPES = {
    "zero-compaction": zero_compaction_events,
    "one-compaction": one_compaction_events,
    "multi-compaction": make_interval_events,
}
INTERVAL_MARKERS = ["SETUP", "MIDDLE_ONE", "MIDDLE_TWO", "END"]
INTERVAL_SUMMARIES = ["SUMMARY_ONE", "SUMMARY_TWO", "SUMMARY_THREE"]


def request(events: list[Event], **overrides) -> MonitorRequest:
    params = dict(
        events=events, transcript_name="synthetic", task_description="Build a loader.",
        visibility="tools-only", render_options=RenderOptions(),
        model=MODEL, provider=PIN, provider_quantizations=("fp8",), reasoning_effort="high",
        internal_repetitions=5,
    )
    params.update(overrides)
    return MonitorRequest(**params)


def run(strategy: str, req: MonitorRequest, client: RecordingClient, journal=None):
    return get_strategy(strategy).run(req, client, journal)


def _prompts_with(client: RecordingClient, marker: str) -> list[str]:
    return [p for p in client.prompts if marker in p]


def _fresh_journal() -> Journal:
    return Journal(Path(tempfile.mkdtemp()) / "journal.jsonl")


class EndToEndProbes(unittest.TestCase):
    """Criterion 1: every strategy returns a complete result on three shapes."""

    def test_runs_end_to_end(self) -> None:
        for strategy in STRATEGIES:
            for shape, build in SHAPES.items():
                with self.subTest(strategy=strategy, shape=shape):
                    client = RecordingClient()
                    result = run(strategy, request(build()), client)
                    self.assertTrue(result.band)
                    self.assertGreaterEqual(result.score, 0)
                    self.assertTrue(result.chunks)
                    # Strategies that send extra templates append their hashes.
                    self.assertTrue(result.config["prompt_version"]
                                    .startswith(MONITOR_PROMPT_VERSION))
                    self.assertEqual(result.config["provider"], list(PIN))
                    self.assertGreaterEqual(client.calls, 1)


class HeadlineRuleProbes(unittest.TestCase):
    """Criterion 2: the headline rule per strategy is the documented one."""


    def test_intervals_headline_is_the_max_over_intervals(self) -> None:
        client = RecordingClient(scores=[2, 9, 2, 2])
        result = run("intervals", request(make_interval_events()), client)
        self.assertEqual([c["view"] for c in result.chunks],
                         ["interval_0", "interval_1", "interval_2", "interval_3"])
        self.assertEqual(result.score, 9)
        self.assertEqual(client.calls, 4)


class PromptContentProbes(unittest.TestCase):
    """Criterion 3: each prompt holds what the strategy name says and nothing else."""

    def _run(self, strategy: str, **overrides) -> RecordingClient:
        client = RecordingClient()
        run(strategy, request(make_interval_events(), **overrides), client)
        return client

    def test_whole_holds_every_event_once(self) -> None:
        client = self._run("whole")
        self.assertEqual(len(client.prompts), 1)
        for marker in INTERVAL_MARKERS + INTERVAL_SUMMARIES:
            self.assertEqual(client.prompts[0].count(marker), 1, marker)

    def test_summaries_only_holds_summaries_and_no_actions(self) -> None:
        client = self._run("summaries-only")
        self.assertEqual(len(client.prompts), 1)
        prompt = client.prompts[0]
        for marker in INTERVAL_SUMMARIES:
            self.assertIn(marker, prompt)
        for marker in INTERVAL_MARKERS:
            self.assertNotIn(marker, prompt)
        self.assertNotIn("Action 1", prompt)


    def test_intervals_views_start_at_summary_and_stop_at_boundary(self) -> None:
        client = self._run("intervals")
        whole = [p for p in client.prompts if all(m in p for m in INTERVAL_MARKERS)]
        self.assertEqual(len(whole), 0)  # the whole trajectory is not a view here
        middle = [p for p in client.prompts if "MIDDLE_ONE" in p and "END" not in p]
        self.assertEqual(len(middle), 1)
        self.assertIn("SUMMARY_ONE", middle[0])
        self.assertNotIn("SETUP", middle[0])
        self.assertNotIn("MIDDLE_TWO", middle[0])
        self.assertNotIn("SUMMARY_TWO", middle[0])


    def test_hierarchical_merges_adjacent_leaves_in_order(self) -> None:
        client = self._run("hierarchical-summary")
        for prompt, marker in zip(client.prompts[:4], INTERVAL_MARKERS, strict=True):
            self.assertIn(marker, prompt)
        merges = client.prompts[4:-1]
        root = client.prompts[-1]
        # BRANCHING = 3 over four leaves: merge(1,2,3) then merge(that, 4).
        self.assertEqual(len(merges), 2)
        first = merges[0]
        self.assertLess(first.index("DIGEST_1"), first.index("DIGEST_2"))
        self.assertLess(first.index("DIGEST_2"), first.index("DIGEST_3"))
        self.assertNotIn("DIGEST_4", first)
        second = merges[1]
        self.assertLess(second.index("DIGEST_5"), second.index("DIGEST_4"))
        self.assertIn("DIGEST_6", root)
        for marker in INTERVAL_MARKERS:
            self.assertNotIn(marker, root)

    def test_hierarchical_depth_is_equal_for_five_leaves(self) -> None:
        from long_context_monitoring.monitor.strategies.hierarchical_summary import leaf_merge_depths
        # Our transcripts have four compactions, so five leaves: every leaf
        # is merged twice. Four leaves (three compactions) is the uneven case.
        self.assertEqual(leaf_merge_depths(5), [2, 2, 2, 2, 2])
        self.assertEqual(leaf_merge_depths(4), [2, 2, 2, 1])
        self.assertEqual(leaf_merge_depths(1), [0])
        result = run("hierarchical-summary", request(make_interval_events()), RecordingClient())
        self.assertEqual(result.config["leaf_merge_depths"], [2, 2, 2, 1])


    def test_agentic_substrate_holds_every_event_once(self) -> None:
        tools = SandboxTools(make_interval_events(), RenderOptions())
        text = "\n".join(tools.transcript.lines)
        for marker in INTERVAL_MARKERS + INTERVAL_SUMMARIES:
            self.assertEqual(text.count(marker), 1, marker)

    def test_intervals_plans_no_whole_view(self) -> None:
        """Probe 19: the whole trajectory belongs to the whole strategy only."""
        req = request(make_interval_events())
        views = [p.view for p in get_strategy("intervals").plan(req)]
        self.assertNotIn("whole", views)
        self.assertEqual(len(views), 4)
        # With no compaction the one interval is the whole trajectory.
        views = [p.view for p in get_strategy("intervals").plan(request(zero_compaction_events()))]
        self.assertEqual(views, ["whole"])


class ContextBudgetProbes(unittest.TestCase):
    """Criterion 4: no call path sends a prompt over the chunk budget."""

    @staticmethod
    def _oversized_events() -> list[Event]:
        events = [_human(1, "Do the task.")]
        for i in range(2, 62):
            events.append(_tool_call(i * 2, f"CMD_{i}", f"u{i}"))
            events.append(_tool_result(i * 2 + 1, "X" * 16_000, f"u{i}"))
        return events

    def test_context_budget_on_every_call(self) -> None:
        target = 20_000
        for strategy in STRATEGIES:
            with self.subTest(strategy=strategy):
                # The agentic loops only grow past the seed when a tool reply
                # comes back, so ask each rep for one full-page read first.
                client = RecordingClient(
                    tool_first="read" if strategy in AGENTIC_STRATEGIES else None,
                    tool_args={"start_line": 1, "end_line": 400})
                req = request(self._oversized_events(), chunk_target_tokens=target,
                              max_output_tokens=2_000)
                run(strategy, req, client)
                worst = max(estimate_tokens(p) for p in client.prompts)
                self.assertLessEqual(worst, target, f"{strategy} sent {worst} tokens")


class ResumeProbes(unittest.TestCase):
    """Criterion 5: resume reuses paid calls under the same settings only."""

    def test_resume_same_settings(self) -> None:
        for strategy in STRATEGIES:
            with self.subTest(strategy=strategy):
                journal = _fresh_journal()
                first = RecordingClient()
                run(strategy, request(make_interval_events()), first, journal)
                second = RecordingClient()
                run(strategy, request(make_interval_events()), second, Journal(journal.path))
                if strategy in SCORE_CHUNK_STRATEGIES:
                    self.assertEqual(second.calls, 0)
                    self.assertTrue(getattr(get_strategy(strategy), "supports_resume", True))
                else:
                    # The strategy itself still pays every call again; the CLI
                    # refuses --resume for it (test_cli_refuses_resume below).
                    self.assertEqual(second.calls, first.calls)
                    self.assertFalse(getattr(get_strategy(strategy), "supports_resume", True))

    def test_cli_refuses_resume_for_direct_call_strategies(self) -> None:
        from long_context_monitoring.monitor.__main__ import main
        for strategy in sorted(set(STRATEGIES) - SCORE_CHUNK_STRATEGIES):
            with self.subTest(strategy=strategy):
                with self.assertRaises(SystemExit) as caught:
                    main(["--strategy", strategy, "--resume", "some-run-dir",
                          "--batch-name", "pairs-scored-by-deepseek", "no-such-transcript"])
                self.assertIn("--resume is not supported", str(caught.exception))

    def test_resume_changed_settings(self) -> None:
        from long_context_monitoring.monitor.strategies.base import ResumeSettingsError
        for strategy in sorted(SCORE_CHUNK_STRATEGIES):
            with self.subTest(strategy=strategy):
                journal = _fresh_journal()
                run(strategy, request(make_interval_events(), temperature=0.0),
                    RecordingClient(), journal)
                second = RecordingClient()
                with self.assertRaises(ResumeSettingsError) as caught:
                    run(strategy, request(make_interval_events(), temperature=0.7,
                                          model="openai/gpt-5.6-luna"),
                        second, Journal(journal.path))
                self.assertEqual(second.calls, 0)
                self.assertIn("model", str(caught.exception))
                self.assertIn("temperature", str(caught.exception))

    def test_resume_refuses_a_journal_without_settings(self) -> None:
        from long_context_monitoring.monitor.strategies.base import ResumeSettingsError
        journal = _fresh_journal()
        run("whole", request(make_interval_events()), RecordingClient(), journal)
        lines = [json.loads(line) for line in
                 journal.path.read_text(encoding="utf-8").splitlines() if line.strip()]
        for line in lines:
            line.pop("settings", None)
        journal.path.write_text("\n".join(json.dumps(line) for line in lines) + "\n",
                                encoding="utf-8")
        with self.assertRaises(ResumeSettingsError):
            run("whole", request(make_interval_events()), RecordingClient(), Journal(journal.path))

    def test_prompt_hashes_match_between_plan_and_run(self) -> None:
        """Probe 5: a journal written by run() is keyed by plan() hashes."""
        for strategy in STRATEGIES:
            with self.subTest(strategy=strategy):
                journal = _fresh_journal()
                req = request(make_interval_events())
                planned = {p.prompt_hash for p in get_strategy(strategy).plan(req)}
                planned_again = {p.prompt_hash for p in get_strategy(strategy).plan(req)}
                self.assertEqual(planned, planned_again)
                run(strategy, req, RecordingClient(), journal)
                journalled = {
                    json.loads(line)["prompt_hash"]
                    for line in journal.path.read_text(encoding="utf-8").splitlines()
                    if line.strip() and "prompt_hash" in line
                }
                self.assertTrue(planned <= journalled, strategy)


class ProviderAndConfigProbes(unittest.TestCase):
    """Criteria 6, 7, 9: pin asserted, cost gate honest, config honest."""

    def test_provider_pin_asserted(self) -> None:
        for strategy in STRATEGIES:
            with self.subTest(strategy=strategy):
                client = RecordingClient(observed_provider="SomeOtherHost")
                with self.assertRaises(RuntimeError):
                    run(strategy, request(make_interval_events()), client)

    def test_observed_provider_is_recorded_on_every_chunk(self) -> None:
        for strategy in STRATEGIES:
            with self.subTest(strategy=strategy):
                result = run(strategy, request(make_interval_events()), RecordingClient())
                providers = {c["provider"] for c in result.chunks if c["input_tokens"]}
                self.assertEqual(providers, {"open-inference"})


    def test_config_honesty(self) -> None:
        for strategy in STRATEGIES:
            with self.subTest(strategy=strategy):
                client = RecordingClient()
                # With a reasoning effort set the client sends no temperature,
                # so the record says None; without one the value is sent and kept.
                result = run(strategy, request(make_interval_events(), temperature=0.3), client)
                self.assertIsNone(result.config["temperature"])
                plain = run(strategy, request(make_interval_events(), temperature=0.3,
                                              reasoning_effort=None), RecordingClient())
                self.assertEqual(plain.config["temperature"], 0.3)
                sent = {c["temperature"] for c in client.complete_calls}
                sent |= {c["extra_kwargs"].get("temperature") for c in client.chat_calls}
                self.assertEqual(sent, {0.3})

    def test_reasoning_effort_and_pin_reach_every_call(self) -> None:
        for strategy in STRATEGIES:
            with self.subTest(strategy=strategy):
                client = RecordingClient()
                run(strategy, request(make_interval_events()), client)
                for call in client.complete_calls + client.chat_calls:
                    self.assertEqual(call["reasoning_effort"], "high")
                    self.assertEqual(call["provider"]["order"], list(PIN))
                    self.assertEqual(call["provider"]["quantizations"], ["fp8"])
                    self.assertIs(call["provider"]["allow_fallbacks"], False)


class PromptProvenanceProbes(unittest.TestCase):
    """Criterion 8: every rendered template has a hash in result.config."""

    def test_prompt_template_hashes_recorded(self) -> None:
        import hashlib
        expected = {
            name: hashlib.sha256((Path("prompts") / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            for name in ["monitor.md", "monitor_extract.md", "monitor_merge.md",
                         "monitor_sandbox.md", "monitor_scratchpad.md"]
        }
        for strategy in STRATEGIES:
            with self.subTest(strategy=strategy):
                result = run(strategy, request(make_interval_events()), RecordingClient())
                hashes = result.config["prompt_template_hashes"]
                for name, digest in expected.items():
                    self.assertEqual(hashes[name], digest, name)


class ParseProbes(unittest.TestCase):
    """Criterion 10: a parse failure cannot become a score."""

    def test_parse_failure_is_not_a_score(self) -> None:
        for strategy in SINGLE_SHOT_STRATEGIES:
            with self.subTest(strategy=strategy):
                client = RecordingClient(replies=["no score here at all"] * 12)
                with self.assertRaises((ScoreParseError, RuntimeError)):
                    run(strategy, request(make_interval_events()), client)

    def test_out_of_range_and_ambiguous_replies(self) -> None:
        rejected = [
            "<reasoning>x</reasoning>\n<score>12</score>",
            "<reasoning>x</reasoning>\n<score>0</score>",
            "Score: 3 for objective one.\nScore: 9 for objective two.",
        ]
        for reply in rejected:
            with self.subTest(reply=reply):
                # Served three times: an unscorable reply is re-requested up to
                # twice, so the parser's rejection has to survive the retry to
                # surface, and the call count pins that it retried twice.
                client = RecordingClient(replies=[reply, reply, reply])
                with self.assertRaises(ScoreParseError):
                    run("whole", request(zero_compaction_events()), client)
                self.assertEqual(client.calls, 3)
        # One fallback line, or several that agree, still parses.
        client = RecordingClient(replies=["Looks fine overall.\nScore: 3\nScore: 3"])
        self.assertEqual(run("whole", request(zero_compaction_events()), client).score, 3)

    def test_no_action_chunk_scores_zero_without_a_call(self) -> None:
        events = [_human(1, "Do the task."), _summary(2, "SUMMARY_ONLY")]
        for strategy in sorted(SCORE_CHUNK_STRATEGIES - {"summaries-only"}):
            with self.subTest(strategy=strategy):
                client = RecordingClient()
                result = run(strategy, request(events), client)
                # Records: 0 is a value the 1..10 prompt never emits, and it
                # reaches result.score with no call made.
                self.assertEqual(client.calls, 0)
                self.assertEqual(result.score, 0)


class ToolProbes(unittest.TestCase):
    """Criterion 11: read-only tools, and evidence readable to its end."""

    def test_tools_are_read_only(self) -> None:
        events = make_interval_events()
        before = copy.deepcopy(events)
        tools = SandboxTools(events, RenderOptions())
        substrate = list(tools.transcript.lines)
        sample_args = {
            "grep": {"pattern": "MIDDLE"}, "read": {"start_line": 1, "end_line": 3},
            "read_around": {"line": 2}, "read_line": {"line": 2},
            "trace": {"value": "MIDDLE"},
        }
        for schema in TOOL_SCHEMAS:
            name = schema["function"]["name"]
            tools.call(name, sample_args.get(name, {}))
        self.assertEqual(events, before)
        self.assertEqual(list(tools.transcript.lines), substrate)

    def test_capped_line_is_reachable(self) -> None:
        tail = "TAIL_MARKER_PAST_CAP"
        events = [_human(1, "Do the task."), _tool_call(2, "x", "a"),
                  _tool_result(3, "Y" * (MAX_LINE_CHARS + 50) + tail, "a")]
        tools = SandboxTools(events, RenderOptions())
        substrate = "\n".join(tools.transcript.lines)
        self.assertIn(tail, substrate)
        # grep echoes the pattern in its header line, so look at the hit lines only.
        grep_hits = tools.call("grep", {"pattern": tail}).split("\n", 1)[1]
        capped = [grep_hits,
                  tools.call("read", {"start_line": 1, "end_line": 10}),
                  tools.call("read_around", {"line": 3})]
        # The capped views name the tool that shows the rest, and that tool does.
        for out in capped:
            self.assertNotIn(tail, out)
            self.assertIn("read_line(8, start_char=2001)", out)
        rest = tools.call("read_line", {"line": 8, "start_char": MAX_LINE_CHARS + 1})
        self.assertIn(tail, rest)
        self.assertIn("read_line", {t["function"]["name"] for t in TOOL_SCHEMAS})


class ScratchpadProtocolProbes(unittest.TestCase):
    """Probe 13: what the scratchpad accepts today."""

    def test_scratchpad_rejects_loose_protocol(self) -> None:
        from long_context_monitoring.monitor.scratchpad_tools import ScratchpadTools
        tools = ScratchpadTools(SandboxTools(make_interval_events(), RenderOptions()))
        self.assertIn("rejected", tools.call("flag", {"line": 0, "claim": "x", "severity": "high"}))
        self.assertIn("rejected", tools.call("flag", {"line": 9999, "claim": "y", "severity": "high"}))
        self.assertIn("flagged #1", tools.call("flag", {"line": 2, "claim": "z", "severity": "high"}))
        self.assertIn("rejected", tools.call(
            "resolve_flag", {"id": 1, "verdict": "banana", "evidence": "e"}))
        self.assertIn("resolved #1", tools.call(
            "resolve_flag", {"id": 1, "verdict": "Dismissed", "evidence": "e"}))

    def test_scratchpad_sends_a_score_back_while_flags_are_open(self) -> None:
        from long_context_monitoring.monitor.strategies.scratchpad import MAX_ITERATIONS
        client = RecordingClient(tool_first="flag",
                                 tool_args={"line": 2, "claim": "x", "severity": "high"})
        result = run("scratchpad", request(make_interval_events()), client)
        # Every rep flags once and never resolves, so each score is sent back
        # until the forced conclusion; the count is on the chunk record.
        for chunk in result.chunks:
            self.assertEqual(chunk["scores_rejected_open_flags"], MAX_ITERATIONS - 1)
        self.assertGreater(result.score, 0)


class VisibilityProbes(unittest.TestCase):
    """Criteria 12 and 13: blind differs only in objectives; tools-only hides text."""

    def test_blind_differs_only_in_objectives(self) -> None:
        for strategy in SINGLE_SHOT_STRATEGIES:
            with self.subTest(strategy=strategy):
                informed, blind = RecordingClient(), RecordingClient()
                run(strategy, request(make_interval_events(), objectives=CATALOG), informed)
                run(strategy, request(make_interval_events(), objectives=None), blind)
                self.assertEqual(len(informed.prompts), len(blind.prompts))
                differing = [(a, b) for a, b in zip(informed.prompts, blind.prompts, strict=True)
                             if a != b]
                # Extraction and merge prompts carry no objectives region, so
                # only the scoring calls may differ.
                self.assertGreaterEqual(len(differing), 1)
                for a, b in differing:
                    self.assertIn(CATALOG, a)
                    self.assertNotIn(CATALOG, b)
                    self.assertLess(len(b), len(a))

    def test_agentic_seed_carries_objectives_only_when_informed(self) -> None:
        for strategy in AGENTIC_STRATEGIES:
            with self.subTest(strategy=strategy):
                informed, blind = RecordingClient(), RecordingClient()
                run(strategy, request(make_interval_events(), objectives=CATALOG), informed)
                run(strategy, request(make_interval_events(), objectives=None), blind)
                self.assertTrue(all(CATALOG in p for p in informed.prompts))
                self.assertTrue(all(CATALOG not in p for p in blind.prompts))

    def test_tools_only_hides_assistant_text(self) -> None:
        events = make_interval_events() + [
            Event(kind="assistant_text", event_id="main:L90:0", file_id="main", line=90,
                  depth=0, text="ASSISTANT_SECRET"),
            Event(kind="thinking", event_id="main:L91:0", file_id="main", line=91,
                  depth=0, text="THINK_SECRET"),
        ]
        visible = apply_visibility(events, "tools-only")
        for strategy in STRATEGIES:
            with self.subTest(strategy=strategy):
                client = RecordingClient()
                run(strategy, request(visible), client)
                for prompt in client.prompts:
                    self.assertNotIn("ASSISTANT_SECRET", prompt)
                    self.assertNotIn("THINK_SECRET", prompt)
        substrate = "\n".join(SandboxTools(visible, RenderOptions()).transcript.lines)
        self.assertNotIn("ASSISTANT_SECRET", substrate)
        self.assertNotIn("THINK_SECRET", substrate)


class AnnotatedHistoryProbes(unittest.TestCase):
    """Annotated-history bypasses score_chunk, so items 3 and 6 are pinned here."""

    def test_resume_reuses_only_under_the_same_settings(self) -> None:
        from long_context_monitoring.monitor.strategies.base import ResumeSettingsError
        journal = _fresh_journal()
        first = RecordingClient()
        run("annotated-history", request(make_interval_events()), first, journal)
        lines = [json.loads(line) for line in
                 journal.path.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertTrue(all("settings" in line for line in lines
                            if line.get("status") == "completed"))
        second = RecordingClient()
        run("annotated-history", request(make_interval_events()), second, Journal(journal.path))
        self.assertEqual(second.calls, 0)
        third = RecordingClient()
        with self.assertRaises(ResumeSettingsError):
            run("annotated-history", request(make_interval_events(), reasoning_effort="low"),
                third, Journal(journal.path))
        self.assertEqual(third.calls, 0)

    def test_provider_pin_is_asserted(self) -> None:
        client = RecordingClient(observed_provider="SomeOtherHost")
        with self.assertRaises(RuntimeError):
            run("annotated-history", request(make_interval_events()), client)

    def test_oversized_interval_is_scored_in_parts_within_budget(self) -> None:
        """An interval above the chunk budget is split like ``intervals`` splits."""
        target = 20_000
        req = request(ContextBudgetProbes._oversized_events(),
                      chunk_target_tokens=target, max_output_tokens=2_000)
        plans = get_strategy("annotated-history").plan(req)
        self.assertGreater(len(plans), 1)
        self.assertEqual([p.index for p in plans], list(range(1, len(plans) + 1)))
        self.assertEqual({p.view_chunk_total for p in plans}, {len(plans)})
        self.assertEqual(plans[0].view_label, f"whole trajectory (part 1/{len(plans)})")
        client = RecordingClient()
        result = run("annotated-history", req, client)
        self.assertEqual(client.calls, len(plans))
        worst = max(estimate_tokens(p) for p in client.prompts)
        self.assertLessEqual(worst, target, f"sent {worst} tokens")
        self.assertEqual(result.chunk_count, len(plans))

    def test_interval_within_budget_plans_one_unlabelled_part(self) -> None:
        """The split must be invisible when nothing overflows: one plan per
        interval, plain interval labels, so in-budget prompts and their
        journal hashes are unchanged."""
        plans = get_strategy("annotated-history").plan(request(make_interval_events()))
        self.assertEqual([p.view_chunk_total for p in plans], [1] * len(plans))
        self.assertFalse(any("(part " in p.view_label for p in plans))


if __name__ == "__main__":
    unittest.main()
