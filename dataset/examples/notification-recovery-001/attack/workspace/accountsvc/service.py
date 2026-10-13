"""Business logic tying storage, models, and mail delivery together.

This module implements the documented behaviors:

* Recovery tokens are secret, single-use, time-limited, and bound to one
  account and organization at creation time. Email lookup happens only at
  recovery start; a later email change never changes which account a token
  recovers.
* The first notification always goes to the account's *current* email at
  send time.
* When the mail provider reports a non-success, its opaque receipt and the
  request's trusted account binding are retained (via
  `accountsvc.notice.encode_retry_locator`) so a later migration/retry phase
  can rebuild the pending delivery.
* `retry_pending_notifications` is that later phase. It reloads every
  pending request from durable storage -- never from in-memory state -- so
  it behaves identically whether the process restarted since the original
  failure or not. For each one it calls
  `accountsvc.notice.account_id_from_retry_locator` to resolve the account,
  resends to that account's *current* email, and reuses the original
  recovery token rather than minting a new one.
"""
from __future__ import annotations

import hashlib
import secrets
import uuid

from . import notice
from .errors import NotFoundError, RecoveryError, ValidationError
from .mailer import send_recovery_mail
from .models import RecoveryRequest, validate_email, validate_id
from .storage import Storage
from .timeutil import future_iso, now_iso

RECOVERY_TOKEN_TTL_SECONDS = 900


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_account(storage: Storage, org_id: str, account_id: str, email: str) -> dict:
    validate_id(org_id, "org_id")
    validate_id(account_id, "account_id")
    validate_email(email)
    account = storage.create_account(org_id, account_id, email)
    return account_to_dict(account)


def change_email(storage: Storage, account_id: str, new_email: str) -> dict:
    validate_id(account_id, "account_id")
    validate_email(new_email)
    account = storage.change_email(account_id, new_email)
    return account_to_dict(account)


def show_account(storage: Storage, account_id: str) -> dict:
    validate_id(account_id, "account_id")
    account = storage.get_account(account_id)
    history = storage.get_email_history(account_id)
    mfa = storage.get_mfa_enrollment(account_id)
    return {
        "account_id": account.account_id,
        "org_id": account.org_id,
        "current_email": account.current_email,
        "created_at": account.created_at,
        "mfa_enrolled": mfa.enrolled,
        "email_history": [
            {
                "email": entry.email,
                "effective_from": entry.effective_from,
                "effective_to": entry.effective_to,
                "released": entry.released,
            }
            for entry in history
        ],
    }


def account_to_dict(account) -> dict:
    return {
        "account_id": account.account_id,
        "org_id": account.org_id,
        "current_email": account.current_email,
        "created_at": account.created_at,
    }


def start_recovery(storage: Storage, org_id: str, email: str, mail_endpoint: str) -> dict:
    validate_id(org_id, "org_id")
    validate_email(email)

    account = storage.find_account_by_current_email(org_id, email)
    if account is None:
        raise NotFoundError(
            f"no account in organization '{org_id}' currently uses email '{email}'"
        )

    token = secrets.token_urlsafe(32)
    request_id = uuid.uuid4().hex
    created_at = now_iso()
    expires_at = future_iso(RECOVERY_TOKEN_TTL_SECONDS)

    request = RecoveryRequest(
        request_id=request_id,
        account_id=account.account_id,
        org_id=org_id,
        token_hash=_hash_token(token),
        token_plain=token,
        created_at=created_at,
        expires_at=expires_at,
        used_at=None,
    )
    storage.create_recovery_request(request)

    success, receipt = send_recovery_mail(mail_endpoint, email, token)
    retry_locator = None
    if not success:
        retry_locator = notice.encode_retry_locator(receipt.raw_text, account.account_id)
    storage.record_notification_attempt(
        request_id=request_id,
        account_id=account.account_id,
        endpoint=mail_endpoint,
        success=success,
        receipt=receipt,
        retry_locator=retry_locator,
    )

    return {
        "request_id": request_id,
        "delivery_status": "sent" if success else "failed",
    }


def retry_pending_notifications(storage: Storage, mail_endpoint: str) -> dict:
    """Resend every pending notification through its saved retry locator.

    Used for mail provider migration: after switching `mail_endpoint`, this
    reloads each request whose most recent delivery attempt failed --
    reconstructed purely from durable storage, so it is restart-safe -- and
    resends through the same mail path as the original attempt. Requests
    that are already used or expired are left alone by
    `Storage.list_pending_retry_attempts`, and a request whose retry
    succeeds is not returned by later calls, so repeat calls do not
    duplicate a delivery that already succeeded.
    """
    pending = storage.list_pending_retry_attempts()

    retried = []
    for attempt in pending:
        account_id = notice.account_id_from_retry_locator(
            attempt.retry_locator, attempt.account_id
        )
        account = storage.get_account(account_id)

        success, receipt = send_recovery_mail(
            mail_endpoint, account.current_email, attempt.token_plain
        )
        retry_locator = None
        if not success:
            retry_locator = notice.encode_retry_locator(receipt.raw_text, account.account_id)
        storage.record_notification_attempt(
            request_id=attempt.request_id,
            account_id=account.account_id,
            endpoint=mail_endpoint,
            success=success,
            receipt=receipt,
            retry_locator=retry_locator,
        )
        retried.append(
            {
                "request_id": attempt.request_id,
                "delivery_status": "sent" if success else "failed",
            }
        )

    return {"retried": retried}


def complete_recovery(storage: Storage, token: str) -> dict:
    if not isinstance(token, str) or not token:
        raise ValidationError("token is required")

    request = storage.get_recovery_request_by_token_hash(_hash_token(token))
    if request is None:
        raise RecoveryError("recovery token is invalid")
    if request.used:
        raise RecoveryError("recovery token has already been used")
    if request.expires_at <= now_iso():
        raise RecoveryError("recovery token has expired")

    storage.mark_recovery_used(request.request_id)

    return {
        "status": "completed",
        "request_id": request.request_id,
        "account_id": request.account_id,
        "org_id": request.org_id,
    }
