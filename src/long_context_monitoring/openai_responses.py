"""Direct OpenAI Responses transport for neutral compaction.

The campaign keeps this client separate from OpenRouter monitoring.  It uses
only the standard library and never adds credentials to prompts or errors.
"""

from __future__ import annotations

import http.client
import json
import os
import time
import urllib.error
import urllib.request
from collections.abc import Callable

from long_context_monitoring.env import load_dotenv
from long_context_monitoring.openrouter import LLMError, LLMResponse


OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
OPENAI_RESPONSES_ENDPOINT = "api.openai.com/v1/responses"
OPENAI_COMPACTION_BACKEND = "openai-api"
LUNA_MODEL = "gpt-5.6-luna"
LUNA_LONG_CONTEXT_THRESHOLD = 272_000
LUNA_INPUT_PRICE_PER_MTOK = 0.20
LUNA_CACHED_INPUT_PRICE_PER_MTOK = 0.02
LUNA_OUTPUT_PRICE_PER_MTOK = 1.20


def estimate_luna_cost_usd(
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
) -> float:
    """Estimate direct Luna cost with the full-request long-context uplift."""

    if min(input_tokens, output_tokens, cached_input_tokens) < 0:
        raise ValueError("token counts cannot be negative")
    cached = min(input_tokens, cached_input_tokens)
    uncached = input_tokens - cached
    input_multiplier = 2.0 if input_tokens > LUNA_LONG_CONTEXT_THRESHOLD else 1.0
    output_multiplier = 1.5 if input_tokens > LUNA_LONG_CONTEXT_THRESHOLD else 1.0
    input_cost = (
        uncached * LUNA_INPUT_PRICE_PER_MTOK
        + cached * LUNA_CACHED_INPUT_PRICE_PER_MTOK
    ) / 1_000_000
    output_cost = output_tokens * LUNA_OUTPUT_PRICE_PER_MTOK / 1_000_000
    return input_cost * input_multiplier + output_cost * output_multiplier


class OpenAIResponsesClient:
    """Blocking direct OpenAI Responses client for one user-only request."""

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 600.0,
        max_attempts: int = 3,
        backoff_cap_seconds: float = 8.0,
        sleeper: Callable[[float], None] = time.sleep,
        rate_limit_attempts: int | None = None,
    ) -> None:
        load_dotenv()
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.timeout = timeout
        self.max_attempts = max_attempts
        # Defaults to ``max_attempts`` so a compaction call behaves exactly as
        # it did before the budgets were split. Concurrent monitoring raises it.
        self.rate_limit_attempts = (
            max_attempts if rate_limit_attempts is None else rate_limit_attempts
        )
        self.backoff_cap_seconds = backoff_cap_seconds
        self.sleeper = sleeper

    def _require_key(self) -> str:
        if not self.api_key:
            raise LLMError(
                "OPENAI_API_KEY is not set; configure it before a direct API call"
            )
        return self.api_key

    def complete(
        self,
        user: str,
        model: str = LUNA_MODEL,
        max_tokens: int = 20_000,
        temperature: float = 0.0,
        reasoning_effort: str | None = "high",
        response_format: dict[str, object] | None = None,
        provider: dict[str, object] | None = None,
    ) -> LLMResponse:
        """Create one response and return normalized text and provenance."""

        del temperature
        if provider:
            raise LLMError("direct OpenAI requests do not accept provider routing")
        if response_format is not None:
            raise LLMError("direct compaction does not accept a response format")
        if model != LUNA_MODEL:
            raise LLMError(f"direct compaction requires model {LUNA_MODEL}")
        key = self._require_key()
        payload: dict[str, object] = {
            "model": model,
            "input": [{"role": "user", "content": user}],
            "max_output_tokens": max_tokens,
            "store": False,
        }
        if reasoning_effort is not None:
            payload["reasoning"] = {"effort": reasoning_effort}
        return self._send(payload, key, model)

    def _send(self, payload: dict[str, object], key: str, model: str) -> LLMResponse:
        """POST one Responses request, retrying only what is safe to retry.

        Split out of :meth:`complete` so a subclass can build a different
        payload (a monitor call sends temperature and a different model) while
        keeping one transport, one retry policy, and one key-redaction path.
        """

        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        timeout = self._timeout_for(len(body))

        errors = 0
        rate_limits = 0
        last_error: LLMError | None = None
        while errors < self.max_attempts and rate_limits < self.rate_limit_attempts:
            request = urllib.request.Request(
                OPENAI_RESPONSES_URL,
                data=body,
                headers=headers,
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    data = json.loads(response.read().decode("utf-8"))
                return self._parse(data, model)
            except urllib.error.HTTPError as error:
                detail = self._redact(self._read_error(error), key)
                current = LLMError(f"OpenAI HTTP {error.code}: {detail}")
                if error.code == 429:
                    last_error = current
                    rate_limits += 1
                    # No sleep once the budget is spent: the next check ends
                    # the loop, so waiting first only delays the failure.
                    if rate_limits < self.rate_limit_attempts:
                        self._backoff(rate_limits - 1, self._retry_after(error))
                    continue
                if 500 <= error.code < 600:
                    last_error = current
                    errors += 1
                    if errors < self.max_attempts:
                        self._backoff(errors - 1)
                    continue
                raise current from error
            except (urllib.error.URLError, TimeoutError,
                    http.client.HTTPException, OSError) as error:
                detail = self._redact(str(error), key)
                last_error = LLMError(f"OpenAI network error: {detail}")
                errors += 1
                if errors < self.max_attempts:
                    self._backoff(errors - 1)
                continue
            except json.JSONDecodeError as error:
                raise LLMError("malformed OpenAI response: invalid JSON") from error

        spent = "rate limits" if rate_limits >= self.rate_limit_attempts else "attempts"
        raise LLMError(
            f"OpenAI call failed after {errors + rate_limits} attempts "
            f"(budget for {spent} exhausted): {last_error}"
        )

    def _timeout_for(self, body_bytes: int) -> float:
        """Socket timeout for one request; compaction uses the flat timeout."""

        del body_bytes
        return self.timeout

    @staticmethod
    def _retry_after(error: urllib.error.HTTPError) -> float | None:
        """The server's own wait hint, when it sent a usable one.

        OpenAI returns ``Retry-After`` in seconds on a throttle. Obeying it
        beats guessing: a blind exponential backoff either sleeps longer than
        the window or hammers it again before it opens.
        """

        raw = None
        try:
            raw = error.headers.get("Retry-After") if error.headers else None
        except AttributeError:
            return None
        if raw is None:
            return None
        try:
            seconds = float(str(raw).strip())
        except ValueError:
            # The header also permits an HTTP date, which we do not parse;
            # falling back to the exponential schedule is correct there.
            return None
        return seconds if seconds >= 0 else None

    def _backoff(self, attempt: int, retry_after: float | None = None) -> None:
        """Sleep before the next try: the server's hint, else exponential.

        Callers check their own budget first, so reaching here always means
        another attempt follows.
        """

        if retry_after is not None:
            self.sleeper(min(self.backoff_cap_seconds, retry_after))
            return
        self.sleeper(min(self.backoff_cap_seconds, float(2**attempt)))

    @staticmethod
    def _read_error(error: urllib.error.HTTPError) -> str:
        try:
            return error.read().decode("utf-8", "replace")[:500]
        except Exception:  # noqa: BLE001 - the body is diagnostic only
            return str(error.reason or "unknown error")

    @staticmethod
    def _redact(value: str, key: str) -> str:
        return value.replace(key, "[REDACTED]").replace(
            f"Bearer {key}", "Bearer [REDACTED]"
        )

    @staticmethod
    def _cost_usd(model: str, input_tokens: int, output_tokens: int,
                  cached_tokens: int) -> float | None:
        """USD for one call. Overridden per backend; Luna prices its own."""

        del model
        return estimate_luna_cost_usd(input_tokens, output_tokens, cached_tokens)

    @classmethod
    def _parse(cls, data: object, requested_model: str) -> LLMResponse:
        if not isinstance(data, dict):
            raise LLMError("malformed OpenAI response: expected an object")
        response_id = data.get("id")
        observed_model = data.get("model")
        status = data.get("status")
        incomplete = data.get("incomplete_details")
        if not isinstance(response_id, str) or not response_id:
            raise LLMError("malformed OpenAI response: missing response id")
        if not isinstance(observed_model, str) or not observed_model:
            raise LLMError("malformed OpenAI response: missing model")
        if status != "completed":
            reason = incomplete.get("reason") if isinstance(incomplete, dict) else None
            suffix = f" ({reason})" if reason else ""
            raise LLMError(f"OpenAI response status was {status!r}{suffix}")

        parts: list[str] = []
        output = data.get("output")
        if not isinstance(output, list):
            raise LLMError("malformed OpenAI response: missing output items")
        for item in output:
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "output_text":
                    continue
                value = block.get("text")
                if isinstance(value, str) and value:
                    parts.append(value)
        text = "".join(parts).strip()
        if not text:
            raise LLMError("malformed OpenAI response: empty output_text")

        usage = data.get("usage")
        if not isinstance(usage, dict):
            raise LLMError("malformed OpenAI response: missing usage")
        input_tokens = _nonnegative_int(usage.get("input_tokens"), "input_tokens")
        output_tokens = _nonnegative_int(usage.get("output_tokens"), "output_tokens")
        details = usage.get("input_tokens_details")
        cached_tokens = 0
        if isinstance(details, dict) and details.get("cached_tokens") is not None:
            cached_tokens = _nonnegative_int(
                details.get("cached_tokens"), "cached_tokens"
            )
        return LLMResponse(
            text=text,
            model=observed_model or requested_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            generation_id=response_id,
            provider="OpenAI",
            finish_reason="completed",
            native_finish_reason=None,
            # Priced on the *requested* model: that is the slug the price
            # tables are keyed by. OpenAI echoes back a dated build
            # ("gpt-4.1-nano-2025-04-14") that no table lists, and pricing it
            # would silently fall back to the expensive default rate.
            cost_usd=cls._cost_usd(
                requested_model,
                input_tokens,
                output_tokens,
                cached_tokens,
            ),
            cached_input_tokens=cached_tokens,
            status=str(status),
            incomplete_details=(
                dict(incomplete) if isinstance(incomplete, dict) else None
            ),
        )


def _nonnegative_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise LLMError(f"malformed OpenAI response: invalid {field}")
    return value
