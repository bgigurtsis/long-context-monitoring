"""Checkpoint bookkeeping for a query index rebuild.

A checkpoint records how far a rebuild has progressed through the source
log. It is pure bookkeeping: it never feeds a segment's or a plan's identity
(``segment_identity``/``plan_identity`` in ``auditlog.models`` only ever hash
content ids), so resuming from, retrying, or discarding a checkpoint can
never change what a rebuild produces from the same source events.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import RebuildPlan


@dataclass(frozen=True)
class RebuildCheckpoint:
    """The last source ``sequence`` a completed rebuild reached."""

    last_sequence: int

    def __post_init__(self) -> None:
        if not isinstance(self.last_sequence, int) or isinstance(self.last_sequence, bool):
            raise ValueError("last_sequence must be an int")
        if self.last_sequence < 0:
            raise ValueError("last_sequence must be >= 0")

    def is_stale(self, latest_sequence: int) -> bool:
        """Whether the source log has advanced past this checkpoint."""

        return latest_sequence > self.last_sequence


def advance_checkpoint(plan: RebuildPlan) -> RebuildCheckpoint:
    """Return the checkpoint a completed rebuild plan implies.

    Only ``plan.checkpoint_sequence`` feeds this — bookkeeping already
    excluded from ``plan.plan_id`` — so the plan's segments and their content
    ids are untouched by checkpoint tracking.
    """

    return RebuildCheckpoint(plan.checkpoint_sequence)
