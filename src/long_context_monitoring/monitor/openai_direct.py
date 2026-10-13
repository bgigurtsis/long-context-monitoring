"""Direct OpenAI Responses transport for monitor scoring.

Why this exists: monitoring normally goes through OpenRouter, which gives the
campaign provider pinning and a billed-cost figure. OpenRouter also adds a
routing hop, and on long monitor prompts that hop dominates wall-clock time.
When the monitor model is an OpenAI model anyway, talking to
``api.openai.com`` directly removes the hop without changing the prompt, the
strategy, or the score.

The class keeps OpenRouter's model naming (``openai/gpt-4.1-nano``) so the
shared context-window and price tables in :mod:`src.openrouter` still govern
chunk budgets and the cost gate, and so a result's ``model`` field means the
same thing under either backend. Only the ``openai/`` prefix is stripped on the
wire.

The backend is recorded in every result and is part of a batch's compatibility
key: a chunk scored through OpenRouter and a chunk scored direct are not the
same monitor condition and must not be pooled.
"""

from __future__ import annotations

import json

from long_context_monitoring.openai_responses import OPENAI_RESPONSES_ENDPOINT, OpenAIResponsesClient
from long_context_monitoring.openrouter import (
    LLMError,
    LLMResponse,
    ToolCall,
    ToolTurn,
    _wall_clock_deadline,
    estimate_cost_usd,
)


OPENAI_DIRECT_BACKEND = "openai-direct"
OPENAI_SLUG_PREFIX = "openai/"
# The one provider label a direct call can ever return. A caller may still pin
# it explicitly; assert_pinned_provider then checks it like any other run.
OPENAI_PROVIDER_LABEL = "OpenAI"


def direct_model_name(model: str) -> str:
    """The wire model name for an OpenRouter-style ``openai/...`` slug."""

    if not model.startswith(OPENAI_SLUG_PREFIX):
        raise LLMError(
            f"the direct OpenAI monitor backend needs an '{OPENAI_SLUG_PREFIX}' "
            f"model slug, got {model!r}"
        )
    name = model[len(OPENAI_SLUG_PREFIX):]
    # ":batch"/":nitro"-style routing variants are an OpenRouter concept and
    # have no meaning here; accepting one silently would bill a different rate
    # than MODEL_PRICES records.
    if not name or ":" in name:
        raise LLMError(f"{model!r} is not a plain OpenAI model slug")
    return name


class OpenAIDirectMonitorClient(OpenAIResponsesClient):
    """``LLMClient`` for monitor calls sent straight to the Responses API.

    Inherits the transport, retry policy, and key redaction of
    :class:`~src.openai_responses.OpenAIResponsesClient`; replaces its
    Luna-specific payload, model guard, and pricing.
    """

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 300.0,
        max_attempts: int = 6,
        rate_limit_attempts: int = 20,
        backoff_cap_seconds: float = 120.0,
        hard_timeout: float | None = None,
        **kwargs: object,
    ) -> None:
        # Monitoring runs many chunks at once, so a 429 is an expected part of
        # a healthy sweep rather than a failure: it gets its own large budget,
        # as OpenRouterClient does. The backoff cap is well above the compaction
        # client's 8 s because the cap also truncates a server Retry-After —
        # an 8 s cap would ignore a 30 s throttle window and hammer it.
        super().__init__(
            api_key=api_key,
            timeout=timeout,
            max_attempts=max_attempts,
            rate_limit_attempts=rate_limit_attempts,
            backoff_cap_seconds=backoff_cap_seconds,
            **kwargs,  # type: ignore[arg-type]
        )
        self.hard_timeout = hard_timeout

    def complete(
        self,
        user: str,
        model: str,
        max_tokens: int = 2000,
        temperature: float = 0.0,
        reasoning_effort: str | None = None,
        response_format: dict[str, object] | None = None,
        provider: dict[str, object] | None = None,
    ) -> LLMResponse:
        """One monitor call. Mirrors ``OpenRouterClient.complete``'s contract."""

        if response_format is not None:
            raise LLMError(
                "the direct OpenAI monitor backend does not send response_format"
            )
        self._check_provider_pin(provider)
        key = self._require_key()
        wire_model = direct_model_name(model)
        payload: dict[str, object] = {
            "model": wire_model,
            "input": [{"role": "user", "content": user}],
            "max_output_tokens": max_tokens,
            # Never let a monitor prompt be retained server side; the same
            # reason the compaction client sets this.
            "store": False,
        }
        # Same rule as OpenRouterClient: an effort turns reasoning on, and
        # sampling controls are left alone while it is on. gpt-4.1-nano is not
        # a reasoning model, so its runs pass effort None and get temperature.
        if reasoning_effort is not None:
            payload["reasoning"] = {"effort": reasoning_effort}
        else:
            payload["temperature"] = temperature
        # _parse reports the observed model; hand it the OpenRouter-style slug
        # so a result's model field reads the same under either backend.
        return self._send(payload, key, model)

    def chat(
        self,
        messages: list[dict],
        model: str,
        *,
        tools: list[dict] | None = None,
        max_tokens: int = 4000,
        temperature: float = 0.0,
        reasoning_effort: str | None = None,
        provider: dict[str, object] | None = None,
    ) -> ToolTurn:
        """One multi-message tool-calling turn, matching OpenRouterClient.chat.

        The agentic strategies (sandbox, scratchpad) drive a tool loop through
        this method instead of :meth:`complete`. They keep their conversation in
        Chat-Completions shape — ``{"role": ..., "content": ...}``, an assistant
        message carrying ``tool_calls``, and ``{"role": "tool",
        "tool_call_id": ...}`` replies — and ``conversation_tokens`` reads
        ``content`` off every entry to budget the next turn.

        The Responses API shapes the same conversation differently: tool calls
        and their outputs are top-level input items keyed by ``call_id``, not
        roles. So this translates both ways and keeps the strategy's list in the
        shape it expects, which also means a run through this client and a run
        through OpenRouter stay comparable.
        """

        if not messages:
            raise LLMError("chat needs at least one message")
        self._check_provider_pin(provider)
        key = self._require_key()
        payload: dict[str, object] = {
            "model": direct_model_name(model),
            "input": _responses_input(messages),
            "max_output_tokens": max_tokens,
            "store": False,
        }
        if reasoning_effort is not None:
            payload["reasoning"] = {"effort": reasoning_effort}
        else:
            payload["temperature"] = temperature
        if tools:
            payload["tools"] = [_responses_tool(tool) for tool in tools]
            payload["tool_choice"] = "auto"
        return self._send_tool_turn(payload, key, model)

    def _send_tool_turn(self, payload: dict[str, object], key: str,
                        model: str) -> ToolTurn:
        """POST one tool-calling turn, reusing the transport's retry policy."""

        captured: dict[str, object] = {}

        def parse(data: object, requested_model: str) -> LLMResponse:
            # _send returns whatever this produces; stash the raw body so the
            # ToolTurn can be built from it after the retries have settled.
            captured["data"] = data
            return LLMResponse(
                text="", model=requested_model, input_tokens=0, output_tokens=0
            )

        original = type(self)._parse
        try:
            type(self)._parse = staticmethod(parse)  # type: ignore[assignment]
            super()._send(payload, key, model)
        finally:
            type(self)._parse = original  # type: ignore[assignment]
        return _tool_turn_from_response(captured["data"], model)

    @staticmethod
    def _check_provider_pin(provider: dict[str, object] | None) -> None:
        """Accept only a pin a direct call can actually honour.

        There is one host, so an ``OpenAI`` pin is already satisfied and any
        other order is a caller mistake worth failing on rather than ignoring.
        """

        order = list((provider or {}).get("order") or ())
        unexpected = [name for name in order if name != OPENAI_PROVIDER_LABEL]
        if unexpected:
            raise LLMError(
                "the direct OpenAI monitor backend cannot honour provider pin "
                f"{unexpected}; it always serves from {OPENAI_PROVIDER_LABEL}"
            )

    def _timeout_for(self, body_bytes: int) -> float:
        """Socket timeout scaled to request size, as OpenRouterClient does.

        A 900k-token monitor prompt takes far longer than the flat timeout to
        prefill, and timing it out only to retry re-pays the same call.
        """

        estimated_tokens = body_bytes / 2.5
        return max(self.timeout, 120.0 + estimated_tokens / 1000.0)

    def _send(self, payload: dict[str, object], key: str, model: str) -> LLMResponse:
        """The inherited POST loop, under the caller's wall-clock deadline."""

        deadline = None
        if self.hard_timeout is not None:
            # Scaled like OpenRouter's: a flat deadline under the socket
            # timeout would kill the largest legitimate chunk calls.
            socket_timeout = self._timeout_for(
                len(str(payload).encode("utf-8"))
            )
            deadline = max(self.hard_timeout, socket_timeout * 1.5)
        with _wall_clock_deadline(deadline):
            return super()._send(payload, key, model)

    @staticmethod
    def _cost_usd(model: str, input_tokens: int, output_tokens: int,
                  cached_tokens: int) -> float | None:
        """Price from the shared table, so the cost gate matches OpenRouter's.

        Cached input is cheaper on OpenAI than this estimate assumes, so the
        figure is an upper bound rather than a billed cost. Unlike OpenRouter,
        the Responses API reports no cost of its own.
        """

        del cached_tokens
        slug = model if model.startswith(OPENAI_SLUG_PREFIX) else (
            OPENAI_SLUG_PREFIX + model
        )
        return estimate_cost_usd(slug, input_tokens, output_tokens)


__all__ = [
    "OPENAI_DIRECT_BACKEND",
    "OPENAI_RESPONSES_ENDPOINT",
    "OpenAIDirectMonitorClient",
    "direct_model_name",
]


def _responses_tool(tool: dict) -> dict:
    """Chat-Completions tool schema -> the flat shape Responses expects."""

    if tool.get("type") != "function":
        raise LLMError(f"unsupported tool type {tool.get('type')!r}")
    function = tool.get("function")
    if not isinstance(function, dict):
        # Already flat (Responses shape); pass it through unchanged.
        return dict(tool)
    return {
        "type": "function",
        "name": function.get("name"),
        "description": function.get("description"),
        "parameters": function.get("parameters") or {},
    }


def _responses_input(messages: list[dict]) -> list[dict]:
    """Chat-Completions conversation -> Responses input items.

    A tool reply becomes a ``function_call_output`` keyed by ``call_id``. An
    assistant turn that called tools replays the exact ``function_call`` items
    the API returned, which this client stashed on the message under
    ``_responses_items``; without them the follow-up ``function_call_output``
    would reference a call the model never sees.
    """

    items: list[dict] = []
    for message in messages:
        role = message.get("role")
        if role == "tool":
            items.append({
                "type": "function_call_output",
                "call_id": message.get("tool_call_id") or "",
                "output": str(message.get("content") or ""),
            })
            continue
        stashed = message.get("_responses_items")
        if isinstance(stashed, list) and stashed:
            items.extend(stashed)
            continue
        content = message.get("content")
        items.append({"role": role or "user", "content": str(content or "")})
    return items


def _tool_turn_from_response(data: object, requested_model: str) -> ToolTurn:
    """Build a ToolTurn from a Responses body, in Chat-Completions shape."""

    if not isinstance(data, dict):
        raise LLMError("malformed OpenAI response: expected an object")
    output = data.get("output")
    if not isinstance(output, list):
        raise LLMError("malformed OpenAI response: missing output items")

    parts: list[str] = []
    calls: list[ToolCall] = []
    raw_items: list[dict] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        kind = item.get("type")
        if kind == "message":
            raw_items.append(item)
            for block in item.get("content") or []:
                if isinstance(block, dict) and block.get("type") == "output_text":
                    value = block.get("text")
                    if isinstance(value, str) and value:
                        parts.append(value)
        elif kind == "function_call":
            raw_items.append(item)
            raw_args = item.get("arguments")
            if isinstance(raw_args, str):
                try:
                    args = json.loads(raw_args or "{}")
                except json.JSONDecodeError:
                    args = {"_unparsed_arguments": raw_args}
            else:
                args = raw_args or {}
            calls.append(ToolCall(
                id=str(item.get("call_id") or item.get("id") or ""),
                name=str(item.get("name") or ""),
                arguments=args if isinstance(args, dict) else {"value": args},
            ))
        elif kind == "reasoning":
            # Reasoning items must be replayed verbatim or the API rejects the
            # follow-up turn that references this one's tool calls.
            raw_items.append(item)

    text = "".join(parts).strip()
    usage = data.get("usage")
    if not isinstance(usage, dict):
        raise LLMError("malformed OpenAI response: missing usage")
    details = usage.get("input_tokens_details")
    cached = 0
    if isinstance(details, dict) and isinstance(details.get("cached_tokens"), int):
        cached = max(0, details["cached_tokens"])

    # ``content`` is what conversation_tokens budgets on, and ``tool_calls``
    # is what a reader of the trace expects; ``_responses_items`` carries the
    # verbatim items needed to replay this turn on the next round-trip.
    assistant_message: dict = {
        "role": "assistant",
        "content": text,
        "_responses_items": raw_items,
    }
    if calls:
        assistant_message["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {"name": call.name,
                             "arguments": json.dumps(call.arguments)},
            }
            for call in calls
        ]

    status = data.get("status")
    return ToolTurn(
        text=text,
        tool_calls=calls,
        assistant_message=assistant_message,
        input_tokens=int(usage.get("input_tokens") or 0),
        output_tokens=int(usage.get("output_tokens") or 0),
        # "completed" is Responses' terminal status; map it to the
        # Chat-Completions vocabulary the strategies already log.
        finish_reason=("tool_calls" if calls else
                       ("stop" if status == "completed" else str(status))),
        # The Responses API reports no cost, so the caller falls back to a
        # token-based estimate rather than recording a false $0.
        cost_usd=None,
        cached_tokens=cached,
        provider=OPENAI_PROVIDER_LABEL,
    )
