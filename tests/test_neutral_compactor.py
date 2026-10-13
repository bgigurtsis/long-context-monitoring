"""Tests for the standalone neutral compactor."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from long_context_monitoring.neutral_compactor import (
    COMPACTION_PROMPT,
    COMPACTION_PROMPT_SHA256,
    DEFAULT_MODEL,
    DEFAULT_REASONING_EFFORT,
    CompactionError,
    ConversationMessage,
    compact,
    group_messages,
    main,
    parse_summary,
    read_claude_messages,
    render_request,
    select_for_compaction,
)
from long_context_monitoring.openrouter import LLMResponse


class FakeClient:
    def __init__(
        self,
        text: str = "<analysis>check</analysis><summary>Keep this.</summary>",
    ) -> None:
        self.text = text
        self.calls: list[dict[str, object]] = []

    def complete(
        self,
        user: str,
        model: str,
        max_tokens: int = 20_000,
        temperature: float = 0.0,
        reasoning_effort: str | None = None,
        provider: dict[str, object] | None = None,
    ) -> LLMResponse:
        self.calls.append(
            {
                "user": user,
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "reasoning_effort": reasoning_effort,
                "provider": provider,
            }
        )
        return LLMResponse(self.text, model, 123, 45, provider="OpenAI")


def message(
    kind: str,
    content: str,
    message_id: str | None = None,
    **kwargs: bool,
) -> ConversationMessage:
    return ConversationMessage(
        type=kind,
        content=content,
        message_id=message_id,
        **kwargs,
    )


class GroupingTests(unittest.TestCase):
    def test_groups_responses_and_preserves_newest_group(self) -> None:
        messages = [
            message("user", "first"),
            message("assistant", "a", "response-1"),
            message("assistant", "b", "response-1"),
            message("user", "second"),
            message("assistant", "c", "response-2"),
            message("user", "latest"),
        ]
        groups = group_messages(messages)
        selection = select_for_compaction(messages)
        self.assertEqual(len(groups), 3)
        self.assertEqual(
            [item.content for item in selection.preserved],
            ["c", "latest"],
        )
        self.assertEqual(
            [item.content for item in selection.summarized],
            ["first", "a", "b", "second"],
        )

    def test_virtual_and_resumed_entries_do_not_start_groups(self) -> None:
        messages = [
            message("user", "first"),
            message("assistant", "a", "response-1"),
            message("assistant", "virtual", "response-2", virtual=True),
            message(
                "assistant",
                "resumed",
                "response-3",
                resumed_from_incomplete_thinking=True,
            ),
            message("assistant", "next", "response-4"),
        ]
        self.assertEqual(len(group_messages(messages)), 3)

    def test_refuses_when_no_old_group_exists(self) -> None:
        with self.assertRaisesRegex(CompactionError, "old group"):
            select_for_compaction([message("user", "only")])


class TranscriptTests(unittest.TestCase):
    def test_ignores_progress_and_history_before_latest_boundary(self) -> None:
        entries = [
            {"type": "user", "message": {"content": "old"}},
            {"type": "progress", "message": {"content": "noise"}},
            {"type": "system", "subtype": "compact_boundary"},
            {"type": "user", "message": {"content": "summary"}},
            {
                "type": "assistant",
                "message": {"id": "a1", "content": "answer"},
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "session.jsonl"
            path.write_text(
                "\n".join(json.dumps(entry) for entry in entries) + "\n",
                encoding="utf-8",
            )
            found = read_claude_messages(path)
        self.assertEqual([item.content for item in found], ["summary", "answer"])

    def test_deduplicates_repeated_native_entries_by_uuid(self) -> None:
        repeated = {
            "type": "user",
            "uuid": "same-entry",
            "message": {"content": "once"},
        }
        entries = [
            repeated,
            repeated,
            {"type": "assistant", "message": {"id": "a1", "content": "answer"}},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "session.jsonl"
            path.write_text(
                "\n".join(json.dumps(entry) for entry in entries) + "\n",
                encoding="utf-8",
            )
            found = read_claude_messages(path)
        self.assertEqual([item.content for item in found], ["once", "answer"])


class RequestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.messages = [
            message("user", "request"),
            message("assistant", "done", "a1"),
            message("user", "recent"),
            message("assistant", "working", "a2"),
        ]

    def test_request_uses_prompt_roles_and_optional_instructions(self) -> None:
        request = render_request(
            select_for_compaction(self.messages),
            "Keep the branch name.",
        )
        self.assertTrue(request.startswith(COMPACTION_PROMPT))
        self.assertIn(
            "Additional Instructions:\nKeep the branch name.",
            request,
        )
        self.assertIn('"role":"user","content":"request"', request)
        self.assertNotIn('"content":"working"', request)
        self.assertEqual(
            hashlib.sha256(COMPACTION_PROMPT.encode("utf-8")).hexdigest(),
            "0d0454635a524796b2f72b581392c196d5a38501028d0ce9fd9a92702a26d3ff",
        )
        self.assertEqual(
            COMPACTION_PROMPT_SHA256,
            "0d0454635a524796b2f72b581392c196d5a38501028d0ce9fd9a92702a26d3ff",
        )

    def test_request_replaces_large_media_payloads(self) -> None:
        messages = [
            ConversationMessage(
                "user",
                [{"type": "image", "source": {"data": "large-base64"}}],
            ),
            message("assistant", "done", "a1"),
            message("assistant", "latest", "a2"),
        ]
        request = render_request(select_for_compaction(messages))
        self.assertIn("[image]", request)
        self.assertNotIn("large-base64", request)

    def test_parser_removes_analysis_and_extracts_summary(self) -> None:
        self.assertEqual(
            parse_summary(
                "<analysis>private</analysis>"
                "<summary>Useful.\n\n\nState.</summary>"
            ),
            "Summary:\nUseful.\n\nState.",
        )
        self.assertEqual(parse_summary("fallback text"), "fallback text")
        with self.assertRaisesRegex(CompactionError, "empty"):
            parse_summary("<analysis>private</analysis>")

    def test_compact_makes_one_call_and_wraps_result(self) -> None:
        client = FakeClient()
        result = compact(self.messages, Path("native.jsonl"), client)
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(client.calls[0]["max_tokens"], 20_000)
        self.assertEqual(client.calls[0]["temperature"], 0.0)
        self.assertEqual(
            client.calls[0]["reasoning_effort"], DEFAULT_REASONING_EFFORT
        )
        self.assertEqual(client.calls[0]["provider"], {"order": ["OpenAI"], "allow_fallbacks": False})
        self.assertEqual(result.compaction_backend, "openrouter")
        self.assertEqual(
            result.compaction_endpoint,
            "openrouter.ai/api/v1/chat/completions",
        )
        self.assertEqual(result.requested_model, DEFAULT_MODEL)
        self.assertEqual(result.reasoning_effort, DEFAULT_REASONING_EFFORT)
        self.assertEqual(result.requested_provider, ("OpenAI",))
        self.assertEqual(result.provider, "OpenAI")
        self.assertEqual(len(result.request_sha256), 64)
        self.assertEqual(len(result.result_sha256), 64)
        self.assertEqual(result.parsed_summary, "Summary:\nKeep this.")
        self.assertIn("Continue directly", result.synthetic_user_message)
        self.assertEqual(
            [item.content for item in result.preserved],
            ["working"],
        )


class CliTests(unittest.TestCase):
    def test_dry_run_needs_no_output_or_model_call(self) -> None:
        entries = [
            {"type": "user", "message": {"content": "first"}},
            {
                "type": "assistant",
                "message": {"id": "a1", "content": "done"},
            },
            {"type": "user", "message": {"content": "latest"}},
            {
                "type": "assistant",
                "message": {"id": "a2", "content": "working"},
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "session.jsonl"
            path.write_text(
                "\n".join(json.dumps(entry) for entry in entries) + "\n",
                encoding="utf-8",
            )
            self.assertEqual(main([str(path), "--dry-run"]), 0)

    def test_openrouter_requires_explicit_transport(self) -> None:
        entries = [
            {"type": "user", "message": {"content": "first"}},
            {"type": "assistant", "message": {"id": "a1", "content": "done"}},
            {"type": "assistant", "message": {"id": "a2", "content": "latest"}},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "session.jsonl"
            path.write_text(
                "\n".join(json.dumps(entry) for entry in entries) + "\n",
                encoding="utf-8",
            )
            self.assertEqual(
                main([str(path), "--backend", "openrouter", "--dry-run"]),
                0,
            )


if __name__ == "__main__":
    unittest.main()
