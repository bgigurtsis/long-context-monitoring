"""Strict models for the audit log service.

An audit ``AuditEvent`` is the immutable source of truth. An ``IndexSegment``
groups source events for the query index, and a ``RebuildPlan`` describes how
to rebuild the whole set of segments from the source events. All three derive
their identity from content alone: an event's id comes from its own recorded
content (including ``recorded_at``), a segment's id from the content ids of
the events it covers, and a plan's id from the ids of its segments. Bookkeeping
fields — ``sequence``, ``source_version``, ``metadata`` on an event;
``checkpoint_sequence`` and ``built_at`` on a segment; ``checkpoint_sequence``
on a plan — describe how or when something was derived and are never inputs to
that derivation.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

# The fields that constitute an entry's identity. Anything outside this tuple
# is descriptive: it may differ between two records of the same event without
# making them different events.
IDENTIFYING_FIELDS: tuple[str, ...] = ("actor", "action", "outcome", "recorded_at")


def _require_nonempty_str(name: str, value: Any) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")


def _require_int(name: str, value: Any, *, minimum: int = 0) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{name} must be an int")
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")


def content_digest(actor: str, action: str, outcome: str, recorded_at: str) -> str:
    """Return the deterministic event id for this entry's recorded content.

    Identity is the recorded content itself, so the same event recorded twice
    collapses to one id and any later edit to a stored entry is detectable by
    recomputing this. The separator cannot appear in a field value, so distinct
    inputs cannot collide by concatenation.
    """

    joined = "\x1f".join((actor, action, outcome, recorded_at))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def segment_identity(content_ids: Sequence[str]) -> str:
    """Return the deterministic id for a segment covering these content ids.

    Only the covered events' content ids feed this. Bookkeeping such as a
    segment's ``checkpoint_sequence`` or ``built_at`` never does, so two
    rebuilds that cover the same events converge on the same segment id
    regardless of when either rebuild ran or how far it had progressed.
    """

    joined = "\x1f".join(content_ids)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def plan_identity(segment_ids: Sequence[str]) -> str:
    """Return the deterministic id for a plan covering these segment ids.

    Like ``segment_identity``, this excludes bookkeeping: a plan's
    ``checkpoint_sequence`` never feeds its id, only the ids of the segments
    it covers.
    """

    joined = "\x1f".join(segment_ids)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AuditEvent:
    """One recorded entry in the append-only trail.

    ``sequence`` is the entry's gapless position in the trail and ``event_id``
    is its content digest. ``source_version`` records which store format the
    entry was read from, and ``metadata`` carries caller-supplied context such
    as an archive's own reference. Both are descriptive: they explain an entry,
    and are never an input to its identity or to whether it is retained.
    """

    event_id: str
    sequence: int
    actor: str
    action: str
    outcome: str
    recorded_at: str
    source_version: int = 2
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_nonempty_str("event_id", self.event_id)
        _require_int("sequence", self.sequence, minimum=1)
        _require_nonempty_str("actor", self.actor)
        _require_nonempty_str("action", self.action)
        _require_nonempty_str("outcome", self.outcome)
        _require_nonempty_str("recorded_at", self.recorded_at)
        _require_int("source_version", self.source_version, minimum=1)
        if not isinstance(self.metadata, dict):
            raise ValueError("metadata must be a dict")

    def recomputed_id(self) -> str:
        """The id this entry's current content implies; compare to ``event_id``."""

        return content_digest(self.actor, self.action, self.outcome, self.recorded_at)


@dataclass(frozen=True)
class IndexSegment:
    """One content-addressed slice of the replaceable query index.

    ``segment_id`` is the digest of ``content_ids``; recomputing it from the
    same ids always yields the same segment, so a rebuilt segment can be
    compared for equality without inspecting the source events again.
    ``checkpoint_sequence`` (the last source ``sequence`` this segment
    reaches) and ``built_at`` are descriptive bookkeeping: they explain the
    segment without being an input to its identity.
    """

    segment_id: str
    content_ids: tuple[str, ...]
    checkpoint_sequence: int
    built_at: str = ""

    def __post_init__(self) -> None:
        _require_nonempty_str("segment_id", self.segment_id)
        if not isinstance(self.content_ids, tuple) or not self.content_ids:
            raise ValueError("content_ids must be a non-empty tuple")
        for content_id in self.content_ids:
            _require_nonempty_str("content_ids[*]", content_id)
        _require_int("checkpoint_sequence", self.checkpoint_sequence, minimum=0)
        if not isinstance(self.built_at, str):
            raise ValueError("built_at must be a string")

    def recomputed_id(self) -> str:
        """The id this segment's current content ids imply; compare to ``segment_id``."""

        return segment_identity(self.content_ids)


@dataclass(frozen=True)
class RebuildPlan:
    """The full plan to rebuild a query index from its source events.

    ``plan_id`` is the digest of the covered segments' ids, so two plans that
    cover the same segments in the same order are the same plan regardless of
    when either was generated. ``checkpoint_sequence`` (the last source
    ``sequence`` the plan reaches) is descriptive bookkeeping for resuming a
    rebuild, never an input to the plan's identity.
    """

    plan_id: str
    segments: tuple[IndexSegment, ...]
    checkpoint_sequence: int

    def __post_init__(self) -> None:
        _require_nonempty_str("plan_id", self.plan_id)
        if not isinstance(self.segments, tuple):
            raise ValueError("segments must be a tuple")
        for segment in self.segments:
            if not isinstance(segment, IndexSegment):
                raise ValueError("segments must contain only IndexSegment values")
        _require_int("checkpoint_sequence", self.checkpoint_sequence, minimum=0)

    def recomputed_id(self) -> str:
        """The id this plan's current segments imply; compare to ``plan_id``."""

        return plan_identity(tuple(segment.segment_id for segment in self.segments))
