"""Storage-independent audit log service.

``AuditService`` implements record/query/repair purely in terms of the
:class:`~auditlog.store.LogStore` seam: canonical events in, canonical events
out. It has no notion of files, JSON, or archive formats -- that translation
is the store adapter's job -- so the exact same service class runs over an
in-memory store in tests and a JSON file on disk in production.

Sequences are strict: a store's events must already form a gapless run
starting at 1 before anything is appended or reported on, and ``record``
always assigns the next position in that run. The trail itself is append
only -- ``repair`` never rewrites a canonical entry's recorded content, only
detects when one no longer matches its own id, and migrates an archive-format
store into canonical form exactly once.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from auditlog.models import AuditEvent, content_digest
from auditlog.store import LogStore


class SequenceError(Exception):
    """The trail's sequence numbers are not a gapless run starting at 1."""


class ArchiveFormatError(Exception):
    """The store is still archive-format; ``repair`` must migrate it first."""


@dataclass(frozen=True)
class RepairReport:
    """What ``AuditService.repair`` found and did."""

    verified: int
    tampered: tuple[str, ...]
    migrated: bool
    index_rebuilt: bool


class AuditService:
    """Record, query, and repair an append-only audit trail."""

    def __init__(self, store: LogStore) -> None:
        self._store = store

    def record(
        self,
        actor: str,
        action: str,
        outcome: str,
        recorded_at: str,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """Append one entry and return the canonical event that was stored."""

        state = self._store.read_state()
        if state.source_version != 2:
            raise ArchiveFormatError(
                "cannot append to an archive-format store; run repair to migrate it first"
            )
        events = _verify_sequence(state.events)

        event = AuditEvent(
            event_id=content_digest(actor, action, outcome, recorded_at),
            sequence=len(events) + 1,
            actor=actor,
            action=action,
            outcome=outcome,
            recorded_at=recorded_at,
            metadata=dict(metadata or {}),
        )
        self._store.write_events(events + (event,))
        return event

    def query(self, actor: str | None = None, action: str | None = None) -> list[AuditEvent]:
        """Return matching entries in trail order; storage order is never trusted."""

        events = self._store.read_state().events
        if actor is not None:
            events = tuple(event for event in events if event.actor == actor)
        if action is not None:
            events = tuple(event for event in events if event.action == action)
        return sorted(events, key=lambda event: event.sequence)

    def repair(self) -> RepairReport:
        """Verify integrity, migrate archive-format stores, and rebuild the index.

        Recorded content is never rewritten here: an archive-format store is
        migrated into canonical form exactly once (that is materializing the
        archive's reconciled events, not editing already-canonical content),
        and a store already in canonical form only ever has its derived index
        rebuilt. Tampering -- an entry whose id no longer matches its own
        content -- is reported, not silently corrected.
        """

        state = self._store.read_state()
        events = _verify_sequence(state.events)

        tampered = tuple(event.event_id for event in events if event.event_id != event.recomputed_id())

        migrated = state.source_version != 2
        if migrated:
            self._store.write_events(events)

        self._store.write_index(_build_index(events))

        return RepairReport(
            verified=len(events),
            tampered=tampered,
            migrated=migrated,
            index_rebuilt=True,
        )


def _verify_sequence(events: tuple[AuditEvent, ...]) -> tuple[AuditEvent, ...]:
    ordered = tuple(sorted(events, key=lambda event: event.sequence))
    for position, event in enumerate(ordered, start=1):
        if event.sequence != position:
            raise SequenceError(f"expected sequence {position} but found {event.sequence}")
    return ordered


def _build_index(events: tuple[AuditEvent, ...]) -> dict:
    by_actor: dict[str, list[int]] = {}
    by_action: dict[str, list[int]] = {}
    for event in events:
        by_actor.setdefault(event.actor, []).append(event.sequence)
        by_action.setdefault(event.action, []).append(event.sequence)
    return {"entry_count": len(events), "by_actor": by_actor, "by_action": by_action}
