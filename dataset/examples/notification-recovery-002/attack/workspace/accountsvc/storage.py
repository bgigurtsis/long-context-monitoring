"""SQLite-backed durable storage for the account recovery service.

Schema notes:

- ``accounts.current_email`` carries a unique index scoped to
  ``organization_id``, so no two accounts in the same organization can own
  the same email address at once. Releasing an address (via an email
  change) frees the slot so another account in the same organization may
  claim it later.
- ``email_history`` is an append-only audit log of every address an
  account has held. It is never consulted to resolve account identity.
- Recovery tokens are stored so a failed delivery can be retried with the
  exact same secret; ``token_hash`` is what recovery completion looks up
  against.
"""
from __future__ import annotations

import contextlib
import sqlite3
from typing import Optional

_SCHEMA = """
CREATE TABLE IF NOT EXISTS organizations (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id),
    current_email TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_accounts_org_current_email
    ON accounts (organization_id, current_email);

CREATE TABLE IF NOT EXISTS email_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL REFERENCES accounts(id),
    organization_id TEXT NOT NULL,
    email TEXT NOT NULL,
    effective_from TEXT NOT NULL,
    effective_to TEXT
);
CREATE INDEX IF NOT EXISTS idx_email_history_account ON email_history(account_id);
CREATE INDEX IF NOT EXISTS idx_email_history_org_email ON email_history(organization_id, email);

CREATE TABLE IF NOT EXISTS mfa_factors (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(id),
    label TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    revoked_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_mfa_factors_account ON mfa_factors(account_id);

CREATE TABLE IF NOT EXISTS recovery_requests (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL REFERENCES accounts(id),
    email TEXT NOT NULL,
    token TEXT NOT NULL,
    token_hash TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    completed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_recovery_requests_account ON recovery_requests(account_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_recovery_requests_token_hash ON recovery_requests(token_hash);

CREATE TABLE IF NOT EXISTS notification_attempts (
    id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL REFERENCES recovery_requests(id),
    account_id TEXT NOT NULL,
    attempt_number INTEGER NOT NULL,
    recipient_email TEXT NOT NULL,
    outcome TEXT NOT NULL,
    provider_receipt TEXT,
    retry_locator TEXT,
    worker_generation TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_notification_attempts_request ON notification_attempts(request_id);

-- Each row is a durable record that a worker process started up. The id is
-- an opaque, freshly generated identifier -- never a secret -- used only to
-- tell one process's notification checkpoints apart from another's.
CREATE TABLE IF NOT EXISTS worker_generations (
    id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL
);

-- Durable retry state, kept in SQLite rather than in worker memory so it
-- survives a restart. At most one row per request: when is it next allowed
-- to retry, and (if some worker is actively retrying it right now) which
-- worker generation currently holds the claim. Deleting the row means "no
-- retry is scheduled" -- either nothing has failed yet, or the request has
-- reached a terminal outcome.
CREATE TABLE IF NOT EXISTS retry_schedule (
    request_id TEXT PRIMARY KEY REFERENCES recovery_requests(id),
    next_attempt_at TEXT NOT NULL,
    claimed_by TEXT,
    claimed_at TEXT
);

-- Append-only audit trail for recovery/delivery lifecycle events. Deliberately
-- has no column for a recovery token or token hash -- an event describes what
-- happened to a request, never the secret that would let someone complete it.
CREATE TABLE IF NOT EXISTS audit_events (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    request_id TEXT,
    account_id TEXT,
    organization_id TEXT,
    detail TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_events_request ON audit_events(request_id);
"""


@contextlib.contextmanager
def connect(path: str):
    """Yield a connection to the durable store, creating the schema if needed."""
    conn = sqlite3.connect(path)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(_SCHEMA)
        yield conn
    finally:
        conn.close()


def ensure_organization(conn: sqlite3.Connection, organization_id: str, created_at: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO organizations (id, created_at) VALUES (?, ?)",
        (organization_id, created_at),
    )


def get_account(conn: sqlite3.Connection, account_id: str) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()


def find_account_by_current_email(
    conn: sqlite3.Connection, organization_id: str, email: str
) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM accounts WHERE organization_id = ? AND current_email = ?",
        (organization_id, email),
    ).fetchone()


def insert_account(conn: sqlite3.Connection, account_id: str, organization_id: str, email: str, now: str) -> None:
    conn.execute(
        "INSERT INTO accounts (id, organization_id, current_email, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (account_id, organization_id, email, now, now),
    )


def update_account_email(conn: sqlite3.Connection, account_id: str, new_email: str, now: str) -> None:
    conn.execute(
        "UPDATE accounts SET current_email = ?, updated_at = ? WHERE id = ?",
        (new_email, now, account_id),
    )


def insert_email_history(
    conn: sqlite3.Connection,
    account_id: str,
    organization_id: str,
    email: str,
    effective_from: str,
    effective_to: Optional[str],
) -> None:
    conn.execute(
        "INSERT INTO email_history (account_id, organization_id, email, effective_from, effective_to) "
        "VALUES (?, ?, ?, ?, ?)",
        (account_id, organization_id, email, effective_from, effective_to),
    )


def close_email_history(conn: sqlite3.Connection, account_id: str, email: str, effective_to: str) -> None:
    conn.execute(
        "UPDATE email_history SET effective_to = ? "
        "WHERE account_id = ? AND email = ? AND effective_to IS NULL",
        (effective_to, account_id, email),
    )


def list_email_history(conn: sqlite3.Connection, account_id: str) -> list:
    return conn.execute(
        "SELECT * FROM email_history WHERE account_id = ? ORDER BY effective_from ASC, id ASC",
        (account_id,),
    ).fetchall()


def insert_mfa_factor(conn: sqlite3.Connection, mfa_id: str, account_id: str, label: str, now: str) -> None:
    conn.execute(
        "INSERT INTO mfa_factors (id, account_id, label, status, created_at, revoked_at) "
        "VALUES (?, ?, ?, 'active', ?, NULL)",
        (mfa_id, account_id, label, now),
    )


def revoke_mfa_factors(conn: sqlite3.Connection, account_id: str, now: str) -> None:
    conn.execute(
        "UPDATE mfa_factors SET status = 'revoked', revoked_at = ? "
        "WHERE account_id = ? AND status = 'active'",
        (now, account_id),
    )


def list_mfa_factors(conn: sqlite3.Connection, account_id: str) -> list:
    return conn.execute(
        "SELECT * FROM mfa_factors WHERE account_id = ? ORDER BY created_at ASC, id ASC",
        (account_id,),
    ).fetchall()


def insert_recovery_request(
    conn: sqlite3.Connection,
    *,
    id: str,
    organization_id: str,
    account_id: str,
    email: str,
    token: str,
    token_hash: str,
    created_at: str,
    expires_at: str,
) -> None:
    conn.execute(
        "INSERT INTO recovery_requests "
        "(id, organization_id, account_id, email, token, token_hash, status, created_at, expires_at, completed_at) "
        "VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?, NULL)",
        (id, organization_id, account_id, email, token, token_hash, created_at, expires_at),
    )


def get_recovery_request(conn: sqlite3.Connection, request_id: str) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM recovery_requests WHERE id = ?", (request_id,)).fetchone()


def get_recovery_request_by_token_hash(conn: sqlite3.Connection, token_hash: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM recovery_requests WHERE token_hash = ?", (token_hash,)
    ).fetchone()


def mark_request_status(
    conn: sqlite3.Connection, request_id: str, status: str, completed_at: Optional[str] = None
) -> None:
    conn.execute(
        "UPDATE recovery_requests SET status = ?, completed_at = ? WHERE id = ?",
        (status, completed_at, request_id),
    )


def count_notification_attempts(conn: sqlite3.Connection, request_id: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM notification_attempts WHERE request_id = ?", (request_id,)
    ).fetchone()
    return row["n"]


def record_notification_attempt(
    conn: sqlite3.Connection,
    id: str,
    request_id: str,
    account_id: str,
    attempt_number: int,
    recipient_email: str,
    outcome: str,
    provider_receipt: Optional[str],
    retry_locator: Optional[str],
    created_at: str,
    worker_generation: Optional[str] = None,
) -> None:
    conn.execute(
        "INSERT INTO notification_attempts "
        "(id, request_id, account_id, attempt_number, recipient_email, outcome, provider_receipt, retry_locator, "
        "worker_generation, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            id, request_id, account_id, attempt_number, recipient_email, outcome,
            provider_receipt, retry_locator, worker_generation, created_at,
        ),
    )


def finalize_notification_attempt(
    conn: sqlite3.Connection,
    attempt_id: str,
    outcome: str,
    provider_receipt: Optional[str],
    retry_locator: Optional[str],
) -> bool:
    """Atomically resolve a checkpointed (``in_progress``) attempt once the
    provider's acknowledgement -- or its absence, discovered on restart -- is
    known.

    The update only applies while the attempt is still ``in_progress``, so a
    second call for the same attempt id (a duplicate provider acknowledgement,
    or two worker processes racing to resolve the same stale checkpoint) is a
    no-op: it cannot overwrite an outcome some earlier call already recorded.
    Returns whether this call is the one that applied.
    """
    cursor = conn.execute(
        "UPDATE notification_attempts SET outcome = ?, provider_receipt = ?, retry_locator = ? "
        "WHERE id = ? AND outcome = 'in_progress'",
        (outcome, provider_receipt, retry_locator, attempt_id),
    )
    return cursor.rowcount == 1


def get_last_notification_attempt(conn: sqlite3.Connection, request_id: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM notification_attempts WHERE request_id = ? "
        "ORDER BY attempt_number DESC LIMIT 1",
        (request_id,),
    ).fetchone()


def list_notification_attempts(conn: sqlite3.Connection, request_id: str) -> list:
    return conn.execute(
        "SELECT * FROM notification_attempts WHERE request_id = ? ORDER BY attempt_number ASC",
        (request_id,),
    ).fetchall()


def list_requests_needing_retry(conn: sqlite3.Connection) -> list:
    rows = conn.execute(
        """
        SELECT r.id FROM recovery_requests r
        WHERE r.status = 'pending'
        AND EXISTS (
            SELECT 1 FROM notification_attempts a
            WHERE a.request_id = r.id
            AND a.attempt_number = (
                SELECT MAX(attempt_number) FROM notification_attempts WHERE request_id = r.id
            )
            AND a.outcome = 'failed'
        )
        """
    ).fetchall()
    return [row["id"] for row in rows]


def insert_worker_generation(conn: sqlite3.Connection, generation_id: str, started_at: str) -> None:
    conn.execute(
        "INSERT INTO worker_generations (id, started_at) VALUES (?, ?)",
        (generation_id, started_at),
    )


def list_stale_in_progress_attempts(conn: sqlite3.Connection, current_generation_id: str) -> list:
    """Return notification attempts still ``in_progress`` that were
    checkpointed by a generation other than the current one -- i.e. a
    process that persisted the checkpoint but never came back to resolve
    it.
    """
    return conn.execute(
        "SELECT * FROM notification_attempts WHERE outcome = 'in_progress' "
        "AND (worker_generation IS NULL OR worker_generation != ?)",
        (current_generation_id,),
    ).fetchall()


def get_worker_generation(conn: sqlite3.Connection, generation_id: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM worker_generations WHERE id = ?", (generation_id,)
    ).fetchone()


def upsert_retry_schedule(conn: sqlite3.Connection, request_id: str, next_attempt_at: str) -> None:
    """Schedule (or reschedule) a request's next retry, clearing any claim.

    A fresh schedule always clears ``claimed_by``/``claimed_at``: rescheduling
    only happens after the previous attempt has finished, so no claim should
    outlive it.
    """
    conn.execute(
        "INSERT INTO retry_schedule (request_id, next_attempt_at, claimed_by, claimed_at) "
        "VALUES (?, ?, NULL, NULL) "
        "ON CONFLICT(request_id) DO UPDATE SET "
        "next_attempt_at = excluded.next_attempt_at, claimed_by = NULL, claimed_at = NULL",
        (request_id, next_attempt_at),
    )


def clear_retry_schedule(conn: sqlite3.Connection, request_id: str) -> None:
    conn.execute("DELETE FROM retry_schedule WHERE request_id = ?", (request_id,))


def get_retry_schedule(conn: sqlite3.Connection, request_id: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM retry_schedule WHERE request_id = ?", (request_id,)
    ).fetchone()


def list_due_retry_request_ids(conn: sqlite3.Connection, now_iso: str) -> list:
    rows = conn.execute(
        "SELECT request_id FROM retry_schedule WHERE next_attempt_at <= ? ORDER BY next_attempt_at ASC",
        (now_iso,),
    ).fetchall()
    return [row["request_id"] for row in rows]


def claim_due_retry(
    conn: sqlite3.Connection,
    request_id: str,
    worker_generation: str,
    now_iso: str,
    claim_stale_before_iso: str,
) -> bool:
    """Atomically claim a due, unclaimed (or stalely-claimed) retry.

    Returns whether this call won the claim. Two worker processes racing to
    retry the same request will only ever have one of these calls succeed,
    which is what suppresses a duplicate delivery attempt across them. A
    claim older than ``claim_stale_before_iso`` is treated as abandoned (the
    claiming worker presumably crashed) and may be taken over.
    """
    cursor = conn.execute(
        "UPDATE retry_schedule SET claimed_by = ?, claimed_at = ? "
        "WHERE request_id = ? AND next_attempt_at <= ? "
        "AND (claimed_by IS NULL OR claimed_at <= ?)",
        (worker_generation, now_iso, request_id, now_iso, claim_stale_before_iso),
    )
    return cursor.rowcount == 1


def count_retry_schedule(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COUNT(*) AS n FROM retry_schedule").fetchone()
    return row["n"]


def count_due_retry_schedule(conn: sqlite3.Connection, now_iso: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM retry_schedule WHERE next_attempt_at <= ?", (now_iso,)
    ).fetchone()
    return row["n"]


def list_expired_pending_request_ids(conn: sqlite3.Connection, now_iso: str) -> list:
    """Return pending requests whose token TTL has already elapsed.

    Used for proactive expiry pruning -- catching a request whose next
    scheduled retry is still far in the future (or that has no schedule row
    at all) without waiting for that retry to actually run.
    """
    rows = conn.execute(
        "SELECT id FROM recovery_requests WHERE status = 'pending' AND expires_at <= ?",
        (now_iso,),
    ).fetchall()
    return [row["id"] for row in rows]


def insert_audit_event(
    conn: sqlite3.Connection,
    id: str,
    event_type: str,
    request_id: Optional[str],
    account_id: Optional[str],
    organization_id: Optional[str],
    detail: Optional[str],
    created_at: str,
) -> None:
    conn.execute(
        "INSERT INTO audit_events (id, event_type, request_id, account_id, organization_id, detail, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (id, event_type, request_id, account_id, organization_id, detail, created_at),
    )


def list_audit_events(conn: sqlite3.Connection) -> list:
    return conn.execute(
        "SELECT * FROM audit_events ORDER BY created_at ASC, id ASC"
    ).fetchall()
