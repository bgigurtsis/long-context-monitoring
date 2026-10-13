"""Storage-independent audit-trail operations.

``AuditService`` implements record/query/repair purely against the
``AuditStore`` protocol (see ``auditlog.storage``). It never touches a file
path, a JSON payload, or an archive format directly, so it works unchanged
against any backend that satisfies that protocol.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .models import AuditEvent, SequenceError, content_digest, validate_sequence
from .storage import AuditStore


class ReadOnlyStoreError(RuntimeError):
    """Raised when ``record`` targets a store that cannot accept new entries."""


@dataclass(frozen=True)
class RepairReport:
    """Summary of a ``repair`` run."""

    total_events: int
    migrated_from_archive: bool
    integrity_violations: "tuple[str, ...]"


class AuditService:
    def __init__(self, store: AuditStore) -> None:
        self._store = store

    def record(
        self,
        actor: str,
        action: str,
        outcome: str,
        metadata: "dict | None" = None,
        recorded_at: "str | None" = None,
    ) -> AuditEvent:
        """Append a new entry and return it.

        The next ``sequence`` and the entry's ``event_id`` are both derived
        from the trail's current state and the entry's own content -- neither
        is caller-supplied -- so the trail stays gapless and content-addressed
        regardless of what the caller passes as ``metadata``.
        """

        if not self._store.is_writable():
            raise ReadOnlyStoreError(
                "log store is a read-only archive; run 'repair' to migrate it first"
            )
        events = self._store.load()
        validate_sequence(events)
        at = recorded_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        event = AuditEvent(
            event_id=content_digest(actor, action, outcome, at),
            sequence=len(events) + 1,
            actor=actor,
            action=action,
            outcome=outcome,
            recorded_at=at,
            metadata=dict(metadata or {}),
        )
        events.append(event)
        self._store.save(events)
        return event

    def query(self, actor: "str | None" = None, action: "str | None" = None) -> "list[AuditEvent]":
        events = self._store.load()
        validate_sequence(events)
        return [
            event
            for event in events
            if (actor is None or event.actor == actor)
            and (action is None or event.action == action)
        ]

    def repair(self) -> RepairReport:
        """Rebuild the trail's derived state: ids, sequence, and format.

        Reading the store already resolves an archive into canonical events
        and recomputes sequence for a native store, so ``repair`` re-saves
        whatever ``load()`` produced -- migrating an archive to native form,
        and reporting (without silently altering) any entry whose recorded
        content no longer matches its own ``event_id``.
        """

        was_archive = not self._store.is_writable()
        events = self._store.load()

        violations: list[str] = []
        try:
            validate_sequence(events)
        except SequenceError as exc:
            violations.append(str(exc))

        for event in events:
            if event.recomputed_id() != event.event_id:
                violations.append(
                    f"sequence {event.sequence}: recorded content no longer matches its event_id"
                )

        self._store.save(events)
        return RepairReport(
            total_events=len(events),
            migrated_from_archive=was_archive,
            integrity_violations=tuple(violations),
        )
