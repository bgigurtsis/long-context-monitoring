"""Overlap planning for archive windows.

Two independent computations combine into one ``OverlapPlan``, and neither
one ever informs the other:

- ``overlapping_window_pairs`` is pure range math over declared window
  spans (inclusive start/end). It never looks at row content, so an
  overlapping range is never by itself treated as evidence that any two
  events in those windows are copies of one another.
- Row grouping comes exclusively from
  ``SqliteAuditService.all_events_with_repair_keys`` -- the dedicated
  repair reader already responsible for deciding, from each row's own
  stored content and receipt, which non-complete-identity candidate (if
  any) is trustworthy. Nothing here recomputes or second-guesses that
  decision; it only groups the reader's own output by repair key and
  records which basis (``BASIS_COMPLETE_IDENTITY``, ``BASIS_VERIFIED_LINEAGE``,
  or ``BASIS_VERIFIED_HTTP_COMPATIBILITY``, all from ``auditlog.sqlite_storage``)
  produced each group. A candidate the reader did not trust -- because it
  failed receipt validation, or failed the distinct-identity cohort check --
  is not eligible, and rows carrying it simply fall back to their own
  complete identity, exactly as the reader itself decides.

Building a plan (``build_overlap_plan``) never writes anything: it is a
pure read over the store's current state. Only ``execute_overlap_plan``
writes, and only after acquiring the named worker lease that serializes
concurrent planners; it delegates persistence to
``SqliteAuditService.persist_overlap_plan``, which makes the persisted plan
an idempotent, restart-safe mirror of its input.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

from auditlog.sqlite_storage import RepairedRow, SqliteAuditService

OVERLAP_MERGE_LEASE_NAME = "overlap-merge-plan"


class LeaseNotHeldError(RuntimeError):
    """Raised when a worker attempts to execute a plan without holding its lease."""


@dataclass(frozen=True)
class WindowSpan:
    """A caller-declared inclusive range for one archive export window.

    Purely descriptive planning input: ``range_start``/``range_end`` are
    compared as opaque, lexicographically ordered strings. This project's
    ``recorded_at`` values are consistently formatted ISO 8601 UTC
    timestamps, which sort correctly this way. Nothing here reads row
    content or storage.
    """

    label: str
    source: str
    range_start: str
    range_end: str


def overlapping_window_pairs(spans: Sequence[WindowSpan]) -> tuple[tuple[str, str], ...]:
    """Pairs of window labels whose declared inclusive ranges overlap.

    Pure range math over the spans given: it never reads storage and never
    implies that any event inside either window is a copy of one in the
    other. That determination is made later, and separately, by the
    dedicated repair reader.
    """

    pairs = []
    for index, first in enumerate(spans):
        for second in spans[index + 1:]:
            if first.range_start <= second.range_end and second.range_start <= first.range_end:
                pairs.append(tuple(sorted((first.label, second.label))))
    return tuple(pairs)


@dataclass(frozen=True)
class PlannedGroup:
    """One repair-key cohort, as grouped straight from the dedicated repair reader.

    Carries the basis the reader assigned it, and only descriptive,
    non-private fields -- member sequence numbers and window labels -- never
    the private stored receipt.
    """

    repair_key: str
    basis: str
    member_sequences: tuple[int, ...]
    window_labels: tuple[str | None, ...]


@dataclass(frozen=True)
class OverlapPlan:
    """A non-mutating description of window range overlaps and repair-key groups.

    ``window_pairs`` and ``groups`` are computed independently (see module
    docstring): a window pair being present here never means, and was never
    used to infer, that ``groups`` contains a corresponding cohort, and a
    group in ``groups`` was never chosen because its members' windows
    overlap.
    """

    window_pairs: tuple[tuple[str, str], ...]
    groups: tuple[PlannedGroup, ...]


def build_overlap_plan(
    service: SqliteAuditService,
    spans: Sequence[WindowSpan],
    *,
    http_compatibility_validator: Callable[..., str | None] | None = None,
) -> OverlapPlan:
    """Compute an ``OverlapPlan`` from the store's current state without writing anything.

    Rows are grouped only by the ``repair_key`` the dedicated reader
    (``SqliteAuditService.all_events_with_repair_keys``) already assigned
    them; this function performs no independent identity or receipt
    computation of its own.
    """

    window_pairs = overlapping_window_pairs(spans)
    kwargs = {}
    if http_compatibility_validator is not None:
        kwargs["http_compatibility_validator"] = http_compatibility_validator
    repaired_rows = service.all_events_with_repair_keys(**kwargs)

    by_key: dict[str, list[RepairedRow]] = {}
    for repaired in repaired_rows:
        by_key.setdefault(repaired.repair_key, []).append(repaired)

    groups = []
    for key, members in by_key.items():
        if len(members) < 2:
            continue
        ordered = sorted(members, key=lambda member: member.copy_observation.sequence)
        member_sequences = tuple(member.copy_observation.sequence for member in ordered)
        window_labels = tuple(
            member.copy_observation.window.label if member.copy_observation.window else None
            for member in ordered
        )
        groups.append(
            PlannedGroup(
                repair_key=key,
                basis=members[0].basis,
                member_sequences=member_sequences,
                window_labels=window_labels,
            )
        )
    groups.sort(key=lambda group: group.member_sequences)
    return OverlapPlan(window_pairs=window_pairs, groups=tuple(groups))


def execute_overlap_plan(
    service: SqliteAuditService,
    spans: Sequence[WindowSpan],
    *,
    owner: str,
    ttl_seconds: float,
    now: float | None = None,
    http_compatibility_validator: Callable[..., str | None] | None = None,
) -> OverlapPlan:
    """Build the same plan ``build_overlap_plan`` would, then durably persist it.

    Requires holding the ``OVERLAP_MERGE_LEASE_NAME`` lease first (acquired
    here on ``owner``'s behalf), so concurrent workers never persist
    conflicting plans at once; raises ``LeaseNotHeldError`` if the lease is
    currently held live by a different owner. Persistence itself
    (``SqliteAuditService.persist_overlap_plan``) is idempotent and
    restart-safe.
    """

    if not service.acquire_worker_lease(OVERLAP_MERGE_LEASE_NAME, owner, ttl_seconds=ttl_seconds, now=now):
        raise LeaseNotHeldError(f"{owner!r} does not hold the {OVERLAP_MERGE_LEASE_NAME!r} lease")
    plan = build_overlap_plan(service, spans, http_compatibility_validator=http_compatibility_validator)
    service.persist_overlap_plan(plan, planned_at=now)
    return plan
