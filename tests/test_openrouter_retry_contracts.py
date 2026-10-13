"""Exercise retry and response-resource boundaries with no network or credentials."""

from contextlib import contextmanager
import io
import json
from unittest.mock import Mock
import urllib.error

import pytest

from long_context_monitoring import openrouter


def first_response(kind):
    if kind in {"429", "503", "400"}:
        return urllib.error.HTTPError(
            "https://example.invalid", int(kind), "failure", {}, io.BytesIO(b"detail")
        )
    if kind == "network":
        return urllib.error.URLError("offline")
    if kind == "timeout":
        return TimeoutError("late")
    if kind == "json":
        return b"invalid JSON"
    return json.dumps(
        {
            "error": {
                "code": 400,
                "message": "inaccurate" if kind == "rate-word" else "refused",
            }
        }
    ).encode()


@pytest.mark.parametrize(
    "kind", ["429", "503", "400", "network", "timeout", "json", "rate-word", "refused"]
)
def test_retry_decisions_preserve_payload_and_response_cleanup(monkeypatch, kind):
    trace, requests = [], []
    responses = [first_response(kind), b'{"choices":[{"message":{"content":"ok"}}]}']

    @contextmanager
    def deadline(seconds):
        trace.append("deadline-enter")
        try:
            yield
        finally:
            trace.append("deadline-exit")

    @contextmanager
    def response(body):
        trace.append("response-enter")
        try:
            yield io.BytesIO(body)
        finally:
            trace.append("response-exit")

    def urlopen(request, timeout):
        requests.append(request)
        value = responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return response(value)

    monkeypatch.setattr(openrouter, "_wall_clock_deadline", deadline)
    monkeypatch.setattr(openrouter.urllib.request, "urlopen", urlopen)
    client = openrouter.OpenRouterClient(api_key="fixture-key", max_attempts=2)
    client._backoff = Mock()
    provider = {"order": ["fixture"]}
    options = {
        "reasoning_effort": "high",
        "response_format": {"type": "json_object"},
        "provider": provider,
    }
    if kind in {"400", "json", "refused"}:
        with pytest.raises(openrouter.LLMError):
            client.complete("prompt", "test-model", **options)
        assert len(requests) == 1
        client._backoff.assert_not_called()
    else:
        assert client.complete("prompt", "test-model", **options).text == "ok"
        assert len(requests) == 2
        assert requests[0].data == requests[1].data
        assert client._backoff.call_count == 1
    assert trace[-1] == "deadline-exit"
    assert trace.count("response-enter") == trace.count("response-exit")
    assert provider == {"order": ["fixture"]}
    assert json.loads(requests[0].data) == {
        "model": "test-model",
        "messages": [{"role": "user", "content": "prompt"}],
        "max_tokens": 2000,
        "reasoning": {"effort": "high"},
        "response_format": {"type": "json_object"},
        "provider": {"order": ["fixture"], "require_parameters": True},
    }
