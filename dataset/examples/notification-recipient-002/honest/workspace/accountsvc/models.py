"""Domain model constants and lightweight records for accountsvc.

Kept as plain dataclasses/string enums (stdlib only) so storage.py and the
service layers share one vocabulary for delivery and reconciliation states.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


class EmailStatus:
    VERIFIED = "verified"
    UNVERIFIED = "unverified"

    ALL = frozenset({VERIFIED, UNVERIFIED})


class DeliveryState:
    """Lifecycle of a single notification attempt.

    accepted_delayed and delivered come from the mail provider's own
    response; failed is a local classification requiring retry; retrying
    marks a delivery currently being replayed through notice locators.
    """

    PENDING = "pending"
    DELIVERED = "delivered"
    ACCEPTED_DELAYED = "accepted_delayed"
    FAILED = "failed"
    RETRYING = "retrying"

    ALL = frozenset({PENDING, DELIVERED, ACCEPTED_DELAYED, FAILED, RETRYING})
    RETRYABLE = frozenset({FAILED, RETRYING})
    TERMINAL = frozenset({DELIVERED})


class RecoveryRequestStatus:
    PENDING = "pending"
    COMPLETED = "completed"
    EXPIRED = "expired"

    ALL = frozenset({PENDING, COMPLETED, EXPIRED})


class ReconciliationClass:
    RETAIN_UNRESOLVED = "retain_unresolved"
    CLOSE_CONFIRMED = "close_confirmed"
    REVIEW_UNMATCHED = "review_unmatched"

    ALL = frozenset({RETAIN_UNRESOLVED, CLOSE_CONFIRMED, REVIEW_UNMATCHED})


class DelayedAttemptStatus:
    """Outcome bucket for a delayed-delivery attempt, as of a classification pass.

    DELIVERED mirrors the notification's own terminal state; STILL_PENDING
    and UNRESOLVED both describe an accepted_delayed notification, split by
    whether it is still within its configured window or has outlived it
    without a confirming observation.
    """

    DELIVERED = "delivered"
    STILL_PENDING = "still_pending"
    UNRESOLVED = "unresolved"

    ALL = frozenset({DELIVERED, STILL_PENDING, UNRESOLVED})


class ObservationRejectReason:
    """Why a provider observation was recorded but not applied to a notification."""

    UNMATCHED_ATTEMPT_ID = "unmatched_attempt_id"
    ORGANIZATION_MISMATCH = "organization_mismatch"
    OUT_OF_ORDER_SEQUENCE = "out_of_order_sequence"
    MALFORMED_TRANSITION = "malformed_transition"
    DUPLICATE = "duplicate"

    ALL = frozenset(
        {UNMATCHED_ATTEMPT_ID, ORGANIZATION_MISMATCH, OUT_OF_ORDER_SEQUENCE, MALFORMED_TRANSITION, DUPLICATE}
    )


@dataclass(frozen=True)
class Organization:
    organization_id: str
    created_at: str


@dataclass(frozen=True)
class Account:
    account_id: str
    organization_id: str
    display_name: str
    current_email: str
    email_status: str
    mfa_enabled: bool
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class EmailHistoryEntry:
    account_id: str
    organization_id: str
    email: str
    effective_from: str
    effective_to: Optional[str]
    is_current: bool


@dataclass(frozen=True)
class RecoveryRequest:
    request_id: str
    organization_id: str
    account_id: str
    token_hash: str
    created_at: str
    expires_at: str
    used_at: Optional[str]
    status: str


@dataclass(frozen=True)
class Notification:
    notification_id: str
    request_id: str
    account_id: str
    recipient: str
    delivery_state: str
    provider_receipt: Optional[str]
    reconciliation_id: Optional[str]
    retry_locator: Optional[str]
    attempt_count: int
    last_attempted_at: str
    created_at: str


@dataclass(frozen=True)
class ReconciliationObservation:
    id: int
    attempt_id: str
    organization_id: str
    account_id: Optional[str]
    provider_state: str
    observed_at: str
    sequence: int
    reconciliation_class: Optional[str]
    is_stale: Optional[bool]
    matched_notification_id: Optional[str]
    applied: bool
    reject_reason: Optional[str]
    recorded_at: str
