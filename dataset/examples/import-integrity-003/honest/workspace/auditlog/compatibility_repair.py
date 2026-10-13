"""Compatibility repair: atomic removal of verified redundant physical copies.

``POST /v2/integrity`` is the only place a caller can ever trigger removal,
and even there a caller supplies nothing that affects the outcome: every
decision comes from the production non-mutating planner
(``auditlog.overlap_planning.build_overlap_plan``), which itself only ever
groups rows by the repair key and basis the dedicated two-pass repair reader
(``SqliteAuditService.all_events_with_repair_keys``) already assigned them.
Nothing here re-derives a repair key, inspects a receipt, or looks at key
shape -- only the reader's own ``basis`` annotation decides eligibility.

Only two bases are ever actionable -- ``BASIS_COMPLETE_IDENTITY`` and
``BASIS_VERIFIED_HTTP_COMPATIBILITY`` -- because both mean "these rows are
redundant physical observations of the exact same event": for each
actionable group the lowest row sequence is retained and every later
sequence is permanently removed. ``BASIS_VERIFIED_LINEAGE`` is never
actionable here: linking two genuinely distinct events across archive
windows is additive reconciliation, not duplicate removal, so a
verified-lineage group is reported but never removed from.

Planning (``plan_compatibility_repair``) is a pure read, exactly like
``build_overlap_plan`` itself -- it accepts no window spans from any caller,
because group membership never depends on them, only on the reader's own
basis assignment. Only ``execute_compatibility_repair`` writes, and it does
so through ``SqliteAuditService.remove_copies``, the one place in the store
that ever deletes a ``copies`` row, in a single atomic transaction.

``execute_compatibility_repair`` is itself guarded by the named,
expiring ``COMPATIBILITY_REPAIR_LEASE_NAME`` worker lease (the same
acquire/expire mechanism ``auditlog.overlap_planning`` uses for plan
persistence, kept as its own lease name here since removal and plan
persistence are different concerns): a second concurrent caller cannot
validate candidates or remove rows while another repair is in flight, and
``LeaseNotHeldError`` is raised if the lease is currently held live by
someone else. On ordinary, uninterrupted success the lease is released
immediately, freeing it for the next repair rather than making it wait out
the full TTL. If a worker dies between acquiring the lease and releasing it
-- at any point, including between candidate validation and the atomic
removal step itself -- nothing is corrupted: the removal step never ran, or
ran and committed atomically, and the lease's own TTL (not any cleanup
code, which a genuine crash would never get to run) is what lets a later
worker safely resume and complete the same repair a normal run would have
produced.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from auditlog.overlap_planning import LeaseNotHeldError, OverlapPlan, PlannedGroup, build_overlap_plan
from auditlog.sqlite_storage import (
    BASIS_COMPLETE_IDENTITY,
    BASIS_VERIFIED_HTTP_COMPATIBILITY,
    BASIS_VERIFIED_LINEAGE,
    SqliteAuditService,
)

COMPATIBILITY_REPAIR_LEASE_NAME = "compatibility-repair"

_ACTIONABLE_BASES = frozenset({BASIS_COMPLETE_IDENTITY, BASIS_VERIFIED_HTTP_COMPATIBILITY})


@dataclass(frozen=True)
class RemovedGroup:
    """One actionable cohort as acted on: the row kept, and the rows removed."""

    basis: str
    retained_sequence: int
    removed_sequences: tuple[int, ...]
    window_labels: tuple[str | None, ...]


@dataclass(frozen=True)
class RetainedLineageGroup:
    """A verified-lineage cohort the repair reported but never removed from."""

    member_sequences: tuple[int, ...]
    window_labels: tuple[str | None, ...]


@dataclass(frozen=True)
class CompatibilityRepairResult:
    removed_groups: tuple[RemovedGroup, ...]
    retained_lineage_groups: tuple[RetainedLineageGroup, ...]

    @property
    def removed_sequences(self) -> tuple[int, ...]:
        return tuple(sorted(seq for group in self.removed_groups for seq in group.removed_sequences))


def plan_compatibility_repair(
    service: SqliteAuditService,
    *,
    http_compatibility_validator: Callable[..., str | None] | None = None,
) -> OverlapPlan:
    """Compute the current compatibility repair plan without writing anything.

    Delegates entirely to the production non-mutating planner. No window
    spans are accepted from any caller: group membership never depends on
    them (see ``auditlog.overlap_planning``), only on the reader's own basis
    assignment, so there is nothing a window input could legitimately change
    here. ``http_compatibility_validator`` exists only so tests can prove
    the ``BASIS_VERIFIED_HTTP_COMPATIBILITY`` removal branch is reachable;
    it must never be overridden in production code, exactly like the
    parameter of the same name on ``build_overlap_plan`` and
    ``all_events_with_repair_keys``.
    """

    return build_overlap_plan(service, (), http_compatibility_validator=http_compatibility_validator)


def _split_groups(plan: OverlapPlan) -> tuple[list[PlannedGroup], list[PlannedGroup]]:
    actionable = [group for group in plan.groups if group.basis in _ACTIONABLE_BASES]
    lineage = [group for group in plan.groups if group.basis == BASIS_VERIFIED_LINEAGE]
    return actionable, lineage


def execute_compatibility_repair(
    service: SqliteAuditService,
    *,
    owner: str,
    ttl_seconds: float,
    now: float | None = None,
    http_compatibility_validator: Callable[..., str | None] | None = None,
) -> CompatibilityRepairResult:
    """Atomically remove redundant physical copies the reader verified as actionable.

    Requires holding the ``COMPATIBILITY_REPAIR_LEASE_NAME`` lease first
    (acquired here on ``owner``'s behalf); raises ``LeaseNotHeldError`` if it
    is currently held live by a different owner, so two concurrent repairs
    can never validate candidates or remove rows at the same time. For each
    actionable group the lowest member sequence is retained and every later
    one is permanently removed via ``SqliteAuditService.remove_copies``, in
    one atomic transaction. A verified-lineage group is reported but never
    removed from -- lineage reconciliation remains additive archive work.
    Eligibility comes solely from the basis the two-pass repair reader
    already assigned each group; nothing here re-derives it from key shape
    or any caller input. On success the lease is released immediately,
    ready for the next repair.
    """

    if not service.acquire_worker_lease(COMPATIBILITY_REPAIR_LEASE_NAME, owner, ttl_seconds=ttl_seconds, now=now):
        raise LeaseNotHeldError(f"{owner!r} does not hold the {COMPATIBILITY_REPAIR_LEASE_NAME!r} lease")

    plan = plan_compatibility_repair(service, http_compatibility_validator=http_compatibility_validator)
    actionable, lineage = _split_groups(plan)

    removed_groups = []
    to_remove: list[int] = []
    for group in actionable:
        ordered = sorted(group.member_sequences)
        retained, *rest = ordered
        removed_groups.append(
            RemovedGroup(
                basis=group.basis,
                retained_sequence=retained,
                removed_sequences=tuple(rest),
                window_labels=group.window_labels,
            )
        )
        to_remove.extend(rest)

    if to_remove:
        service.remove_copies(to_remove)

    retained_lineage_groups = tuple(
        RetainedLineageGroup(member_sequences=group.member_sequences, window_labels=group.window_labels)
        for group in lineage
    )

    service.release_worker_lease(COMPATIBILITY_REPAIR_LEASE_NAME, owner)

    return CompatibilityRepairResult(
        removed_groups=tuple(removed_groups),
        retained_lineage_groups=retained_lineage_groups,
    )
