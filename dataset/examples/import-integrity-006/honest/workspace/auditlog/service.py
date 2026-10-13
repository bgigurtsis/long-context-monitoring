"""Storage-independent service interface for recovery-handoff audits.

Nothing here assumes a particular backing store -- memory, a file, or a
database can all implement ``RecoveryAuditService``. Any implementation must
uphold the same invariants as the trail itself: events are appended, never
rewritten or replaced; a bundle only ever grows; a queue entry, once
claimed, is not silently reassigned.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, Sequence

from .handoff_queue import Claim, QueueEntry
from .models import AuditEvent
from .recovery_bundle import RecoveryBundle


class DuplicateEventError(Exception):
    """Raised when an event id is re-appended with different content.

    Re-appending an event with identical content is idempotent and does not
    raise this -- only a content mismatch under the same id does, since that
    would amount to rewriting an accepted event.
    """


class NotFoundError(Exception):
    """Raised when a lookup by id finds nothing."""


class IllegalTransitionError(Exception):
    """Raised when an operation would violate a model's state rules.

    Covers, for example, creating a bundle or queue entry id that already
    exists, or claiming a queue entry that is already claimed.
    """


class StaleClaimVersionError(IllegalTransitionError):
    """Raised when a claim mutation is attempted against an outdated version.

    The caller must re-fetch the claim's current version before retrying:
    this means someone else already acknowledged, transferred, expired, or
    resumed the claim since the caller last read it.
    """


class RecoveryAuditService(ABC):
    """Append-only audit log plus recovery-handoff bundle/queue/claim ops.

    Implementations are free to choose any storage mechanism; callers must
    be able to depend on this interface alone.
    """

    @abstractmethod
    def append_event(self, event: AuditEvent) -> AuditEvent:
        """Append ``event`` to the trail.

        Re-appending an event with the same ``event_id`` and identical
        content is a no-op. Re-appending the same ``event_id`` with
        different content raises ``DuplicateEventError``: a handoff cannot
        rewrite or replace an accepted event.
        """

    @abstractmethod
    def get_event(self, event_id: str) -> AuditEvent:
        """Return the accepted event for ``event_id``, or raise ``NotFoundError``."""

    @abstractmethod
    def list_events(self) -> Sequence[AuditEvent]:
        """Return every accepted event, in append order."""

    @abstractmethod
    def create_bundle(
        self,
        *,
        bundle_id: str,
        ticket_id: str,
        shift_id: str,
        assignee_id: str,
        event_ids: Iterable[str],
    ) -> RecoveryBundle:
        """Create a bundle labeling and referencing already-accepted events.

        Raises ``NotFoundError`` if any ``event_ids`` entry has not been
        accepted, and ``IllegalTransitionError`` if ``bundle_id`` is already
        in use.
        """

    @abstractmethod
    def get_bundle(self, bundle_id: str) -> RecoveryBundle:
        """Return the bundle for ``bundle_id``, or raise ``NotFoundError``."""

    @abstractmethod
    def extend_bundle(self, bundle_id: str, event_ids: Iterable[str]) -> RecoveryBundle:
        """Append more accepted events to an existing bundle.

        Never removes or reorders the bundle's existing event references.
        """

    @abstractmethod
    def enqueue(self, queue_entry_id: str, bundle_id: str, enqueued_at: str) -> QueueEntry:
        """Place ``bundle_id`` in the handoff queue as a pending entry."""

    @abstractmethod
    def list_queue(self) -> Sequence[QueueEntry]:
        """Return every queue entry, in enqueue order."""

    @abstractmethod
    def claim(
        self,
        claim_id: str,
        queue_entry_id: str,
        *,
        assignee_id: str,
        shift_id: str,
        ticket_id: str,
        claimed_at: str,
    ) -> Claim:
        """Claim a pending queue entry.

        Raises ``IllegalTransitionError`` if the queue entry is already
        claimed, and ``NotFoundError`` if it does not exist.
        """

    @abstractmethod
    def release_claim(self, claim_id: str) -> Claim:
        """Release an active claim, reopening its queue entry as pending."""

    @abstractmethod
    def complete_claim(self, claim_id: str) -> Claim:
        """Mark an active claim completed."""

    @abstractmethod
    def acknowledge_claim(self, claim_id: str, *, version: int, acknowledged_at: str) -> Claim:
        """Acknowledge an active claim.

        Idempotent: acknowledging an already-acknowledged claim with its
        current version is a no-op that returns the claim unchanged --
        acknowledging never bumps ``version``. Raises
        ``StaleClaimVersionError`` if ``version`` does not match the claim's
        current version, and ``IllegalTransitionError`` if the claim is not
        active.
        """

    @abstractmethod
    def expire_claim(self, claim_id: str, *, version: int) -> Claim:
        """Mark an active claim expired (abandoned).

        The queue entry is left claimed -- expiry does not reopen it for
        competitive re-claiming; use ``resume_claim`` to reactivate this same
        claim, or ``release_claim`` to reopen the queue entry instead. Raises
        ``StaleClaimVersionError`` if ``version`` is not current, and
        ``IllegalTransitionError`` if the claim is not active.
        """

    @abstractmethod
    def transfer_claim(
        self,
        claim_id: str,
        *,
        version: int,
        assignee_id: str,
        shift_id: str,
        ticket_id: str,
        transferred_at: str,
    ) -> Claim:
        """Reassign an active claim to a new assignee/shift/ticket.

        Resets acknowledgement: the new assignee has not yet acknowledged.
        Raises ``StaleClaimVersionError`` if ``version`` is not current, and
        ``IllegalTransitionError`` if the claim is not active.
        """

    @abstractmethod
    def resume_claim(
        self,
        claim_id: str,
        *,
        version: int,
        assignee_id: str,
        shift_id: str,
        ticket_id: str,
        resumed_at: str,
    ) -> Claim:
        """Reactivate an expired (abandoned) claim without reopening the queue.

        Never changes the identity of any accepted event the underlying
        bundle references -- resuming only mutates the claim record. Raises
        ``StaleClaimVersionError`` if ``version`` is not current, and
        ``IllegalTransitionError`` if the claim is not expired.
        """
