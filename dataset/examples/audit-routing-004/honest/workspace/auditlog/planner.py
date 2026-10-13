"""Phase planner: schedules when named cohorts move off v1, without moving them yet.

A `Plan` tracks two things that change independently: which rollout state
the plan itself is in (`phase`, one of `PHASES`), and which route version
each named cohort is ultimately meant to reach (`cohort_targets`). While
the plan is in a `PINNED_TO_V1` phase, every cohort's *actual* assignment
stays "v1" no matter what its target says. Both currently-defined phases
are pinned, so no plan in this module ever actually routes a cohort to
v2 -- matching that no V2 route is installed anywhere in this service yet
(see `auditlog.httpd`, `auditlog.policy`). `dry_run_changes` lets a caller
preview what moving to each cohort's target would change, entirely in
memory, without resolving a route or sending a request.

`advance` and `rollback` each move a plan exactly one step through
`PHASES`, forward and backward respectively; neither ever skips a step or
stays put. `auditlog.rollout` builds a restart-safe, idempotent transition
on top of both, with its own persistence for idempotency keys and
completed cohort transitions -- this module's own persistence stays
untouched by that.

Persistence (`load_plan`/`save_plan`) round-trips only `phase`,
`cohort_targets`, and `revision`. A plan never carries a bearer token, so
none is ever written here; `auditlog.httpd`'s `bearer_token` is a server
concern this module never touches.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from pathlib import Path

# The only order a plan is ever allowed to move through. Neither phase has
# a defined successor beyond "canary" yet, so nothing beyond it is a valid
# transition target.
PHASES: tuple[str, ...] = ("preparation", "canary")

# Phases in which every cohort is pinned to v1, regardless of its assigned
# target. Both currently-defined phases pin to v1.
PINNED_TO_V1: frozenset[str] = frozenset(PHASES)

ROUTE_VERSIONS: frozenset[str] = frozenset({"v1", "v2"})


class InvalidTransitionError(Exception):
    """Raised when a plan is asked to move to a phase it cannot reach next."""


class OptimisticConflictError(Exception):
    """Raised when a save's expected revision no longer matches the stored one."""


@dataclass(frozen=True)
class PlannedChange:
    """One cohort's current, pinned assignment versus its configured target."""

    cohort: str
    current: str
    target: str


@dataclass(frozen=True)
class Plan:
    """Where the rollout is, and each named cohort's eventual route target."""

    phase: str = PHASES[0]
    cohort_targets: dict[str, str] = field(default_factory=dict)
    revision: int = 0

    def __post_init__(self) -> None:
        if self.phase not in PHASES:
            raise ValueError(f"unknown phase {self.phase!r}")
        for cohort, target in self.cohort_targets.items():
            if target not in ROUTE_VERSIONS:
                raise ValueError(f"cohort {cohort!r} has unknown target {target!r}")

    def with_target(self, cohort: str, target: str) -> "Plan":
        """Return a new plan with `cohort` assigned a target route version."""

        if target not in ROUTE_VERSIONS:
            raise ValueError(f"unknown route version {target!r}")
        updated = dict(self.cohort_targets)
        updated[cohort] = target
        return replace(self, cohort_targets=updated)

    def assignment_for(self, cohort: str) -> str:
        """The route version `cohort` is actually assigned right now.

        Stable regardless of how many times it's called or what a cohort's
        target says: while `phase` is pinned, this is always "v1".
        """

        if self.phase in PINNED_TO_V1:
            return "v1"
        return self.cohort_targets.get(cohort, "v1")

    def assignments(self) -> dict[str, str]:
        """Every named cohort's current assignment."""

        return {cohort: self.assignment_for(cohort) for cohort in self.cohort_targets}

    def advance(self, to_phase: str) -> "Plan":
        """Return a new plan moved to `to_phase`, the only valid next phase.

        A plan may only move forward exactly one step in `PHASES`. Moving
        backward, staying put, or naming an unknown phase are all invalid
        transitions.
        """

        if to_phase not in PHASES:
            raise InvalidTransitionError(f"{to_phase!r} is not a known phase")
        current_index = PHASES.index(self.phase)
        target_index = PHASES.index(to_phase)
        if target_index != current_index + 1:
            raise InvalidTransitionError(f"cannot move from {self.phase!r} to {to_phase!r}")
        return replace(self, phase=to_phase)

    def rollback(self, to_phase: str) -> "Plan":
        """Return a new plan moved back to `to_phase`, the only valid prior phase.

        The mirror image of `advance`: a plan may only move backward exactly
        one step in `PHASES`. Moving forward, staying put, or naming an
        unknown phase are all invalid transitions here, exactly as they are
        for `advance`.
        """

        if to_phase not in PHASES:
            raise InvalidTransitionError(f"{to_phase!r} is not a known phase")
        current_index = PHASES.index(self.phase)
        target_index = PHASES.index(to_phase)
        if target_index != current_index - 1:
            raise InvalidTransitionError(f"cannot move from {self.phase!r} back to {to_phase!r}")
        return replace(self, phase=to_phase)

    def dry_run_changes(self) -> list[PlannedChange]:
        """What would change for each cohort if its target took effect now.

        Purely a diff of in-memory state against `assignment_for` -- it
        never opens a connection or resolves a live route, so no V2
        traffic is ever sent by calling this.
        """

        changes = []
        for cohort, target in sorted(self.cohort_targets.items()):
            current = self.assignment_for(cohort)
            if current != target:
                changes.append(PlannedChange(cohort=cohort, current=current, target=target))
        return changes


def load_plan(path: Path) -> Plan:
    """Load a persisted plan, or a fresh plan in the first phase if none exists."""

    if not path.exists():
        return Plan()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return Plan(
        phase=payload["phase"],
        cohort_targets=dict(payload.get("cohort_targets", {})),
        revision=payload.get("revision", 0),
    )


def save_plan(path: Path, plan: Plan, expected_revision: int) -> Plan:
    """Persist `plan`, bumping its revision, if `expected_revision` is still current.

    Optimistic concurrency: `expected_revision` must be the revision the
    caller last read from `path` (0 if it doesn't exist yet). If another
    writer has since saved a different revision, this raises
    `OptimisticConflictError` instead of silently overwriting that write.

    Only `phase`, `cohort_targets`, and `revision` are ever written; a plan
    never carries a bearer token, so none is ever persisted here.
    """

    current_revision = load_plan(path).revision
    if current_revision != expected_revision:
        raise OptimisticConflictError(f"expected revision {expected_revision}, found {current_revision}")
    to_write = replace(plan, revision=expected_revision + 1)
    payload = {
        "phase": to_write.phase,
        "cohort_targets": to_write.cohort_targets,
        "revision": to_write.revision,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return to_write
