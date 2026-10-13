"""Check transport retries, deadlines, and provider identity without network calls."""
from __future__ import annotations

import io
import json
import unittest
import urllib.error
from unittest import mock

from long_context_monitoring.openrouter import LLMError, OpenRouterClient


def ok_body() -> bytes:
    return json.dumps({
        "model": "deepseek/deepseek-v4-flash-0731",
        "provider": "DeepInfra",
        "choices": [{"message": {"content": "<score>3</score>"},
                     "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 2},
    }).encode("utf-8")


class Response:
    """Minimal stand-in for the urlopen context manager."""

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return ok_body()


def http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        "https://openrouter.ai", code, "err", {}, io.BytesIO(b'{"error":{}}'))


class RateLimitBudgetTests(unittest.TestCase):
    def setUp(self) -> None:
        # Patch the sleep so the exponential backoff does not slow the suite.
        patcher = mock.patch("long_context_monitoring.openrouter.time.sleep")
        self.sleep = patcher.start()
        self.addCleanup(patcher.stop)

    def _client(self, **kw) -> OpenRouterClient:
        return OpenRouterClient(api_key="test", **kw)

    def test_rate_limits_do_not_spend_the_billable_budget(self) -> None:
        """Ten 429s then success. Under one shared six-attempt budget this
        raised; the rate-limit budget must carry it through."""
        attempts = [http_error(429)] * 10 + [Response()]
        with mock.patch("long_context_monitoring.openrouter.urllib.request.urlopen",
                        side_effect=attempts) as urlopen:
            client = self._client(max_attempts=6, rate_limit_attempts=14)
            result = client.complete("p", "deepseek/deepseek-v4-flash-0731")
        self.assertEqual(urlopen.call_count, 11)
        self.assertIn("<score>3</score>", result.text)

    def test_rate_limit_budget_is_still_bounded(self) -> None:
        """It is a larger budget, not an unlimited one: a provider that is down
        must fail rather than spin forever."""
        with mock.patch("long_context_monitoring.openrouter.urllib.request.urlopen",
                        side_effect=[http_error(429)] * 50) as urlopen:
            client = self._client(max_attempts=6, rate_limit_attempts=4)
            with self.assertRaises(LLMError) as caught:
                client.complete("p", "deepseek/deepseek-v4-flash-0731")
        self.assertEqual(urlopen.call_count, 4)
        self.assertIn("rate-limited", str(caught.exception))

    def test_server_errors_keep_the_smaller_budget(self) -> None:
        """A 5xx may already have been billed, so it must not borrow the
        rate-limit allowance."""
        with mock.patch("long_context_monitoring.openrouter.urllib.request.urlopen",
                        side_effect=[http_error(503)] * 50) as urlopen:
            client = self._client(max_attempts=3, rate_limit_attempts=14)
            with self.assertRaises(LLMError):
                client.complete("p", "deepseek/deepseek-v4-flash-0731")
        self.assertEqual(urlopen.call_count, 3)

    def test_a_fatal_status_is_not_retried_at_all(self) -> None:
        """Check a fatal status is not retried at all."""
        with mock.patch("long_context_monitoring.openrouter.urllib.request.urlopen",
                        side_effect=[http_error(404)] * 20) as urlopen:
            client = self._client()
            with self.assertRaisesRegex(LLMError, "HTTP 404"):
                client.complete("p", "deepseek/deepseek-v4-flash-0731")
        self.assertEqual(urlopen.call_count, 1)

    def test_a_timeout_still_gets_exactly_one_retry(self) -> None:
        """Unchanged behaviour, and the reason is cost: a timed-out large
        prompt may have been billed, so it is retried once and no more."""
        with mock.patch("long_context_monitoring.openrouter.urllib.request.urlopen",
                        side_effect=[TimeoutError("timed out")] * 10) as urlopen:
            client = self._client(max_attempts=6, rate_limit_attempts=14)
            with self.assertRaisesRegex(LLMError, "timed out twice"):
                client.complete("p", "deepseek/deepseek-v4-flash-0731")
        self.assertEqual(urlopen.call_count, 2)

    def test_a_truncated_body_is_a_billed_retry_not_an_escape(self) -> None:
        """The server closed a chunked 200 mid-body. http.client raises
        IncompleteRead, which is not a URLError, so before this it escaped the
        retry loop and every handler above it: the invocation died with a
        clean "ended" line and no recorded reason. It is now a network error
        on the billed budget, retried, and legible if it exhausts."""
        import http.client

        class Truncated(Response):
            def read(self):
                raise http.client.IncompleteRead(b"partial")

        with mock.patch("long_context_monitoring.openrouter.urllib.request.urlopen",
                        side_effect=[Truncated(), Response()]) as urlopen:
            client = self._client(max_attempts=6, rate_limit_attempts=14)
            result = client.complete("p", "deepseek/deepseek-v4-flash-0731")
        self.assertEqual(urlopen.call_count, 2)
        self.assertIn("<score>3</score>", result.text)

        with mock.patch("long_context_monitoring.openrouter.urllib.request.urlopen",
                        side_effect=[Truncated()] * 10) as urlopen:
            client = self._client(max_attempts=3, rate_limit_attempts=14)
            with self.assertRaisesRegex(LLMError, "network error"):
                client.complete("p", "deepseek/deepseek-v4-flash-0731")
        self.assertEqual(urlopen.call_count, 3)

    def test_an_http_200_error_payload_counts_as_a_rate_limit(self) -> None:
        """OpenRouter returns some upstream rate limits under HTTP 200 with an
        error object. Those are refused upstream too, so they draw on the same
        larger budget rather than the billable one."""
        class Overloaded(Response):
            def read(self):
                return json.dumps(
                    {"error": {"code": 429, "message": "rate limited"}}
                ).encode("utf-8")

        attempts = [Overloaded()] * 8 + [Response()]
        with mock.patch("long_context_monitoring.openrouter.urllib.request.urlopen",
                        side_effect=attempts) as urlopen:
            client = self._client(max_attempts=6, rate_limit_attempts=14)
            client.complete("p", "deepseek/deepseek-v4-flash-0731")
        self.assertEqual(urlopen.call_count, 9)


if __name__ == "__main__":
    unittest.main()
