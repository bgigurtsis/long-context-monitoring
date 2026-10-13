"""Tests for the prompt-cache breakpoint helpers in ``src.openrouter``.

These cover the pure request-shaping logic (no network): which model families
get an explicit ``cache_control`` breakpoint, that the marker lands on the right
blocks, and that the caller's message list is never mutated.
"""
from __future__ import annotations

import unittest

from long_context_monitoring.openrouter import apply_cache_breakpoints, uses_cache_breakpoints

_EPHEMERAL = {"type": "ephemeral"}


class CacheBreakpointGateTest(unittest.TestCase):
    def test_anthropic_and_gemini_use_breakpoints(self):
        self.assertTrue(uses_cache_breakpoints("anthropic/claude-haiku-4.5"))
        self.assertTrue(uses_cache_breakpoints("anthropic/claude-sonnet-5"))
        self.assertTrue(uses_cache_breakpoints("google/gemini-2.5-pro"))

    def test_auto_caching_providers_do_not(self):
        # OpenAI (luna), Z.ai (GLM default) and DeepSeek cache automatically, so
        # they must be left untouched — no breakpoint sent.
        self.assertFalse(uses_cache_breakpoints("openai/gpt-5.6-luna"))
        self.assertFalse(uses_cache_breakpoints("z-ai/glm-5.2"))
        self.assertFalse(uses_cache_breakpoints("z-ai/glm-5.2:nitro"))
        self.assertFalse(uses_cache_breakpoints("deepseek/deepseek-v4-pro"))


class ApplyCacheBreakpointsTest(unittest.TestCase):
    def test_single_message_prompt_is_marked(self):
        messages = [{"role": "user", "content": "the whole transcript prompt"}]
        out = apply_cache_breakpoints(messages, "anthropic/claude-haiku-4.5")
        self.assertEqual(out[0]["content"], [{
            "type": "text",
            "text": "the whole transcript prompt",
            "cache_control": _EPHEMERAL,
        }])

    def test_auto_caching_provider_is_unchanged(self):
        messages = [{"role": "user", "content": "prompt"}]
        out = apply_cache_breakpoints(messages, "openai/gpt-5.6-luna")
        self.assertEqual(out, messages)
        self.assertIsInstance(out[0]["content"], str)

    def test_first_and_last_marked_middle_untouched(self):
        messages = [
            {"role": "user", "content": "seed"},
            {"role": "assistant", "content": "thinking"},
            {"role": "tool", "tool_call_id": "t1", "content": "tool result"},
        ]
        out = apply_cache_breakpoints(messages, "anthropic/claude-sonnet-5")
        # First (seed) and last (latest turn) carry the breakpoint.
        self.assertEqual(out[0]["content"][0]["cache_control"], _EPHEMERAL)
        self.assertEqual(out[-1]["content"][0]["cache_control"], _EPHEMERAL)
        # The middle message is left as a plain string.
        self.assertEqual(out[1]["content"], "thinking")

    def test_caller_list_and_dicts_not_mutated(self):
        messages = [
            {"role": "user", "content": "seed"},
            {"role": "tool", "tool_call_id": "t1", "content": "result"},
        ]
        apply_cache_breakpoints(messages, "anthropic/claude-haiku-4.5")
        # Originals stay plain strings so the agentic loop can re-mark fresh.
        self.assertEqual(messages[0]["content"], "seed")
        self.assertEqual(messages[1]["content"], "result")

    def test_tool_calls_only_message_is_skipped(self):
        # An assistant turn with no text content (only tool_calls) has nothing to
        # mark; it must pass through without error and leave the seed marked.
        messages = [
            {"role": "user", "content": "seed"},
            {"role": "assistant", "content": None,
             "tool_calls": [{"id": "t1", "function": {"name": "grep"}}]},
        ]
        out = apply_cache_breakpoints(messages, "anthropic/claude-haiku-4.5")
        self.assertEqual(out[0]["content"][0]["cache_control"], _EPHEMERAL)
        self.assertIsNone(out[-1]["content"])

    def test_empty_message_list(self):
        self.assertEqual(apply_cache_breakpoints([], "anthropic/claude-haiku-4.5"), [])


if __name__ == "__main__":
    unittest.main()
