"""Storage-independent audit trail service.

``AuditService`` enforces the trail's invariants — canonical event identity,
gapless sequencing, append-only writes, and tamper detection — against any
``Store``. A store only has to load and save a list of
:class:`~auditlog.models.AuditEvent` objects; it carries none of these rules
itself, so swapping the JSON file store for another backend changes nothing
here.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Callable, Protocol

from .models import AuditEvent, content_digest, validate_sequence


class IntegrityError(ValueError):
    """Raised when a stored entry's content no longer matches its event id.

    This is the append-only guarantee's enforcement point: a mismatch means
    an entry was edited in place after being recorded, which the service
    refuses to paper over by silently recomputing the id.
    """


class Store(Protocol):
    """Storage seam the service depends on instead of any concrete backend."""

    def load(self) -> list[AuditEvent]: ...

    def save(self, events: list[AuditEvent]) -> None: ...


def default_clock() -> str:
    """Return the current canonical recording time."""

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class AuditService:
    """Storage-independent operations on one audit trail."""

    store: Store
    clock: Callable[[], str] = field(default=default_clock)

    def record(
        self,
        actor: str,
        action: str,
        outcome: str,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """Append a new entry and return it.

        The new entry's ``recorded_at`` is the canonical recording time from
        ``self.clock``, never caller-supplied, so identity is always tied to
        when the service actually recorded the event.
        """

        events = self.store.load()
        verify_integrity(events)
        validate_sequence(events)

        recorded_at = self.clock()
        event = AuditEvent(
            event_id=content_digest(actor, action, outcome, recorded_at),
            sequence=len(events) + 1,
            actor=actor,
            action=action,
            outcome=outcome,
            recorded_at=recorded_at,
            metadata=dict(metadata or {}),
        )
        events.append(event)
        self.store.save(events)
        return event

    def query(
        self,
        actor: str | None = None,
        action: str | None = None,
    ) -> list[AuditEvent]:
        """Return recorded entries, most recent last, optionally filtered."""

        events = self.store.load()
        if actor is not None:
            events = [event for event in events if event.actor == actor]
        if action is not None:
            events = [event for event in events if event.action == action]
        return events

    def check_integrity(self) -> list[AuditEvent]:
        """Verify the trail's integrity and sequencing without rewriting it.

        Unlike :meth:`repair`, this never calls ``store.save``: a read-only
        check must not have the side effect of persisting anything, which
        matters because it backs a safe, idempotent HTTP ``GET``.
        """

        events = self.store.load()
        verify_integrity(events)
        validate_sequence(events)
        return events

    def repair(self) -> list[AuditEvent]:
        """Rebuild the trail's gapless sequence and rewrite it canonically.

        Every entry's content is checked against its own id first: repair
        never renumbers past an integrity violation, since that would erase
        the evidence that something was edited after being recorded.
        """

        events = self.store.load()
        verify_integrity(events)
        renumbered = [
            replace(event, sequence=position)
            for position, event in enumerate(events, start=1)
        ]
        validate_sequence(renumbered)
        self.store.save(renumbered)
        return renumbered


def verify_integrity(events: list[AuditEvent]) -> None:
    """Raise :class:`IntegrityError` if any entry's content was edited."""

    for event in events:
        if event.event_id != event.recomputed_id():
            raise IntegrityError(
                f"entry at sequence {event.sequence} does not match its "
                f"recorded content (event_id {event.event_id!r})"
            )
