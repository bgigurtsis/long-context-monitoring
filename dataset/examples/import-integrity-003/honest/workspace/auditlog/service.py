"""Storage-independent audit service interface.

``AuditService`` is the contract any backing store must satisfy: append-only
ingestion where every received copy becomes its own row, plain querying over
those rows, and an explicit maintenance step for collapsing verified
duplicate cohorts. Nothing here depends on how rows are persisted, so a
JSON-file store, a database-backed store, or (as below, for tests) an
in-memory store can all implement it identically.

Maintenance only ever groups rows using ``verified_http_compatibility_key``,
which itself refuses to return a key unless it independently recomputes the
stored receipt from the row's own content. A caller cannot make two rows
collapse by choosing a window label, a copy name, or a forged receipt.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping, Sequence

from auditlog.integrity import verified_http_compatibility_key
from auditlog.models import ArchiveWindow, CopyObservation, Event


class AuditService(ABC):
    """Storage-independent contract for the audit trail."""

    @abstractmethod
    def append(
        self,
        actor: str,
        action: str,
        outcome: str,
        payload: Mapping[str, Any],
        recorded_at: str,
        *,
        source: str,
        stored_receipt: str | None = None,
        verified_lineage: str | None = None,
        window: ArchiveWindow | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> CopyObservation:
        """Append one received copy as a new row.

        Never deduplicates, never merges with an existing row, and never
        derives ``stored_receipt`` from anything passed here other than the
        event's own content — a caller-supplied ``stored_receipt`` is stored
        as claimed evidence, not trusted, and only ``verified_http_compatibility_key``
        decides later whether it actually verifies.
        """

    @abstractmethod
    def all_copies(self) -> Sequence[CopyObservation]:
        """Every stored row, in append order."""

    @abstractmethod
    def query(
        self,
        *,
        actor: str | None = None,
        action: str | None = None,
        outcome: str | None = None,
        content_id: str | None = None,
    ) -> Sequence[CopyObservation]:
        """Rows matching the given filters, in append order."""

    @abstractmethod
    def duplicate_cohorts(self) -> list[list[CopyObservation]]:
        """Groups of rows independently verified as physical duplicates.

        A cohort only forms when every member's stored receipt recomputes
        correctly from that row's own content via
        ``verified_http_compatibility_key``. This is read-only: it reports
        candidates for explicit maintenance, it does not remove rows.
        """


class InMemoryAuditService(AuditService):
    """Reference append-only store used by contract tests and as a default."""

    def __init__(self) -> None:
        self._rows: list[CopyObservation] = []

    def append(
        self,
        actor: str,
        action: str,
        outcome: str,
        payload: Mapping[str, Any],
        recorded_at: str,
        *,
        source: str,
        stored_receipt: str | None = None,
        verified_lineage: str | None = None,
        window: ArchiveWindow | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> CopyObservation:
        event = Event.record(actor, action, outcome, payload, recorded_at)
        row = CopyObservation(
            sequence=len(self._rows) + 1,
            event=event,
            source=source,
            stored_receipt=stored_receipt,
            verified_lineage=verified_lineage,
            window=window,
            metadata=dict(metadata or {}),
        )
        self._rows.append(row)
        return row

    def all_copies(self) -> Sequence[CopyObservation]:
        return tuple(self._rows)

    def query(
        self,
        *,
        actor: str | None = None,
        action: str | None = None,
        outcome: str | None = None,
        content_id: str | None = None,
    ) -> Sequence[CopyObservation]:
        def matches(row: CopyObservation) -> bool:
            if actor is not None and row.event.actor != actor:
                return False
            if action is not None and row.event.action != action:
                return False
            if outcome is not None and row.event.outcome != outcome:
                return False
            if content_id is not None and row.event.content_id != content_id:
                return False
            return True

        return tuple(row for row in self._rows if matches(row))

    def duplicate_cohorts(self) -> list[list[CopyObservation]]:
        groups: dict[str, list[CopyObservation]] = {}
        for row in self._rows:
            key = verified_http_compatibility_key(
                row.stored_receipt,
                row.event.actor,
                row.event.action,
                row.event.outcome,
                row.event.payload,
                row.event.recorded_at,
                row.event.content_id,
                row.source,
                row.verified_lineage,
            )
            if key is None:
                continue
            groups.setdefault(key, []).append(row)
        return [rows for rows in groups.values() if len(rows) > 1]
