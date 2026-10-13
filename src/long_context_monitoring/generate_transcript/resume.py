"""Persist and validate redacted recovery checkpoints without replaying a session."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from long_context_monitoring.artifact_layout import evidence_file
from . import delivery
from .session import SessionError
from .specification import _runtime_guidance_turns

RESUME_FILENAME = "resume.json"


def write_resume_state(
    destination: Path,
    *,
    name: str,
    arm: str,
    session_id: str,
    workspace: Path,
    fingerprint: str,
    plan: list[tuple[str, str]],
    plan_segments: list[delivery.Segment],
    spec: dict,
    completed: int,
    policy_model: str,
    policy_effort: str | None,
    backend: str = "claude",
    native_home: Path | None = None,
) -> None:
    """Record just enough to resume an interrupted run, and no side-task text.

    Written after every turn and deleted on clean completion, so the file's
    presence *is* the "this run died partway" signal that the (later) resume
    path keys off. It stores the pinned session id and the temp workspace so a
    resume can re-attach the same session in the same dir instead of re-copying
    the seed, plus the plan labels and how many completed. It never carries the
    side-task text, matching the honest-only generation contract.
    """
    destination.mkdir(parents=True, exist_ok=True)
    completed_segments: list[str] = []
    segment_end = 0
    for segment in plan_segments:
        segment_end += len(segment.messages)
        if completed >= segment_end:
            completed_segments.append(segment.label)
    runtime_guidance_turns = _runtime_guidance_turns(spec)
    state = {
        "name": name,
        "arm": arm,
        "session_id": session_id,
        "workspace": str(workspace),
        "workspace_fingerprint": fingerprint,
        "plan_labels": [label for label, _ in plan],
        "compaction_mode": spec["compaction_mode"],
        "configured_compact_after": spec["configured_compact_after"],
        "runtime_guidance_turns": runtime_guidance_turns,
        "delivery_segment_prompt_sha256s": [None for _ in plan_segments],
        "completed_segments": completed_segments,
        "policy_model": policy_model,
        "policy_effort": policy_effort,
        "backend": backend,
        "native_home": str(native_home) if native_home is not None else None,
        "completed": completed,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    # Write-then-rename so a crash mid-write can never leave a torn resume file.
    temporary = destination / (RESUME_FILENAME + ".tmp")
    temporary.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    temporary.replace(destination / RESUME_FILENAME)


def load_resume_state(
    destination: Path,
    plan: list[tuple[str, str]],
    plan_segments: list[delivery.Segment],
    spec: dict,
    policy_model: str,
    policy_effort: str | None,
    backend: str = "claude",
) -> dict:
    """Read and validate the resume marker for a crashed run under ``destination``.

    Guards against the two ways resume corrupts a dataset: a missing marker (the
    run finished or never checkpointed, so there is nothing to resume) and a spec
    that changed since the crash (different plan -> the remaining turns no longer
    line up, which would splice two different runs into one transcript). A drifted
    spec is a hard error, not a silent re-plan.
    """
    marker = evidence_file(destination, RESUME_FILENAME)
    if not marker.is_file():
        raise SessionError(
            f"no {RESUME_FILENAME} under {destination}; nothing to resume "
            "(the run completed, or died before its first turn finished)"
        )
    state = json.loads(marker.read_text(encoding="utf-8"))
    if state.get("backend", "claude") != backend:
        raise SessionError(
            f"the backend changed since the crash: {state.get('backend')!r} -> "
            f"{backend!r}; regenerate from scratch instead"
        )
    recorded_labels = state.get("plan_labels")
    current_labels = [label for label, _ in plan]
    if recorded_labels != current_labels:
        raise SessionError(
            "the spec changed since the crash, so the run cannot be resumed:\n"
            f"  crashed plan: {recorded_labels}\n  current plan: {current_labels}\n"
            "Resume splices onto the existing session, so a different plan would "
            "mix two runs. Regenerate from scratch instead."
        )
    expected_shape = {
        "compaction_mode": spec["compaction_mode"],
        "configured_compact_after": spec["configured_compact_after"],
        "runtime_guidance_turns": _runtime_guidance_turns(spec),
        "delivery_segment_prompt_sha256s": [None for _ in plan_segments],
    }
    for key, expected in expected_shape.items():
        if state.get(key) != expected:
            raise SessionError(
                f"the spec's {key} changed since the crash:\n"
                f"  crashed: {state.get(key)!r}\n  current: {expected!r}\n"
                "Resume would mix two delivery configurations in one transcript. "
                "Regenerate from scratch instead."
            )
    completed = int(state.get("completed", 0))
    expected_completed_segments: list[str] = []
    segment_end = 0
    for segment in plan_segments:
        segment_end += len(segment.messages)
        if completed >= segment_end:
            expected_completed_segments.append(segment.label)
    if state.get("completed_segments") != expected_completed_segments:
        raise SessionError(
            "resume.json has inconsistent completed segment state; regenerate "
            "from scratch instead"
        )
    recorded_model = state.get("policy_model")
    if recorded_model != policy_model:
        raise SessionError(
            "the policy model changed since the crash, so the run cannot be "
            "resumed:\n"
            f"  crashed model: {recorded_model!r}\n"
            f"  current model: {policy_model!r}\n"
            "Resume would mix two policy models in one transcript. Regenerate "
            "from scratch instead."
        )
    recorded_effort = state.get("policy_effort")
    if recorded_effort != policy_effort:
        raise SessionError(
            "the policy effort changed since the crash, so the run cannot be "
            "resumed:\n"
            f"  crashed effort: {recorded_effort!r}\n"
            f"  current effort: {policy_effort!r}\n"
            "Resume would mix two policy effort settings in one transcript. "
            "Regenerate from scratch instead."
        )
    workspace = Path(state["workspace"])
    if not workspace.is_dir():
        raise SessionError(
            f"the temp workspace from the crashed run is gone ({workspace}); "
            "its edits cannot be recovered, so regenerate from scratch"
        )
    return state
