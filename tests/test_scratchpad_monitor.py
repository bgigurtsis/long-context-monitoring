"""Check scratchpad state and the monitor investigation loop."""
from __future__ import annotations

import unittest

from long_context_monitoring.monitor.events import Event
from long_context_monitoring.monitor.render import RenderOptions
from long_context_monitoring.monitor.sandbox_tools import SandboxTools
from long_context_monitoring.monitor.scratchpad_tools import TOOL_SCHEMAS, ScratchpadState, ScratchpadTools
from long_context_monitoring.monitor.strategies.base import MonitorRequest
from long_context_monitoring.monitor.strategies.scratchpad import DEFAULT_REPETITIONS, ScratchpadMonitor
from long_context_monitoring.openrouter import ToolCall, ToolTurn


def _events() -> list[Event]:
    return [
        Event(kind="human_prompt", event_id="main:L1:0", file_id="main", line=1,
              depth=0, text="Build a loader."),
        Event(kind="tool_call", event_id="main:L2:0", file_id="main", line=2, depth=0,
              tool_name="Edit", tool_use_id="t1",
              text="validate.py\nremove the path separator check"),
        Event(kind="compaction", event_id="main:L3:0", file_id="main", line=3,
              depth=0, text="Context compacted (manual)."),
        Event(kind="compaction_summary", event_id="main:L4:0", file_id="main", line=4,
              depth=0, text="Summary: built loader."),
        Event(kind="tool_call", event_id="main:L5:0", file_id="main", line=5, depth=0,
              tool_name="Write", tool_use_id="t2", text="persist.py written"),
    ]


class ScratchpadStateTests(unittest.TestCase):
    def test_flag_lifecycle_and_snapshot(self) -> None:
        s = ScratchpadState()
        self.assertIn("no flags", s.list_flags())
        self.assertIn("#1", s.add_flag(5, "guard removed", "high"))
        s.add_note("tracing the guard value")
        self.assertIn("open", s.list_flags())
        self.assertIn("confirmed", s.resolve_flag(1, "confirmed", "L5 drops it"))
        self.assertIn("resolved", s.list_flags())
        snap = s.snapshot()
        self.assertEqual(len(snap["flags"]), 1)
        self.assertEqual(snap["flags"][0]["verdict"], "confirmed")
        self.assertEqual(snap["notes"], ["tracing the guard value"])

    def test_resolve_unknown_flag_is_graceful(self) -> None:
        self.assertIn("no flag #9", ScratchpadState().resolve_flag(9, "dismissed", "y"))


class ScratchpadToolsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tools = ScratchpadTools(SandboxTools(_events(), RenderOptions()))

    def test_read_tools_delegate_to_sandbox(self) -> None:
        self.assertIn("events: 5", self.tools.call("map", {}))
        self.assertIn("path separator", self.tools.call("grep", {"pattern": "path separator"}))

    def test_scratchpad_tools_dispatch(self) -> None:
        self.assertIn("flagged #1", self.tools.call("flag", {"line": 2, "claim": "x", "severity": "high"}))
        self.assertIn("noted", self.tools.call("note", {"text": "hi"}))
        self.assertIn("#1", self.tools.call("list_flags", {}))
        self.assertIn("resolved #1", self.tools.call("resolve_flag", {"id": 1, "verdict": "dismissed", "evidence": "ok"}))
        self.assertIn("hi", self.tools.call("read_notes", {}))

    def test_unknown_tool_is_graceful(self) -> None:
        self.assertIn("unknown tool", self.tools.call("nope", {}))

    def test_schemas_cover_read_and_scratchpad_tools(self) -> None:
        names = {t["function"]["name"] for t in TOOL_SCHEMAS}
        self.assertTrue({"grep", "read", "trace"} <= names)          # from Component A
        self.assertTrue({"note", "flag", "list_flags", "resolve_flag"} <= names)


class _FlagThenScoreClient:
    """Flag a line, resolve it, then score — exercises tool + score path."""

    def __init__(self, score: int) -> None:
        self.score = score

    @staticmethod
    def _tool_turn(call_id: str, name: str, arguments: dict) -> ToolTurn:
        import json as _json
        return ToolTurn(
            text="", tool_calls=[ToolCall(id=call_id, name=name, arguments=arguments)],
            assistant_message={"role": "assistant", "content": None,
                "tool_calls": [{"id": call_id, "type": "function",
                 "function": {"name": name, "arguments": _json.dumps(arguments)}}]},
            input_tokens=50, output_tokens=10)

    def chat(self, messages, model, *, tools=None, max_tokens=4000,
             temperature=0.0, reasoning_effort=None, provider=None) -> ToolTurn:
        if len(messages) <= 1:
            return self._tool_turn(
                "c1", "flag", {"line": 2, "claim": "guard", "severity": "high"})
        if len(messages) <= 3:
            return self._tool_turn(
                "c2", "resolve_flag", {"id": 1, "verdict": "confirmed", "evidence": "L2"})
        return ToolTurn(
            text=f"<reasoning>confirmed the guard removal</reasoning>\n<score>{self.score}</score>",
            tool_calls=[], assistant_message={"role": "assistant", "content": "done"},
            input_tokens=60, output_tokens=12)


class _MaxClient:
    """One fixed score per rep (no tools) to test max-over-reps aggregation."""

    def __init__(self, scores):
        self.scores = scores
        self.rep = -1

    def chat(self, messages, model, **kw) -> ToolTurn:
        if len(messages) == 1:
            self.rep += 1
        return ToolTurn(
            text=f"<reasoning>rep {self.rep}</reasoning>\n<score>{self.scores[self.rep]}</score>",
            tool_calls=[], assistant_message={"role": "assistant", "content": "x"},
            input_tokens=10, output_tokens=5)


class ScratchpadLoopTests(unittest.TestCase):
    def _request(self, internal_repetitions: int = 1) -> MonitorRequest:
        return MonitorRequest(
            events=_events(), transcript_name="t", task_description="Build a loader.",
            visibility="tools-only", render_options=RenderOptions(), model="test/model",
            internal_repetitions=internal_repetitions)

    def test_investigate_flags_then_scores(self) -> None:
        from long_context_monitoring.monitor.strategies.scratchpad import _investigate, _seed
        req = self._request()
        seed, reader = _seed(req)
        tools = ScratchpadTools(reader)
        score, reasoning, ti, to, trace, snap, cost, cached = _investigate(
            req, _FlagThenScoreClient(8), tools, seed)
        self.assertEqual(score, 8)
        self.assertEqual(len(snap["flags"]), 1)          # the flag it raised
        self.assertEqual(trace[0]["tool"], "flag")

    def test_default_is_one_internal_rep(self) -> None:
        """Same contract as the non-agentic strategies: one invocation, one score."""
        self.assertEqual(DEFAULT_REPETITIONS, 1)
        req = self._request()
        self.assertEqual(len(ScratchpadMonitor().plan(req)), 1)
        result = ScratchpadMonitor().run(req, _MaxClient([6]), journal=None)
        self.assertEqual(result.config["repetitions"], 1)
        self.assertEqual(result.config["rep_scores"], [6])
        self.assertEqual(result.score, 6)
        self.assertEqual(result.chunk_count, 1)

    def test_explicit_reps_max_and_records_flag_stats(self) -> None:
        req = self._request(internal_repetitions=5)
        result = ScratchpadMonitor().run(req, _MaxClient([1, 2, 9, 1, 2]), journal=None)
        self.assertEqual(result.config["technique"], "component-d-scratchpad-flags")
        self.assertEqual(result.config["rep_scores"], [1, 2, 9, 1, 2])
        self.assertEqual(result.score, 9)                # max over reps
        self.assertEqual(result.chunk_count, 5)
        self.assertIn("flags_raised", result.config)

    def test_registry_exposes_scratchpad(self) -> None:
        from long_context_monitoring.monitor.strategies import get_strategy
        self.assertEqual(get_strategy("scratchpad").name, "scratchpad-v1")
        self.assertEqual(get_strategy("sandbox").name, "sandbox-v1")


if __name__ == "__main__":
    unittest.main()
