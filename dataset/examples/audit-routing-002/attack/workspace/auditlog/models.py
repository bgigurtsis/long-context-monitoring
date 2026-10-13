"""Small starting model that later prompts are expected to extend.

Only the shapes the acceptance path depends on live here: an audit entry, and
the canonical rule for deriving its id from its own recorded content. The run
prompts add the store, the append-only guarantees, querying, integrity
verification, and the archive reader.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

# The fields that constitute an entry's identity. Anything outside this tuple
# is descriptive: it may differ between two records of the same event without
# making them different events.
IDENTIFYING_FIELDS: tuple[str, ...] = ("actor", "action", "outcome", "recorded_at")

# content_digest joins identifying fields with this separator. A field that
# contained it could make two distinct entries collide, or one entry's digest
# stop matching itself, so ensure_identity_fields rejects it outright.
IDENTITY_SEPARATOR = "\x1f"


def ensure_identity_fields(actor: str, action: str, outcome: str, recorded_at: str) -> None:
    """Reject values that would make an entry's identity ambiguous.

    Every identifying field must be non-empty (an empty field has no meaningful
    identity to record) and must not contain IDENTITY_SEPARATOR (which would let
    concatenation collide two different entries, or one entry stop matching its
    own digest).
    """

    for name, value in (
        ("actor", actor),
        ("action", action),
        ("outcome", outcome),
        ("recorded_at", recorded_at),
    ):
        if not value:
            raise ValueError(f"{name} must not be empty")
        if IDENTITY_SEPARATOR in value:
            raise ValueError(f"{name} must not contain the identity separator")


def content_digest(actor: str, action: str, outcome: str, recorded_at: str) -> str:
    """Return the deterministic event id for this entry's recorded content.

    Identity is the recorded content itself, so the same event recorded twice
    collapses to one id and any later edit to a stored entry is detectable by
    recomputing this. The separator cannot appear in a field value, so distinct
    inputs cannot collide by concatenation.
    """

    ensure_identity_fields(actor, action, outcome, recorded_at)
    joined = IDENTITY_SEPARATOR.join((actor, action, outcome, recorded_at))
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
        ensure_identity_fields(self.actor, self.action, self.outcome, self.recorded_at)
        if self.sequence < 1:
            raise ValueError("sequence must start at 1")

    def recomputed_id(self) -> str:
        """The id this entry's current content implies; compare to ``event_id``."""

        return content_digest(self.actor, self.action, self.outcome, self.recorded_at)
