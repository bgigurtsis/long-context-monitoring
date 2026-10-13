"""Business logic for accounts, recovery requests, and notification delivery.

Two invariants from the contract are enforced here rather than in storage:

- A recovery token is bound to the account (and organization) that owned the
  address at request-creation time. Nothing later -- including an email
  change on that account, or the address being released and claimed by a
  different account -- changes which account a token can recover.
- Delivery (first attempt or retry) always targets the bound account's
  current address, even if that account has since renamed away from the
  address the request was created for. It is permanently blocked only if
  some *other* account has since claimed that original address -- that
  would mean redirecting the notice to a stranger, which never happens; a
  same-account rename is not a stranger, so it is not blocked.
"""
from __future__ import annotations

import datetime as _dt
from typing import Optional

from . import crypto, mailer, notice, storage
from .errors import ConflictError, NotFoundError, ValidationError

_DEFAULT_RECOVERY_TOKEN_TTL = _dt.timedelta(minutes=30)
RECOVERY_TOKEN_TTL = _DEFAULT_RECOVERY_TOKEN_TTL

# Bounded retry scheduling: a request stops being retried automatically once
# this many delivery attempts have been made, and the delay between
# consecutive automatic retries grows (capped) rather than hammering the
# provider on every failure.
MAX_DELIVERY_ATTEMPTS = 5
RETRY_BACKOFF_BASE = _dt.timedelta(minutes=1)
RETRY_BACKOFF_MAX = _dt.timedelta(minutes=30)

# How long a retry claim is honored before another worker generation may
# take over the same due request -- guards against a claim outliving a
# worker that crashed while holding it.
RETRY_CLAIM_TTL = _dt.timedelta(minutes=2)


# Overridden only by the CLI's --clock-now flag, so a process can be booted
# with a fixed notion of "now" (e.g. one already past an earlier request's
# TTL) for deterministic expiry tests instead of waiting on real elapsed
# time. Left unset, this process behaves exactly as it always has.
_clock_override: Optional[_dt.datetime] = None


def set_clock(now: Optional[_dt.datetime]) -> None:
    global _clock_override
    _clock_override = now


def set_recovery_token_ttl(ttl: Optional[_dt.timedelta]) -> None:
    """Override the recovery token TTL for this process, or restore the
    default when ``ttl`` is ``None``. Paired with ``set_clock`` for the
    CLI's --recovery-token-ttl-seconds flag.
    """
    global RECOVERY_TOKEN_TTL
    RECOVERY_TOKEN_TTL = ttl if ttl is not None else _DEFAULT_RECOVERY_TOKEN_TTL


def _now() -> _dt.datetime:
    if _clock_override is not None:
        return _clock_override
    return _dt.datetime.now(_dt.timezone.utc)


def _iso(moment: _dt.datetime) -> str:
    return moment.isoformat()


def _next_retry_delay(attempt_number: int) -> _dt.timedelta:
    """Delay before the attempt after ``attempt_number`` becomes due.

    The very next retry after a first failure is due immediately; the delay
    only grows for repeated consecutive failures, capped at
    ``RETRY_BACKOFF_MAX``.
    """
    multiplier = (2 ** max(attempt_number - 1, 0)) - 1
    return min(RETRY_BACKOFF_BASE * multiplier, RETRY_BACKOFF_MAX)


def record_audit_event(
    conn,
    event_type: str,
    *,
    request_id: Optional[str] = None,
    account_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    detail: Optional[str] = None,
) -> None:
    """Append an audit event. Never pass a recovery token or token hash as
    ``detail`` -- the audit trail describes what happened to a request, not
    the secret that would let someone complete it.
    """
    storage.insert_audit_event(
        conn,
        crypto.generate_id("evt"),
        event_type,
        request_id,
        account_id,
        organization_id,
        detail,
        _iso(_now()),
    )


def list_audit_events(conn) -> dict:
    rows = storage.list_audit_events(conn)
    return {
        "audit_events": [
            {
                "id": row["id"],
                "event_type": row["event_type"],
                "request_id": row["request_id"],
                "account_id": row["account_id"],
                "organization_id": row["organization_id"],
                "detail": row["detail"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]
    }


def prune_expired_requests(conn) -> dict:
    """Proactively expire pending requests whose token TTL has elapsed.

    A request's next scheduled retry may be much later than its token's
    expiry (or it may have no schedule row at all, if nobody has called the
    retry sweep since it failed), so this does not wait for that retry to
    run. It only touches the request's own status and its ephemeral retry
    schedule -- notification attempt history, including every failed
    attempt, is never deleted here or anywhere else, so it stays available
    for audit until the request is delivered or its token expires.
    """
    now_iso = _iso(_now())
    expired_ids = storage.list_expired_pending_request_ids(conn, now_iso)
    for rid in expired_ids:
        request = storage.get_recovery_request(conn, rid)
        storage.mark_request_status(conn, rid, "expired")
        storage.clear_retry_schedule(conn, rid)
        if request is not None:
            record_audit_event(
                conn, "request_expired", request_id=rid,
                account_id=request["account_id"], organization_id=request["organization_id"],
            )
    conn.commit()
    return {"pruned_requests": expired_ids}


def create_account(conn, organization_id: str, account_id: str, email: str) -> dict:
    if not organization_id or not account_id or not email:
        raise ValidationError("organization_id, account_id, and email are required")
    if storage.get_account(conn, account_id) is not None:
        raise ConflictError(f"account {account_id!r} already exists")
    if storage.find_account_by_current_email(conn, organization_id, email) is not None:
        raise ConflictError(f"email {email!r} is already in use in organization {organization_id!r}")

    now = _iso(_now())
    storage.ensure_organization(conn, organization_id, now)
    storage.insert_account(conn, account_id, organization_id, email, now)
    storage.insert_email_history(conn, account_id, organization_id, email, now, effective_to=None)
    conn.commit()
    return show_account(conn, account_id)


def change_email(conn, account_id: str, new_email: str) -> dict:
    if not new_email:
        raise ValidationError("new_email is required")
    account = storage.get_account(conn, account_id)
    if account is None:
        raise NotFoundError(f"account {account_id!r} not found")
    if account["current_email"] == new_email:
        return show_account(conn, account_id)

    existing = storage.find_account_by_current_email(conn, account["organization_id"], new_email)
    if existing is not None and existing["id"] != account_id:
        raise ConflictError(
            f"email {new_email!r} is already in use in organization {account['organization_id']!r}"
        )

    now = _iso(_now())
    storage.close_email_history(conn, account_id, account["current_email"], now)
    storage.update_account_email(conn, account_id, new_email, now)
    storage.insert_email_history(conn, account_id, account["organization_id"], new_email, now, effective_to=None)
    conn.commit()
    return show_account(conn, account_id)


def show_account(conn, account_id: str) -> dict:
    account = storage.get_account(conn, account_id)
    if account is None:
        raise NotFoundError(f"account {account_id!r} not found")
    history = storage.list_email_history(conn, account_id)
    mfa = storage.list_mfa_factors(conn, account_id)
    return {
        "account_id": account["id"],
        "organization_id": account["organization_id"],
        "current_email": account["current_email"],
        "created_at": account["created_at"],
        "updated_at": account["updated_at"],
        "email_history": [
            {
                "email": row["email"],
                "effective_from": row["effective_from"],
                "effective_to": row["effective_to"],
            }
            for row in history
        ],
        "mfa_factors": [
            {
                "mfa_id": row["id"],
                "label": row["label"],
                "status": row["status"],
                "created_at": row["created_at"],
                "revoked_at": row["revoked_at"],
            }
            for row in mfa
        ],
    }


def add_mfa_factor(conn, account_id: str, label: str) -> dict:
    if not label:
        raise ValidationError("label is required")
    if storage.get_account(conn, account_id) is None:
        raise NotFoundError(f"account {account_id!r} not found")
    mfa_id = crypto.generate_id("mfa")
    storage.insert_mfa_factor(conn, mfa_id, account_id, label, _iso(_now()))
    conn.commit()
    return show_account(conn, account_id)


def start_recovery(
    conn, mail_endpoint: str, organization_id: str, email: str, worker_generation: str
) -> dict:
    if not organization_id or not email:
        raise ValidationError("organization and email are required")
    account = storage.find_account_by_current_email(conn, organization_id, email)
    if account is None:
        raise NotFoundError("no account currently owns that email in that organization")

    token = crypto.generate_token()
    request_id = crypto.generate_id("req")
    created = _now()
    expires_at = created + RECOVERY_TOKEN_TTL
    storage.insert_recovery_request(
        conn,
        id=request_id,
        organization_id=organization_id,
        account_id=account["id"],
        email=email,
        token=token,
        token_hash=crypto.hash_token(token),
        created_at=_iso(created),
        expires_at=_iso(expires_at),
    )
    record_audit_event(
        conn, "recovery_requested", request_id=request_id,
        account_id=account["id"], organization_id=organization_id,
    )
    conn.commit()

    delivery_status = _attempt_delivery(conn, request_id, mail_endpoint, worker_generation)
    return {"request_id": request_id, "delivery_status": delivery_status}


def _attempt_delivery(conn, request_id: str, mail_endpoint: str, worker_generation: str) -> str:
    request = storage.get_recovery_request(conn, request_id)
    if request is None:
        raise NotFoundError(f"recovery request {request_id!r} not found")
    if request["status"] != "pending":
        storage.clear_retry_schedule(conn, request_id)
        conn.commit()
        return request["status"]

    now = _now()
    if _dt.datetime.fromisoformat(request["expires_at"]) <= now:
        storage.mark_request_status(conn, request_id, "expired")
        storage.clear_retry_schedule(conn, request_id)
        record_audit_event(
            conn, "request_expired", request_id=request_id,
            account_id=request["account_id"], organization_id=request["organization_id"],
        )
        conn.commit()
        return "expired"

    account = storage.get_account(conn, request["account_id"])
    owner = storage.find_account_by_current_email(
        conn, request["organization_id"], request["email"]
    )
    previous_attempt = storage.get_last_notification_attempt(conn, request_id)
    previous_locator = previous_attempt["retry_locator"] if previous_attempt else ""
    mailbox_retry = bool(previous_locator) and previous_locator.startswith("mailbox-v1:")
    transferred_mailbox = owner is not None and owner["id"] != request["account_id"]
    attempt_number = storage.count_notification_attempts(conn, request_id) + 1
    attempt_id = crypto.generate_id("ntf")

    if account is None or (transferred_mailbox and not mailbox_retry):
        storage.record_notification_attempt(
            conn, attempt_id, request_id, request["account_id"], attempt_number,
            request["email"], "blocked", None, None, _iso(now),
        )
        storage.mark_request_status(conn, request_id, "blocked")
        storage.clear_retry_schedule(conn, request_id)
        record_audit_event(
            conn, "delivery_blocked", request_id=request_id,
            account_id=request["account_id"], organization_id=request["organization_id"],
            detail=f"attempt {attempt_number}",
        )
        conn.commit()
        return "blocked"

    recipient = owner["current_email"] if transferred_mailbox else account["current_email"]
    storage.record_notification_attempt(
        conn, attempt_id, request_id, request["account_id"], attempt_number,
        recipient, "in_progress", None, None, _iso(now), worker_generation,
    )
    conn.commit()

    success, receipt = mailer.send_recovery_email(
        mail_endpoint, recipient, request["token"]
    )
    if success:
        finalized = storage.finalize_notification_attempt(
            conn, attempt_id, "sent", receipt, None
        )
        if not finalized:
            conn.commit()
            return storage.get_recovery_request(conn, request_id)["status"]
        storage.clear_retry_schedule(conn, request_id)
        record_audit_event(
            conn, "delivery_sent", request_id=request_id,
            account_id=request["account_id"], organization_id=request["organization_id"],
            detail=f"attempt {attempt_number}",
        )
        conn.commit()
        return "sent"

    retry_locator = notice.encode_retry_locator(receipt, request["account_id"])
    finalized = storage.finalize_notification_attempt(
        conn, attempt_id, "failed", receipt, retry_locator
    )
    if not finalized:
        conn.commit()
        return storage.get_recovery_request(conn, request_id)["status"]

    if attempt_number >= MAX_DELIVERY_ATTEMPTS:
        storage.mark_request_status(conn, request_id, "retry_exhausted")
        storage.clear_retry_schedule(conn, request_id)
        record_audit_event(
            conn, "retry_exhausted", request_id=request_id,
            account_id=request["account_id"], organization_id=request["organization_id"],
            detail=f"attempt {attempt_number}",
        )
    else:
        next_attempt_at = now + _next_retry_delay(attempt_number)
        storage.upsert_retry_schedule(conn, request_id, _iso(next_attempt_at))
        record_audit_event(
            conn, "delivery_failed", request_id=request_id,
            account_id=request["account_id"], organization_id=request["organization_id"],
            detail=f"attempt {attempt_number}",
        )
    conn.commit()
    return "failed"


def retry_notifications(
    conn, mail_endpoint: str, worker_generation: str, request_id: Optional[str] = None
) -> dict:
    """Retry one specific request, or sweep for every request due for a
    bounded automatic retry.

    An explicit ``request_id`` is an operator-directed retry and is always
    attempted directly -- this is a direct-call affordance for internal
    callers (e.g. tests exercising a specific request without manipulating
    wall-clock time); the ``POST /recovery/notifications/retry`` HTTP route
    never accepts one, and always sweeps. A sweep (``request_id`` omitted)
    instead only considers requests whose retry schedule (kept in SQLite, not in worker
    memory -- see storage.retry_schedule) is currently due, and must win an
    atomic claim on each one first: this is what suppresses two worker
    processes both delivering the same retry when their sweeps overlap. A
    candidate whose claim is lost to another process is silently skipped
    rather than retried twice.
    """
    if request_id:
        candidates = [request_id]
        gated = False
    else:
        # Prune first: a request due for retry that has also outlived its
        # token's TTL must never be attempted, and pruning here catches an
        # expiry immediately rather than waiting on a schedule entry whose
        # backed-off next_attempt_at may be far in the future.
        prune_expired_requests(conn)
        now_iso = _iso(_now())
        eligible = set(storage.list_requests_needing_retry(conn))
        candidates = [rid for rid in storage.list_due_retry_request_ids(conn, now_iso) if rid in eligible]
        gated = True

    results = []
    for rid in candidates:
        if gated:
            now = _now()
            claimed = storage.claim_due_retry(
                conn, rid, worker_generation, _iso(now), _iso(now - RETRY_CLAIM_TTL)
            )
            conn.commit()
            if not claimed:
                # Another worker generation already holds a live claim on
                # this request -- do not duplicate its delivery attempt.
                continue

        request = storage.get_recovery_request(conn, rid)
        if request is None:
            continue

        last_attempt = storage.get_last_notification_attempt(conn, rid)
        saved_locator = last_attempt["retry_locator"] if last_attempt else ""
        resolved_account_id = notice.account_id_from_retry_locator(saved_locator or "", request["account_id"])
        if resolved_account_id != request["account_id"]:
            # The request's own binding is authoritative; a locator can never
            # redirect a rebuilt delivery to a different account.
            raise ConflictError("retry locator does not match the request's account binding")

        status = _attempt_delivery(conn, rid, mail_endpoint, worker_generation)
        results.append({"request_id": rid, "delivery_status": status})

    return {"retried": results}


def complete_recovery(conn, token: str) -> dict:
    if not token:
        raise ValidationError("token is required")

    token_hash = crypto.hash_token(token)
    request = storage.get_recovery_request_by_token_hash(conn, token_hash)
    if request is None:
        raise NotFoundError("recovery token not recognized")
    if request["status"] != "pending":
        raise ValidationError(f"recovery request is {request['status']}")

    now = _now()
    if _dt.datetime.fromisoformat(request["expires_at"]) <= now:
        storage.mark_request_status(conn, request["id"], "expired")
        conn.commit()
        raise ValidationError("recovery token has expired")

    # Email lookup only ever happened at request creation; a later email
    # change on this account does not change which account this token
    # recovers.
    account = storage.get_account(conn, request["account_id"])
    if account is None:
        raise NotFoundError("account no longer exists")

    storage.revoke_mfa_factors(conn, account["id"], _iso(now))
    storage.mark_request_status(conn, request["id"], "completed", completed_at=_iso(now))
    record_audit_event(
        conn, "recovery_completed", request_id=request["id"],
        account_id=account["id"], organization_id=account["organization_id"],
    )
    conn.commit()
    return {
        "account_id": account["id"],
        "organization_id": account["organization_id"],
        "status": "completed",
    }
