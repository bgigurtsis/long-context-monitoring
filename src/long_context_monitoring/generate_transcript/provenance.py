"""Observe native compactions and redacted delivery records without rewriting JSONL."""

from __future__ import annotations

from pathlib import Path
from . import codex_session, delivery
from .native_session import read_jsonl
from .session import SessionError, POLICY_EFFORT, build_argv


def validate_compaction_boundaries(spec: dict, boundaries: list[dict]) -> None:
    """Enforce the configured manual count or the native automatic contract."""
    triggers = [boundary["trigger"] for boundary in boundaries]
    if spec["compaction_mode"] == "manual":
        expected = len(spec["configured_compact_after"])
        if len(boundaries) != expected or any(
            trigger != "manual" for trigger in triggers
        ):
            raise SessionError(
                f"expected {expected} manual compaction boundaries; observed "
                f"{len(boundaries)} with triggers {triggers}"
            )
        return
    if any(trigger != "auto" for trigger in triggers):
        raise SessionError(
            f"automatic compaction mode observed non-auto triggers {triggers}"
        )


def _scan_transcript(
    jsonl: Path,
    prompts: list[tuple[int, str]],
) -> tuple[list[dict], dict[int, int]]:
    """Pair boundaries and count those preceding each expected host prompt."""
    _, entries = read_jsonl(jsonl)
    preceding: dict[int, int] = {}
    boundaries: list[dict] = []
    pending_boundary: dict | None = None
    prompt_index = 0
    boundary_count = 0
    seen_boundary_ids: set[str] = set()

    for line_number, entry in enumerate(entries, start=1):
        if entry.get("isSidechain"):
            continue
        is_boundary = (
            entry.get("type") == "system" and entry.get("subtype") == "compact_boundary"
        )
        if is_boundary:
            event_id = entry.get("uuid")
            if event_id is not None and event_id in seen_boundary_ids:
                continue
            if event_id is not None:
                seen_boundary_ids.add(event_id)
            if pending_boundary is not None:
                raise SessionError(
                    f"compaction boundary at line {pending_boundary['line']} of "
                    f"{jsonl} has no paired main-thread compact summary"
                )
            metadata = entry.get("compactMetadata") or {}
            pending_boundary = {
                "line": line_number,
                "boundary_event_id": event_id,
                "trigger": metadata.get("trigger"),
                "pre_tokens": metadata.get("preTokens"),
                "post_tokens": metadata.get("postTokens"),
            }
            boundary_count += 1
            continue
        if entry.get("isCompactSummary"):
            if pending_boundary is not None:
                boundaries.append(
                    {
                        "line": pending_boundary["line"],
                        "summary_line": line_number,
                        "boundary_event_id": pending_boundary["boundary_event_id"],
                        "summary_event_id": entry.get("uuid"),
                        "trigger": pending_boundary["trigger"],
                        "pre_tokens": pending_boundary["pre_tokens"],
                        "post_tokens": pending_boundary["post_tokens"],
                    }
                )
                pending_boundary = None
            continue
        if prompt_index >= len(prompts) or entry.get("type") != "user":
            continue
        content = (entry.get("message") or {}).get("content")
        turn_id, expected = prompts[prompt_index]
        if content == expected:
            preceding[turn_id] = boundary_count
            prompt_index += 1

    if pending_boundary is not None:
        raise SessionError(
            f"compaction boundary at line {pending_boundary['line']} of {jsonl} "
            "has no paired main-thread compact summary"
        )
    missing = [turn_id for turn_id, _ in prompts if turn_id not in preceding]
    if missing:
        raise SessionError(
            f"could not locate host turns {missing} in {jsonl}; activation "
            "provenance would be ambiguous"
        )
    return boundaries, preceding


def _codex_message_text(payload: dict) -> str:
    """Flatten a Codex Responses message payload without normalizing the file."""

    content = payload.get("content")
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") in ("input_text", "output_text", "text"):
            parts.append(str(block.get("text") or ""))
    return "\n".join(parts)


def _scan_codex_transcript(
    jsonl: Path, prompts: list[tuple[int, str]], compaction_mode: str
) -> tuple[list[dict], dict[int, int]]:
    """Observe host prompts and native ``compacted`` rollout records."""

    _, entries = read_jsonl(jsonl)
    boundaries: list[dict] = []
    preceding: dict[int, int] = {}
    prompt_index = 0
    for line_number, entry in enumerate(entries, start=1):
        if entry.get("type") == "compacted":
            payload = entry.get("payload") or {}
            boundaries.append(
                {
                    "line": line_number,
                    "summary_line": line_number,
                    "boundary_event_id": payload.get("window_id"),
                    "summary_event_id": payload.get("window_id"),
                    "trigger": "manual" if compaction_mode == "manual" else "auto",
                    "trigger_source": "configured app-server operation",
                    "pre_tokens": None,
                    "post_tokens": None,
                }
            )
            continue
        if prompt_index >= len(prompts) or entry.get("type") != "response_item":
            continue
        payload = entry.get("payload") or {}
        if payload.get("type") != "message" or payload.get("role") != "user":
            continue
        turn_id, expected = prompts[prompt_index]
        if _codex_message_text(payload) == expected:
            preceding[turn_id] = len(boundaries)
            prompt_index += 1

    missing = [turn_id for turn_id, _ in prompts if turn_id not in preceding]
    if missing:
        raise SessionError(
            f"could not locate host turns {missing} in {jsonl}; activation "
            "provenance would be ambiguous"
        )
    return boundaries, preceding


def compaction_boundaries(jsonl: Path) -> list[dict]:
    """Compatibility view of the main-thread compaction observations."""
    boundaries, _ = _scan_transcript(jsonl, [])
    return boundaries


def transcript_provenance(
    jsonl: Path,
    spec: dict,
    plan_segments: list[delivery.Segment],
    policy_model: str,
    policy_effort: str | None = POLICY_EFFORT,
    backend: str = "claude",
) -> tuple[list[dict], list[dict], list[dict]]:
    """Observe compactions and build redacted delivery provenance in one pass."""
    prompts = [(turn["id"], turn["prompt"]) for turn in spec["host_turns"]]
    if backend == "codex":
        boundaries, preceding = _scan_codex_transcript(
            jsonl, prompts, spec["compaction_mode"]
        )
        invocation = codex_session.redacted_invocation
    else:
        boundaries, preceding = _scan_transcript(jsonl, prompts)
        invocation = build_argv

    segment_records: list[dict] = []
    activations: list[dict] = []
    for segment in plan_segments:
        redacted_resume = "<session-id>" if segment.resumes else None
        argv = (
            invocation(
                redacted_resume,
                policy_model,
                policy_effort,
                segment.tool_profile,
            )
            if backend == "claude"
            else invocation(
                redacted_resume,
                policy_model,
                policy_effort,
            )
        )
        segment_records.append(
            {
                "starting_turn": segment.start_turn,
                "cumulative_guidance_turn_ids": [],
                "appended_prompt_sha256": None,
                "resume_status": "resumed" if segment.resumes else "new",
                "argv": argv,
                "tool_profile": segment.tool_profile,
                "padding_turn": segment.padding_turn,
            }
        )
    return boundaries, segment_records, activations


def delivery_provenance(
    jsonl: Path,
    spec: dict,
    plan_segments: list[delivery.Segment],
    policy_model: str,
    policy_effort: str | None = POLICY_EFFORT,
    backend: str = "claude",
) -> tuple[list[dict], list[dict]]:
    """Compatibility view of redacted segments and guidance activations."""
    _, records, activations = transcript_provenance(
        jsonl, spec, plan_segments, policy_model, policy_effort, backend
    )
    return records, activations
