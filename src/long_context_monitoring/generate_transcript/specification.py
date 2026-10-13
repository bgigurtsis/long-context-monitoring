"""Validate the honest four-key spec before generation can perform any work."""

from __future__ import annotations

from pathlib import Path
import yaml
from long_context_monitoring.run_layout import resolve_repo_path
from .side_task import SpecError, guidance_schedule, is_scheduled, load_side_task

SPEC_KEYS = frozenset({"workspace", "host_turns", "compact_after", "side_task"})


def load_spec(path: Path, *, require_workspace: bool = True) -> dict:
    """Read and fully validate a live spec, or raise ``SpecError``.

    Every check runs before the first model call, because a spec that is wrong
    about where compaction lands produces a transcript that cannot answer the
    question it was generated for.
    """
    try:
        path = resolve_repo_path(path)
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise SpecError(f"{path}: invalid YAML: {error}") from error
    if not isinstance(raw, dict):
        raise SpecError(f"{path}: spec must be a YAML mapping")
    unknown = sorted(set(raw) - SPEC_KEYS)
    if unknown:
        raise SpecError(f"{path}: unknown keys {unknown}; allowed: {sorted(SPEC_KEYS)}")
    for key in ("workspace", "host_turns", "compact_after", "side_task"):
        if key not in raw:
            raise SpecError(f"{path}: missing required key '{key}'")

    turns = raw["host_turns"]
    ids = _host_turn_ids(turns, path)

    compaction_mode, manual_points = _compaction_configuration(
        raw["compact_after"], ids, path
    )

    workspace_value = Path(str(raw["workspace"])).expanduser()
    workspace = resolve_repo_path(workspace_value, path.parent)
    if require_workspace and not workspace.is_dir():
        raise SpecError(f"{path}: workspace '{workspace}' is not a directory")
    # Either the original free-prose scalar or the structured five-field form;
    # ``side_task.py`` owns that distinction and the audience split it implies.
    side_task = load_side_task(raw.get("side_task"), path)
    if is_scheduled(side_task):
        _, schedule = guidance_schedule(side_task)
        missing_guidance = [turn_id for turn_id, _ in schedule if turn_id not in ids]
        if missing_guidance:
            raise SpecError(
                f"{path}: runtime_guidance turns {missing_guidance} match no "
                f"host-turn id in {ids}"
            )

    return {
        "workspace": workspace.resolve(),
        "host_turns": [{"id": t["id"], "prompt": str(t["prompt"])} for t in turns],
        "compaction_mode": compaction_mode,
        "configured_compact_after": manual_points,
        "side_task": side_task,
    }


def _is_int(value: object) -> bool:
    """True for a real integer; ``bool`` is an ``int`` subclass, so exclude it."""
    return isinstance(value, int) and not isinstance(value, bool)


def _runtime_guidance_turns(spec: dict) -> list[int]:
    """Return scheduled activation turns without any guidance text."""
    if not is_scheduled(spec["side_task"]):
        return []
    _, schedule = guidance_schedule(spec["side_task"])
    return [turn_id for turn_id, _ in schedule]


def _host_turn_ids(turns: object, path: Path) -> list[int]:
    """Validate turn order before compaction and guidance refer to those IDs."""
    if not isinstance(turns, list) or not turns:
        raise SpecError(f"{path}: host_turns must be a non-empty list")
    ids: list[int] = []
    for position, turn in enumerate(turns):
        if not isinstance(turn, dict) or set(turn) != {"id", "prompt"}:
            raise SpecError(
                f"{path}: host_turns[{position}] needs exactly 'id' and 'prompt'"
            )
        if not _is_int(turn["id"]):
            raise SpecError(f"{path}: host_turns[{position}].id must be an integer")
        if not str(turn["prompt"]).strip():
            raise SpecError(f"{path}: host_turns[{position}].prompt is empty")
        ids.append(turn["id"])
    if ids != list(range(1, len(ids) + 1)):
        raise SpecError(
            f"{path}: host_turns ids must be contiguous and ascending from 1; got {ids}"
        )
    return ids


def _compaction_configuration(
    compact_after: object, ids: list[int], path: Path
) -> tuple[str, list[int]]:
    """Keep the ordered diagnostics for manual versus automatic compaction."""
    if compact_after == "auto":
        compaction_mode = "automatic"
        manual_points: list[int] = []
    else:
        compaction_mode = "manual"
        if _is_int(compact_after):
            manual_points = [compact_after]
        elif isinstance(compact_after, list):
            if not compact_after:
                raise SpecError(
                    f"{path}: compact_after list is empty; use 'auto' or name "
                    "at least one turn"
                )
            if not all(_is_int(point) for point in compact_after):
                raise SpecError(
                    f"{path}: compact_after list must contain only integer turn ids"
                )
            manual_points = list(compact_after)
        else:
            raise SpecError(
                f"{path}: compact_after must be 'auto', an integer turn id, "
                "or an ordered integer list"
            )
        if manual_points != sorted(set(manual_points)):
            raise SpecError(
                f"{path}: compact_after points must be unique and strictly "
                f"ascending; got {manual_points}"
            )
        missing_points = [point for point in manual_points if point not in ids]
        if missing_points:
            raise SpecError(
                f"{path}: compact_after points {missing_points} match no id in {ids}"
            )
        if ids[-1] in manual_points:
            raise SpecError(
                f"{path}: compact_after cannot include final turn {ids[-1]}"
            )
    return compaction_mode, manual_points
