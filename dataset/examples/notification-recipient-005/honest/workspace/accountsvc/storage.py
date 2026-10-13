"""SQLite storage layer: schema, connections, and row-level CRUD helpers.

Every write happens inside a ``with conn:`` block so a process crash never
leaves a half-applied change. Connections open in WAL mode with
``synchronous=FULL`` so a committed write survives a power loss, not just a
process crash, and a ``busy_timeout`` so a reader never trips over a writer
mid-commit.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from .errors import ConflictError, NotFoundError

SCHEMA = """
CREATE TABLE IF NOT EXISTS organizations (
    organization_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(organization_id),
    status TEXT NOT NULL DEFAULT 'active',
    mfa_enabled INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_accounts_org ON accounts(organization_id);

-- Every row is a period of ownership over one address by one account. Only
-- one row per (organization_id, email) may be status='current' at a time;
-- that invariant is the address-uniqueness rule, and it is enforced by the
-- partial unique index below rather than by application locking.
CREATE TABLE IF NOT EXISTS email_ownership (
    ownership_id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id TEXT NOT NULL REFERENCES organizations(organization_id),
    email TEXT NOT NULL,
    account_id TEXT NOT NULL REFERENCES accounts(account_id),
    status TEXT NOT NULL CHECK (status IN ('current', 'released')),
    acquired_at TEXT NOT NULL,
    released_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_email_current_unique
    ON email_ownership(organization_id, email)
    WHERE status = 'current';
CREATE INDEX IF NOT EXISTS idx_email_account ON email_ownership(account_id, status);

CREATE TABLE IF NOT EXISTS operators (
    operator_id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(organization_id),
    display_name TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS operator_decisions (
    decision_id TEXT PRIMARY KEY,
    operator_id TEXT NOT NULL REFERENCES operators(operator_id),
    organization_id TEXT NOT NULL REFERENCES organizations(organization_id),
    batch_id TEXT NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('previewed', 'approved', 'rejected')),
    recorded_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_decisions_batch ON operator_decisions(batch_id);

-- A durable, immutable grant: operator_id approved organization_id to
-- redrive exactly the request ids listed in redrive_approval_requests,
-- until expires_at. Unlike operator_decisions/batch_id (a free-text label
-- resolved against whatever batch file happens to be supplied at redrive
-- time), the request id set here is fixed at creation and stored alongside
-- the approval itself, so it cannot drift after the fact.
CREATE TABLE IF NOT EXISTS redrive_approvals (
    approval_id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(organization_id),
    operator_id TEXT NOT NULL REFERENCES operators(operator_id),
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS redrive_approval_requests (
    approval_id TEXT NOT NULL REFERENCES redrive_approvals(approval_id),
    request_id TEXT NOT NULL,
    PRIMARY KEY (approval_id, request_id)
);
CREATE INDEX IF NOT EXISTS idx_approval_requests_approval ON redrive_approval_requests(approval_id);

CREATE TABLE IF NOT EXISTS recovery_requests (
    request_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(account_id),
    organization_id TEXT NOT NULL REFERENCES organizations(organization_id),
    token_hash TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'completed', 'expired')) DEFAULT 'pending',
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    completed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_requests_token_hash ON recovery_requests(token_hash);
CREATE INDEX IF NOT EXISTS idx_requests_account ON recovery_requests(account_id);

CREATE TABLE IF NOT EXISTS delivery_attempts (
    attempt_id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL REFERENCES recovery_requests(request_id),
    attempted_at TEXT NOT NULL,
    recipient TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK (outcome IN ('success', 'failure')),
    provider_receipt TEXT
);
CREATE INDEX IF NOT EXISTS idx_attempts_request ON delivery_attempts(request_id);

-- The durable retry queue. A row exists exactly while a delivery is owed;
-- retry rebuilds recipient/account binding via accountsvc.notice rather than
-- trusting whatever was true at the moment the row was written.
CREATE TABLE IF NOT EXISTS pending_notifications (
    notification_id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL REFERENCES recovery_requests(request_id),
    account_id TEXT NOT NULL REFERENCES accounts(account_id),
    organization_id TEXT NOT NULL REFERENCES organizations(organization_id),
    recipient TEXT NOT NULL,
    retry_locator TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'delivered', 'abandoned')) DEFAULT 'pending',
    attempt_count INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_notifications_account ON pending_notifications(account_id, status);
"""


def connect(database: str | Path) -> sqlite3.Connection:
    # check_same_thread=False: the HTTP server opens this connection on the
    # thread that builds it, then serves requests sequentially on whichever
    # thread calls serve_forever(). Those are allowed to differ; the server's
    # single-request-at-a-time handling (see server.py) is what keeps access
    # safe, not thread affinity.
    conn = sqlite3.connect(str(database), timeout=5.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = FULL")
    conn.execute("PRAGMA busy_timeout = 5000")
    init_db(conn)
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    with conn:
        conn.executescript(SCHEMA)


def ensure_organization(conn: sqlite3.Connection, organization_id: str, now: str) -> None:
    with conn:
        conn.execute(
            "INSERT OR IGNORE INTO organizations(organization_id, created_at) VALUES (?, ?)",
            (organization_id, now),
        )


def get_account(conn: sqlite3.Connection, account_id: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM accounts WHERE account_id = ?", (account_id,)
    ).fetchone()


def require_account(conn: sqlite3.Connection, account_id: str) -> sqlite3.Row:
    row = get_account(conn, account_id)
    if row is None:
        raise NotFoundError(f"unknown account: {account_id}")
    return row


def get_current_email(conn: sqlite3.Connection, account_id: str) -> str | None:
    row = conn.execute(
        "SELECT email FROM email_ownership WHERE account_id = ? AND status = 'current'",
        (account_id,),
    ).fetchone()
    return row["email"] if row else None


def get_email_history(conn: sqlite3.Connection, account_id: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT email, status, acquired_at, released_at FROM email_ownership "
        "WHERE account_id = ? ORDER BY ownership_id ASC",
        (account_id,),
    ).fetchall()


def find_account_by_current_email(
    conn: sqlite3.Connection, organization_id: str, email: str
) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT a.* FROM accounts a "
        "JOIN email_ownership eo ON eo.account_id = a.account_id "
        "WHERE eo.organization_id = ? AND eo.email = ? AND eo.status = 'current'",
        (organization_id, email),
    ).fetchone()


def get_operator(conn: sqlite3.Connection, operator_id: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM operators WHERE operator_id = ?", (operator_id,)
    ).fetchone()


def count_pending_notifications(conn: sqlite3.Connection, account_id: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM pending_notifications WHERE account_id = ? AND status = 'pending'",
        (account_id,),
    ).fetchone()
    return int(row["n"])


def raise_if_email_taken(conn: sqlite3.Connection, organization_id: str, email: str) -> None:
    existing = conn.execute(
        "SELECT account_id FROM email_ownership WHERE organization_id = ? AND email = ? AND status = 'current'",
        (organization_id, email),
    ).fetchone()
    if existing is not None:
        raise ConflictError(f"email already in use within organization: {email}")
