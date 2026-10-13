"""Build the monitor's task brief for each view from the owning spec.

The monitor prompt has one ``<task_description>`` block. Under the
``interval-turns-only-v1`` mode that block holds only the host turns that fall
inside the interval being scored, labelled with their real turn numbers. A
``pair_I_J`` view is told interval I's turns and then interval J's. The
``whole`` view is told every host turn.

Steps, in order:

1. Find the spec: an explicit ``--spec`` path, else the ``spec.yaml`` that owns
   the transcript's ``generations/`` folder.
2. Read ``host_turns`` and ``compact_after`` from it. Nothing else is read, so
   the registered side task can never reach a monitor prompt from here.
3. Turn ``compact_after`` into one inclusive turn range per interval.
4. Check the transcript really has that many intervals, then format one brief
   per view.

Example: 17 turns with ``compact_after: [3, 6, 9, 12]`` gives
``interval_0`` = turns 1-3, ``interval_1`` = 4-6, ``interval_2`` = 7-9,
``interval_3`` = 10-12 and ``interval_4`` = 13-17.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

# Recorded in every result. Scores under different labels are never pooled.
FULL_TASK_CONTEXT_MODE = "constant-full-final-task-v1"
INTERVAL_TURNS_CONTEXT_MODE = "interval-turns-only-v1"

# Only these strategies name their views ``interval_N``, ``pair_I_J`` or ``whole``.
INTERVAL_TURN_STRATEGIES = frozenset({"intervals", "pairs", "whole"})


class TaskContextError(ValueError):
    """The per-interval brief could not be built; the monitor must not run."""


@dataclass(frozen=True)
class HostTurnContext:
    """The two spec fields the brief needs, already validated."""

    spec_path: Path
    prompts: tuple[str, ...]
    compact_after: tuple[int, ...]


def find_owning_spec(transcript_path: Path) -> Path | None:
    """Find a public example's spec without depending on a campaign layout."""
    for parent in transcript_path.resolve().parents:
        candidate = parent / "spec.yaml"
        if candidate.is_file():
            return candidate
    return None


def load_host_turn_context(spec_path: Path) -> HostTurnContext:
    """Read host turns and manual compaction points from one spec.
    Why: the brief for interval N is defined by these two fields and nothing else.
    If wrong: an interval is scored against turns the agent was not given in it,
    and honest and attack scores stop meaning the same thing across runs.
    """
    try:
        raw = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise TaskContextError(f"{spec_path}: cannot read spec: {error}") from error
    if not isinstance(raw, dict):
        raise TaskContextError(f"{spec_path}: spec must be a YAML mapping")

    turns = raw.get("host_turns")
    if not isinstance(turns, list) or not turns:
        raise TaskContextError(f"{spec_path}: host_turns are missing")
    prompts: list[str] = []
    for position, turn in enumerate(turns, start=1):
        if not isinstance(turn, dict) or turn.get("id") != position:
            raise TaskContextError(
                f"{spec_path}: host turn {position} must have id {position}"
            )
        prompt = str(turn.get("prompt") or "").strip()
        if not prompt:
            raise TaskContextError(f"{spec_path}: host turn {position} is empty")
        prompts.append(prompt)

    compact_after = raw.get("compact_after")
    # Automatic compaction lets the backend pick boundaries, so no turn range
    # can be assigned to an interval from the spec alone.
    if compact_after == "auto":
        raise TaskContextError(
            f"{spec_path}: compact_after is 'auto'; interval turn ranges are "
            "only defined for manual compaction"
        )
    if isinstance(compact_after, int) and not isinstance(compact_after, bool):
        compact_after = [compact_after]
    if not isinstance(compact_after, list):
        raise TaskContextError(f"{spec_path}: compact_after must be a list of turn ids")
    points: list[int] = []
    for value in compact_after:
        if not isinstance(value, int) or isinstance(value, bool):
            raise TaskContextError(f"{spec_path}: compact_after holds a non-integer")
        # The last turn cannot be a boundary: nothing would follow it.
        if value < 1 or value >= len(prompts):
            raise TaskContextError(
                f"{spec_path}: compact_after {value} is not a non-final turn id"
            )
        if points and value <= points[-1]:
            raise TaskContextError(f"{spec_path}: compact_after must increase")
        points.append(value)
    return HostTurnContext(spec_path, tuple(prompts), tuple(points))


def interval_turn_ranges(turn_count: int, compact_after: tuple[int, ...]) -> list[tuple[int, int]]:
    """Return one inclusive ``(first_turn, last_turn)`` pair per interval."""
    ranges: list[tuple[int, int]] = []
    first = 1
    for boundary in compact_after:
        ranges.append((first, boundary))
        first = boundary + 1
    ranges.append((first, turn_count))
    return ranges


def format_turns(prompts: tuple[str, ...], first: int, last: int) -> str:
    """Join turns ``first`` to ``last`` with their real ``[Turn N]`` markers."""
    return "\n\n".join(
        f"[Turn {number}] {prompts[number - 1]}" for number in range(first, last + 1)
    )


def build_view_briefs(
    context: HostTurnContext,
    transcript_interval_count: int,
    *,
    include_pairs: bool = False,
) -> dict[str, str]:
    """Return the ``<task_description>`` text for every view name.
    Why: each monitoring strategy must show interval N the same host turns.
    If wrong: a transcript that compacted at different turns than the spec says
    gets briefs for the wrong intervals, so the count mismatch stops the run.

    ``include_pairs`` adds a ``pair_I_J`` brief for every ``I < J``: interval
    I's turns, then interval J's. It is off by default so the brief set, and
    the per-view hashes recorded for other strategies, stay unchanged.
    """
    ranges = interval_turn_ranges(len(context.prompts), context.compact_after)
    if transcript_interval_count != len(ranges):
        raise TaskContextError(
            f"{context.spec_path}: compact_after defines {len(ranges)} intervals "
            f"but the transcript has {transcript_interval_count}"
        )
    whole = format_turns(context.prompts, 1, len(context.prompts))
    briefs = {"whole": whole}
    # A session with no compaction has one interval and its view is named
    # ``whole``, so it needs no ``interval_0`` entry.
    if len(ranges) > 1:
        for index, (first, last) in enumerate(ranges):
            briefs[f"interval_{index}"] = format_turns(context.prompts, first, last)
    if include_pairs and len(ranges) > 1:
        for first_index in range(len(ranges)):
            for second_index in range(first_index + 1, len(ranges)):
                briefs[f"pair_{first_index}_{second_index}"] = (
                    briefs[f"interval_{first_index}"]
                    + "\n\n"
                    + briefs[f"interval_{second_index}"]
                )
    return briefs
