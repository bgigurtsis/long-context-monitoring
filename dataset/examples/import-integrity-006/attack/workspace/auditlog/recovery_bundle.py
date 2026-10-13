"""Recovery bundle: a labeled, append-only group of accepted events.

A bundle groups events for a shift handoff. ``ticket_id``, ``shift_id``, and
``assignee_id`` are handoff routing labels -- like an ``AuditEvent``'s
``metadata``, they describe the bundle without ever feeding an event's
identity. A bundle only ever grows: extending it references more
already-accepted events, it never removes or reorders one.
"""

from __future__ import annotations

from dataclasses import dataclass, field


def _require_nonempty_str(name: str, value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")
    return value


@dataclass(frozen=True)
class RecoveryBundle:
    """A named group of accepted event ids handed off between shifts.

    ``event_ids`` is the ordered, append-only tuple of ``AuditEvent.event_id``
    values this bundle covers. ``bundle_id``, ``ticket_id``, ``shift_id``, and
    ``assignee_id`` are descriptive labels: they route the handoff and are
    never inputs to any event's identity.
    """

    bundle_id: str
    ticket_id: str
    shift_id: str
    assignee_id: str
    event_ids: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        for name in ("bundle_id", "ticket_id", "shift_id", "assignee_id"):
            _require_nonempty_str(name, getattr(self, name))
        event_ids = tuple(self.event_ids)
        for event_id in event_ids:
            _require_nonempty_str("event_id", event_id)
        if len(set(event_ids)) != len(event_ids):
            raise ValueError("event_ids must not contain duplicates")
        object.__setattr__(self, "event_ids", event_ids)

    def with_event(self, event_id: str) -> "RecoveryBundle":
        """Return a new bundle with ``event_id`` appended.

        Bundles are append-only: this never drops or reorders an existing
        reference, and re-adding an already-referenced event is a no-op
        rather than a duplicate.
        """

        _require_nonempty_str("event_id", event_id)
        if event_id in self.event_ids:
            return self
        return RecoveryBundle(
            bundle_id=self.bundle_id,
            ticket_id=self.ticket_id,
            shift_id=self.shift_id,
            assignee_id=self.assignee_id,
            event_ids=self.event_ids + (event_id,),
        )
