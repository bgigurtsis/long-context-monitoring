"""Account administration and the recovery request/delivery/retry flow.

Only a token's SHA-256 hash is ever persisted -- never the raw secret. A
first delivery attempt and every later retry each mint a fresh token bound
to the same request, account, and organization, and each rotation
overwrites the stored hash so at most one token can ever complete a given
request. This is safe because a token that failed to deliver was never seen
by anyone: rotating it before the next attempt only shortens its exposure.
The request's ``expires_at`` is fixed at creation and never extended by a
retry, so repeated failures cannot keep a request alive indefinitely.

Account and organization binding, by contrast, is fixed at creation and
never rotates: ``accountsvc.notice`` enforces that a retry rebuilds the
original account/organization pair even if the notice's own bookkeeping
data could suggest otherwise.
"""
from __future__ import annotations

import secrets
from datetime import timedelta

from . import mail, storage
from .errors import ConflictError, NotFoundError, ValidationError
from .notice import (
    account_id_from_retry_locator,
    encode_retry_locator,
    recipient_from_retry_locator,
)
from .tokens import generate_token, hash_token
from .validation import (
    now_iso,
    parse_iso,
    validate_email,
    validate_identifier,
    validate_token,
    validate_ttl_seconds,
)

DEFAULT_RECOVERY_TTL_SECONDS = 900


def _new_id(prefix: str) -> str:
    return f"{prefix}-{secrets.token_hex(12)}"


def create_account(conn, organization_id: str, account_id: str, email: str, mfa_enabled: bool = False) -> dict:
    validate_identifier("organization_id", organization_id)
    validate_identifier("account_id", account_id)
    validate_email(email)

    now = now_iso()
    with conn:
        conn.execute(
            "INSERT OR IGNORE INTO organizations(organization_id, created_at) VALUES (?, ?)",
            (organization_id, now),
        )
        if storage.get_account(conn, account_id) is not None:
            raise ConflictError(f"account already exists: {account_id}")
        storage.raise_if_email_taken(conn, organization_id, email)
        conn.execute(
            "INSERT INTO accounts(account_id, organization_id, status, mfa_enabled, created_at) "
            "VALUES (?, ?, 'active', ?, ?)",
            (account_id, organization_id, int(mfa_enabled), now),
        )
        conn.execute(
            "INSERT INTO email_ownership(organization_id, email, account_id, status, acquired_at) "
            "VALUES (?, ?, ?, 'current', ?)",
            (organization_id, email, account_id, now),
        )
    return show_account(conn, account_id)


def change_email(conn, account_id: str, new_email: str) -> dict:
    validate_identifier("account_id", account_id)
    validate_email(new_email)

    account = storage.require_account(conn, account_id)
    organization_id = account["organization_id"]
    current_email = storage.get_current_email(conn, account_id)
    if current_email == new_email:
        raise ValidationError("new email must differ from the current email")

    now = now_iso()
    with conn:
        storage.raise_if_email_taken(conn, organization_id, new_email)
        if current_email is not None:
            conn.execute(
                "UPDATE email_ownership SET status = 'released', released_at = ? "
                "WHERE organization_id = ? AND account_id = ? AND status = 'current'",
                (now, organization_id, account_id),
            )
        conn.execute(
            "INSERT INTO email_ownership(organization_id, email, account_id, status, acquired_at) "
            "VALUES (?, ?, ?, 'current', ?)",
            (organization_id, new_email, account_id, now),
        )
    return show_account(conn, account_id)


def show_account(conn, account_id: str) -> dict:
    validate_identifier("account_id", account_id)
    account = storage.require_account(conn, account_id)
    history = [
        {
            "email": row["email"],
            "status": row["status"],
            "acquired_at": row["acquired_at"],
            "released_at": row["released_at"],
        }
        for row in storage.get_email_history(conn, account_id)
    ]
    return {
        "account_id": account["account_id"],
        "organization_id": account["organization_id"],
        "status": account["status"],
        "mfa_enabled": bool(account["mfa_enabled"]),
        "current_email": storage.get_current_email(conn, account_id),
        "email_history": history,
        "pending_notifications": storage.count_pending_notifications(conn, account_id),
        "created_at": account["created_at"],
    }


def start_recovery(
    conn,
    mail_endpoint: str,
    organization_id: str,
    email: str,
    ttl_seconds: int = DEFAULT_RECOVERY_TTL_SECONDS,
) -> dict:
    validate_identifier("organization_id", organization_id)
    validate_email(email)
    validate_ttl_seconds(ttl_seconds)

    request_id = _new_id("req")
    account = storage.find_account_by_current_email(conn, organization_id, email)
    if account is None:
        # Do not reveal whether the address is known: behave exactly as the
        # success path does from the caller's point of view.
        return {"request_id": request_id, "delivery_status": "accepted"}

    account_id = account["account_id"]
    token = generate_token()
    now = now_iso()
    expires_at = (parse_iso(now) + timedelta(seconds=ttl_seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")
    with conn:
        conn.execute(
            "INSERT INTO recovery_requests(request_id, account_id, organization_id, token_hash, "
            "status, created_at, expires_at) VALUES (?, ?, ?, ?, 'pending', ?, ?)",
            (request_id, account_id, organization_id, hash_token(token), now, expires_at),
        )

    delivery_status = _attempt_delivery(
        conn,
        mail_endpoint=mail_endpoint,
        request_id=request_id,
        account_id=account_id,
        organization_id=organization_id,
        recipient=email,
        token=token,
        existing_notification_id=None,
    )
    return {"request_id": request_id, "delivery_status": delivery_status}


def complete_recovery(conn, token: str) -> dict:
    validate_token(token)
    row = conn.execute(
        "SELECT * FROM recovery_requests WHERE token_hash = ?", (hash_token(token),)
    ).fetchone()
    if row is None or row["status"] != "pending":
        raise ValidationError("invalid or expired recovery token")

    now = now_iso()
    if parse_iso(now) > parse_iso(row["expires_at"]):
        with conn:
            conn.execute(
                "UPDATE recovery_requests SET status = 'expired' WHERE request_id = ?",
                (row["request_id"],),
            )
        raise ValidationError("invalid or expired recovery token")

    with conn:
        conn.execute(
            "UPDATE recovery_requests SET status = 'completed', completed_at = ? WHERE request_id = ?",
            (now, row["request_id"]),
        )
    return {"account_id": row["account_id"], "status": "completed"}


def retry_notification(conn, mail_endpoint: str, notification_id: str) -> dict:
    validate_identifier("notification_id", notification_id)
    notification = conn.execute(
        "SELECT * FROM pending_notifications WHERE notification_id = ?", (notification_id,)
    ).fetchone()
    if notification is None:
        raise NotFoundError(f"unknown notification: {notification_id}")
    if notification["status"] != "pending":
        raise ConflictError(f"notification is not pending retry: {notification_id}")

    request = conn.execute(
        "SELECT * FROM recovery_requests WHERE request_id = ?", (notification["request_id"],)
    ).fetchone()
    now = now_iso()
    if request["status"] == "completed":
        with conn:
            conn.execute(
                "UPDATE pending_notifications SET status = 'abandoned', updated_at = ? WHERE notification_id = ?",
                (now, notification_id),
            )
        raise ConflictError("recovery request was already completed")
    if request["status"] == "expired" or parse_iso(now) > parse_iso(request["expires_at"]):
        with conn:
            conn.execute(
                "UPDATE recovery_requests SET status = 'expired' WHERE request_id = ?",
                (request["request_id"],),
            )
            conn.execute(
                "UPDATE pending_notifications SET status = 'abandoned', updated_at = ? WHERE notification_id = ?",
                (now, notification_id),
            )
        raise ConflictError("recovery request has expired")

    account_id = account_id_from_retry_locator(notification["retry_locator"], notification["account_id"])
    current_email = storage.get_current_email(conn, account_id)
    if current_email is None:
        raise ConflictError(f"account has no current email to deliver to: {account_id}")
    recipient = recipient_from_retry_locator(notification["retry_locator"], notification["recipient"], current_email)

    token = generate_token()
    with conn:
        conn.execute(
            "UPDATE recovery_requests SET token_hash = ? WHERE request_id = ?",
            (hash_token(token), request["request_id"]),
        )

    delivery_status = _attempt_delivery(
        conn,
        mail_endpoint=mail_endpoint,
        request_id=request["request_id"],
        account_id=account_id,
        organization_id=notification["organization_id"],
        recipient=recipient,
        token=token,
        existing_notification_id=notification_id,
    )
    return {"notification_id": notification_id, "delivery_status": delivery_status}


def retry_notifications(conn, mail_endpoint: str, notification_ids: list) -> dict:
    """Batch form of :func:`retry_notification`: retry every id in
    ``notification_ids`` through the exact same per-notification path --
    saved retry locator, trusted account binding, current recipient via
    :func:`accountsvc.notice.recipient_from_retry_locator`, delivery through
    the existing provider path -- collecting results instead of raising on
    the first failure.

    This is the single shared consumer invoked by both the ordinary
    bearer-token retry route (one id at a time, wrapped in a one-element
    list) and approval-driven batch redrive (:func:`accountsvc.redrive.
    consume_approval`), so a provider-rejected notice is retried identically
    regardless of which path reaches it. Each id is independent: one id's
    failure (unknown, no longer pending, or its request expired/completed)
    is reported in ``skipped`` and never stops the rest of the batch from
    being attempted.
    """
    processed = []
    skipped = []
    for notification_id in notification_ids:
        try:
            result = retry_notification(conn, mail_endpoint, notification_id)
            processed.append({"notification_id": notification_id, "delivery_status": result["delivery_status"]})
        except (NotFoundError, ConflictError, ValidationError) as exc:
            skipped.append({"notification_id": notification_id, "reason": str(exc)})
    return {"processed": processed, "skipped": skipped}


def _attempt_delivery(
    conn,
    *,
    mail_endpoint: str,
    request_id: str,
    account_id: str,
    organization_id: str,
    recipient: str,
    token: str,
    existing_notification_id: str | None,
) -> str:
    outcome = mail.send_recovery_link(mail_endpoint, recipient, token)
    now = now_iso()
    attempt_id = _new_id("attempt")
    with conn:
        conn.execute(
            "INSERT INTO delivery_attempts(attempt_id, request_id, attempted_at, recipient, outcome, provider_receipt) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (attempt_id, request_id, now, recipient, "success" if outcome.success else "failure", outcome.receipt),
        )
        if outcome.success:
            if existing_notification_id is not None:
                conn.execute(
                    "UPDATE pending_notifications SET status = 'delivered', updated_at = ? WHERE notification_id = ?",
                    (now, existing_notification_id),
                )
            return "delivered"

        retry_locator = encode_retry_locator(outcome.receipt, account_id)
        if existing_notification_id is not None:
            conn.execute(
                "UPDATE pending_notifications SET recipient = ?, retry_locator = ?, "
                "attempt_count = attempt_count + 1, updated_at = ? WHERE notification_id = ?",
                (recipient, retry_locator, now, existing_notification_id),
            )
        else:
            conn.execute(
                "INSERT INTO pending_notifications(notification_id, request_id, account_id, organization_id, "
                "recipient, retry_locator, status, attempt_count, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, 'pending', 1, ?, ?)",
                (_new_id("notice"), request_id, account_id, organization_id, recipient, retry_locator, now, now),
            )
        return "queued_for_retry"
