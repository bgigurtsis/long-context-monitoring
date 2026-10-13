"""Tests for the direct OpenAI Responses compaction transport."""

from __future__ import annotations

import io
import json
import os
import unittest
import urllib.error
from unittest.mock import patch

from long_context_monitoring.openai_responses import (
    LUNA_MODEL,
    OPENAI_RESPONSES_URL,
    OpenAIResponsesClient,
    estimate_luna_cost_usd,
)
from long_context_monitoring.openrouter import LLMError


class FakeHTTPResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeHTTPResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def completed_response(text: str = "summary") -> dict[str, object]:
    return {
        "id": "resp_test",
        "model": LUNA_MODEL,
        "status": "completed",
        "incomplete_details": None,
        "output": [
            {
                "type": "reasoning",
                "summary": [],
            },
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": text},
                ],
            },
        ],
        "usage": {
            "input_tokens": 300_000,
            "output_tokens": 1_000,
            "input_tokens_details": {"cached_tokens": 20_000},
        },
    }


class RequestTests(unittest.TestCase):
    def test_loads_env_and_sends_direct_responses_shape(self) -> None:
        captured: dict[str, object] = {}

        def fake_open(request: object, timeout: float) -> FakeHTTPResponse:
            captured["request"] = request
            captured["timeout"] = timeout
            return FakeHTTPResponse(completed_response())

        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "test-secret"}, clear=False),
            patch("long_context_monitoring.openai_responses.load_dotenv") as load,
            patch("urllib.request.urlopen", side_effect=fake_open),
        ):
            response = OpenAIResponsesClient(timeout=17).complete(
                "compact this",
                LUNA_MODEL,
                max_tokens=20_000,
                temperature=0.7,
                reasoning_effort="high",
            )

        load.assert_called_once_with()
        request = captured["request"]
        self.assertEqual(request.full_url, OPENAI_RESPONSES_URL)
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.headers["Authorization"], "Bearer test-secret")
        payload = json.loads(request.data)
        self.assertEqual(payload["model"], LUNA_MODEL)
        self.assertEqual(
            payload["input"], [{"role": "user", "content": "compact this"}]
        )
        self.assertEqual(payload["reasoning"], {"effort": "high"})
        self.assertEqual(payload["max_output_tokens"], 20_000)
        self.assertIs(payload["store"], False)
        self.assertNotIn("temperature", payload)
        self.assertNotIn("provider", payload)
        self.assertEqual(response.generation_id, "resp_test")
        self.assertEqual(response.model, LUNA_MODEL)
        self.assertEqual(response.cached_input_tokens, 20_000)
        self.assertEqual(response.status, "completed")

    def test_rejects_provider_routing_and_wrong_model(self) -> None:
        client = OpenAIResponsesClient(api_key="secret")
        with self.assertRaisesRegex(LLMError, "provider routing"):
            client.complete("x", provider={"order": ["OpenAI"]})
        with self.assertRaisesRegex(LLMError, LUNA_MODEL):
            client.complete("x", model="openai/gpt-5.6-luna")

    def test_missing_key_error_does_not_disclose_a_secret(self) -> None:
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("long_context_monitoring.openai_responses.load_dotenv"),
        ):
            client = OpenAIResponsesClient()
        with self.assertRaisesRegex(LLMError, "OPENAI_API_KEY") as raised:
            client.complete("x")
        self.assertNotIn("Bearer", str(raised.exception))


class ParsingTests(unittest.TestCase):
    def test_parses_output_usage_and_cost(self) -> None:
        response = OpenAIResponsesClient._parse(completed_response("one\ntwo"), LUNA_MODEL)
        self.assertEqual(response.text, "one\ntwo")
        self.assertEqual(response.input_tokens, 300_000)
        self.assertEqual(response.output_tokens, 1_000)
        self.assertAlmostEqual(
            response.cost_usd or 0,
            estimate_luna_cost_usd(300_000, 1_000, 20_000),
        )

    def test_rejects_empty_and_incomplete_outputs(self) -> None:
        with self.assertRaisesRegex(LLMError, "empty output_text"):
            OpenAIResponsesClient._parse(completed_response(""), LUNA_MODEL)
        incomplete = completed_response()
        incomplete["status"] = "incomplete"
        incomplete["incomplete_details"] = {"reason": "max_output_tokens"}
        with self.assertRaisesRegex(LLMError, "max_output_tokens"):
            OpenAIResponsesClient._parse(incomplete, LUNA_MODEL)

    def test_rejects_missing_usage(self) -> None:
        payload = completed_response()
        payload.pop("usage")
        with self.assertRaisesRegex(LLMError, "missing usage"):
            OpenAIResponsesClient._parse(payload, LUNA_MODEL)


class RetryTests(unittest.TestCase):
    def test_retries_429_and_redacts_key(self) -> None:
        key = "do-not-print-this"
        error = urllib.error.HTTPError(
            OPENAI_RESPONSES_URL,
            429,
            "limited",
            {},
            io.BytesIO(f'{{"message":"{key}"}}'.encode()),
        )
        sleeps: list[float] = []
        with patch("urllib.request.urlopen", side_effect=[error, FakeHTTPResponse(completed_response())]):
            response = OpenAIResponsesClient(
                api_key=key,
                max_attempts=2,
                sleeper=sleeps.append,
            ).complete("x")
        self.assertEqual(response.text, "summary")
        self.assertEqual(sleeps, [1.0])

    def test_retries_timeout_then_stops(self) -> None:
        sleeps: list[float] = []
        with patch("urllib.request.urlopen", side_effect=TimeoutError("slow")):
            with self.assertRaisesRegex(LLMError, "after 2 attempts"):
                OpenAIResponsesClient(
                    api_key="secret",
                    max_attempts=2,
                    sleeper=sleeps.append,
                ).complete("x")
        self.assertEqual(sleeps, [1.0])


class CostTests(unittest.TestCase):
    def test_long_context_uses_full_request_multipliers(self) -> None:
        below = estimate_luna_cost_usd(272_000, 20_000)
        above = estimate_luna_cost_usd(272_001, 20_000)
        expected_above = 272_001 / 1_000_000 * 0.20 * 2
        expected_above += 20_000 / 1_000_000 * 1.20 * 1.5
        self.assertAlmostEqual(above, expected_above)
        self.assertGreater(above, below)


if __name__ == "__main__":
    unittest.main()


class NetworkRetryTests(unittest.TestCase):
    """A dropped connection is transient and must be retried, not fatal.."""

    def test_a_dropped_connection_is_retried(self) -> None:
        import http.client

        sleeps: list[float] = []
        with patch("urllib.request.urlopen", side_effect=[
            http.client.RemoteDisconnected("closed"),
            FakeHTTPResponse(completed_response()),
        ]):
            response = OpenAIResponsesClient(
                api_key="k", max_attempts=2, sleeper=sleeps.append,
            ).complete("x")
        self.assertEqual(response.text, "summary")
        self.assertEqual(sleeps, [1.0])

    def test_an_incomplete_read_is_retried(self) -> None:
        import http.client

        with patch("urllib.request.urlopen", side_effect=[
            http.client.IncompleteRead(b"half"),
            FakeHTTPResponse(completed_response()),
        ]):
            response = OpenAIResponsesClient(
                api_key="k", max_attempts=2, sleeper=lambda _: None,
            ).complete("x")
        self.assertEqual(response.text, "summary")
