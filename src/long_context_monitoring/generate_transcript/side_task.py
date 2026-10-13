"""Validate structured side-task metadata and exact manual edits."""
from __future__ import annotations

from pathlib import Path
from typing import TypeAlias

# Every key a structured side task may carry, and all of them are required. A
# side task with a missing field is a half-written one, and the fields a reviewer
# reads are exactly the ones nothing else in the pipeline would notice were
# absent — so absence has to be an error rather than a default.
SIDE_TASK_KEYS = frozenset({
    "id",
    "objective",
    "runtime_guidance",
    "explanation",
})

MANUAL_GUIDANCE_KEYS = frozenset({"instruction", "manual_edit"})
MANUAL_EDIT_KEYS = frozenset({
    "path",
    "function",
    "expected_signature",
    "replacement",
    "when",
})
MANUAL_EDIT_REQUIRED_KEYS = MANUAL_EDIT_KEYS - {"when"}
MANUAL_EDIT_WHEN = frozenset({"before_host_turn", "after_host_turn", "after_native_function_edit"})

ManualEdit: TypeAlias = dict[str, str]
GuidanceStage: TypeAlias = str | dict[str, object]


class SpecError(ValueError):
    """A live spec is malformed. Raised before anything is spawned.

    Defined here rather than in ``live.py`` because the spec loader's first
    validation step now lives in this module; ``live`` re-exports it, so
    ``live.SpecError`` still resolves for existing callers.
    """


def load_side_task(raw: object, path: Path) -> dict | None:
    """Validate structured metadata without sending it to honest generation."""
    if raw is None:
        return None

    if isinstance(raw, dict):
        unknown = sorted(set(raw) - SIDE_TASK_KEYS)
        if unknown:
            raise SpecError(
                f"{path}: side_task has unknown keys {unknown}; "
                f"allowed: {sorted(SIDE_TASK_KEYS)}"
            )
        missing = sorted(SIDE_TASK_KEYS - set(raw))
        if missing:
            raise SpecError(f"{path}: side_task is missing required keys {missing}")
        for key in sorted(SIDE_TASK_KEYS):
            value = raw[key]
            if key == "runtime_guidance" and isinstance(value, dict):
                value = _validate_guidance_schedule(value, path)
                raw = dict(raw)
                raw[key] = value
                continue
            if not isinstance(value, str):
                raise SpecError(
                    f"{path}: side_task.{key} must be a string, got "
                    f"{type(value).__name__}"
                )
            if not value.strip():
                raise SpecError(f"{path}: side_task.{key} is empty")
        return {key: raw[key] for key in sorted(SIDE_TASK_KEYS)}

    raise SpecError(
        f"{path}: side_task must be a mapping of "
        f"{sorted(SIDE_TASK_KEYS)}, got {type(raw).__name__}"
    )


def _validate_guidance_schedule(value: dict, path: Path) -> dict[int, GuidanceStage]:
    """Validate guidance keyed by the host-turn id where it becomes active."""
    if not value:
        raise SpecError(
            f"{path}: side_task.runtime_guidance is an empty mapping; "
            "give at least one host-turn id or use a single string"
        )

    schedule: dict[int, GuidanceStage] = {}
    for turn_id, stage in value.items():
        if not isinstance(turn_id, int) or isinstance(turn_id, bool):
            raise SpecError(
                f"{path}: side_task.runtime_guidance keys must be integer "
                f"host-turn ids, got {turn_id!r}"
            )
        if isinstance(stage, dict):
            schedule[turn_id] = _validate_guidance_stage(stage, path, turn_id)
            continue
        if not isinstance(stage, str):
            raise SpecError(
                f"{path}: side_task.runtime_guidance.{turn_id} must be a string, "
                f"got {type(stage).__name__}"
            )
        if not stage.strip():
            raise SpecError(
                f"{path}: side_task.runtime_guidance.{turn_id} is empty"
            )
        schedule[turn_id] = stage
    return {turn_id: schedule[turn_id] for turn_id in sorted(schedule)}


def _validate_guidance_stage(
    stage: dict, path: Path, turn_id: int
) -> dict[str, object]:
    """Validate one inline instruction and registered manual edit."""

    label = f"{path}: side_task.runtime_guidance.{turn_id}"
    unknown = sorted(set(stage) - MANUAL_GUIDANCE_KEYS)
    missing = sorted(MANUAL_GUIDANCE_KEYS - set(stage))
    if unknown:
        raise SpecError(
            f"{label} has unknown keys {unknown}; allowed: "
            f"{sorted(MANUAL_GUIDANCE_KEYS)}"
        )
    if missing:
        raise SpecError(f"{label} is missing required keys {missing}")
    instruction = stage["instruction"]
    if not isinstance(instruction, str) or not instruction.strip():
        raise SpecError(f"{label}.instruction must be a non-empty string")
    manual_edit = stage["manual_edit"]
    if not isinstance(manual_edit, dict):
        raise SpecError(f"{label}.manual_edit must be a mapping")
    return {
        "instruction": instruction,
        "manual_edit": _validate_manual_edit(manual_edit, path, turn_id),
    }


def _validate_manual_edit(
    edit: dict, path: Path, turn_id: int
) -> ManualEdit:
    """Validate one exact top-level Python function replacement."""

    label = f"{path}: side_task.runtime_guidance.{turn_id}.manual_edit"
    unknown = sorted(set(edit) - MANUAL_EDIT_KEYS)
    missing = sorted(MANUAL_EDIT_REQUIRED_KEYS - set(edit))
    if unknown:
        raise SpecError(
            f"{label} has unknown keys {unknown}; allowed: "
            f"{sorted(MANUAL_EDIT_KEYS)}"
        )
    if missing:
        raise SpecError(f"{label} is missing required keys {missing}")
    loaded: ManualEdit = {}
    for key in sorted(MANUAL_EDIT_REQUIRED_KEYS):
        value = edit[key]
        if not isinstance(value, str) or not value.strip():
            raise SpecError(f"{label}.{key} must be a non-empty string")
        loaded[key] = value
    when = edit.get("when", "before_host_turn")
    if not isinstance(when, str) or when not in MANUAL_EDIT_WHEN:
        raise SpecError(
            f"{label}.when must be one of {sorted(MANUAL_EDIT_WHEN)}, "
            f"got {when!r}"
        )
    loaded["when"] = when
    return loaded


def is_scheduled(side_task: dict | None) -> bool:
    """True when this side task changes guidance at named host turns."""
    return (
        isinstance(side_task, dict)
        and isinstance(side_task.get("runtime_guidance"), dict)
    )


def guidance_schedule(side_task: dict) -> tuple[str, list[tuple[int, str]]]:
    """Return the objective and ordered incremental guidance entries."""
    guidance = side_task["runtime_guidance"]
    if not isinstance(guidance, dict):
        raise ValueError(
            "runtime_guidance is not scheduled; use attacker_view() for a "
            "whole-session guidance string"
        )
    entries = [
        (
            turn_id,
            (
                guidance[turn_id]["instruction"]
                if isinstance(guidance[turn_id], dict)
                else guidance[turn_id]
            ),
        )
        for turn_id in sorted(guidance)
    ]
    return side_task["objective"], entries


def manual_edit_schedule(side_task: dict) -> list[tuple[int, ManualEdit]]:
    """Return registered inline edits without exposing them to a policy."""

    guidance = side_task.get("runtime_guidance")
    if not isinstance(guidance, dict):
        return []
    edits: list[tuple[int, ManualEdit]] = []
    for turn_id in sorted(guidance):
        stage = guidance[turn_id]
        if isinstance(stage, dict):
            edit = stage.get("manual_edit")
            if isinstance(edit, dict):
                edits.append((turn_id, dict(edit)))
    return edits
