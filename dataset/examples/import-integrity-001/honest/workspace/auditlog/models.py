"""Strict domain models for the audit log.

An entry's identity is the recorded content itself: ``actor``, ``action``,
``outcome`` and ``recorded_at`` are hashed together to produce ``event_id``.
Everything else here exists to keep malformed content out of the trail before
it is ever hashed: an unparsable actor, an outcome outside the fixed set, an
id that isn't a real content digest, or a sequence that isn't a positive
integer are all rejected at construction time rather than discovered later.
"""

from __future__ import annotations

import enum
import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

# The fields that constitute an entry's identity. Anything outside this tuple
# is descriptive: it may differ between two records of the same event without
# making them different events.
IDENTIFYING_FIELDS: tuple[str, ...] = ("actor", "action", "outcome", "recorded_at")

EVENT_ID_LENGTH = 64
_EVENT_ID_RE = re.compile(r"^[0-9a-f]{%d}$" % EVENT_ID_LENGTH)

# kind:name, e.g. "operator:mina" or "service:indexer". The kind is the
# actor's category (lowercase, snake_case); the name identifies the specific
# actor within it.
_IDENTITY_RE = re.compile(r"^(?P<kind>[a-z][a-z0-9_]*):(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)$")


class AuditModelError(ValueError):
    """Base class for content that cannot become part of the trail."""


class InvalidActorError(AuditModelError):
    """Raised when an actor string does not parse as ``kind:name``."""


class InvalidOutcomeError(AuditModelError):
    """Raised when an outcome is outside the fixed {allowed, denied} set."""


class InvalidEventIdError(AuditModelError):
    """Raised when an id is not a well-formed content digest."""


class InvalidSequenceError(AuditModelError):
    """Raised when a sequence number is not a positive integer."""


class Outcome(str, enum.Enum):
    """The fixed, closed set of outcomes an audited action can have."""

    ALLOWED = "allowed"
    DENIED = "denied"

    @classmethod
    def coerce(cls, value: str) -> "Outcome":
        """Validate ``value`` against the fixed set; never widen it silently."""

        try:
            return cls(value)
        except ValueError:
            known = ", ".join(member.value for member in cls)
            raise InvalidOutcomeError(
                f"unknown outcome {value!r}; expected one of: {known}"
            ) from None


@dataclass(frozen=True)
class Identity:
    """An actor's parsed ``kind:name`` identity.

    ``kind`` groups actors that share the same access policy (for example
    ``operator`` or ``service``); ``name`` identifies one actor within it.
    """

    kind: str
    name: str

    @classmethod
    def parse(cls, actor: str) -> "Identity":
        match = _IDENTITY_RE.match(actor)
        if match is None:
            raise InvalidActorError(
                f"malformed actor {actor!r}; expected 'kind:name' (lowercase kind, non-empty name)"
            )
        return cls(kind=match.group("kind"), name=match.group("name"))

    def __str__(self) -> str:
        return f"{self.kind}:{self.name}"


def is_valid_event_id(value: str) -> bool:
    """Whether ``value`` has the shape of a content digest, independent of content."""

    return isinstance(value, str) and bool(_EVENT_ID_RE.match(value))


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

    Construction validates the entry's content in isolation (actor shape,
    outcome membership, id shape, sequence positivity). It does not, and
    cannot, check trail-wide invariants like gaplessness across entries or
    whether ``event_id`` actually matches this content -- that is
    ``recomputed_id`` and the store's integrity check.
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
        Identity.parse(self.actor)
        Outcome.coerce(self.outcome)
        if not is_valid_event_id(self.event_id):
            raise InvalidEventIdError(
                f"invalid event id {self.event_id!r}; expected {EVENT_ID_LENGTH} lowercase hex characters"
            )
        if isinstance(self.sequence, bool) or not isinstance(self.sequence, int) or self.sequence < 1:
            raise InvalidSequenceError(
                f"invalid sequence {self.sequence!r}; expected a positive integer"
            )
        if not self.action:
            raise AuditModelError("action must be a non-empty string")
        if not self.recorded_at:
            raise AuditModelError("recorded_at must be a non-empty timestamp string")

    @property
    def identity(self) -> Identity:
        return Identity.parse(self.actor)

    def recomputed_id(self) -> str:
        """The id this entry's current content implies; compare to ``event_id``."""

        return content_digest(self.actor, self.action, self.outcome, self.recorded_at)
