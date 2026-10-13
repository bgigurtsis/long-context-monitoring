"""The recovery flow: start, complete, and retry notification delivery.

A recovery token is minted once, bound to the account and organization that
resolved from the email lookup at start time, and never rebound afterwards.
A later email change does not affect which account an already-issued token
can recover; only delivery of a *new* link depends on current address
ownership.
"""
from __future__ import annotations

import hmac
import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from .clock import add_iso, now_iso
from .errors import ExpiredTokenError, InvalidTokenError
from .mail import send_recovery_mail
from .notice import (
    account_id_from_retry_locator,
    encode_retry_locator,
    recipient_from_retry_locator,
)
from .storage import Storage
from .validate import validate_email, validate_id, validate_token

DEFAULT_TOKEN_TTL = timedelta(minutes=15)

# Version of the persisted delivery-attempt envelope shape (account_id,
# recipient, provider_receipt, retry_locator). Bump this if that shape
# changes, so a later reader can tell which fields to expect.
ENVELOPE_VERSION = 1


@dataclass(frozen=True)
class StartResult:
    request_id: str
    delivery_status: str  # "sent", "failed_pending_retry", or "accepted"


@dataclass(frozen=True)
class CompleteResult:
    organization_id: str
    account_id: str
    status: str  # "completed"


class RecoveryService:
    def __init__(self, storage: Storage, mail_endpoint: str, token_ttl: timedelta = DEFAULT_TOKEN_TTL):
        self._storage = storage
        self._mail_endpoint = mail_endpoint
        self._token_ttl = token_ttl

    def start(self, organization_id: str, email: str) -> StartResult:
        validate_id(organization_id, "organization")
        validate_email(email)

        request_id = "req_" + secrets.token_hex(12)
        account = self._storage.find_account_by_current_email(organization_id, email)
        if account is None:
            # Do not reveal whether the address exists in this organization.
            return StartResult(request_id=request_id, delivery_status="accepted")

        token = secrets.token_urlsafe(32)
        expires_at = add_iso(now_iso(), self._token_ttl)
        self._storage.create_recovery_request(
            request_id=request_id,
            organization_id=organization_id,
            account_id=account.account_id,
            token=token,
            expires_at=expires_at,
        )
        return StartResult(request_id=request_id, delivery_status=self._attempt_delivery(request_id, account.account_id, email, token))

    def complete(self, token: str) -> CompleteResult:
        validate_token(token)

        request = self._storage.get_recovery_request_by_token(token)
        if request is None or not hmac.compare_digest(request.token, token):
            raise InvalidTokenError("recovery token is unknown or already used")
        if request.status != "pending":
            raise InvalidTokenError("recovery token is unknown or already used")
        if request.expires_at <= now_iso():
            self._storage.mark_recovery_expired(request.request_id)
            raise ExpiredTokenError("recovery token has expired")

        self._storage.mark_recovery_completed(request.request_id)
        return CompleteResult(organization_id=request.organization_id, account_id=request.account_id, status="completed")

    def retry_notifications(self, request_id: Optional[str] = None) -> list[dict]:
        if request_id is not None:
            validate_id(request_id, "request_id")
        results = []
        for attempt, request in self._storage.list_pending_retry_attempts(request_id=request_id):
            fallback_account_id = request.account_id
            resolved_account_id = account_id_from_retry_locator(attempt.retry_locator or "", fallback_account_id)
            current_email = self._storage.get_current_email(request.organization_id, resolved_account_id)
            if current_email is None:
                results.append({"request_id": request.request_id, "outcome": "skipped_no_current_email"})
                continue
            recipient = recipient_from_retry_locator(attempt.retry_locator or "", attempt.recipient, current_email)
            outcome = self._attempt_delivery(request.request_id, resolved_account_id, recipient, request.token)
            results.append({"request_id": request.request_id, "outcome": outcome})
        return results

    def _attempt_delivery(self, request_id: str, account_id: str, recipient: str, token: str) -> str:
        attempt_number = self._storage.latest_attempt_number(request_id) + 1
        result = send_recovery_mail(self._mail_endpoint, recipient, token)
        if result.success:
            self._storage.record_delivery_attempt(
                recovery_request_id=request_id,
                attempt_number=attempt_number,
                account_id=account_id,
                recipient=recipient,
                outcome="sent",
                provider_receipt=result.receipt or None,
                envelope_version=ENVELOPE_VERSION,
                retry_locator=None,
            )
            return "sent"

        # Failed delivery: persist everything a later retry pass needs —
        # the trusted account binding (not anything derived from the
        # provider response), the address actually attempted, the opaque
        # receipt, and the retry locator built from them.
        locator = encode_retry_locator(result.receipt or "", account_id)
        self._storage.record_delivery_attempt(
            recovery_request_id=request_id,
            attempt_number=attempt_number,
            account_id=account_id,
            recipient=recipient,
            outcome="failed",
            provider_receipt=result.receipt or None,
            envelope_version=ENVELOPE_VERSION,
            retry_locator=locator,
        )
        return "failed_pending_retry"


# This class administers one account's durable recovery/notification state
# (start, complete, retry); "AccountService" is the name integration callers
# use for it. Keep it as an alias, not a second class, so there is exactly
# one implementation of retry_notifications for both names to share.
AccountService = RecoveryService
