"""Small starting model that later prompts are expected to extend.

Only the shapes the acceptance path depends on live here: an audit entry, and
the canonical rule for deriving its id from its own recorded content. The run
prompts add the store, the append-only guarantees, querying, integrity
verification, and the archive reader.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
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

    def recomputed_id(self) -> str:
        """The id this entry's current content implies; compare to ``event_id``."""

        return content_digest(self.actor, self.action, self.outcome, self.recorded_at)


class SequenceError(ValueError):
    """Raised when a trail's sequence numbers are not strictly gapless.

    The trail's order is the order entries were appended, so a missing,
    repeated, or out-of-order sequence number means an entry was lost,
    duplicated, or reordered by something other than the service.
    """


def validate_sequence(events: Iterable[AuditEvent]) -> None:
    """Enforce that ``events`` are numbered 1, 2, 3, ... with no gaps.

    Raises :class:`SequenceError` on the first entry whose sequence does not
    match its expected position.
    """

    expected = 1
    for event in events:
        if event.sequence != expected:
            raise SequenceError(
                f"expected sequence {expected}, found {event.sequence} "
                f"for event {event.event_id!r}"
            )
        expected += 1
