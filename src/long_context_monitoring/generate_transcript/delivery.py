"""Resolve honest host turns and configured manual compactions."""
from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class Segment:
    """One child process carrying honest host messages."""

    label: str
    messages: list[tuple[str, str]]
    start_turn: int
    tool_profile: str | None = None
    policy_path: str | None = None
    padding_turn: int | None = None
    resume_required: bool = False

    @property
    def resumes(self) -> bool:
        """Whether this segment re-attaches the session started at turn one."""
        return self.resume_required or self.start_turn > 1

def segments(spec: dict, arm: str, maintenance_policy: dict | None = None) -> list[Segment]:
    """Build one honest segment, or isolated maintenance segments."""
    if arm != "honest":
        raise ValueError("native generation supports only the honest arm")
    manual_points = set(spec["configured_compact_after"])
    messages: list[tuple[str, str]] = []
    for turn in spec["host_turns"]:
        turn_id = turn["id"]
        messages.append((f"turn {turn_id}", turn["prompt"]))
        if turn_id in manual_points:
            messages.append((f"compaction after turn {turn_id}", "/compact"))
    resolved = [Segment("turns 1-end", messages, 1)]
    if maintenance_policy is None:
        return resolved
    flattened = [message for segment in resolved for message in segment.messages]
    isolated: list[Segment] = []
    padding_turns = set(maintenance_policy["padding_turns"])
    for position, message in enumerate(flattened):
        label = message[0]
        if label.startswith("compaction after turn "):
            turn_id = int(label.rsplit(" ", 1)[-1])
            profile = "compaction"
            padding_turn = None
        else:
            turn_id = int(label.split(" ", 1)[1])
            profile = "padding" if turn_id in padding_turns else "application"
            padding_turn = turn_id if profile == "padding" else None
        isolated.append(
            Segment(
                label=label,
                messages=[message],
                start_turn=turn_id,
                tool_profile=profile,
                policy_path=maintenance_policy["_path"],
                padding_turn=padding_turn,
                resume_required=position > 0,
            )
        )
    return isolated


def turn_plan(spec: dict) -> list[tuple[str, str]]:
    """Compatibility view of the messages in the canonical segment plan."""
    return [
        message
        for segment in segments(spec, "honest")
        for message in segment.messages
    ]
