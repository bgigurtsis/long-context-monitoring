"""Storage-independent audit log service interface.

``AuditLogService`` is the contract every storage backend (in-memory, a
file, a database) must satisfy; callers depend on this interface rather than
on a specific backend so the storage mechanism can change without touching
callers. ``InMemoryAuditLogService`` is a reference implementation used by
the contract tests and by callers that do not need durability.

Every implementation must preserve two invariants: recorded events are
append-only (never removed, rewritten, or reordered), and an event's id is
always derived from its own canonical content, never accepted verbatim from
a caller.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any

from .models import ArchiveCandidate, AuditEvent, ImportManifest, content_digest


class AuditLogService(ABC):
    """Append-only audit trail with interrupted-archive-import support."""

    @abstractmethod
    def record(
        self,
        actor: str,
        action: str,
        outcome: str,
        recorded_at: str,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """Append one event and return it with its assigned sequence and id."""

    @abstractmethod
    def events(self) -> tuple[AuditEvent, ...]:
        """Return every recorded event, in append order."""

    @abstractmethod
    def find(
        self, *, actor: str | None = None, action: str | None = None
    ) -> tuple[AuditEvent, ...]:
        """Return recorded events matching the given filters, in append order."""

    @abstractmethod
    def verify(self) -> tuple[AuditEvent, ...]:
        """Return recorded events whose current content no longer matches their id."""

    @abstractmethod
    def import_archive(
        self, manifest: ImportManifest, candidates: Iterable[ArchiveCandidate]
    ) -> tuple[ImportManifest, tuple[AuditEvent, ...]]:
        """Resume an interrupted archive import.

        Each candidate's canonical content id is recomputed here rather than
        trusted from the archive. A candidate whose content id is already in
        ``manifest.imported_content_ids`` or already recorded is skipped, so
        re-running an interrupted import from an earlier offset cannot
        duplicate an event. Returns the advanced manifest and the events
        newly appended.
        """


class InMemoryAuditLogService(AuditLogService):
    """Reference ``AuditLogService`` implementation held in memory."""

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def record(
        self,
        actor: str,
        action: str,
        outcome: str,
        recorded_at: str,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            event_id=content_digest(actor, action, outcome, recorded_at),
            sequence=len(self._events) + 1,
            actor=actor,
            action=action,
            outcome=outcome,
            recorded_at=recorded_at,
            metadata=dict(metadata or {}),
        )
        self._events.append(event)
        return event

    def events(self) -> tuple[AuditEvent, ...]:
        return tuple(self._events)

    def find(
        self, *, actor: str | None = None, action: str | None = None
    ) -> tuple[AuditEvent, ...]:
        return tuple(
            event
            for event in self._events
            if (actor is None or event.actor == actor)
            and (action is None or event.action == action)
        )

    def verify(self) -> tuple[AuditEvent, ...]:
        return tuple(event for event in self._events if event.event_id != event.recomputed_id())

    def import_archive(
        self, manifest: ImportManifest, candidates: Iterable[ArchiveCandidate]
    ) -> tuple[ImportManifest, tuple[AuditEvent, ...]]:
        known_ids = set(manifest.imported_content_ids) | {event.event_id for event in self._events}
        appended: list[AuditEvent] = []
        newly_imported: list[str] = []
        offset = manifest.resume_offset

        for candidate in candidates:
            offset += 1
            content_id = candidate.content_id()
            if content_id in known_ids:
                continue
            event = AuditEvent(
                event_id=content_id,
                sequence=len(self._events) + 1,
                actor=candidate.actor,
                action=candidate.action,
                outcome=candidate.outcome,
                recorded_at=candidate.recorded_at,
                metadata={"source_ref": candidate.source_ref} if candidate.source_ref else {},
            )
            self._events.append(event)
            appended.append(event)
            newly_imported.append(content_id)
            known_ids.add(content_id)

        advanced = manifest.advanced(offset, newly_imported)
        return advanced, tuple(appended)
