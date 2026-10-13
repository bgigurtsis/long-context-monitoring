"""Canonical shapes for the audit trail.

An ``AuditEvent`` is the one form every store format is reconciled into: its
identity is its own recorded content, and it is frozen so nothing downstream
can mutate a recorded entry in place. ``LegacyRecord`` is the raw shape the
older archive log-store format produced; :func:`reconcile_legacy_records`
turns a batch of those into canonical events by deciding, deterministically,
when two archive entries describe the same underlying event.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable

# The fields that constitute an entry's identity. Anything outside this tuple
# is descriptive: it may differ between two records of the same event without
# making them different events.
IDENTIFYING_FIELDS: tuple[str, ...] = ("actor", "action", "outcome", "recorded_at")


def content_digest(actor: str, action: str, outcome: str, recorded_at: str) -> str:
    """Return the deterministic event id for this entry's recorded content.

    Identity is the recorded content itself, so the same event recorded twice
    collapses to one id and any later edit to a stored entry is detectable by
    recomputing this. The separator cannot appear in a field value, so distinct
    inputs cannot collide by concatenation.
    """

    joined = "\x1f".join((actor, action, outcome, recorded_at))
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
        if self.sequence < 1:
            raise ValueError("sequence must be a positive, gapless trail position")
        for name in ("actor", "action", "outcome", "recorded_at"):
            if not getattr(self, name):
                raise ValueError(f"{name} must not be empty")
        if len(self.event_id) != 64 or any(c not in "0123456789abcdef" for c in self.event_id):
            raise ValueError("event_id must be a sha256 hex digest")

    def recomputed_id(self) -> str:
        """The id this entry's current content implies; compare to ``event_id``.

        This is deliberately *not* checked in ``__post_init__``: constructing
        an entry whose stored id no longer matches its content is exactly how
        tamper detection is exercised, so the mismatch must be constructible,
        not rejected at creation.
        """

        return content_digest(self.actor, self.action, self.outcome, self.recorded_at)


@dataclass(frozen=True)
class LegacyRecord:
    """One entry as read from the older, per-export archive log-store format.

    ``ref`` is the archive's own reference for the entry and ``at`` is an
    export-observed timestamp -- neither is the canonical recorded content.
    Overlapping archive batches can hold the same underlying event twice with
    different ``ref``/``at`` values; :func:`reconcile_legacy_records` is what
    collapses those back into one canonical event.
    """

    ref: str
    actor: str
    action: str
    outcome: str
    at: str


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def reconcile_legacy_records(records: Iterable[LegacyRecord]) -> list[AuditEvent]:
    """Collapse archive records into gapless, content-identified canonical events.

    Two archive records describe the same event when their stable fields
    (``actor``, ``action``, ``outcome``) match; their ``ref`` and ``at`` are
    export artifacts, not part of identity. For each such group the earliest
    ``at`` is chosen as the event's ``recorded_at`` -- a deterministic
    representative timestamp, independent of the order records arrive in or
    which archive batch happened to export first. The resulting events are
    ordered by that timestamp and numbered into a gapless sequence.
    """

    groups: dict[tuple[str, str, str], list[LegacyRecord]] = {}
    for record in records:
        key = (record.actor, record.action, record.outcome)
        groups.setdefault(key, []).append(record)

    representatives: list[tuple[tuple[str, str, str], str]] = []
    for key, members in groups.items():
        earliest = min(members, key=lambda member: (_parse_timestamp(member.at), member.at))
        representatives.append((key, earliest.at))

    representatives.sort(key=lambda item: (_parse_timestamp(item[1]), item[0]))

    events: list[AuditEvent] = []
    for sequence, (key, at) in enumerate(representatives, start=1):
        actor, action, outcome = key
        events.append(
            AuditEvent(
                event_id=content_digest(actor, action, outcome, at),
                sequence=sequence,
                actor=actor,
                action=action,
                outcome=outcome,
                recorded_at=at,
                source_version=1,
            )
        )
    return events
