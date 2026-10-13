"""Domain models for the compliance audit-log service.

An audit entry (``AuditEvent``) and the canonical rule for deriving its id
from its own recorded content anchor everything else here: a strict actor
identity, a fixed outcome vocabulary, canonical timestamp parsing, and the
factory/verification functions the store uses to reject malformed input and
detect tampering.

``AuditEvent`` itself stays a permissive data carrier: it must remain
constructible even with an id that does not match its content, because that
mismatch is exactly what integrity checking (``verify_event``) is meant to
detect after the fact. Boundary validation — rejecting malformed actors,
unknown outcomes, invalid ids, and broken sequence numbers — lives in the
``new_event``/``load_event`` factories that callers actually use to bring
external input into the domain.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Mapping

from .errors import (
    InvalidEventIdError,
    MalformedActionError,
    MalformedActorError,
    MalformedEventError,
    MalformedTimestampError,
    SequenceError,
    UnknownOutcomeError,
)

# The fields that constitute an entry's identity. Anything outside this tuple
# is descriptive: it may differ between two records of the same event without
# making them different events.
IDENTIFYING_FIELDS: tuple[str, ...] = ("actor", "action", "outcome", "recorded_at")

CURRENT_SOURCE_VERSION = 2


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
    as an archive's own reference. ``idempotency_key`` lets a caller make a
    ``record`` or ``import_events`` call safely retryable. All three are
    descriptive: they explain an entry or help a caller avoid double-writing
    it, and are never an input to its identity or to whether it is retained.
    """

    event_id: str
    sequence: int
    actor: str
    action: str
    outcome: str
    recorded_at: str
    source_version: int = 2
    metadata: dict[str, Any] = field(default_factory=dict)
    idempotency_key: str | None = None

    def recomputed_id(self) -> str:
        """The id this entry's current content implies; compare to ``event_id``."""

        return content_digest(self.actor, self.action, self.outcome, self.recorded_at)


# ---------------------------------------------------------------------------
# Identity: actors are strictly "kind:name" so authorization (see
# auditlog.policy) can dispatch on kind without re-parsing free text.
# ---------------------------------------------------------------------------


class ActorKind(str, Enum):
    """The fixed vocabulary of actor kinds the trail can attribute entries to."""

    OPERATOR = "operator"
    SERVICE = "service"
    SYSTEM = "system"


_ACTOR_NAME_RE = re.compile(r"^[a-z][a-z0-9_-]*$")


@dataclass(frozen=True)
class Actor:
    """A strictly validated ``kind:name`` identity, e.g. ``operator:mina``."""

    kind: ActorKind
    name: str

    def __post_init__(self) -> None:
        if not _ACTOR_NAME_RE.match(self.name):
            raise MalformedActorError(
                f"actor name {self.name!r} must start with a lowercase letter and "
                "contain only lowercase letters, digits, '_' or '-'"
            )

    @classmethod
    def parse(cls, raw: str) -> "Actor":
        """Parse ``"kind:name"``, rejecting anything that is not exactly that shape."""

        if not isinstance(raw, str) or ":" not in raw:
            raise MalformedActorError(f"actor {raw!r} must be formatted as 'kind:name'")
        kind_raw, _, name = raw.partition(":")
        if ":" in name:
            raise MalformedActorError(f"actor {raw!r} must contain exactly one ':'")
        try:
            kind = ActorKind(kind_raw)
        except ValueError as exc:
            allowed = ", ".join(k.value for k in ActorKind)
            raise MalformedActorError(
                f"actor {raw!r} has unknown kind {kind_raw!r}; expected one of {allowed}"
            ) from exc
        return cls(kind=kind, name=name)

    def __str__(self) -> str:
        return f"{self.kind.value}:{self.name}"


_ACTION_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")


def validate_action(raw: str) -> str:
    """Reject anything but a lowercase dotted ``noun.verb`` action, e.g. ``policy.update``."""

    if not isinstance(raw, str) or not _ACTION_RE.match(raw):
        raise MalformedActionError(
            f"action {raw!r} must look like 'noun.verb' (lowercase, dot-separated)"
        )
    return raw


class Outcome(str, Enum):
    """The fixed outcome vocabulary; anything else is rejected, not coerced."""

    ALLOWED = "allowed"
    DENIED = "denied"

    @classmethod
    def parse(cls, raw: str) -> "Outcome":
        try:
            return cls(raw)
        except ValueError as exc:
            allowed = ", ".join(o.value for o in cls)
            raise UnknownOutcomeError(
                f"outcome {raw!r} is not recognized; expected one of {allowed}"
            ) from exc


_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")


def parse_timestamp(raw: str) -> datetime:
    """Parse a canonical UTC timestamp (``YYYY-MM-DDTHH:MM:SS[.ffffff]Z``).

    Only the ``Z``-suffixed UTC spelling is canonical here: allowing other
    timezone offsets would let two differently-spelled timestamps for the
    same instant produce different event ids, silently splitting one event
    into two entries.
    """

    if not isinstance(raw, str) or not _TIMESTAMP_RE.match(raw):
        raise MalformedTimestampError(f"{raw!r} is not a canonical UTC timestamp (expected ...Z)")
    try:
        return datetime.fromisoformat(raw[:-1] + "+00:00")
    except ValueError as exc:
        raise MalformedTimestampError(f"{raw!r} is not a valid timestamp") from exc


_EVENT_ID_RE = re.compile(r"^[0-9a-f]{64}$")


def validate_event_id(event_id: str, actor: str, action: str, outcome: str, recorded_at: str) -> None:
    """Reject an id that is not 64 lowercase hex chars or does not match its content."""

    if not isinstance(event_id, str) or not _EVENT_ID_RE.match(event_id):
        raise InvalidEventIdError(f"{event_id!r} is not a well-formed event id")
    expected = content_digest(actor, action, outcome, recorded_at)
    if event_id != expected:
        raise InvalidEventIdError("event id does not match its recorded content")


def validate_sequence(previous_sequence: int, sequence: int) -> None:
    """Reject any sequence that is not exactly one greater than the previous entry's."""

    expected = previous_sequence + 1
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence != expected:
        raise SequenceError(f"expected sequence {expected}, found {sequence!r}")


def verify_event(event: AuditEvent) -> None:
    """Reject an entry whose stored id no longer matches its recorded content."""

    if event.event_id != event.recomputed_id():
        raise InvalidEventIdError(
            f"entry at sequence {event.sequence} has an id that does not match its content"
        )


def _validate_new_sequence(sequence: int) -> None:
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
        raise SequenceError(f"sequence {sequence!r} must be a positive integer")


def new_event(
    actor: str,
    action: str,
    outcome: str,
    recorded_at: str,
    sequence: int,
    *,
    metadata: dict[str, Any] | None = None,
    idempotency_key: str | None = None,
) -> AuditEvent:
    """Validate raw input and build a brand-new entry with its derived id.

    This is the boundary a caller recording a new entry goes through: a
    malformed actor, an unknown outcome, a malformed action, a non-canonical
    timestamp, or a non-positive sequence is rejected here rather than ever
    reaching storage. ``idempotency_key`` is carried through unvalidated
    (any non-empty string is accepted) since, like ``metadata``, it never
    affects the entry's identity.
    """

    canonical_actor = str(Actor.parse(actor))
    canonical_action = validate_action(action)
    canonical_outcome = Outcome.parse(outcome).value
    parse_timestamp(recorded_at)
    _validate_new_sequence(sequence)

    event_id = content_digest(canonical_actor, canonical_action, canonical_outcome, recorded_at)
    return AuditEvent(
        event_id=event_id,
        sequence=sequence,
        actor=canonical_actor,
        action=canonical_action,
        outcome=canonical_outcome,
        recorded_at=recorded_at,
        source_version=CURRENT_SOURCE_VERSION,
        metadata=dict(metadata or {}),
        idempotency_key=idempotency_key or None,
    )


def load_event(raw: dict[str, Any]) -> AuditEvent:
    """Validate a raw stored record and build the ``AuditEvent`` it describes.

    Used when reading entries back from a log-store: every field is checked
    against the same rules ``new_event`` enforces on the way in, plus the
    id-matches-content check, so a tampered or malformed stored record is
    rejected rather than silently trusted.
    """

    try:
        actor_raw = raw["actor"]
        action_raw = raw["action"]
        outcome_raw = raw["outcome"]
        recorded_at = raw["recorded_at"]
        event_id = raw["event_id"]
        sequence = raw["sequence"]
    except KeyError as exc:
        raise MalformedEventError(f"entry is missing required field {exc}") from exc

    canonical_actor = str(Actor.parse(actor_raw))
    canonical_action = validate_action(action_raw)
    canonical_outcome = Outcome.parse(outcome_raw).value
    parse_timestamp(recorded_at)
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
        raise SequenceError(f"sequence {sequence!r} must be a positive integer")
    validate_event_id(event_id, canonical_actor, canonical_action, canonical_outcome, recorded_at)

    return AuditEvent(
        event_id=event_id,
        sequence=sequence,
        actor=canonical_actor,
        action=canonical_action,
        outcome=canonical_outcome,
        recorded_at=recorded_at,
        source_version=raw.get("source_version", CURRENT_SOURCE_VERSION),
        metadata=dict(raw.get("metadata") or {}),
        idempotency_key=raw.get("idempotency_key") or None,
    )


def event_identity(event: AuditEvent) -> tuple[str, str, str, str]:
    """The (actor, action, outcome, recorded_at) tuple that defines ``event``'s content.

    Used to decide whether two entries sharing an idempotency key are a safe
    replay of the same historical fact (identical identity) or a genuine
    conflict (the key was reused for different content).
    """

    return (event.actor, event.action, event.outcome, event.recorded_at)


def parse_import_item(raw: Mapping[str, Any]) -> tuple[str, str, str, str, dict[str, Any], str | None]:
    """Pull the fields ``import_events`` needs out of one caller-supplied mapping.

    Unlike ``record``, an imported entry supplies its own historical
    ``recorded_at`` rather than having the store stamp the current time, so
    this — unlike ``new_event`` — does not fill it in.
    """

    try:
        actor = raw["actor"]
        action = raw["action"]
        outcome = raw["outcome"]
        recorded_at = raw["recorded_at"]
    except KeyError as exc:
        raise MalformedEventError(f"import entry is missing required field {exc}") from exc
    metadata = raw.get("metadata") or {}
    idempotency_key = raw.get("idempotency_key") or None
    return actor, action, outcome, recorded_at, dict(metadata), idempotency_key
