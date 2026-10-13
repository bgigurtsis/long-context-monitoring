"""Storage-independent audit log service.

``AuditLogService`` depends only on the :class:`EventStore` and
:class:`~auditlog.index_segments.QueryIndex` contracts, never on a concrete
backing store or index implementation. Either half is freely replaceable:
swap the store for a different persistence mechanism, or swap the index for a
different rebuild or query strategy, without changing the other or the
service itself. Everything here is the Python standard library only.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Protocol

from .index_segments import QueryIndex
from .models import AuditEvent, RebuildPlan, content_digest


class EventStore(Protocol):
    """Storage-independent contract for the append-only source of events."""

    def append(self, event: AuditEvent) -> None: ...

    def iter_events(self) -> Iterator[AuditEvent]: ...


class InMemoryEventStore:
    """Reference :class:`EventStore`: an append-only, order-preserving list.

    Existing entries are never replaced or reordered; ``append`` only grows
    the trail.
    """

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def append(self, event: AuditEvent) -> None:
        self._events.append(event)

    def iter_events(self) -> Iterator[AuditEvent]:
        return iter(self._events)


class AuditLogService:
    """Wires a source-of-truth event store to a replaceable query index.

    ``repair`` rebuilds the index by reading the store; it never writes back
    to the store, so the source events it reads stay exactly as recorded.
    """

    def __init__(self, store: EventStore, index: QueryIndex) -> None:
        self._store = store
        self._index = index

    def record(self, event: AuditEvent) -> None:
        self._store.append(event)
        self._reindex()

    def record_new(
        self,
        *,
        actor: str,
        action: str,
        outcome: str,
        recorded_at: str,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """Construct, store, and return a new event from its recorded content.

        The event's id comes from its own content, including ``recorded_at``;
        its ``sequence`` comes from how many events the store already holds.
        ``metadata`` is caller-supplied descriptive context and never feeds
        the id, matching ``content_digest``'s fixed input set.
        """

        sequence = sum(1 for _ in self._store.iter_events()) + 1
        event_id = content_digest(actor, action, outcome, recorded_at)
        event = AuditEvent(event_id, sequence, actor, action, outcome, recorded_at, metadata=metadata or {})
        self._store.append(event)
        self._reindex()
        return event

    def _reindex(self) -> None:
        """Keep the query index caught up with the store after a write.

        ``repair`` remains the explicit, on-demand way to rebuild the index
        (for example after replacing it); this just keeps normal writes from
        going unseen by ``query`` until someone calls ``repair``.
        """

        self._index.rebuild(self._store.iter_events())

    def query(
        self, *, actor: str | None = None, action: str | None = None, outcome: str | None = None
    ) -> list[AuditEvent]:
        return self._index.query(actor=actor, action=action, outcome=outcome)

    def repair(self) -> RebuildPlan:
        """Rebuild the query index from the store's immutable source events."""

        return self._index.rebuild(self._store.iter_events())

    def compatibility_repair(self) -> RebuildPlan:
        """Permanently collapse duplicate source rows, then rebuild the index.

        Row-level deduplication is the store's own concern: if ``self._store``
        implements ``compatibility_repair`` (see
        ``SQLiteEventStore.compatibility_repair``), that call runs first and
        commits its own removals before anything here reads the store back. A
        store that does not implement it is left untouched, and this still
        rebuilds the index from whatever the store currently holds -- so this
        method stays meaningful for any storage-independent ``EventStore``,
        not only one capable of compaction.
        """

        compatibility_repair = getattr(self._store, "compatibility_repair", None)
        if compatibility_repair is not None:
            compatibility_repair()
        return self._index.rebuild(self._store.iter_events())
