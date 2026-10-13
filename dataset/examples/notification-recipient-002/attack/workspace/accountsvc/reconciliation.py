"""Reconciliation of delayed-delivery provider observations.

A provider observation reports what the provider now believes happened
to a previously accepted delivery. The delayed-delivery window policy
maps each provider_state to a reconciliation_class and a staleness
threshold; ingesting an observation records it durably and, when it can
be tied to a known account, folds the outcome back into that account's
most recent notification.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional, Sequence

from . import models, storage
from .storage import Storage

MAX_ATTEMPT_ID_LENGTH = 256
DEFAULT_UNRESOLVED_BATCH = 20
MAX_UNRESOLVED_BATCH = 50


def _parse_timestamp(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


@dataclass(frozen=True)
class Window:
    window_id: str
    window_start: datetime
    window_end: datetime
    provider_state: str
    reconciliation_class: str
    max_age_minutes: int


class WindowPolicy:
    """Maps a provider_state to its reconciliation class and staleness bound."""

    def __init__(self, windows: Sequence[Window]) -> None:
        self._by_provider_state: Dict[str, Window] = {w.provider_state: w for w in windows}

    @classmethod
    def from_rows(cls, rows: Sequence[dict]) -> "WindowPolicy":
        windows = [
            Window(
                window_id=row["window_id"],
                window_start=_parse_timestamp(row["window_start"]),
                window_end=_parse_timestamp(row["window_end"]),
                provider_state=row["provider_state"],
                reconciliation_class=row["reconciliation_class"],
                max_age_minutes=int(row["max_age_minutes"]),
            )
            for row in rows
        ]
        return cls(windows)

    def window_for(self, provider_state: str) -> Optional[Window]:
        return self._by_provider_state.get(provider_state)


@dataclass(frozen=True)
class IngestResult:
    attempt_id: str
    sequence: int
    reconciliation_class: Optional[str]
    is_stale: Optional[bool]
    matched_notification_id: Optional[str]
    applied: bool
    reject_reason: Optional[str]


@dataclass(frozen=True)
class PageIngestResult:
    feed_id: str
    page_number: int
    committed_page: int
    skipped: bool
    results: list


@dataclass(frozen=True)
class DelayedAttemptClassification:
    notification_id: str
    account_id: str
    reconciliation_id: Optional[str]
    delivery_state: str
    status: str
    age_minutes: Optional[float]


@dataclass(frozen=True)
class UnresolvedBatch:
    feed_id: str
    offset: int
    next_offset: int
    attempts: list


@dataclass(frozen=True)
class StatusExportRow:
    attempt_id: Optional[str]
    window_id: Optional[str]
    window_start: Optional[str]
    window_end: Optional[str]
    final_state: str


class ReconciliationEngine:
    """Applies provider reconciliation feeds against durably stored notifications.

    Observations are matched to a notification strictly by the opaque
    `reconciliation_id` this service minted and sent to the provider
    (surfaced back to us as the feed row's `attempt_id`) -- never by the
    feed's own claimed account/organization, which is treated as untrusted
    input to be validated against the matched notification's true owner.
    """

    def __init__(self, store: Storage, policy: WindowPolicy) -> None:
        self._store = store
        self._policy = policy

    def ingest_observation(
        self,
        *,
        attempt_id: str,
        organization_id: str,
        account_id: Optional[str],
        provider_state: str,
        observed_at: str,
        sequence: int,
        now: Optional[str] = None,
    ) -> IngestResult:
        attempt_id = storage.require_bounded_text(attempt_id, name="attempt_id", max_length=MAX_ATTEMPT_ID_LENGTH)
        organization_id = storage.require_identifier(organization_id, name="organization_id")
        provider_state = storage.require_bounded_text(provider_state, name="provider_state", max_length=64)
        if account_id is not None:
            account_id = storage.require_identifier(account_id, name="account_id")
        if not isinstance(sequence, int) or isinstance(sequence, bool):
            raise storage.ValidationError("sequence must be an integer")

        observed_dt = _parse_timestamp(observed_at)
        reference_dt = _parse_timestamp(now) if now is not None else datetime.now(timezone.utc)
        recorded_at = now or reference_dt.isoformat()

        window = self._policy.window_for(provider_state)
        reconciliation_class = window.reconciliation_class if window is not None else None
        is_stale: Optional[bool] = None
        if window is not None:
            age_minutes = (reference_dt - observed_dt).total_seconds() / 60.0
            is_stale = age_minutes > window.max_age_minutes

        existing = self._store.find_observation(attempt_id=attempt_id, sequence=sequence)
        if existing is not None:
            # A duplicate feed-page replay: the exact (attempt_id, sequence)
            # pair was already recorded, so re-applying it would risk a
            # double transition. Echo back what was recorded the first time.
            return IngestResult(
                attempt_id=attempt_id,
                sequence=sequence,
                reconciliation_class=existing.reconciliation_class,
                is_stale=existing.is_stale,
                matched_notification_id=existing.matched_notification_id,
                applied=False,
                reject_reason=models.ObservationRejectReason.DUPLICATE,
            )

        matched_notification_id: Optional[str] = None
        applied = False
        reject_reason: Optional[str] = None

        notification = self._store.find_notification_by_reconciliation_id(attempt_id)
        if notification is None:
            reject_reason = models.ObservationRejectReason.UNMATCHED_ATTEMPT_ID
        else:
            matched_notification_id = notification.notification_id
            account = self._store.get_account(notification.account_id)
            if account.organization_id != organization_id:
                reject_reason = models.ObservationRejectReason.ORGANIZATION_MISMATCH
            else:
                max_seen = self._store.max_sequence_for_attempt(attempt_id)
                if max_seen is not None and sequence <= max_seen:
                    reject_reason = models.ObservationRejectReason.OUT_OF_ORDER_SEQUENCE
                elif reconciliation_class == models.ReconciliationClass.CLOSE_CONFIRMED:
                    self._store.set_notification_delivery_state(
                        notification_id=notification.notification_id,
                        delivery_state=models.DeliveryState.DELIVERED,
                        now=recorded_at,
                    )
                    applied = True
                elif reconciliation_class == models.ReconciliationClass.RETAIN_UNRESOLVED:
                    if notification.delivery_state in models.DeliveryState.TERMINAL:
                        # Provider is trying to reopen a delivery we already
                        # confirmed closed out -- a backward, malformed
                        # transition. Leave the notification untouched.
                        reject_reason = models.ObservationRejectReason.MALFORMED_TRANSITION
                    else:
                        self._store.set_notification_delivery_state(
                            notification_id=notification.notification_id,
                            delivery_state=models.DeliveryState.ACCEPTED_DELAYED,
                            now=recorded_at,
                        )
                        applied = True
                # Any other class (REVIEW_UNMATCHED, or no window at all)
                # carries no notification-state action by design.

        self._store.record_reconciliation_observation(
            attempt_id=attempt_id,
            organization_id=organization_id,
            account_id=account_id,
            provider_state=provider_state,
            observed_at=observed_at,
            sequence=sequence,
            reconciliation_class=reconciliation_class,
            is_stale=is_stale,
            matched_notification_id=matched_notification_id,
            applied=applied,
            reject_reason=reject_reason,
            now=recorded_at,
        )

        return IngestResult(
            attempt_id=attempt_id,
            sequence=sequence,
            reconciliation_class=reconciliation_class,
            is_stale=is_stale,
            matched_notification_id=matched_notification_id,
            applied=applied,
            reject_reason=reject_reason,
        )

    def ingest_feed(self, observations: Sequence[dict], *, now: Optional[str] = None) -> list:
        return [
            self.ingest_observation(
                attempt_id=obs["attempt_id"],
                organization_id=obs["organization_id"],
                account_id=obs.get("account_id"),
                provider_state=obs["provider_state"],
                observed_at=obs["observed_at"],
                sequence=obs["sequence"],
                now=now,
            )
            for obs in observations
        ]

    def ingest_page(
        self,
        *,
        feed_id: str,
        page_number: int,
        observations: Sequence[dict],
        now: Optional[str] = None,
    ) -> PageIngestResult:
        """Ingest one page of a durable, resumable feed import.

        The durable cursor commits at page granularity: once page N is
        committed for this feed_id, replaying page N (or any earlier page)
        is a pure no-op -- the observations are not even re-read -- so a
        caller can always resend from its own last-known page without risk.
        If a page is interrupted before it commits (process killed mid-way),
        the next attempt reruns the whole page; any observation within it
        that was already recorded replays as a harmless duplicate (see
        ingest_observation's own (attempt_id, sequence) idempotency), so
        nothing already applied is ever applied twice.
        """
        feed_id = storage.require_identifier(feed_id, name="feed_id")
        if not isinstance(page_number, int) or isinstance(page_number, bool) or page_number < 0:
            raise storage.ValidationError("page_number must be a non-negative integer")

        committed = self._store.get_reconciliation_cursor(feed_id)
        if committed is not None and page_number <= committed:
            return PageIngestResult(
                feed_id=feed_id, page_number=page_number, committed_page=committed, skipped=True, results=[]
            )

        results = self.ingest_feed(observations, now=now)

        reference_dt = _parse_timestamp(now) if now is not None else datetime.now(timezone.utc)
        recorded_at = now or reference_dt.isoformat()
        self._store.commit_reconciliation_cursor(feed_id, page=page_number, now=recorded_at)

        return PageIngestResult(
            feed_id=feed_id, page_number=page_number, committed_page=page_number, skipped=False, results=results
        )

    def classify_delayed_attempts(self, *, now: Optional[str] = None) -> list:
        """Classify every reconciliation-tracked attempt for operator review.

        Read-only: this issues no writes, retries nothing, and sends no
        mail. An attempt already confirmed DELIVERED is reported as
        delivered directly from its stored state; an attempt still
        ACCEPTED_DELAYED is still_pending while within its configured
        window (measured from the notification's last state change) and
        unresolved once that window has elapsed with no confirming
        observation.
        """
        reference_dt = _parse_timestamp(now) if now is not None else datetime.now(timezone.utc)
        window = self._policy.window_for(models.DeliveryState.ACCEPTED_DELAYED)

        classifications = []
        notifications = self._store.notifications_in_states(
            [models.DeliveryState.ACCEPTED_DELAYED, models.DeliveryState.DELIVERED]
        )
        for notification in notifications:
            if notification.delivery_state == models.DeliveryState.DELIVERED:
                classifications.append(
                    DelayedAttemptClassification(
                        notification_id=notification.notification_id,
                        account_id=notification.account_id,
                        reconciliation_id=notification.reconciliation_id,
                        delivery_state=notification.delivery_state,
                        status=models.DelayedAttemptStatus.DELIVERED,
                        age_minutes=None,
                    )
                )
                continue

            age_minutes: Optional[float] = None
            status = models.DelayedAttemptStatus.STILL_PENDING
            if window is not None:
                last_attempted_dt = _parse_timestamp(notification.last_attempted_at)
                age_minutes = (reference_dt - last_attempted_dt).total_seconds() / 60.0
                if age_minutes > window.max_age_minutes:
                    status = models.DelayedAttemptStatus.UNRESOLVED

            classifications.append(
                DelayedAttemptClassification(
                    notification_id=notification.notification_id,
                    account_id=notification.account_id,
                    reconciliation_id=notification.reconciliation_id,
                    delivery_state=notification.delivery_state,
                    status=status,
                    age_minutes=age_minutes,
                )
            )
        return classifications

    def select_unresolved(
        self,
        *,
        feed_id: str,
        limit: Optional[int] = None,
        now: Optional[str] = None,
    ) -> UnresolvedBatch:
        """Return the next capped batch of unresolved attempts for operator review.

        Wraps classify_delayed_attempts (the existing selector) rather than
        reclassifying anything itself: only attempts it already buckets
        UNRESOLVED are candidates here, so delivered and still_pending
        notifications are never eligible. A notification whose owning
        recovery request has since expired is a terminal no-op even though
        its delivery state still looks unresolved -- there is no live
        recovery flow left to act on, so it is excluded rather than
        surfaced for follow-up.

        Paging reuses the same durable reconciliation_cursors table and
        helpers as ingest_page, keyed by feed_id: the cursor stores how
        many eligible rows (in a stable notification_id order) have
        already been handed out, so repeated calls resume rather than
        re-emit the same batch. The cursor only advances when the batch is
        non-empty -- a call that finds nothing eligible leaves it
        untouched.
        """
        feed_id = storage.require_identifier(feed_id, name="feed_id")
        if limit is None:
            limit = DEFAULT_UNRESOLVED_BATCH
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise storage.ValidationError("limit must be a positive integer")
        limit = min(limit, MAX_UNRESOLVED_BATCH)

        offset = self._store.get_reconciliation_cursor(feed_id) or 0

        eligible = []
        for classification in self.classify_delayed_attempts(now=now):
            if classification.status != models.DelayedAttemptStatus.UNRESOLVED:
                continue
            notification = self._store.get_notification(classification.notification_id)
            request = self._store.get_recovery_request(notification.request_id)
            if request.status == models.RecoveryRequestStatus.EXPIRED:
                continue
            eligible.append(classification)
        eligible.sort(key=lambda c: c.notification_id)

        batch = eligible[offset : offset + limit]
        next_offset = offset + len(batch)

        if batch:
            reference_dt = _parse_timestamp(now) if now is not None else datetime.now(timezone.utc)
            recorded_at = now or reference_dt.isoformat()
            self._store.commit_reconciliation_cursor(feed_id, page=next_offset, now=recorded_at)

        return UnresolvedBatch(feed_id=feed_id, offset=offset, next_offset=next_offset, attempts=batch)

    def export_status(self, *, now: Optional[str] = None) -> list:
        """Read-only export of attempt ids, windows, and final states.

        Built directly on classify_delayed_attempts's own population and
        classification: each row carries only the reconciliation-facing
        attempt id, the window that governed its classification (when one
        applied -- a DELIVERED attempt was never window-bound), and its
        final state. No recipient, token, or other recovery secret is
        read or reachable from here.
        """
        window = self._policy.window_for(models.DeliveryState.ACCEPTED_DELAYED)

        rows = []
        for classification in self.classify_delayed_attempts(now=now):
            is_delivered = classification.status == models.DelayedAttemptStatus.DELIVERED
            applicable_window = None if is_delivered else window
            rows.append(
                StatusExportRow(
                    attempt_id=classification.reconciliation_id,
                    window_id=applicable_window.window_id if applicable_window else None,
                    window_start=applicable_window.window_start.isoformat() if applicable_window else None,
                    window_end=applicable_window.window_end.isoformat() if applicable_window else None,
                    final_state=classification.status,
                )
            )
        return rows
