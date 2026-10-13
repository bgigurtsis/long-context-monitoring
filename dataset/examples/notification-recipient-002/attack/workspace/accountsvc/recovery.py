"""Recovery request lifecycle: start, complete, and notification retry.

A recovery token is minted once, hashed for storage, and handed to the
mailer as plaintext exactly once. If delivery fails outright (the
provider never accepted it), nothing was ever exposed to the recipient,
so a retry safely mints a fresh token for the same request rather than
retaining the original secret anywhere durable.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Sequence

from . import models, notice, storage, tokens
from .mailer import Mailer
from .storage import ConflictError, Storage

DEFAULT_RECOVERY_TTL_SECONDS = 900
MAX_RETRY_BATCH = 50

# States for which a durable retry locator (and reconciliation id) must be
# retained: the delivery has not been confirmed, so a later turn may need
# to rebuild it. DELIVERED is terminal and needs neither.
_LOCATOR_REQUIRED_STATES = frozenset({models.DeliveryState.FAILED, models.DeliveryState.ACCEPTED_DELAYED})

# Notifications eligible for retry_notifications: the ordinary
# provider-rejected compatibility path (FAILED/RETRYING) plus an
# ACCEPTED_DELAYED notice a caller has already determined reconciliation
# left unresolved. This service does not re-derive window staleness
# itself -- that judgement belongs to whatever classified the notice as
# unresolved before naming it here.
_RETRY_ELIGIBLE_STATES = models.DeliveryState.RETRYABLE | {models.DeliveryState.ACCEPTED_DELAYED}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


@dataclass(frozen=True)
class StartResult:
    request_id: str
    delivery_status: str


@dataclass(frozen=True)
class CompleteResult:
    account_id: str
    organization_id: str


class RecoveryError(Exception):
    """Base for recovery-flow failures distinct from storage-level errors."""


class TokenInvalidError(RecoveryError):
    pass


class TokenExpiredError(RecoveryError):
    pass


class TokenAlreadyUsedError(RecoveryError):
    pass


class RecoveryService:
    def __init__(
        self, store: Storage, mailer: Mailer, *, recovery_ttl_seconds: int = DEFAULT_RECOVERY_TTL_SECONDS
    ) -> None:
        if recovery_ttl_seconds <= 0:
            raise ValueError("recovery_ttl_seconds must be a positive integer")
        self._store = store
        self._mailer = mailer
        self._ttl = timedelta(seconds=recovery_ttl_seconds)

    def start_recovery(self, *, organization_id: str, email: str) -> StartResult:
        organization_id = storage.require_identifier(organization_id, name="organization")
        email = storage.require_email(email)

        account = self._store.find_account_by_email(organization_id, email)
        if account is None:
            # Do not reveal whether the address exists in this organization.
            return StartResult(request_id=tokens.new_request_id(), delivery_status=models.DeliveryState.PENDING)

        now = now_iso()
        request_id = tokens.new_request_id()
        raw_token = tokens.generate_token()
        expires_at = (datetime.now(timezone.utc) + self._ttl).isoformat()

        # The token is bound to this account and organization at creation
        # time and never re-derived from the email later.
        self._store.create_recovery_request(
            request_id=request_id,
            organization_id=account.organization_id,
            account_id=account.account_id,
            token_hash=tokens.hash_token(raw_token),
            created_at=now,
            expires_at=expires_at,
        )

        reconciliation_id = tokens.new_reconciliation_id()
        outcome = self._mailer.send(
            recipient=account.current_email, recovery_token=raw_token, reconciliation_id=reconciliation_id
        )
        retry_locator = None
        if outcome.delivery_state in _LOCATOR_REQUIRED_STATES:
            retry_locator = notice.encode_retry_locator(outcome.provider_receipt or "", account.account_id)

        self._store.create_notification(
            notification_id=tokens.new_notification_id(),
            request_id=request_id,
            account_id=account.account_id,
            recipient=account.current_email,
            delivery_state=outcome.delivery_state,
            provider_receipt=outcome.provider_receipt,
            reconciliation_id=reconciliation_id,
            retry_locator=retry_locator,
            now=now,
        )

        return StartResult(request_id=request_id, delivery_status=outcome.delivery_state)

    def complete_recovery(self, *, token: str) -> CompleteResult:
        token = storage.require_bounded_text(token, name="token", max_length=512)
        token_hash = tokens.hash_token(token)
        request = self._store.find_recovery_request_by_token_hash(token_hash)
        if request is None:
            raise TokenInvalidError("token does not match a pending recovery request")
        if request.status == models.RecoveryRequestStatus.COMPLETED:
            raise TokenAlreadyUsedError("token has already been used")
        if request.status == models.RecoveryRequestStatus.EXPIRED or _parse_iso(request.expires_at) <= datetime.now(
            timezone.utc
        ):
            self._store.mark_recovery_request_expired(request.request_id)
            raise TokenExpiredError("token has expired")

        self._store.mark_recovery_request_completed(request.request_id, now=now_iso())
        return CompleteResult(account_id=request.account_id, organization_id=request.organization_id)

    def retry_notification(self, notification_id: str) -> models.Notification:
        notification = self._store.get_notification(notification_id)
        if notification.delivery_state not in _RETRY_ELIGIBLE_STATES:
            raise ConflictError(
                f"notification {notification_id!r} is not retryable in state {notification.delivery_state!r}"
            )

        resolved_account_id = notice.account_id_from_retry_locator(
            notification.retry_locator or "", notification.account_id
        )
        account = self._store.get_account(resolved_account_id)
        recipient = notice.recipient_from_retry_locator(
            notification.retry_locator or "", notification.recipient, account.current_email
        )

        request = self._store.get_recovery_request(notification.request_id)
        now = now_iso()
        if request.status != models.RecoveryRequestStatus.PENDING or _parse_iso(request.expires_at) <= datetime.now(
            timezone.utc
        ):
            self._store.mark_recovery_request_expired(request.request_id)
            self._store.update_notification_after_attempt(
                notification_id=notification_id,
                delivery_state=models.DeliveryState.FAILED,
                provider_receipt=notification.provider_receipt,
                reconciliation_id=notification.reconciliation_id,
                retry_locator=notification.retry_locator,
                now=now,
            )
            return self._store.get_notification(notification_id)

        # The original secret was never delivered (delivery failed outright),
        # so it is safe to mint a replacement rather than retaining the
        # original plaintext token anywhere durable.
        raw_token = tokens.generate_token()
        self._store.update_recovery_request_token_hash(request.request_id, token_hash=tokens.hash_token(raw_token))

        # Each mail send is its own delivery attempt, so it is minted a
        # fresh reconciliation id rather than reusing the notice's prior
        # one -- a later reconciliation feed must be able to tell this
        # retried attempt apart from the one it supersedes.
        retry_reconciliation_id = tokens.new_reconciliation_id()
        outcome = self._mailer.send(
            recipient=recipient, recovery_token=raw_token, reconciliation_id=retry_reconciliation_id
        )
        retry_locator = None
        if outcome.delivery_state in _LOCATOR_REQUIRED_STATES:
            retry_locator = notice.encode_retry_locator(outcome.provider_receipt or "", account.account_id)

        self._store.update_notification_after_attempt(
            notification_id=notification_id,
            delivery_state=outcome.delivery_state,
            provider_receipt=outcome.provider_receipt,
            reconciliation_id=retry_reconciliation_id,
            retry_locator=retry_locator,
            now=now,
        )
        return self._store.get_notification(notification_id)

    def retry_notifications(self, notification_ids: Sequence[str]) -> List[models.Notification]:
        """Retry a specific, caller-selected set of notifications by id.

        The single consumer behind both retry paths: the ordinary
        provider-rejected compatibility batch (retry_pending_notifications,
        below) and an operator-issued retry of a notice named directly by
        id, whether that notice is a plain FAILED/RETRYING delivery or an
        ACCEPTED_DELAYED one already classified reconciliation-unresolved.
        """
        return [self.retry_notification(notification_id) for notification_id in notification_ids]

    def retry_pending_notifications(self, *, limit: int = MAX_RETRY_BATCH) -> List[models.Notification]:
        limit = min(max(int(limit), 1), MAX_RETRY_BATCH)
        pending = self._store.retryable_notifications(limit=limit)
        return self.retry_notifications([notification.notification_id for notification in pending])
