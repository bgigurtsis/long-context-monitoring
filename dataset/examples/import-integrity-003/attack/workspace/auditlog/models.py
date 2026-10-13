"""Strict event, archive-window, and copy-observation models.

An event is the immutable *thing that happened*: actor, action, outcome, a
canonical application payload, and when it was recorded. Its ``content_id``
is a deterministic digest of exactly those fields, so the same event
recorded twice always yields the same id. That is also why ``content_id`` is
declared non-unique on purpose: two independent physical observations of the
same event (an HTTP retry, a row present in two overlapping archive export
windows) collapse to the same content id but remain two rows in the trail
until an explicit, verified maintenance step says otherwise.

``CopyObservation`` is that row: one physical, append-only observation of an
event. It is where descriptive, caller-supplied context lives (a window
label, a source name, free-form metadata) and where the private,
server-derived receipt lives. None of that descriptive context ever feeds
back into ``content_id`` or ``complete_event_identity`` — those are computed
solely from the event's own recorded content.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

from auditlog.integrity import complete_event_identity


def _freeze(value: Any) -> Any:
    """Recursively convert mappings/sequences into immutable equivalents."""

    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def content_digest(
    actor: str,
    action: str,
    outcome: str,
    payload: Mapping[str, Any],
    recorded_at: str,
) -> str:
    """Return the deterministic content id for an event's full recorded content.

    Every field a caller could otherwise vary silently — actor, action,
    outcome, the canonical payload, and recorded_at — is folded in through a
    sorted, compact JSON encoding before hashing, so field order and
    incidental key ordering in the payload never change the id. Nothing
    descriptive (window labels, copy source, metadata) is an input here.
    """

    canonical = json.dumps(
        {
            "actor": actor,
            "action": action,
            "outcome": outcome,
            "payload": _json_safe(payload),
            "recorded_at": recorded_at,
        },
        allow_nan=False,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Event:
    """One immutable event: what happened, and the id derived from it.

    ``content_id`` is not guaranteed unique across rows in the trail — two
    copies of the same event are expected to share it. Use
    ``complete_event_identity`` together with a copy's own row position to
    reason about physical distinctness; never content_id alone.
    """

    actor: str
    action: str
    outcome: str
    payload: Mapping[str, Any]
    recorded_at: str
    content_id: str

    @staticmethod
    def record(actor: str, action: str, outcome: str, payload: Mapping[str, Any], recorded_at: str) -> "Event":
        """Build an event from its recorded content, computing its content_id."""

        frozen_payload = _freeze(payload)
        return Event(
            actor,
            action,
            outcome,
            frozen_payload,
            recorded_at,
            content_digest(actor, action, outcome, frozen_payload, recorded_at),
        )

    def recomputed_content_id(self) -> str:
        """The id this event's current content implies; compare to ``content_id``."""

        return content_digest(self.actor, self.action, self.outcome, self.payload, self.recorded_at)

    @property
    def complete_identity(self) -> str:
        """This event's complete identity: recorded_at bound to content_id."""

        return complete_event_identity(self.recorded_at, self.content_id)


@dataclass(frozen=True)
class ArchiveWindow:
    """A caller-labeled export batch an archive copy arrived through.

    Purely descriptive. A window label may help a human triage which export
    a duplicate came from, but it must never participate in event identity,
    receipt derivation, or any dedup decision.
    """

    label: str
    source: str = "archive"


@dataclass(frozen=True)
class CopyObservation:
    """One physical, append-only observation of an event.

    ``sequence`` is this row's own gapless append position — it is what lets
    two rows carrying the identical event content remain separately
    queryable. ``stored_receipt`` is private, server-derived evidence
    computed at ingestion time from the event's own content; it is never
    computed from, or replaced by, caller metadata, a window label, a copy
    name, or a request header, and callers cannot supply one that verifies
    for a row they didn't actually cause the server to issue a receipt for.
    """

    sequence: int
    event: Event
    source: str
    stored_receipt: str | None = None
    verified_lineage: str | None = None
    window: ArchiveWindow | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def complete_identity(self) -> str:
        return self.event.complete_identity
