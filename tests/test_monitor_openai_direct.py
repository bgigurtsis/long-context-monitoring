"""Tests for the direct OpenAI monitor transport and its CLI wiring."""

from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

from long_context_monitoring.monitor.openai_direct import (
    OPENAI_DIRECT_BACKEND,
    OpenAIDirectMonitorClient,
    direct_model_name,
)
from long_context_monitoring.openrouter import OPENROUTER_BACKEND, LLMError, estimate_cost_usd


NANO = "openai/gpt-4.1-nano"


class FakeHTTPResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeHTTPResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def completed_response(text: str = "Score: 3", model: str = "gpt-4.1-nano-2025-04-14"):
    """A minimal Responses payload; ``model`` is the dated build OpenAI echoes."""

    return {
        "id": "resp_monitor",
        "model": model,
        "status": "completed",
        "incomplete_details": None,
        "output": [
            {"type": "message", "content": [{"type": "output_text", "text": text}]}
        ],
        "usage": {
            "input_tokens": 400_000,
            "output_tokens": 500,
            "input_tokens_details": {"cached_tokens": 10_000},
        },
    }


def run_complete(captured: dict[str, object], **kwargs: object):
    """Call the client against a stubbed transport, capturing the request."""

    def fake_open(request: object, timeout: float) -> FakeHTTPResponse:
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeHTTPResponse(completed_response())

    with (
        patch.dict(os.environ, {"OPENAI_API_KEY": "test-secret"}, clear=False),
        patch("long_context_monitoring.openai_responses.load_dotenv"),
        patch("urllib.request.urlopen", side_effect=fake_open),
    ):
        return OpenAIDirectMonitorClient().complete(**kwargs)  # type: ignore[arg-type]


class ModelNameTests(unittest.TestCase):
    def test_strips_the_openrouter_prefix(self) -> None:
        self.assertEqual(direct_model_name(NANO), "gpt-4.1-nano")

    def test_rejects_a_model_from_another_provider(self) -> None:
        with self.assertRaises(LLMError):
            direct_model_name("deepseek/deepseek-v4-flash-0731")

    def test_rejects_an_openrouter_routing_variant(self) -> None:
        # ":batch" is an OpenRouter concept billed at a different rate; sending
        # it on would price the call against a table entry it does not match.
        with self.assertRaises(LLMError):
            direct_model_name("openai/gpt-4.1-nano:batch")


class RequestShapeTests(unittest.TestCase):
    def test_sends_temperature_when_no_effort_is_set(self) -> None:
        captured: dict[str, object] = {}
        run_complete(
            captured, user="score this", model=NANO, max_tokens=2000,
            temperature=0.0, reasoning_effort=None,
        )
        payload = json.loads(captured["request"].data.decode("utf-8"))
        self.assertEqual(payload["model"], "gpt-4.1-nano")
        self.assertEqual(payload["input"], [{"role": "user", "content": "score this"}])
        self.assertEqual(payload["max_output_tokens"], 2000)
        self.assertEqual(payload["temperature"], 0.0)
        self.assertFalse(payload["store"])
        self.assertNotIn("reasoning", payload)

    def test_sends_effort_and_no_temperature_when_reasoning_is_on(self) -> None:
        captured: dict[str, object] = {}
        run_complete(
            captured, user="score this", model="openai/gpt-5-nano",
            reasoning_effort="low", temperature=0.7,
        )
        payload = json.loads(captured["request"].data.decode("utf-8"))
        self.assertEqual(payload["reasoning"], {"effort": "low"})
        self.assertNotIn("temperature", payload)

    def test_socket_timeout_grows_with_the_prompt(self) -> None:
        captured: dict[str, object] = {}
        run_complete(captured, user="x" * 2_000_000, model=NANO)
        # 2 MB of body at ~2.5 bytes/token is ~800k tokens, so well past the
        # flat 300 s default; a flat timeout would abort and re-pay the call.
        self.assertGreater(float(captured["timeout"]), 300.0)


class GuardTests(unittest.TestCase):
    def test_refuses_a_response_format(self) -> None:
        with self.assertRaises(LLMError):
            OpenAIDirectMonitorClient(api_key="k").complete(
                "x", NANO, response_format={"type": "json_object"}
            )

    def test_refuses_a_pin_it_cannot_honour(self) -> None:
        with self.assertRaises(LLMError) as raised:
            OpenAIDirectMonitorClient(api_key="k").complete(
                "x", NANO, provider={"order": ["DeepInfra"]}
            )
        self.assertIn("DeepInfra", str(raised.exception))

    def test_accepts_an_openai_pin(self) -> None:
        captured: dict[str, object] = {}
        response = run_complete(
            captured, user="x", model=NANO, provider={"order": ["OpenAI"]}
        )
        self.assertEqual(response.provider, "OpenAI")

    def test_requires_a_key(self) -> None:
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("long_context_monitoring.openai_responses.load_dotenv"),
        ):
            with self.assertRaises(LLMError):
                OpenAIDirectMonitorClient().complete("x", NANO)


class CostTests(unittest.TestCase):
    def test_prices_the_requested_slug_not_the_dated_build_openai_echoes(self) -> None:
        captured: dict[str, object] = {}
        response = run_complete(captured, user="x", model=NANO)
        # OpenAI reports "gpt-4.1-nano-2025-04-14"; no price table lists that,
        # so pricing it would fall back to the expensive default rate.
        self.assertEqual(response.model, "gpt-4.1-nano-2025-04-14")
        self.assertAlmostEqual(
            response.cost_usd, estimate_cost_usd(NANO, 400_000, 500)
        )
        self.assertLess(response.cost_usd, 1.0)


class CliWiringTests(unittest.TestCase):
    def test_backends_are_distinct_ids(self) -> None:
        self.assertNotEqual(OPENAI_DIRECT_BACKEND, OPENROUTER_BACKEND)

    def test_request_records_the_backend_and_it_reaches_the_config(self) -> None:
        from long_context_monitoring.monitor.strategies.base import MonitorRequest

        request = MonitorRequest(
            events=[], transcript_name="t", task_description="d",
            visibility="tools-only", render_options=None, model=NANO,
            backend=OPENAI_DIRECT_BACKEND,
        )
        self.assertEqual(request.backend, OPENAI_DIRECT_BACKEND)
        self.assertEqual(MonitorRequest(
            events=[], transcript_name="t", task_description="d",
            visibility="tools-only", render_options=None, model=NANO,
        ).backend, OPENROUTER_BACKEND)


if __name__ == "__main__":
    unittest.main()


class EffortSentinelTests(unittest.TestCase):
    """``--reasoning-effort none`` must omit the field, not send "none"."""

    def test_none_sentinel_becomes_no_effort(self) -> None:
        from long_context_monitoring.monitor.__main__ import _resolved_effort

        self.assertIsNone(_resolved_effort("none"))
        self.assertIsNone(_resolved_effort(None))
        self.assertEqual(_resolved_effort("high"), "high")


class BatchBackendKeyTests(unittest.TestCase):
    """The transport has to be part of a batch's identity, not just its results.

    The compatibility check filters the caller's configuration through
    BATCH_CONFIGURATION_KEYS, so a key missing from that tuple is silently
    ignored however carefully the caller passes it.
    """

    def test_backend_is_part_of_the_compatibility_key(self) -> None:
        from long_context_monitoring.monitor.recording import BATCH_CONFIGURATION_KEYS

        self.assertIn("backend", BATCH_CONFIGURATION_KEYS)

    def test_a_direct_run_cannot_join_a_router_served_batch(self) -> None:
        import json
        import tempfile
        from pathlib import Path

        from long_context_monitoring.monitor.recording import assert_batch_configuration_compatible

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = {"model": NANO, "strategy": "s", "visibility": "tools-only",
                    "objectives_provided": True, "prompt_version": "v1",
                    "reasoning_effort": None, "provider": [],
                    "provider_quantizations": []}
            (root / "manifest.json").write_text(json.dumps({
                "configurations": [dict(base, backend=OPENROUTER_BACKEND)]
            }), encoding="utf-8")

            assert_batch_configuration_compatible(
                root, dict(base, backend=OPENROUTER_BACKEND))
            with self.assertRaises(ValueError):
                assert_batch_configuration_compatible(
                    root, dict(base, backend=OPENAI_DIRECT_BACKEND))

    def test_a_pre_backend_manifest_still_accepts_an_openrouter_run(self) -> None:
        """Every batch recorded before this existed was OpenRouter-served."""
        import json
        import tempfile
        from pathlib import Path

        from long_context_monitoring.monitor.recording import assert_batch_configuration_compatible

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = {"model": NANO, "strategy": "s", "visibility": "tools-only",
                    "objectives_provided": True, "prompt_version": "v1",
                    "reasoning_effort": None, "provider": [],
                    "provider_quantizations": []}
            (root / "manifest.json").write_text(
                json.dumps({"configurations": [dict(base)]}), encoding="utf-8")

            assert_batch_configuration_compatible(
                root, dict(base, backend=OPENROUTER_BACKEND))
            with self.assertRaises(ValueError):
                assert_batch_configuration_compatible(
                    root, dict(base, backend=OPENAI_DIRECT_BACKEND))


class ChatTranslationTests(unittest.TestCase):
    """chat() must round-trip a tool loop between two different API shapes.

    The agentic strategies keep Chat-Completions messages and read ``content``
    off every one to budget the next turn; the Responses API keys tool calls
    and their outputs as top-level items by ``call_id``. A mistranslation
    either drops the budget field or references a call the model never sees.
    """

    TOOL = {"type": "function", "function": {
        "name": "grep", "description": "search",
        "parameters": {"type": "object", "properties": {"pattern": {"type": "string"}}}}}

    def _turn(self, payload_out, messages, tools=None):
        captured = {}

        def fake_open(request, timeout):
            captured["body"] = json.loads(request.data.decode("utf-8"))
            return FakeHTTPResponse(payload_out)

        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "k"}, clear=False),
            patch("long_context_monitoring.openai_responses.load_dotenv"),
            patch("urllib.request.urlopen", side_effect=fake_open),
        ):
            turn = OpenAIDirectMonitorClient().chat(
                messages, NANO, tools=tools, max_tokens=99,
                reasoning_effort="medium")
        return turn, captured["body"]

    @staticmethod
    def _body(items, in_tok=10, out_tok=5):
        return {"id": "r", "model": "gpt-4.1-nano", "status": "completed",
                "incomplete_details": None, "output": items,
                "usage": {"input_tokens": in_tok, "output_tokens": out_tok,
                          "input_tokens_details": {"cached_tokens": 2}}}

    def test_a_tool_call_becomes_a_toolcall_and_replays_verbatim(self) -> None:
        call = {"type": "function_call", "id": "fc_1", "call_id": "call_abc",
                "name": "grep", "arguments": '{"pattern": "secret"}'}
        turn, body = self._turn(self._body([call]), [{"role": "user", "content": "go"}],
                                tools=[self.TOOL])
        self.assertEqual(body["tools"], [{
            "type": "function", "name": "grep", "description": "search",
            "parameters": self.TOOL["function"]["parameters"]}])
        self.assertEqual(len(turn.tool_calls), 1)
        self.assertEqual(turn.tool_calls[0].name, "grep")
        self.assertEqual(turn.tool_calls[0].id, "call_abc")
        self.assertEqual(turn.tool_calls[0].arguments, {"pattern": "secret"})
        self.assertEqual(turn.finish_reason, "tool_calls")
        # conversation_tokens reads content off every message, so it must exist.
        self.assertIn("content", turn.assistant_message)

        # The next turn carries the tool reply; the model must see its own call.
        messages = [{"role": "user", "content": "go"}, turn.assistant_message,
                    {"role": "tool", "tool_call_id": "call_abc", "content": "hit"}]
        _, body2 = self._turn(
            self._body([{"type": "message",
                         "content": [{"type": "output_text", "text": "done"}]}]),
            messages, tools=[self.TOOL])
        self.assertIn(call, body2["input"])
        self.assertIn({"type": "function_call_output",
                       "call_id": "call_abc", "output": "hit"}, body2["input"])

    def test_a_text_turn_reports_no_tool_calls(self) -> None:
        turn, _ = self._turn(
            self._body([{"type": "message",
                         "content": [{"type": "output_text", "text": "Score: 3"}]}]),
            [{"role": "user", "content": "go"}])
        self.assertEqual(turn.tool_calls, [])
        self.assertEqual(turn.text, "Score: 3")
        self.assertEqual(turn.finish_reason, "stop")
        self.assertEqual((turn.input_tokens, turn.output_tokens), (10, 5))
        self.assertEqual(turn.cached_tokens, 2)
        self.assertEqual(turn.provider, "OpenAI")
        # No billed cost is reported, so the caller must estimate rather than
        # record a false $0.
        self.assertIsNone(turn.cost_usd)

    def test_reasoning_items_are_replayed(self) -> None:
        """A reasoning item must come back verbatim or the API rejects the
        follow-up turn that references this turn's tool calls."""
        reasoning = {"type": "reasoning", "id": "rs_1", "summary": []}
        turn, _ = self._turn(self._body([reasoning, {
            "type": "function_call", "id": "fc", "call_id": "c",
            "name": "grep", "arguments": "{}"}]),
            [{"role": "user", "content": "go"}], tools=[self.TOOL])
        _, body = self._turn(self._body([{"type": "message", "content": []}]),
                             [{"role": "user", "content": "go"},
                              turn.assistant_message], tools=[self.TOOL])
        self.assertIn(reasoning, body["input"])
