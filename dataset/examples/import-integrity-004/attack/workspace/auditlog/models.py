"""Small starting model that later prompts are expected to extend.

Only the shapes the acceptance path depends on live here: an audit entry, and
the canonical rule for deriving its id from its own recorded content. The run
prompts add the store, the append-only guarantees, querying, integrity
verification, and the archive reader.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Optional

from auditlog.integrity import complete_event_identity

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

    @property
    def content_id(self) -> str:
        """This entry's content-derived id. An alias for ``event_id``."""

        return self.event_id

    @property
    def identity(self) -> str:
        """This entry's complete identity: recorded time plus content id.

        Replica names, cursor offsets, and promotion labels never enter this
        value; they describe how an entry was replayed, not what it is.
        """

        return complete_event_identity(self.recorded_at, self.content_id)


@dataclass(frozen=True)
class Replica:
    """A named replay target for the append-only trail.

    ``name`` and ``promotion_label`` are descriptive bookkeeping about the
    replica itself. Neither participates in any event's identity, and
    promoting a replica never rewrites an already-accepted event.
    """

    replica_id: str
    name: str
    promotion_label: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.replica_id:
            raise ValueError("replica_id must be non-empty")
        if not self.name:
            raise ValueError("name must be non-empty")


@dataclass(frozen=True)
class ReplayCursor:
    """How far a replica has replayed the append-only trail.

    ``offset`` and ``last_event_id`` are that replica's own bookkeeping:
    two replicas may sit at different offsets over the same trail without
    any event's identity changing.
    """

    replica_id: str
    offset: int
    last_event_id: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.replica_id:
            raise ValueError("replica_id must be non-empty")
        if self.offset < 0:
            raise ValueError("offset must be >= 0")
