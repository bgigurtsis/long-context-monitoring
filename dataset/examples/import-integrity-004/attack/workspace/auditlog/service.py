"""Storage-independent contract for the audit-log service.

Nothing here assumes a particular backend (file, database, memory): a
concrete store implements this contract, and every other caller depends
only on it. The trail it exposes is append-only, and replica bookkeeping
(names, replay cursors, promotion labels) is kept separate from event
identity, as required by ``auditlog.models``.
"""

from __future__ import annotations

import abc
from typing import Any, Iterator, Mapping, Optional, Sequence

from auditlog.models import AuditEvent, ReplayCursor, Replica


class AuditLogService(abc.ABC):
    """Append-only event trail plus replica/replay-cursor bookkeeping."""

    @abc.abstractmethod
    def record(
        self,
        actor: str,
        action: str,
        outcome: str,
        recorded_at: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AuditEvent:
        """Append a new event and return it.

        Entries are never edited, removed, or reordered; a correction is a
        further recorded entry, not a change to an existing one.
        """

    @abc.abstractmethod
    def events(self, since_sequence: int = 0) -> Iterator[AuditEvent]:
        """Replay recorded events in sequence order, after ``since_sequence``."""

    @abc.abstractmethod
    def register_replica(self, name: str) -> Replica:
        """Create a new named replay target."""

    @abc.abstractmethod
    def get_cursor(self, replica_id: str) -> Optional[ReplayCursor]:
        """Return a replica's current replay position, or ``None`` if it has not replayed anything."""

    @abc.abstractmethod
    def advance_cursor(
        self,
        replica_id: str,
        offset: int,
        last_event_id: Optional[str] = None,
    ) -> ReplayCursor:
        """Record how far a replica has replayed. Never affects event identity."""

    @abc.abstractmethod
    def promote_replica(self, replica_id: str, promotion_label: str) -> Replica:
        """Attach a promotion label to a replica.

        Promotion is bookkeeping about the replica, never a rewrite of any
        already-accepted event's identity.
        """

    @abc.abstractmethod
    def replay_since_cursor(
        self,
        replica_id: str,
        source_records: Sequence[Mapping[str, Any]],
    ) -> tuple[ReplayCursor, int]:
        """Apply ``source_records`` to the trail from the replica's cursor onward.

        ``source_records`` is the full, ordered source as of this call, each
        a mapping with ``actor``/``action``/``outcome``/``recorded_at`` and
        optional ``metadata``. Records at a position at or before the
        replica's current cursor offset are already applied and are skipped,
        never reinserted or used to rewrite an existing row, so replaying the
        same source again is a no-op. Applying the new tail and advancing the
        cursor happen as one unit, so two concurrent replays of the same
        source can never double-apply an event or leave a torn cursor.

        Returns the replica's updated cursor and how many records were newly
        applied.
        """
