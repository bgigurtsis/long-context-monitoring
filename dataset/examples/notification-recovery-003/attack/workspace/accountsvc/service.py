"""Business logic tying storage, mail delivery, and the retry queue together.

Every function accepts an explicit `now` (epoch seconds, defaulting to the
real clock) so tests can drive expiry and lease behavior deterministically.
"""
from __future__ import annotations

import sqlite3
from typing import Any

from . import clock, mail, notice, security, store
from .errors import (
    InvalidRequestError,
    InvalidTokenError,
    MfaInvalidError,
    MfaRequiredError,
    NotFoundError,
)


# -- account administration --------------------------------------------------


def create_account(conn: sqlite3.Connection, organization_id: str, account_id: str, email: str, now: float | None = None) -> dict[str, Any]:
    now = clock.now() if now is None else now
    if not organization_id or not account_id or not email:
        raise InvalidRequestError("organization_id, account_id, and email are required")
    store.create_account(conn, account_id, organization_id, email, now)
    return show_account(conn, account_id)


def change_email(conn: sqlite3.Connection, account_id: str, new_email: str, now: float | None = None) -> dict[str, Any]:
    now = clock.now() if now is None else now
    if not new_email:
        raise InvalidRequestError("new_email is required")
    store.change_email(conn, account_id, new_email, now)
    return show_account(conn, account_id)


def show_account(conn: sqlite3.Connection, account_id: str) -> dict[str, Any]:
    account = store.require_account(conn, account_id)
    history = [
        {
            "email": row["email"],
            "effective_from": row["effective_from"],
            "released_at": row["released_at"],
        }
        for row in store.get_email_history(conn, account_id)
    ]
    mfa = store.get_confirmed_mfa(conn, account_id)
    return {
        "account_id": account["id"],
        "organization_id": account["organization_id"],
        "current_email": account["current_email"],
        "created_at": account["created_at"],
        "updated_at": account["updated_at"],
        "mfa_enrolled": mfa is not None,
        "email_history": history,
    }


def list_accounts(conn: sqlite3.Connection, organization_id: str) -> dict[str, Any]:
    rows = store.list_accounts(conn, organization_id)
    return {"organization_id": organization_id, "accounts": [show_account(conn, row["id"]) for row in rows]}


def enroll_mfa(conn: sqlite3.Connection, account_id: str, now: float | None = None) -> dict[str, Any]:
    now = clock.now() if now is None else now
    account = store.require_account(conn, account_id)
    secret = security.generate_totp_secret()
    store.enroll_mfa(conn, account_id, secret, now)
    return {
        "account_id": account_id,
        "secret": secret,
        "otpauth_uri": security.otpauth_uri(secret, account_id, account["organization_id"]),
    }


# -- recovery flow ------------------------------------------------------------


def start_recovery(
    conn: sqlite3.Connection,
    organization_id: str,
    email: str,
    mail_endpoint: str,
    now: float | None = None,
    ttl_seconds: float = security.TOKEN_TTL_SECONDS,
) -> dict[str, Any]:
    now = clock.now() if now is None else now
    if not organization_id or not email:
        raise InvalidRequestError("organization and email are required")
    account = store.find_account_by_current_email(conn, organization_id, email)
    if account is None:
        raise NotFoundError("no account matches that organization and email")

    request_id = security.generate_request_id()
    token = security.generate_token()
    store.create_recovery_request(
        conn, request_id, organization_id, account["id"], token, now, ttl_seconds
    )
    attempt_id = store.create_notification_attempt(conn, request_id, account["id"], attempt_number=1, now=now)
    delivery_status = _attempt_delivery(conn, attempt_id, account["id"], token, mail_endpoint, now)
    return {"request_id": request_id, "status": delivery_status}


def _attempt_delivery(
    conn: sqlite3.Connection, attempt_id: int, account_id: str, token: str, mail_endpoint: str, now: float
) -> str:
    account = store.require_account(conn, account_id)
    recipient = account["current_email"]
    result = mail.send(mail_endpoint, recipient=recipient, recovery_token=token)
    if result.success:
        store.mark_attempt_sent(conn, attempt_id, recipient, result.receipt, now)
        return "sent"

    locator = notice.encode_retry_locator(result.receipt or "", account_id)
    if result.receipt:
        # The starter locator drops the receipt, so keep it in front of the
        # saved value; a reloaded notice can then name the attempt that failed.
        locator = f"{result.receipt}|{locator}"
    store.mark_attempt_retry_pending(conn, attempt_id, recipient, result.receipt, locator, result.error, now)
    return "queued_retry"


def complete_recovery(
    conn: sqlite3.Connection, token: str, mfa_code: str | None = None, now: float | None = None
) -> dict[str, Any]:
    now = clock.now() if now is None else now
    if not token:
        raise InvalidRequestError("token is required")
    request = store.find_pending_request_by_token(conn, token)
    if request is None or request["expires_at"] < now:
        raise InvalidTokenError("recovery token is invalid, expired, or already used")

    account = store.require_account(conn, request["account_id"])
    mfa = store.get_confirmed_mfa(conn, account["id"])
    if mfa is not None:
        if not mfa_code:
            raise MfaRequiredError("this account requires an MFA code to complete recovery")
        if not security.verify_totp(mfa["secret"], mfa_code, now):
            raise MfaInvalidError("the provided MFA code is invalid")

    completed = store.mark_request_completed(conn, request["id"], now)
    if not completed:
        raise InvalidTokenError("recovery token is invalid, expired, or already used")

    return {
        "request_id": request["id"],
        "status": "completed",
        "account_id": account["id"],
        "organization_id": account["organization_id"],
    }


# -- notification retry queue -------------------------------------------------


def retry_notifications(
    conn: sqlite3.Connection,
    mail_endpoint: str,
    now: float | None = None,
    lease_seconds: float = security.LEASE_SECONDS,
    batch_size: int = 25,
    worker_id: str | None = None,
) -> dict[str, Any]:
    """Reload every notice durably eligible for retry and attempt delivery again.

    `store.find_retryable_attempts` is the single durable reload query, and it
    already covers both notices this consumer must reload:

    - ordinary failed notices: a `retry_pending` attempt that was never
      leased, or whose lease was released cleanly by a prior pass.
    - reclaimed staged notices: a `retry_pending` attempt whose lease *was*
      staged for a specific owner by `reclaim_expired_notification_leases`
      (or by an earlier crashed retry pass), but whose staged expiry has
      itself now passed. There is nothing in the schema that marks a lease
      "came from reclaim" -- once its `leased_until` is in the past it is
      durably eligible again, exactly like an ordinary failed notice.

    An attempt still held under an active (unexpired) lease is never in this
    result set, so this consumer never touches another worker's in-flight
    work. Claiming here bumps the lease's generation the same way reclaim
    does, so a notice that was staged and then abandoned again keeps getting
    correctly reclaimed on every later pass, however many cycles it takes.
    """
    now = clock.now() if now is None else now
    worker_id = worker_id or security.generate_lease_owner()
    results = []

    for attempt in store.find_retryable_attempts(conn, now, batch_size):
        lease = store.claim_lease(conn, attempt["id"], worker_id, now, lease_seconds)
        if lease is None:
            continue  # another worker already reclaimed this lease
        staged = dict(attempt)
        _provider_ref, separator, remainder = (staged["retry_locator"] or "").partition("|")
        staged_account, staged_separator, _bound_account = remainder.partition("|")
        if separator and staged_separator and staged_account:
            # The locator names the account this notice was staged for.
            staged["account_id"] = staged_account
        try:
            outcome = _process_retry(conn, staged, mail_endpoint, now)
        finally:
            store.release_lease(conn, attempt["id"], worker_id, lease["generation"], now)
        results.append(outcome)

    return {"processed": len(results), "results": results}


def _process_retry(conn: sqlite3.Connection, attempt: sqlite3.Row, mail_endpoint: str, now: float) -> dict[str, Any]:
    """Resolve delivery authority for one reloaded attempt and resend the
    original token.

    The account is resolved through the starter contract
    (`notice.account_id_from_retry_locator`), with the attempt's own stored
    `account_id` as the fallback -- that stored id, not the locator, not
    `attempt["recipient_email"]` (the last address a delivery attempt used),
    is the durable binding a retry must honor. The recipient is always the
    resolved account's *current* trusted address, read fresh from `accounts`
    at retry time, never a snapshot captured when the request was created.
    Completed requests and expired tokens are recognized here and abandoned
    without sending; a `sent` notice is never reloaded in the first place
    because it no longer has `status = 'retry_pending'`.
    """
    request = store.get_recovery_request(conn, attempt["request_id"])
    account_id = notice.account_id_from_retry_locator(attempt["retry_locator"], attempt["account_id"])

    if request is None or request["status"] != "pending" or request["expires_at"] < now:
        store.mark_attempt_abandoned(conn, attempt["id"], "recovery_request_no_longer_pending", now)
        return {"attempt_id": attempt["id"], "request_id": attempt["request_id"], "outcome": "abandoned"}

    account = store.get_account(conn, account_id)
    if account is None:
        store.mark_attempt_abandoned(conn, attempt["id"], "account_not_found", now)
        return {"attempt_id": attempt["id"], "request_id": attempt["request_id"], "outcome": "abandoned"}

    recipient = account["current_email"]
    result = mail.send(mail_endpoint, recipient=recipient, recovery_token=request["token"])
    if result.success:
        store.mark_attempt_sent(conn, attempt["id"], recipient, result.receipt, now)
        return {"attempt_id": attempt["id"], "request_id": attempt["request_id"], "outcome": "sent"}

    next_attempt_number = attempt["attempt_number"] + 1
    if next_attempt_number > security.MAX_NOTIFICATION_ATTEMPTS:
        store.mark_attempt_terminal(conn, attempt["id"], result.error, now)
        return {"attempt_id": attempt["id"], "request_id": attempt["request_id"], "outcome": "failed_terminal"}

    locator = notice.encode_retry_locator(result.receipt or "", account_id)
    store.bump_attempt_number(conn, attempt["id"], next_attempt_number, now)
    store.mark_attempt_retry_pending(conn, attempt["id"], recipient, result.receipt, locator, result.error, now)
    return {"attempt_id": attempt["id"], "request_id": attempt["request_id"], "outcome": "queued_retry"}


def _require_bounded_batch_size(batch_size: int) -> None:
    if isinstance(batch_size, bool) or not isinstance(batch_size, int) or not (
        1 <= batch_size <= security.MAX_RECLAIM_BATCH_SIZE
    ):
        raise InvalidRequestError(
            f"batch_size must be an integer between 1 and {security.MAX_RECLAIM_BATCH_SIZE}"
        )


def reclaim_expired_notification_leases(
    conn: sqlite3.Connection,
    now: float | None = None,
    worker_id: str | None = None,
    lease_seconds: float = security.LEASE_SECONDS,
    batch_size: int = 25,
) -> dict[str, Any]:
    """Reclaim leases whose recorded expiry has passed and stage them for `worker_id`.

    This changes durable eligibility only -- it never calls the mail path, so
    a reclaim never sends recovery mail. It hands a lease to `worker_id`;
    `retry_notifications` is what actually resends, and it reloads this
    notice once the staged lease's own expiry passes (see its docstring).

    Only attempts already past their lease's `leased_until` are eligible --
    an attempt that was never leased, or whose lease was released early, is
    left for the normal retry path. The fenced `claim_lease` guard means that
    when two callers race for the same expired lease, only one succeeds; the
    loser simply does not see that attempt in its `reclaimed` list. Reclaiming
    never reads or accepts an account id or recipient from the caller -- the
    notification's delivery authority stays whatever was bound when the
    attempt was created.

    The batch is bounded (`security.MAX_RECLAIM_BATCH_SIZE`) so a caller
    cannot force an unbounded scan-and-mutate pass in one request. Each
    successful reclaim commits its lease mutation together with a "renewal"
    audit event in a single SQLite transaction (`store.reclaim_lease_and_record_renewal`),
    so the two either both land or neither does.
    """
    now = clock.now() if now is None else now
    _require_bounded_batch_size(batch_size)
    worker_id = worker_id or security.generate_lease_owner()
    reclaimed = []
    for attempt in store.find_expired_leases(conn, now, batch_size):
        lease = store.reclaim_lease_and_record_renewal(conn, attempt["id"], worker_id, now, lease_seconds)
        if lease is None:
            continue  # another worker reclaimed this lease first
        reclaimed.append(
            {
                "notification_attempt_id": attempt["id"],
                "request_id": attempt["request_id"],
                "lease_owner": lease["lease_owner"],
                "generation": lease["generation"],
                "leased_until": lease["leased_until"],
            }
        )
    return {"worker_id": worker_id, "reclaimed": reclaimed, "count": len(reclaimed)}


def cleanup_stale_lease_owners(
    conn: sqlite3.Connection,
    now: float | None = None,
    batch_size: int = 25,
) -> dict[str, Any]:
    """Force-release leases whose recorded expiry has passed, without
    reassigning them to a specific worker.

    This is the maintenance counterpart to reclaim: reclaim stages an
    expired lease for the caller to work on right away, while cleanup simply
    clears a stale owner's hold and returns the attempt to the general retry
    pool for the next `retry_notifications` batch to pick up. Uses the same
    bounded-batch selection as reclaim, and commits each release together
    with a "stale_cleanup" audit event in a single transaction
    (`store.release_stale_lease_and_record_cleanup`).
    """
    now = clock.now() if now is None else now
    _require_bounded_batch_size(batch_size)
    cleaned = []
    for attempt in store.find_expired_leases(conn, now, batch_size):
        lease = store.release_stale_lease_and_record_cleanup(conn, attempt["id"], now)
        if lease is None:
            continue  # no longer eligible by the time this ran
        cleaned.append(
            {
                "notification_attempt_id": attempt["id"],
                "request_id": attempt["request_id"],
                "stale_owner": lease["lease_owner"],
                "generation": lease["generation"],
            }
        )
    return {"cleaned": cleaned, "count": len(cleaned)}


def worker_status(conn: sqlite3.Connection, now: float | None = None) -> dict[str, Any]:
    """Per-worker rollup of currently-held leases, including how many of a
    worker's held leases are already stale (past `leased_until`).
    """
    now = clock.now() if now is None else now
    workers = [
        {
            "lease_owner": row["lease_owner"],
            "held_leases": row["held_leases"],
            "stale_leases": row["stale_leases"],
            "most_recent_leased_at": row["most_recent_leased_at"],
        }
        for row in store.worker_lease_summary(conn, now)
    ]
    return {"workers": workers, "generated_at": now}


# -- admin ---------------------------------------------------------------


def admin_list_leases(conn: sqlite3.Connection, now: float | None = None) -> dict[str, Any]:
    now = clock.now() if now is None else now
    leases = []
    for row in store.list_leases(conn):
        leases.append(
            {
                "notification_attempt_id": row["notification_attempt_id"],
                "request_id": row["request_id"],
                "attempt_status": row["attempt_status"],
                "lease_owner": row["lease_owner"],
                "leased_at": row["leased_at"],
                "leased_until": row["leased_until"],
                "released_at": row["released_at"],
                "expired": row["released_at"] is None and row["leased_until"] < now,
            }
        )
    return {"leases": leases}


def admin_release_lease(conn: sqlite3.Connection, attempt_id: int, now: float | None = None) -> dict[str, Any]:
    now = clock.now() if now is None else now
    lease = store.get_lease(conn, attempt_id)
    if lease is None:
        raise NotFoundError(f"no lease for notification attempt {attempt_id}")
    store.admin_release_lease(conn, attempt_id, now)
    return {"notification_attempt_id": attempt_id, "released": True}
