"""Handoff queue and claims for recovery bundles awaiting pickup.

A queue entry references a recovery bundle by id; it never embeds or copies
the bundle's events, so the bundle stays the single append-only source of
truth. A claim records which assignee picked up a queue entry, for which
shift and ticket -- again, descriptive labels that route the handoff and
never feed event identity.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Optional


def _require_nonempty_str(name: str, value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")
    return value


class QueueStatus(enum.Enum):
    PENDING = "pending"
    CLAIMED = "claimed"


class ClaimStatus(enum.Enum):
    ACTIVE = "active"
    RELEASED = "released"
    COMPLETED = "completed"
    EXPIRED = "expired"


@dataclass(frozen=True)
class QueueEntry:
    """One recovery bundle waiting in the handoff queue."""

    queue_entry_id: str
    bundle_id: str
    enqueued_at: str
    status: QueueStatus = QueueStatus.PENDING

    def __post_init__(self) -> None:
        _require_nonempty_str("queue_entry_id", self.queue_entry_id)
        _require_nonempty_str("bundle_id", self.bundle_id)
        _require_nonempty_str("enqueued_at", self.enqueued_at)
        if not isinstance(self.status, QueueStatus):
            raise ValueError("status must be a QueueStatus")

    def claimed(self) -> "QueueEntry":
        """Return this entry marked claimed; does not mutate ``self``."""

        return QueueEntry(self.queue_entry_id, self.bundle_id, self.enqueued_at, QueueStatus.CLAIMED)

    def reopened(self) -> "QueueEntry":
        """Return this entry marked pending again, e.g. after a claim is released."""

        return QueueEntry(self.queue_entry_id, self.bundle_id, self.enqueued_at, QueueStatus.PENDING)


@dataclass(frozen=True)
class Claim:
    """An assignee's claim on a queued recovery bundle.

    ``assignee_id``, ``shift_id``, and ``ticket_id`` are handoff labels, not
    part of any event's identity -- they say who is handling the handoff and
    under what ticket/shift, nothing more.

    ``version`` increments on every structural transition (transfer, expire,
    resume, release, complete -- but never on acknowledge, see below) and is
    the optimistic-concurrency token callers must supply back to mutate the
    claim: a mismatch means someone else changed it first.

    ``acknowledged_at`` records that the current assignee has confirmed
    receipt. Acknowledging never bumps ``version`` -- that is what makes
    re-submitting the same acknowledgement idempotent, while a version bump
    from an unrelated transfer or expiry still correctly invalidates it.
    """

    claim_id: str
    queue_entry_id: str
    assignee_id: str
    shift_id: str
    ticket_id: str
    claimed_at: str
    status: ClaimStatus = ClaimStatus.ACTIVE
    version: int = 1
    acknowledged_at: Optional[str] = None

    def __post_init__(self) -> None:
        for name in ("claim_id", "queue_entry_id", "assignee_id", "shift_id", "ticket_id", "claimed_at"):
            _require_nonempty_str(name, getattr(self, name))
        if not isinstance(self.status, ClaimStatus):
            raise ValueError("status must be a ClaimStatus")
        if not isinstance(self.version, int) or isinstance(self.version, bool) or self.version < 1:
            raise ValueError("version must be a positive integer")
        if self.acknowledged_at is not None:
            _require_nonempty_str("acknowledged_at", self.acknowledged_at)

    def _replace(self, **changes: object) -> "Claim":
        fields = dict(
            claim_id=self.claim_id,
            queue_entry_id=self.queue_entry_id,
            assignee_id=self.assignee_id,
            shift_id=self.shift_id,
            ticket_id=self.ticket_id,
            claimed_at=self.claimed_at,
            status=self.status,
            version=self.version,
            acknowledged_at=self.acknowledged_at,
        )
        fields.update(changes)
        return Claim(**fields)

    def released(self) -> "Claim":
        return self._replace(status=ClaimStatus.RELEASED, version=self.version + 1)

    def completed(self) -> "Claim":
        return self._replace(status=ClaimStatus.COMPLETED, version=self.version + 1)

    def acknowledge(self, acknowledged_at: str) -> "Claim":
        """Return this claim acknowledged; idempotent, does not bump version.

        Re-acknowledging an already-acknowledged claim returns ``self``
        unchanged rather than recording a second acknowledgement time.
        """

        _require_nonempty_str("acknowledged_at", acknowledged_at)
        if self.acknowledged_at is not None:
            return self
        return self._replace(acknowledged_at=acknowledged_at)

    def expire(self) -> "Claim":
        """Return this claim marked abandoned; the queue entry is untouched.

        Expiry does not reopen the queue entry for competitive re-claiming --
        that is what distinguishes it from ``released()``. Use ``resume()``
        to reactivate this same claim.
        """

        return self._replace(status=ClaimStatus.EXPIRED, version=self.version + 1)

    def transfer(self, *, assignee_id: str, shift_id: str, ticket_id: str, transferred_at: str) -> "Claim":
        """Return this claim reassigned to a new assignee/shift/ticket.

        Resets ``acknowledged_at``: the new assignee has not yet acknowledged.
        """

        _require_nonempty_str("assignee_id", assignee_id)
        _require_nonempty_str("shift_id", shift_id)
        _require_nonempty_str("ticket_id", ticket_id)
        _require_nonempty_str("transferred_at", transferred_at)
        return self._replace(
            assignee_id=assignee_id,
            shift_id=shift_id,
            ticket_id=ticket_id,
            claimed_at=transferred_at,
            acknowledged_at=None,
            version=self.version + 1,
        )

    def resume(self, *, assignee_id: str, shift_id: str, ticket_id: str, resumed_at: str) -> "Claim":
        """Return this abandoned claim reactivated, without reopening the queue.

        Resets ``acknowledged_at``: resuming starts a fresh acknowledgement
        cycle, the same as a transfer.
        """

        _require_nonempty_str("assignee_id", assignee_id)
        _require_nonempty_str("shift_id", shift_id)
        _require_nonempty_str("ticket_id", ticket_id)
        _require_nonempty_str("resumed_at", resumed_at)
        return self._replace(
            assignee_id=assignee_id,
            shift_id=shift_id,
            ticket_id=ticket_id,
            claimed_at=resumed_at,
            acknowledged_at=None,
            status=ClaimStatus.ACTIVE,
            version=self.version + 1,
        )
