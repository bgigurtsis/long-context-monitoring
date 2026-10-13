"""SQL-backed persistence for organizations, accounts, MFA, recovery
requests, notification attempts, and queue leases.

Every function takes an open connection explicitly rather than owning one,
so the HTTP layer can use a short-lived connection per request while the CLI
and tests can share a single connection.
"""
from __future__ import annotations

import sqlite3
from typing import Any

from . import clock
from .errors import ConflictError, NotFoundError

# -- organizations -----------------------------------------------------


def get_or_create_organization(conn: sqlite3.Connection, organization_id: str, now: float) -> None:
    conn.execute(
        "INSERT INTO organizations (id, created_at) VALUES (?, ?) "
        "ON CONFLICT(id) DO NOTHING",
        (organization_id, clock.iso(now)),
    )


# -- accounts ------------------------------------------------------------


def create_account(
    conn: sqlite3.Connection, account_id: str, organization_id: str, email: str, now: float
) -> None:
    ts = clock.iso(now)
    conn.execute("BEGIN IMMEDIATE")
    try:
        if conn.execute("SELECT 1 FROM accounts WHERE id = ?", (account_id,)).fetchone():
            raise ConflictError(f"account {account_id!r} already exists")
        if conn.execute(
            "SELECT 1 FROM accounts WHERE organization_id = ? AND current_email = ?",
            (organization_id, email),
        ).fetchone():
            raise ConflictError(f"email {email!r} is already in use in this organization")
        get_or_create_organization(conn, organization_id, now)
        conn.execute(
            "INSERT INTO accounts (id, organization_id, current_email, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (account_id, organization_id, email, ts, ts),
        )
        conn.execute(
            "INSERT INTO email_history (organization_id, account_id, email, effective_from, released_at) "
            "VALUES (?, ?, ?, ?, NULL)",
            (organization_id, account_id, email, ts),
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def get_account(conn: sqlite3.Connection, account_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()


def require_account(conn: sqlite3.Connection, account_id: str) -> sqlite3.Row:
    row = get_account(conn, account_id)
    if row is None:
        raise NotFoundError(f"account {account_id!r} not found")
    return row


def find_account_by_current_email(
    conn: sqlite3.Connection, organization_id: str, email: str
) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM accounts WHERE organization_id = ? AND current_email = ?",
        (organization_id, email),
    ).fetchone()


def list_accounts(conn: sqlite3.Connection, organization_id: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM accounts WHERE organization_id = ? ORDER BY id", (organization_id,)
    ).fetchall()


def change_email(conn: sqlite3.Connection, account_id: str, new_email: str, now: float) -> None:
    ts = clock.iso(now)
    conn.execute("BEGIN IMMEDIATE")
    try:
        account = conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
        if account is None:
            raise NotFoundError(f"account {account_id!r} not found")
        if account["current_email"] == new_email:
            conn.execute("COMMIT")
            return
        clash = conn.execute(
            "SELECT 1 FROM accounts WHERE organization_id = ? AND current_email = ? AND id != ?",
            (account["organization_id"], new_email, account_id),
        ).fetchone()
        if clash:
            raise ConflictError(f"email {new_email!r} is already in use in this organization")
        conn.execute(
            "UPDATE email_history SET released_at = ? "
            "WHERE account_id = ? AND email = ? AND released_at IS NULL",
            (ts, account_id, account["current_email"]),
        )
        conn.execute(
            "UPDATE accounts SET current_email = ?, updated_at = ? WHERE id = ?",
            (new_email, ts, account_id),
        )
        conn.execute(
            "INSERT INTO email_history (organization_id, account_id, email, effective_from, released_at) "
            "VALUES (?, ?, ?, ?, NULL)",
            (account["organization_id"], account_id, new_email, ts),
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def get_email_history(conn: sqlite3.Connection, account_id: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM email_history WHERE account_id = ? ORDER BY id", (account_id,)
    ).fetchall()


# -- MFA -------------------------------------------------------------------


def enroll_mfa(conn: sqlite3.Connection, account_id: str, secret: str, now: float, factor_type: str = "totp") -> None:
    ts = clock.iso(now)
    conn.execute(
        "INSERT INTO mfa_factors (account_id, factor_type, secret, created_at, confirmed_at) "
        "VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(account_id, factor_type) DO UPDATE SET secret = excluded.secret, "
        "created_at = excluded.created_at, confirmed_at = excluded.confirmed_at",
        (account_id, factor_type, secret, ts, ts),
    )


def get_confirmed_mfa(conn: sqlite3.Connection, account_id: str, factor_type: str = "totp") -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM mfa_factors WHERE account_id = ? AND factor_type = ? AND confirmed_at IS NOT NULL",
        (account_id, factor_type),
    ).fetchone()


# -- recovery requests -------------------------------------------------------


def create_recovery_request(
    conn: sqlite3.Connection,
    request_id: str,
    organization_id: str,
    account_id: str,
    token: str,
    now: float,
    ttl_seconds: float,
) -> None:
    conn.execute(
        "INSERT INTO recovery_requests "
        "(id, organization_id, account_id, token, status, created_at, expires_at, completed_at) "
        "VALUES (?, ?, ?, ?, 'pending', ?, ?, NULL)",
        (request_id, organization_id, account_id, token, clock.iso(now), now + ttl_seconds),
    )


def get_recovery_request(conn: sqlite3.Connection, request_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM recovery_requests WHERE id = ?", (request_id,)).fetchone()


def find_pending_request_by_token(conn: sqlite3.Connection, token: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM recovery_requests WHERE token = ? AND status = 'pending'", (token,)
    ).fetchone()


def mark_request_completed(conn: sqlite3.Connection, request_id: str, now: float) -> bool:
    cur = conn.execute(
        "UPDATE recovery_requests SET status = 'completed', completed_at = ? "
        "WHERE id = ? AND status = 'pending' AND expires_at >= ?",
        (clock.iso(now), request_id, now),
    )
    return cur.rowcount == 1


# -- notification attempts ---------------------------------------------------


def create_notification_attempt(
    conn: sqlite3.Connection,
    request_id: str,
    account_id: str,
    attempt_number: int,
    now: float,
) -> int:
    ts = clock.iso(now)
    cur = conn.execute(
        "INSERT INTO notification_attempts "
        "(request_id, account_id, attempt_number, status, recipient_email, provider_receipt, "
        " retry_locator, last_error, created_at, updated_at) "
        "VALUES (?, ?, ?, 'in_progress', NULL, NULL, NULL, NULL, ?, ?)",
        (request_id, account_id, attempt_number, ts, ts),
    )
    return cur.lastrowid


def mark_attempt_sent(conn: sqlite3.Connection, attempt_id: int, recipient: str, provider_receipt: str | None, now: float) -> None:
    conn.execute(
        "UPDATE notification_attempts SET status = 'sent', recipient_email = ?, "
        "provider_receipt = ?, last_error = NULL, updated_at = ? WHERE id = ?",
        (recipient, provider_receipt, clock.iso(now), attempt_id),
    )


def mark_attempt_retry_pending(
    conn: sqlite3.Connection,
    attempt_id: int,
    recipient: str,
    provider_receipt: str | None,
    retry_locator: str,
    error: str | None,
    now: float,
) -> None:
    conn.execute(
        "UPDATE notification_attempts SET status = 'retry_pending', recipient_email = ?, "
        "provider_receipt = ?, retry_locator = ?, last_error = ?, updated_at = ? WHERE id = ?",
        (recipient, provider_receipt, retry_locator, error, clock.iso(now), attempt_id),
    )


def mark_attempt_terminal(conn: sqlite3.Connection, attempt_id: int, error: str | None, now: float) -> None:
    conn.execute(
        "UPDATE notification_attempts SET status = 'failed_terminal', last_error = ?, updated_at = ? WHERE id = ?",
        (error, clock.iso(now), attempt_id),
    )


def mark_attempt_abandoned(conn: sqlite3.Connection, attempt_id: int, reason: str, now: float) -> None:
    conn.execute(
        "UPDATE notification_attempts SET status = 'abandoned', last_error = ?, updated_at = ? WHERE id = ?",
        (reason, clock.iso(now), attempt_id),
    )


def bump_attempt_number(conn: sqlite3.Connection, attempt_id: int, attempt_number: int, now: float) -> None:
    conn.execute(
        "UPDATE notification_attempts SET attempt_number = ?, updated_at = ? WHERE id = ?",
        (attempt_number, clock.iso(now), attempt_id),
    )


def get_notification_attempt(conn: sqlite3.Connection, attempt_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM notification_attempts WHERE id = ?", (attempt_id,)).fetchone()


def find_retryable_attempts(conn: sqlite3.Connection, now: float, limit: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT na.* FROM notification_attempts na "
        "LEFT JOIN queue_leases ql ON ql.notification_attempt_id = na.id "
        "WHERE na.status = 'retry_pending' "
        "AND (ql.id IS NULL OR ql.released_at IS NOT NULL OR ql.leased_until < ?) "
        "ORDER BY na.created_at LIMIT ?",
        (now, limit),
    ).fetchall()


def find_expired_leases(conn: sqlite3.Connection, now: float, limit: int) -> list[sqlite3.Row]:
    """Retryable attempts still held under a lease whose recorded expiry has passed.

    Unlike `find_retryable_attempts`, this excludes attempts that were never
    leased and leases that were already released early -- it only surfaces
    leases abandoned by a worker that stopped renewing before `leased_until`.
    """
    return conn.execute(
        "SELECT na.* FROM notification_attempts na "
        "JOIN queue_leases ql ON ql.notification_attempt_id = na.id "
        "WHERE na.status = 'retry_pending' "
        "AND ql.released_at IS NULL AND ql.leased_until < ? "
        "ORDER BY na.created_at LIMIT ?",
        (now, limit),
    ).fetchall()


# -- queue leases --------------------------------------------------------


def claim_lease(
    conn: sqlite3.Connection, attempt_id: int, owner: str, now: float, lease_seconds: float
) -> sqlite3.Row | None:
    """Claim an attempt's lease for `owner`, bumping its generation.

    Succeeds only if the lease is unheld (first claim), released, or expired,
    so an active lease can never move to a different owner out from under
    whoever currently holds it. The returned row's `generation` is the
    fencing token the caller must present to `renew_lease`/`release_lease`.
    """
    cur = conn.execute(
        "INSERT INTO queue_leases "
        "(notification_attempt_id, lease_owner, generation, leased_at, leased_until, released_at) "
        "VALUES (?, ?, 1, ?, ?, NULL) "
        "ON CONFLICT(notification_attempt_id) DO UPDATE SET "
        "lease_owner = excluded.lease_owner, "
        "generation = queue_leases.generation + 1, "
        "leased_at = excluded.leased_at, "
        "leased_until = excluded.leased_until, "
        "released_at = NULL "
        "WHERE queue_leases.released_at IS NOT NULL OR queue_leases.leased_until < ?",
        (attempt_id, owner, now, now + lease_seconds, now),
    )
    if cur.rowcount != 1:
        return None
    return get_lease(conn, attempt_id)


def renew_lease(
    conn: sqlite3.Connection,
    attempt_id: int,
    owner: str,
    generation: int,
    now: float,
    lease_seconds: float,
) -> sqlite3.Row | None:
    """Extend an unexpired lease still held by (owner, generation)."""
    cur = conn.execute(
        "UPDATE queue_leases SET leased_until = ? "
        "WHERE notification_attempt_id = ? AND lease_owner = ? AND generation = ? "
        "AND released_at IS NULL AND leased_until >= ?",
        (now + lease_seconds, attempt_id, owner, generation, now),
    )
    if cur.rowcount != 1:
        return None
    return get_lease(conn, attempt_id)


def release_lease(conn: sqlite3.Connection, attempt_id: int, owner: str, generation: int, now: float) -> bool:
    """Release a lease still held by (owner, generation)."""
    cur = conn.execute(
        "UPDATE queue_leases SET released_at = ? "
        "WHERE notification_attempt_id = ? AND lease_owner = ? AND generation = ? AND released_at IS NULL",
        (now, attempt_id, owner, generation),
    )
    return cur.rowcount == 1


def admin_release_lease(conn: sqlite3.Connection, attempt_id: int, now: float) -> bool:
    """Force-release a lease regardless of current owner/generation."""
    cur = conn.execute(
        "UPDATE queue_leases SET released_at = ? WHERE notification_attempt_id = ? AND released_at IS NULL",
        (now, attempt_id),
    )
    return cur.rowcount == 1


def get_lease(conn: sqlite3.Connection, attempt_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM queue_leases WHERE notification_attempt_id = ?", (attempt_id,)
    ).fetchone()


def list_leases(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT ql.*, na.status AS attempt_status, na.request_id AS request_id "
        "FROM queue_leases ql JOIN notification_attempts na ON na.id = ql.notification_attempt_id "
        "ORDER BY ql.id"
    ).fetchall()


def worker_lease_summary(conn: sqlite3.Connection, now: float) -> list[sqlite3.Row]:
    """Per-owner rollup of currently-held leases, for worker status reporting."""
    return conn.execute(
        "SELECT lease_owner, "
        "COUNT(*) AS held_leases, "
        "SUM(CASE WHEN leased_until < ? THEN 1 ELSE 0 END) AS stale_leases, "
        "MAX(leased_at) AS most_recent_leased_at "
        "FROM queue_leases WHERE released_at IS NULL "
        "GROUP BY lease_owner ORDER BY lease_owner",
        (now,),
    ).fetchall()


# -- lease audit log -------------------------------------------------------


def record_lease_audit_event(
    conn: sqlite3.Connection,
    attempt_id: int,
    event_type: str,
    lease_owner: str,
    generation: int,
    now: float,
    previous_owner: str | None = None,
) -> None:
    """Append a structured lease lifecycle event.

    Only the attempt id, the owners involved, the generation, and a
    timestamp are recorded. There is no free-text field, so a recovery
    token (or any other secret) can never be written into this table.
    """
    conn.execute(
        "INSERT INTO lease_audit_events "
        "(notification_attempt_id, event_type, previous_owner, lease_owner, generation, occurred_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (attempt_id, event_type, previous_owner, lease_owner, generation, now),
    )


def list_lease_audit_events(conn: sqlite3.Connection, attempt_id: int | None = None) -> list[sqlite3.Row]:
    if attempt_id is None:
        return conn.execute("SELECT * FROM lease_audit_events ORDER BY id").fetchall()
    return conn.execute(
        "SELECT * FROM lease_audit_events WHERE notification_attempt_id = ? ORDER BY id",
        (attempt_id,),
    ).fetchall()


def reclaim_lease_and_record_renewal(
    conn: sqlite3.Connection, attempt_id: int, owner: str, now: float, lease_seconds: float
) -> sqlite3.Row | None:
    """Claim an expired lease for `owner` and record the renewal audit event
    in one transaction, so the lease mutation and the notice's staging
    record either both land or neither does.

    Returns None (with nothing written) if the lease was no longer eligible
    for reclaim by the time this ran, e.g. another worker reclaimed it first.
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        previous = get_lease(conn, attempt_id)
        previous_owner = previous["lease_owner"] if previous is not None else None
        lease = claim_lease(conn, attempt_id, owner, now, lease_seconds)
        if lease is None:
            conn.execute("ROLLBACK")
            return None
        record_lease_audit_event(
            conn, attempt_id, "renewal", lease["lease_owner"], lease["generation"], now,
            previous_owner=previous_owner,
        )
        conn.execute("COMMIT")
        return lease
    except Exception:
        conn.execute("ROLLBACK")
        raise


def release_stale_lease_and_record_cleanup(
    conn: sqlite3.Connection, attempt_id: int, now: float
) -> sqlite3.Row | None:
    """Force-release a lease still held by a stale (expired) owner and record
    the cleanup audit event in one transaction.

    Unlike reclaim, this does not reassign the lease to a new owner -- it
    only clears the stale owner's hold so the attempt returns to the general
    retry pool. Re-checks that the lease is still expired under the write
    lock this transaction holds, so a lease renewed or reclaimed between
    selection and this call is left untouched.
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        lease = get_lease(conn, attempt_id)
        if lease is None or lease["released_at"] is not None or lease["leased_until"] >= now:
            conn.execute("ROLLBACK")
            return None
        released = admin_release_lease(conn, attempt_id, now)
        if not released:
            conn.execute("ROLLBACK")
            return None
        record_lease_audit_event(
            conn, attempt_id, "stale_cleanup", lease["lease_owner"], lease["generation"], now,
            previous_owner=None,
        )
        conn.execute("COMMIT")
        return lease
    except Exception:
        conn.execute("ROLLBACK")
        raise


def to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None
