"""Recovery orchestration: start, complete, retry, reconcile, redrive."""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from . import mail, storage
from .delivery_address import load_delivery_address, resolve_effective_address

TOKEN_TTL = timedelta(minutes=15)
MAX_RECONCILE_RECEIPTS = 100
RECONCILABLE_STATUSES = ("delivered", "bounced", "failed")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _expiry_from(now_iso: str) -> str:
    now = datetime.fromisoformat(now_iso)
    return (now + TOKEN_TTL).isoformat()


class RecoveryError(Exception):
    """A request-level error with an HTTP status and a stable error code."""

    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


class RecoveryService:
    def __init__(self, database: str, mail_endpoint: str):
        self.database = database
        self.mail_endpoint = mail_endpoint
        storage.initialize(database)

    # -- account administration -------------------------------------

    def create_account(self, org_id: str, account_id: str, email: str) -> None:
        storage.create_account(self.database, org_id, account_id, email)

    def change_email(self, account_id: str, new_email: str) -> None:
        storage.change_email(self.database, account_id, new_email)

    def show_account(self, account_id: str) -> Optional[dict]:
        return storage.get_account(self.database, account_id)

    # -- recovery flow -------------------------------------------------

    def start_recovery(self, organization: str, email: str) -> dict:
        account = storage.find_account_by_email(self.database, organization, email)
        if account is None:
            # Do not reveal whether the organization/email pair exists.
            return {"request_id": str(uuid.uuid4()), "status": "accepted"}

        now = _now()
        request_id = str(uuid.uuid4())
        token = secrets.token_urlsafe(32)
        storage.create_recovery_request(
            self.database,
            request_id=request_id,
            org_id=organization,
            account_id=account["account_id"],
            recipient=email,
            token=token,
            created_at=now,
            expires_at=_expiry_from(now),
        )
        receipt_id = str(uuid.uuid4())
        storage.create_notification(
            self.database,
            receipt_id=receipt_id,
            request_id=request_id,
            recipient=email,
            created_at=now,
        )
        status = self._attempt_delivery(receipt_id, email, token)
        return {"request_id": request_id, "status": status}

    def complete_recovery(self, token: str) -> dict:
        now = _now()
        req = storage.find_recovery_request_by_token(self.database, token)
        if req is None:
            raise RecoveryError("invalid_token", "recovery token is invalid", 400)
        if req["used_at"] is not None:
            raise RecoveryError("invalid_token", "recovery token already used", 400)
        if req["expires_at"] < now:
            raise RecoveryError("invalid_token", "recovery token has expired", 400)
        storage.mark_recovery_request_used(self.database, req["request_id"], now)
        return {
            "status": "recovered",
            "organization": req["org_id"],
            "account_id": req["account_id"],
        }

    # -- notification lifecycle -----------------------------------------

    def retry_notifications(self) -> dict:
        """Bulk-retry every notification currently marked failed."""
        failed = storage.list_notifications_by_status(self.database, "failed")
        results = []
        for notification in failed:
            req = storage.get_recovery_request(self.database, notification["request_id"])
            status = self._attempt_delivery(
                notification["receipt_id"], notification["recipient"], req["token"]
            )
            results.append({"receipt_id": notification["receipt_id"], "status": status})
        return {"retried": results}

    def redrive_notification(self, receipt_id: str) -> dict:
        """Force a resend of one specific failed notice, by its receipt id."""
        notification = storage.get_notification(self.database, receipt_id)
        if notification is None:
            raise RecoveryError("not_found", "no notification with that receipt id", 404)
        if notification["status"] != "failed":
            raise RecoveryError(
                "not_failed", "only a failed notice may be redriven", 409
            )
        req = storage.get_recovery_request(self.database, notification["request_id"])
        if req["expires_at"] < _now():
            raise RecoveryError(
                "token_expired", "the underlying recovery token has expired", 409
            )
        account = storage.get_account(self.database, req["account_id"])
        address = load_delivery_address(self.database, account)
        status = self._attempt_delivery(receipt_id, address, req["token"])
        return {"receipt_id": receipt_id, "status": status}

    def get_attempt_status(self, receipt_id: str) -> dict:
        """Return a notice's delivery-attempt history and its effective address."""
        notification = storage.get_notification(self.database, receipt_id)
        if notification is None:
            raise RecoveryError("not_found", "no notification with that receipt id", 404)
        req = storage.get_recovery_request(self.database, notification["request_id"])
        account = storage.get_account(self.database, req["account_id"])
        claim_history = storage.list_address_claims(self.database, req["account_id"])
        effective_address = resolve_effective_address(
            {"current_address": account["email"] if account else ""}, claim_history
        )
        return {
            "receipt_id": receipt_id,
            "status": notification["status"],
            "attempts": storage.list_attempts(self.database, receipt_id),
            "effective_address": effective_address,
        }

    def reconcile_receipts(self, receipts: list) -> dict:
        """Apply a batch of provider delivery receipts to matching notifications."""
        if not isinstance(receipts, list):
            raise RecoveryError("bad_request", "receipts must be a list", 400)
        if len(receipts) > MAX_RECONCILE_RECEIPTS:
            raise RecoveryError(
                "too_many_receipts",
                f"at most {MAX_RECONCILE_RECEIPTS} receipts per request",
                413,
            )
        now = _now()
        reconciled = []
        unknown = []
        for entry in receipts:
            receipt_id = entry.get("receipt_id") if isinstance(entry, dict) else None
            provider_status = entry.get("status") if isinstance(entry, dict) else None
            provider_message_id = (
                entry.get("provider_message_id") if isinstance(entry, dict) else None
            )
            if not receipt_id or provider_status not in RECONCILABLE_STATUSES:
                unknown.append(receipt_id)
                continue
            notification = storage.get_notification(self.database, receipt_id)
            if notification is None:
                unknown.append(receipt_id)
                continue
            storage.reconcile_notification(
                self.database,
                receipt_id=receipt_id,
                provider_status=provider_status,
                provider_message_id=provider_message_id,
                reconciled_at=now,
            )
            reconciled.append(receipt_id)
        return {"reconciled": reconciled, "unknown": unknown}

    # -- internal --------------------------------------------------------

    def _attempt_delivery(self, receipt_id: str, recipient: str, token: str) -> str:
        result = mail.send_notification(self.mail_endpoint, recipient, token, receipt_id)
        now = _now()
        storage.record_attempt(
            self.database,
            receipt_id=receipt_id,
            outcome="success" if result.success else "failure",
            http_status=result.http_status,
            error=result.error,
            attempted_at=now,
        )
        status = "sent" if result.success else "failed"
        storage.update_notification_status(self.database, receipt_id, status, now, result.error)
        return status
