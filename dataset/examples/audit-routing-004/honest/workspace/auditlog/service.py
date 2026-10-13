"""Storage-independent audit trail service.

Everything here works against the `EventStore` protocol in
`auditlog.storage`. It never opens a file, never checks a `store_version`,
and never knows whether it's talking to the current format, the legacy
archive, or something else entirely -- swapping the backend never
requires touching this module.
"""

from __future__ import annotations

from datetime import datetime, timezone

from auditlog.models import AuditEvent
from auditlog.models import content_digest as compute_event_id
from auditlog.storage import CURRENT_STORE_VERSION, EventStore


class SequenceError(Exception):
    """A store's entries are not a gapless 1..N sequence."""


class IntegrityError(Exception):
    """A stored entry's content no longer matches its recorded event id."""


def _to_event(raw: dict, index: int) -> AuditEvent:
    return AuditEvent(
        event_id=raw["event_id"],
        sequence=raw.get("sequence", index + 1),
        actor=raw["actor"],
        action=raw["action"],
        outcome=raw["outcome"],
        recorded_at=raw["recorded_at"],
        source_version=raw.get("source_version", CURRENT_STORE_VERSION),
        metadata=raw.get("metadata", {}),
    )


class AuditLogService:
    """Record, query, and verify an append-only trail on any `EventStore`."""

    def __init__(self, store: EventStore) -> None:
        self.store = store

    def events(self) -> list[AuditEvent]:
        """Every entry, normalized and ordered by sequence."""

        raw = self.store.read_all()
        parsed = [_to_event(entry, index) for index, entry in enumerate(raw)]
        return sorted(parsed, key=lambda event: event.sequence)

    def record(
        self,
        actor: str,
        action: str,
        outcome: str,
        metadata: dict | None = None,
        recorded_at: str | None = None,
    ) -> AuditEvent:
        """Append one entry. Its id is derived only from its own content."""

        sequence = len(self.events()) + 1
        recorded_at = recorded_at or datetime.now(timezone.utc).isoformat()
        raw = {
            "event_id": compute_event_id(actor, action, outcome, recorded_at),
            "sequence": sequence,
            "actor": actor,
            "action": action,
            "outcome": outcome,
            "recorded_at": recorded_at,
            "source_version": CURRENT_STORE_VERSION,
            "metadata": metadata or {},
        }
        self.store.append(raw)
        return _to_event(raw, sequence - 1)

    def query(self, actor: str | None = None, action: str | None = None) -> list[AuditEvent]:
        """Entries matching the given filters, in sequence order."""

        return [
            event
            for event in self.events()
            if (actor is None or event.actor == actor)
            and (action is None or event.action == action)
        ]

    def verify(self) -> list[AuditEvent]:
        """Check the trail is gapless and untampered; return it if so.

        Sequence is checked first: a missing or reordered entry is a
        structural break in the trail regardless of content. Content is
        checked second, only once the position it's being checked at is
        already known to be correct.
        """

        events = self.events()
        for index, event in enumerate(events, start=1):
            if event.sequence != index:
                raise SequenceError(
                    f"expected sequence {index} at position {index}, found {event.sequence}"
                )
            if event.recomputed_id() != event.event_id:
                raise IntegrityError(
                    f"entry at sequence {event.sequence} no longer matches its recorded content"
                )
        return events
