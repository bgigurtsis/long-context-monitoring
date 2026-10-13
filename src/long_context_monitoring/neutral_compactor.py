"""A small, neutral implementation of Claude Code-style compaction.

The compactor makes one model request with no tools. It receives only the
conversation selected for summarization and the public compaction prompt. It
does not inherit the policy session's hidden side-task instructions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from importlib.resources import files
from pathlib import Path
from typing import Protocol, Sequence

from long_context_monitoring.env import load_dotenv
from long_context_monitoring.openai_responses import (
    LUNA_MODEL,
    OPENAI_COMPACTION_BACKEND,
    OPENAI_RESPONSES_ENDPOINT,
    OpenAIResponsesClient,
    estimate_luna_cost_usd,
)
from long_context_monitoring.openrouter import (
    LLMError,
    LLMResponse,
    OpenRouterClient,
    assert_pinned_provider,
    default_provider_order,
    estimate_cost_usd,
    provider_pin,
)


DEFAULT_BACKEND = "openrouter"
DEFAULT_MODEL = "openai/gpt-5.6-luna"
OPENROUTER_MODEL = "openai/gpt-5.6-luna"
OPENROUTER_ENDPOINT = "openrouter.ai/api/v1/chat/completions"
DEFAULT_REASONING_EFFORT = "high"
MAX_OUTPUT_TOKENS = 20_000

COMPACTION_PROMPT = files("prompts").joinpath("compaction.md").read_text(encoding="utf-8")
COMPACTION_PROMPT_SHA256 = "0d0454635a524796b2f72b581392c196d5a38501028d0ce9fd9a92702a26d3ff"

SUMMARY_WRAPPER = """This session continues from an earlier conversation that exceeded its context window.
The summary below covers the removed portion.

{summary}

If exact details are needed, inspect the native transcript at:
{transcript_path}

Recent messages following this summary are preserved verbatim.

Continue directly from the previous state.
Do not recap the summary or ask the user to repeat information."""


class CompactionError(RuntimeError):
    """The transcript, model response, or budget failed compaction."""


class CompactorClient(Protocol):
    """The one operation needed from a tool-free model transport."""

    def complete(
        self,
        user: str,
        model: str,
        max_tokens: int = MAX_OUTPUT_TOKENS,
        temperature: float = 0.0,
        reasoning_effort: str | None = None,
        provider: dict[str, object] | None = None,
    ) -> LLMResponse:
        ...


@dataclass(frozen=True)
class ConversationMessage:
    """One native conversation entry used by the grouping algorithm."""

    type: str
    content: object
    uuid: str | None = None
    message_id: str | None = None
    virtual: bool = False
    resumed_from_incomplete_thinking: bool = False


@dataclass(frozen=True)
class CompactionSelection:
    """The old messages to summarize and the recent suffix to retain."""

    summarized: tuple[ConversationMessage, ...]
    preserved: tuple[ConversationMessage, ...]
    group_count: int


@dataclass(frozen=True)
class CompactionResult:
    """The parsed replacement context and model-call provenance."""

    parsed_summary: str
    synthetic_user_message: str
    preserved: tuple[ConversationMessage, ...]
    compaction_backend: str
    compaction_endpoint: str
    requested_model: str
    model: str
    response_id: str | None
    reasoning_effort: str | None
    requested_provider: tuple[str, ...]
    provider: str | None
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int
    estimated_cost_usd: float
    request_sha256: str
    result_sha256: str
    response_status: str | None
    incomplete_details: dict[str, object] | None


def backend_identity(backend: str) -> tuple[str, str]:
    """Return the stable provenance names for one compaction transport."""

    if backend == "openai":
        return OPENAI_COMPACTION_BACKEND, OPENAI_RESPONSES_ENDPOINT
    if backend == "openrouter":
        return "openrouter", OPENROUTER_ENDPOINT
    raise CompactionError(f"unsupported compaction backend: {backend}")


def compactor_client(backend: str) -> CompactorClient:
    """Build the configured neutral compactor client."""

    if backend == "openai":
        return OpenAIResponsesClient()
    if backend == "openrouter":
        return OpenRouterClient()
    raise CompactionError(f"unsupported compaction backend: {backend}")


def estimate_compaction_cost_usd(
    backend: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_input_tokens: int = 0,
) -> float:
    """Estimate cost without mixing direct and OpenRouter price rules."""

    if backend == "openai":
        if model != LUNA_MODEL:
            raise CompactionError(f"direct OpenAI compaction requires {LUNA_MODEL}")
        return estimate_luna_cost_usd(
            input_tokens,
            output_tokens,
            cached_input_tokens,
        )
    if backend == "openrouter":
        return estimate_cost_usd(model, input_tokens, output_tokens)
    raise CompactionError(f"unsupported compaction backend: {backend}")


def _copy_json(value: object) -> object:
    """Detach transcript content from the parsed native record."""

    return json.loads(json.dumps(value, ensure_ascii=False))


def _content_for_compactor(content: object) -> object:
    """Replace large media payloads while retaining their place in history."""

    if not isinstance(content, list):
        return content
    copied: list[object] = []
    for block in content:
        if isinstance(block, dict) and block.get("type") in {"image", "document"}:
            copied.append(f"[{block['type']}]")
        else:
            copied.append(block)
    return copied


def read_claude_messages(path: Path) -> list[ConversationMessage]:
    """Read the active conversation from a native Claude Code JSONL file.

    Progress records are ignored. An existing compaction boundary resets the
    active conversation because older entries left the current model context.
    """

    messages: list[ConversationMessage] = []
    seen_uuids: set[str] = set()
    try:
        lines = path.read_text(encoding="utf-8", errors="strict").split("\n")
    except OSError as error:
        raise CompactionError(f"could not read transcript {path}: {error}") from error

    for line_number, line in enumerate(lines, start=1):
        # ``split("\n")`` leaves a trailing empty string on a file that ends in
        # a newline, where ``splitlines`` did not. Blank lines carry no entry.
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as error:
            raise CompactionError(f"invalid JSONL at {path}:{line_number}") from error
        if not isinstance(entry, dict):
            raise CompactionError(f"JSONL entry at {path}:{line_number} is not an object")
        if entry.get("type") == "progress":
            continue
        if entry.get("type") == "system" and entry.get("subtype") == "compact_boundary":
            messages = []
            seen_uuids = set()
            continue
        if entry.get("type") not in {"user", "assistant"}:
            continue
        message = entry.get("message")
        if not isinstance(message, dict) or "content" not in message:
            continue
        entry_uuid = entry.get("uuid")
        if isinstance(entry_uuid, str):
            if entry_uuid in seen_uuids:
                continue
            seen_uuids.add(entry_uuid)
        message_id = message.get("id")
        messages.append(
            ConversationMessage(
                type=str(entry["type"]),
                content=_copy_json(message["content"]),
                uuid=entry_uuid if isinstance(entry_uuid, str) else None,
                message_id=message_id if isinstance(message_id, str) else None,
                virtual=entry.get("virtual") is True,
                resumed_from_incomplete_thinking=(
                    entry.get("resumed_from_incomplete_thinking") is True
                ),
            )
        )
    return messages


def group_messages(
    messages: Sequence[ConversationMessage],
) -> list[list[ConversationMessage]]:
    """Group entries around distinct assistant API responses like Claude Code."""

    groups: list[list[ConversationMessage]] = []
    current: list[ConversationMessage] = []
    previous_assistant_id: str | None = None

    for message in messages:
        if message.virtual:
            current.append(message)
            continue

        starts_group = (
            message.type == "assistant"
            and message.message_id != previous_assistant_id
            and not message.resumed_from_incomplete_thinking
            and bool(current)
        )
        if starts_group:
            groups.append(current)
            current = [message]
        else:
            current.append(message)

        if message.type == "assistant":
            previous_assistant_id = message.message_id

    if current:
        groups.append(current)
    return groups


def select_for_compaction(
    messages: Sequence[ConversationMessage], groups_to_preserve: int = 1
) -> CompactionSelection:
    """Select old groups for summary while preserving the newest group."""

    if groups_to_preserve < 1:
        raise ValueError("groups_to_preserve must be at least one")
    groups = group_messages(messages)
    if len(groups) <= groups_to_preserve:
        raise CompactionError(
            "compaction needs at least one old group and one preserved group"
        )
    split = len(groups) - groups_to_preserve
    summarized = tuple(message for group in groups[:split] for message in group)
    preserved = tuple(message for group in groups[split:] for message in group)
    return CompactionSelection(summarized, preserved, len(groups))


def render_request(
    selection: CompactionSelection, additional_instructions: str | None = None
) -> str:
    """Render one deterministic, role-preserving compactor request."""

    history = [
        {"role": message.type, "content": _content_for_compactor(message.content)}
        for message in selection.summarized
    ]
    instructions = ""
    if additional_instructions and additional_instructions.strip():
        instructions = f"\n\nAdditional Instructions:\n{additional_instructions.strip()}"
    return (
        f"{COMPACTION_PROMPT}{instructions}\n\n"
        "<conversation_history>\n"
        f"{json.dumps(history, ensure_ascii=False, separators=(',', ':'))}\n"
        "</conversation_history>"
    )


def parse_summary(text: str) -> str:
    """Parse Claude-compatible XML while tolerating harmless model chatter."""

    without_analysis = re.sub(
        r"<analysis\b[^>]*>.*?</analysis\s*>",
        "",
        text,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )
    match = re.search(
        r"<summary\b[^>]*>(.*?)</summary\s*>",
        without_analysis,
        flags=re.IGNORECASE | re.DOTALL,
    )
    parsed = f"Summary:\n{match.group(1).strip()}" if match else without_analysis.strip()
    parsed = re.sub(r"\n[ \t]*\n(?:[ \t]*\n)+", "\n\n", parsed).strip()
    if not parsed:
        raise CompactionError("compactor returned an empty summary")
    return parsed


def compact(
    messages: Sequence[ConversationMessage],
    transcript_path: Path,
    client: CompactorClient,
    model: str = DEFAULT_MODEL,
    additional_instructions: str | None = None,
    reasoning_effort: str | None = DEFAULT_REASONING_EFFORT,
    backend: str = DEFAULT_BACKEND,
) -> CompactionResult:
    """Make one tool-free model call and return the replacement context."""

    selection = select_for_compaction(messages)
    request = render_request(selection, additional_instructions)
    backend_name, endpoint = backend_identity(backend)
    if backend == "openai" and model != LUNA_MODEL:
        raise CompactionError(f"direct OpenAI compaction requires {LUNA_MODEL}")
    if backend == "openrouter" and model == LUNA_MODEL:
        raise CompactionError(
            "OpenRouter compaction requires an OpenRouter model slug"
        )
    requested_provider = (
        default_provider_order(model, None) if backend == "openrouter" else ()
    )
    provider = provider_pin(requested_provider or None) if backend == "openrouter" else None
    try:
        response = client.complete(
            request,
            model,
            max_tokens=MAX_OUTPUT_TOKENS,
            temperature=0.0,
            reasoning_effort=reasoning_effort,
            provider=provider,
        )
    except LLMError as error:
        raise CompactionError(f"compactor model call failed: {error}") from error
    if backend == "openrouter":
        try:
            assert_pinned_provider(response, requested_provider or None)
        except LLMError as error:
            raise CompactionError(f"compactor provider pin failed: {error}") from error
    parsed = parse_summary(response.text)
    wrapper = SUMMARY_WRAPPER.format(
        summary=parsed,
        transcript_path=transcript_path.resolve(),
    )
    return CompactionResult(
        parsed_summary=parsed,
        synthetic_user_message=wrapper,
        preserved=selection.preserved,
        compaction_backend=backend_name,
        compaction_endpoint=endpoint,
        requested_model=model,
        model=response.model,
        response_id=response.generation_id,
        reasoning_effort=reasoning_effort,
        requested_provider=requested_provider,
        provider=response.provider,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        cached_input_tokens=response.cached_input_tokens,
        estimated_cost_usd=(
            response.cost_usd
            if response.cost_usd is not None
            else estimate_compaction_cost_usd(
                backend,
                model,
                response.input_tokens,
                response.output_tokens,
                response.cached_input_tokens,
            )
        ),
        request_sha256=hashlib.sha256(request.encode("utf-8")).hexdigest(),
        result_sha256=hashlib.sha256(parsed.encode("utf-8")).hexdigest(),
        response_status=response.status,
        incomplete_details=response.incomplete_details,
    )


def _estimate_tokens(text: str) -> int:
    return max(1, (len(text.encode("utf-8")) + 3) // 4)


def _result_json(result: CompactionResult) -> dict[str, object]:
    return {
        "schema_version": 1,
        "query_source": "compact",
        "max_turns": 1,
        "tools": [],
        "skip_transcript": True,
        "skip_cache_write": True,
        "compaction_prompt_sha256": COMPACTION_PROMPT_SHA256,
        "compaction_backend": result.compaction_backend,
        "compaction_endpoint": result.compaction_endpoint,
        "requested_model": result.requested_model,
        "observed_model": result.model,
        "response_id": result.response_id,
        "reasoning_effort": result.reasoning_effort,
        "requested_provider": list(result.requested_provider),
        "provider": result.provider,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "cached_input_tokens": result.cached_input_tokens,
        "estimated_cost_usd": result.estimated_cost_usd,
        "request_sha256": result.request_sha256,
        "result_sha256": result.result_sha256,
        "response_status": result.response_status,
        "incomplete_details": result.incomplete_details,
        "parsed_summary": result.parsed_summary,
        "synthetic_user_message": result.synthetic_user_message,
        "preserved_messages": [asdict(message) for message in result.preserved],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lcm compact",
        description="Create a neutral Claude-compatible compaction summary.",
    )
    parser.add_argument("transcript", type=Path, help="native Claude Code JSONL")
    parser.add_argument("--output", type=Path, help="write replacement context as JSON")
    parser.add_argument(
        "--backend",
        default=DEFAULT_BACKEND,
        choices=("openai", "openrouter"),
    )
    parser.add_argument("--model")
    parser.add_argument(
        "--reasoning-effort",
        default=DEFAULT_REASONING_EFFORT,
        choices=("none", "minimal", "low", "medium", "high", "xhigh", "max"),
    )
    parser.add_argument("--instructions", help="additional compaction instructions")
    parser.add_argument("--max-cost-usd", type=float, default=5.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    try:
        model = args.model or (
            DEFAULT_MODEL
            if args.backend == "openai"
            else OPENROUTER_MODEL
        )
        messages = read_claude_messages(args.transcript)
        selection = select_for_compaction(messages)
        request = render_request(selection, args.instructions)
        estimated_input = _estimate_tokens(request)
        estimated_cost = estimate_compaction_cost_usd(
            args.backend,
            model,
            estimated_input,
            MAX_OUTPUT_TOKENS,
        )
        backend_name, endpoint = backend_identity(args.backend)
        preview = {
            "backend": backend_name,
            "endpoint": endpoint,
            "model": model,
            "reasoning_effort": args.reasoning_effort,
            "provider": (
                list(default_provider_order(model, None))
                if args.backend == "openrouter"
                else []
            ),
            "groups": selection.group_count,
            "summarized_messages": len(selection.summarized),
            "preserved_messages": len(selection.preserved),
            "estimated_input_tokens": estimated_input,
            "estimated_max_cost_usd": estimated_cost,
        }
        if args.dry_run:
            print(json.dumps(preview, indent=2))
            return 0
        if args.output is None:
            raise CompactionError("--output is required for a real compaction")
        if args.max_cost_usd < 0:
            raise CompactionError("--max-cost-usd cannot be negative")
        if estimated_cost > args.max_cost_usd:
            raise CompactionError(
                f"estimated max cost ${estimated_cost:.4f} exceeds "
                f"--max-cost-usd ${args.max_cost_usd:.4f}"
            )
        if args.output.exists():
            raise CompactionError(f"refusing to overwrite {args.output}")
        load_dotenv()
        result = compact(
            messages,
            args.transcript,
            compactor_client(args.backend),
            model,
            args.instructions,
            args.reasoning_effort,
            args.backend,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(_result_json(result), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(args.output)
        return 0
    except (CompactionError, OSError) as error:
        print(f"[error] {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
