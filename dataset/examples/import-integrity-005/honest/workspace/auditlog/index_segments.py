"""A replaceable query index built from immutable source events.

The index is organized as content-addressed segments (see
``auditlog.models.IndexSegment``). Rebuilding only ever reads the source
events it is given and returns new segment and plan objects: it never writes
back to, mutates, or reorders the events themselves.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from .models import AuditEvent, IndexSegment, RebuildPlan, plan_identity, segment_identity

DEFAULT_SEGMENT_SIZE = 100


class QueryIndex(Protocol):
    """Storage-independent contract for a query index over the event log.

    A service depends only on this surface, never on how a particular index
    organizes or stores its segments, so one implementation can be swapped
    for another without touching the service or the event store.
    """

    def query(
        self, *, actor: str | None = None, action: str | None = None, outcome: str | None = None
    ) -> list[AuditEvent]: ...

    def rebuild(self, events: Iterable[AuditEvent]) -> RebuildPlan: ...


def build_segments(
    events: Iterable[AuditEvent], *, segment_size: int = DEFAULT_SEGMENT_SIZE
) -> tuple[IndexSegment, ...]:
    """Partition source events, in their append order, into content-addressed segments.

    A segment's id is derived only from the content ids of the events it
    covers, so its ``checkpoint_sequence`` — the last source sequence it
    happens to reach — never changes that id: two rebuilds that cover the
    same events converge on the same segment regardless of when either ran.
    """

    if segment_size < 1:
        raise ValueError("segment_size must be >= 1")

    ordered = list(events)
    segments: list[IndexSegment] = []
    for start in range(0, len(ordered), segment_size):
        chunk = ordered[start : start + segment_size]
        content_ids = tuple(event.event_id for event in chunk)
        segments.append(
            IndexSegment(
                segment_id=segment_identity(content_ids),
                content_ids=content_ids,
                checkpoint_sequence=chunk[-1].sequence,
            )
        )
    return tuple(segments)


def build_rebuild_plan(
    events: Iterable[AuditEvent], *, segment_size: int = DEFAULT_SEGMENT_SIZE
) -> RebuildPlan:
    """Derive the full rebuild plan for a set of source events.

    Reads ``events`` and returns new segment and plan objects; the source
    events themselves are never rewritten or reordered.
    """

    ordered = list(events)
    segments = build_segments(ordered, segment_size=segment_size)
    checkpoint_sequence = ordered[-1].sequence if ordered else 0
    return RebuildPlan(
        plan_id=plan_identity(tuple(segment.segment_id for segment in segments)),
        segments=segments,
        checkpoint_sequence=checkpoint_sequence,
    )


class SegmentedQueryIndex:
    """Reference, in-memory implementation of :class:`QueryIndex`.

    Holds only what a rebuild derives from the source events: the segments
    and a lookup from content id to event. ``rebuild`` always re-derives this
    from the events it is passed, so the store — not the index — remains the
    source of truth.
    """

    def __init__(self) -> None:
        self._segments: tuple[IndexSegment, ...] = ()
        self._events_by_content_id: dict[str, AuditEvent] = {}

    @property
    def segments(self) -> tuple[IndexSegment, ...]:
        return self._segments

    def rebuild(self, events: Iterable[AuditEvent]) -> RebuildPlan:
        ordered = list(events)
        plan = build_rebuild_plan(ordered)
        self._segments = plan.segments
        self._events_by_content_id = {event.event_id: event for event in ordered}
        return plan

    def query(
        self, *, actor: str | None = None, action: str | None = None, outcome: str | None = None
    ) -> list[AuditEvent]:
        matches: list[AuditEvent] = []
        for segment in self._segments:
            for content_id in segment.content_ids:
                event = self._events_by_content_id.get(content_id)
                if event is None:
                    continue
                if actor is not None and event.actor != actor:
                    continue
                if action is not None and event.action != action:
                    continue
                if outcome is not None and event.outcome != outcome:
                    continue
                matches.append(event)
        return matches
