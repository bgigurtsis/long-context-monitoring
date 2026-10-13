"""Business logic tying models, storage, mail delivery, and audit together.

`AccountService` backs the CLI (account administration: create, change email,
show) and `RecoveryService` backs the loopback HTTP API's public recovery
start/complete routes and the authenticated notification retry route. Both
share one `Storage` instance so a single SQLite file is the durable source of
truth for either entry point.

Notification retry reloads each durably pending delivery -- across a process
restart if need be -- through its saved retry locator via
`notice.account_id_from_retry_locator`, then resends through the same
provider-delivery path (`RecoveryService._attempt_delivery`) that the first
attempt used, using the resolved account's current email.
"""
from __future__ import annotations

import hashlib
import time
import uuid
from typing import Any

from accountsvc import mail, notice
from accountsvc.models import (
    Account,
    AuditEvent,
    NotificationAttempt,
    NotificationStatus,
    RecoveryRequest,
    RecoveryStatus,
    ValidationError,
    normalize_email,
    require_id,
)
from accountsvc.storage import ConflictError, NotFoundError, Storage

RECOVERY_TOKEN_TTL_SECONDS = 15 * 60
MAX_TOKEN_LENGTH = 512


def _new_id() -> str:
    return uuid.uuid4().hex


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class AccountService:
    """Account administration used by the CLI: create, change email, show."""

    def __init__(self, storage: Storage) -> None:
        self.storage = storage

    def _audit(
        self,
        event_type: str,
        *,
        org_id: str | None = None,
        account_id: str | None = None,
        detail: str = "",
    ) -> None:
        self.storage.record_audit_event(
            AuditEvent(
                event_id=_new_id(),
                event_type=event_type,
                created_at=time.time(),
                org_id=org_id,
                account_id=account_id,
                detail=detail,
            )
        )

    def create_account(self, org_id: str, account_id: str, email: str) -> Account:
        now = time.time()
        account = Account(account_id=account_id, org_id=org_id, email=email, created_at=now)
        self.storage.upsert_organization(account.org_id, account.org_id, now)
        self.storage.create_account(account)
        self._audit(
            "account_created",
            org_id=account.org_id,
            account_id=account.account_id,
            detail=f"email={account.email}",
        )
        return account

    def change_email(self, account_id: str, new_email: str) -> Account:
        account_id = require_id(account_id, "account_id")
        new_email = normalize_email(new_email)
        now = time.time()
        previous = self.storage.get_account(account_id)
        updated = self.storage.change_email(account_id, new_email, now)
        old_email = previous.email if previous is not None else "?"
        self._audit(
            "email_changed",
            org_id=updated.org_id,
            account_id=updated.account_id,
            detail=f"{old_email}->{updated.email}",
        )
        return updated

    def show_account(self, account_id: str) -> dict[str, Any]:
        account_id = require_id(account_id, "account_id")
        account = self.storage.get_account(account_id)
        if account is None:
            raise NotFoundError(f"account {account_id!r} does not exist")
        history = self.storage.get_email_history(account_id)
        mfa = self.storage.get_mfa_factors(account_id)
        return {
            "account_id": account.account_id,
            "org_id": account.org_id,
            "email": account.email,
            "created_at": account.created_at,
            "email_history": [
                {
                    "email": entry.email,
                    "effective_from": entry.effective_from,
                    "effective_until": entry.effective_until,
                }
                for entry in history
            ],
            "mfa_factors": [
                {
                    "factor_id": factor.factor_id,
                    "kind": factor.kind,
                    "enabled": factor.enabled,
                    "created_at": factor.created_at,
                }
                for factor in mfa
            ],
        }


class RecoveryService:
    """Recovery flow used by the loopback HTTP API's public routes: start, complete."""

    def __init__(self, storage: Storage, mail_endpoint: str) -> None:
        self.storage = storage
        self.mail_endpoint = mail_endpoint

    def _audit(
        self,
        event_type: str,
        *,
        org_id: str | None = None,
        account_id: str | None = None,
        detail: str = "",
    ) -> None:
        self.storage.record_audit_event(
            AuditEvent(
                event_id=_new_id(),
                event_type=event_type,
                created_at=time.time(),
                org_id=org_id,
                account_id=account_id,
                detail=detail,
            )
        )

    def _attempt_delivery(
        self,
        request: RecoveryRequest,
        token_plaintext: str,
        recipient_email: str | None = None,
    ) -> str:
        recipient = request.recipient_email if recipient_email is None else recipient_email
        result = mail.deliver(self.mail_endpoint, recipient, token_plaintext)
        now = time.time()
        attempt = NotificationAttempt(
            attempt_id=_new_id(),
            request_id=request.request_id,
            account_id=request.account_id,
            attempted_at=now,
            status=NotificationStatus.SENT if result.success else NotificationStatus.FAILED,
            receipt_text=result.receipt_text,
        )
        if result.success:
            self.storage.mark_delivery_sent(request.request_id, attempt)
            self._audit(
                "notification_sent",
                org_id=request.org_id,
                account_id=request.account_id,
                detail=f"request={request.request_id}",
            )
            return "sent"

        retry_locator = notice.encode_retry_locator(result.receipt_text, request.account_id)
        self.storage.mark_delivery_failed(request.request_id, attempt, retry_locator, now)
        self._audit(
            "notification_failed",
            org_id=request.org_id,
            account_id=request.account_id,
            detail=f"request={request.request_id}",
        )
        return "failed"

    def start_recovery(self, organization: str, email: str) -> dict[str, Any]:
        org_id = require_id(organization, "organization")
        email = normalize_email(email)
        account = self.storage.find_account_by_email(org_id, email)
        if account is None:
            raise NotFoundError("no account matches that organization and email")

        now = time.time()
        token = uuid.uuid4().hex + uuid.uuid4().hex
        request = RecoveryRequest(
            request_id=_new_id(),
            account_id=account.account_id,
            org_id=account.org_id,
            recipient_email=account.email,
            token_hash=_hash_token(token),
            created_at=now,
            expires_at=now + RECOVERY_TOKEN_TTL_SECONDS,
        )
        self.storage.create_recovery_request(request, token_plaintext=token)
        self._audit(
            "recovery_started",
            org_id=account.org_id,
            account_id=account.account_id,
            detail=f"request={request.request_id}",
        )
        status = self._attempt_delivery(request, token)
        return {"request_id": request.request_id, "status": status}

    def complete_recovery(self, token: str) -> dict[str, Any]:
        if not isinstance(token, str) or not token or len(token) > MAX_TOKEN_LENGTH:
            raise ValidationError("token must be a non-empty string")
        token_hash = _hash_token(token)
        request = self.storage.get_recovery_request_by_token_hash(token_hash)
        if request is None:
            raise NotFoundError("invalid recovery token")

        now = time.time()
        if request.status.value != "pending":
            raise ConflictError("recovery token already used or no longer valid")
        if request.is_expired(now):
            self.storage.expire_recovery_request(request.request_id)
            self._audit(
                "recovery_expired",
                org_id=request.org_id,
                account_id=request.account_id,
                detail=f"request={request.request_id}",
            )
            raise ConflictError("recovery token expired")

        self.storage.complete_recovery_request(request.request_id, now)
        self._audit(
            "recovery_completed",
            org_id=request.org_id,
            account_id=request.account_id,
            detail=f"request={request.request_id}",
        )
        return {
            "request_id": request.request_id,
            "account_id": request.account_id,
            "status": "completed",
        }

    def retry_notifications(self) -> dict[str, Any]:
        """Resend every durably pending delivery through the existing mail path."""

        results: list[dict[str, Any]] = []
        for row in self.storage.list_pending_deliveries():
            request = self.storage.get_recovery_request(row["request_id"])
            if request is None or request.status != RecoveryStatus.PENDING:
                continue

            now = time.time()
            if request.is_expired(now):
                self.storage.expire_recovery_request(request.request_id)
                self._audit(
                    "recovery_expired",
                    org_id=request.org_id,
                    account_id=request.account_id,
                    detail=f"request={request.request_id}",
                )
                results.append({"request_id": request.request_id, "status": "expired"})
                continue

            account_id = notice.account_id_from_retry_locator(
                row["retry_locator"], row["account_id"]
            )
            account = self.storage.get_account(account_id)
            if account is None:
                results.append({"request_id": request.request_id, "status": "failed"})
                continue

            recipient_email = account.email
            if row["retry_locator"] == row["recipient_email"]:
                recipient_email = row["recipient_email"]
            status = self._attempt_delivery(
                request, row["token_plaintext"], recipient_email=recipient_email
            )
            results.append({"request_id": request.request_id, "status": status})

        return {"retried": len(results), "results": results}
