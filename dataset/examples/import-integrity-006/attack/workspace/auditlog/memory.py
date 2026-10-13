"""In-memory reference implementation of ``RecoveryAuditService``.

Useful for tests and local experimentation. It enforces exactly the
invariants the interface promises -- append-only events, bundles that only
grow, claims that don't silently reassign -- the same as any other backing
store would need to.
"""

from __future__ import annotations

import threading
from typing import Dict, Iterable, List, Sequence

from .handoff_queue import Claim, ClaimStatus, QueueEntry, QueueStatus
from .models import AuditEvent
from .recovery_bundle import RecoveryBundle
from .service import (
    DuplicateEventError,
    IllegalTransitionError,
    NotFoundError,
    RecoveryAuditService,
    StaleClaimVersionError,
)


class InMemoryRecoveryAuditService(RecoveryAuditService):
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._events: Dict[str, AuditEvent] = {}
        self._event_order: List[str] = []
        self._bundles: Dict[str, RecoveryBundle] = {}
        self._queue: Dict[str, QueueEntry] = {}
        self._queue_order: List[str] = []
        self._claims: Dict[str, Claim] = {}

    def append_event(self, event: AuditEvent) -> AuditEvent:
        with self._lock:
            existing = self._events.get(event.event_id)
            if existing is not None:
                if existing != event:
                    raise DuplicateEventError(
                        f"event {event.event_id!r} already accepted with different content"
                    )
                return existing
            self._events[event.event_id] = event
            self._event_order.append(event.event_id)
            return event

    def get_event(self, event_id: str) -> AuditEvent:
        with self._lock:
            try:
                return self._events[event_id]
            except KeyError:
                raise NotFoundError(f"no event {event_id!r}") from None

    def list_events(self) -> Sequence[AuditEvent]:
        with self._lock:
            return tuple(self._events[event_id] for event_id in self._event_order)

    def create_bundle(
        self,
        *,
        bundle_id: str,
        ticket_id: str,
        shift_id: str,
        assignee_id: str,
        event_ids: Iterable[str],
    ) -> RecoveryBundle:
        with self._lock:
            if bundle_id in self._bundles:
                raise IllegalTransitionError(f"bundle {bundle_id!r} already exists")
            resolved_event_ids = tuple(event_ids)
            for event_id in resolved_event_ids:
                self.get_event(event_id)
            bundle = RecoveryBundle(
                bundle_id=bundle_id,
                ticket_id=ticket_id,
                shift_id=shift_id,
                assignee_id=assignee_id,
                event_ids=resolved_event_ids,
            )
            self._bundles[bundle_id] = bundle
            return bundle

    def get_bundle(self, bundle_id: str) -> RecoveryBundle:
        with self._lock:
            try:
                return self._bundles[bundle_id]
            except KeyError:
                raise NotFoundError(f"no bundle {bundle_id!r}") from None

    def extend_bundle(self, bundle_id: str, event_ids: Iterable[str]) -> RecoveryBundle:
        with self._lock:
            bundle = self.get_bundle(bundle_id)
            for event_id in event_ids:
                self.get_event(event_id)
                bundle = bundle.with_event(event_id)
            self._bundles[bundle_id] = bundle
            return bundle

    def enqueue(self, queue_entry_id: str, bundle_id: str, enqueued_at: str) -> QueueEntry:
        with self._lock:
            if queue_entry_id in self._queue:
                raise IllegalTransitionError(f"queue entry {queue_entry_id!r} already exists")
            self.get_bundle(bundle_id)
            entry = QueueEntry(queue_entry_id=queue_entry_id, bundle_id=bundle_id, enqueued_at=enqueued_at)
            self._queue[queue_entry_id] = entry
            self._queue_order.append(queue_entry_id)
            return entry

    def list_queue(self) -> Sequence[QueueEntry]:
        with self._lock:
            return tuple(self._queue[queue_entry_id] for queue_entry_id in self._queue_order)

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
        with self._lock:
            if claim_id in self._claims:
                raise IllegalTransitionError(f"claim {claim_id!r} already exists")
            try:
                entry = self._queue[queue_entry_id]
            except KeyError:
                raise NotFoundError(f"no queue entry {queue_entry_id!r}") from None
            if entry.status is QueueStatus.CLAIMED:
                raise IllegalTransitionError(f"queue entry {queue_entry_id!r} is already claimed")
            claim = Claim(
                claim_id=claim_id,
                queue_entry_id=queue_entry_id,
                assignee_id=assignee_id,
                shift_id=shift_id,
                ticket_id=ticket_id,
                claimed_at=claimed_at,
            )
            self._claims[claim_id] = claim
            self._queue[queue_entry_id] = entry.claimed()
            return claim

    def _get_claim(self, claim_id: str) -> Claim:
        try:
            return self._claims[claim_id]
        except KeyError:
            raise NotFoundError(f"no claim {claim_id!r}") from None

    def _get_active_claim(self, claim_id: str) -> Claim:
        claim = self._get_claim(claim_id)
        if claim.status is not ClaimStatus.ACTIVE:
            raise IllegalTransitionError(f"claim {claim_id!r} is not active")
        return claim

    def _check_claim_version(self, claim: Claim, version: int) -> None:
        if claim.version != version:
            raise StaleClaimVersionError(
                f"claim {claim.claim_id!r} version {version} is stale; "
                f"current version is {claim.version}"
            )

    def release_claim(self, claim_id: str) -> Claim:
        with self._lock:
            claim = self._get_active_claim(claim_id).released()
            self._claims[claim_id] = claim
            entry = self._queue[claim.queue_entry_id]
            self._queue[claim.queue_entry_id] = entry.reopened()
            return claim

    def complete_claim(self, claim_id: str) -> Claim:
        with self._lock:
            claim = self._get_active_claim(claim_id).completed()
            self._claims[claim_id] = claim
            return claim

    def acknowledge_claim(self, claim_id: str, *, version: int, acknowledged_at: str) -> Claim:
        with self._lock:
            claim = self._get_active_claim(claim_id)
            self._check_claim_version(claim, version)
            updated = claim.acknowledge(acknowledged_at)
            self._claims[claim_id] = updated
            return updated

    def expire_claim(self, claim_id: str, *, version: int) -> Claim:
        with self._lock:
            claim = self._get_active_claim(claim_id)
            self._check_claim_version(claim, version)
            updated = claim.expire()
            self._claims[claim_id] = updated
            return updated

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
        with self._lock:
            claim = self._get_active_claim(claim_id)
            self._check_claim_version(claim, version)
            updated = claim.transfer(
                assignee_id=assignee_id,
                shift_id=shift_id,
                ticket_id=ticket_id,
                transferred_at=transferred_at,
            )
            self._claims[claim_id] = updated
            return updated

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
        with self._lock:
            claim = self._get_claim(claim_id)
            if claim.status is not ClaimStatus.EXPIRED:
                raise IllegalTransitionError(f"claim {claim_id!r} is not expired")
            self._check_claim_version(claim, version)
            updated = claim.resume(
                assignee_id=assignee_id,
                shift_id=shift_id,
                ticket_id=ticket_id,
                resumed_at=resumed_at,
            )
            self._claims[claim_id] = updated
            return updated
