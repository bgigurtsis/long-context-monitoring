"""SQLite schema and connection helper for the account recovery service."""
from __future__ import annotations

import sqlite3

SCHEMA = """
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
CREATE UNIQUE INDEX IF NOT EXISTS ux_accounts_org_email
    ON accounts(organization_id, current_email);

CREATE TABLE IF NOT EXISTS email_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL REFERENCES accounts(id),
    email TEXT NOT NULL,
    effective_from TEXT NOT NULL,
    released_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_email_history_account ON email_history(account_id);
CREATE INDEX IF NOT EXISTS ix_email_history_org_email ON email_history(organization_id, email);

CREATE TABLE IF NOT EXISTS mfa_factors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL REFERENCES accounts(id),
    factor_type TEXT NOT NULL,
    secret TEXT NOT NULL,
    created_at TEXT NOT NULL,
    confirmed_at TEXT,
    UNIQUE(account_id, factor_type)
);

-- token is stored durably (not hashed) because a failed delivery must be
-- retried with the identical secret link; the service is loopback-only and
-- the token is never echoed back through any API response.
CREATE TABLE IF NOT EXISTS recovery_requests (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL REFERENCES accounts(id),
    token TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at REAL NOT NULL,
    completed_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_recovery_requests_account ON recovery_requests(account_id);
CREATE UNIQUE INDEX IF NOT EXISTS ux_recovery_requests_token ON recovery_requests(token);

CREATE TABLE IF NOT EXISTS notification_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL REFERENCES recovery_requests(id),
    account_id TEXT NOT NULL,
    attempt_number INTEGER NOT NULL,
    status TEXT NOT NULL,
    recipient_email TEXT,
    provider_receipt TEXT,
    retry_locator TEXT,
    last_error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_notification_attempts_request ON notification_attempts(request_id);
CREATE INDEX IF NOT EXISTS ix_notification_attempts_status ON notification_attempts(status);

CREATE TABLE IF NOT EXISTS queue_leases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notification_attempt_id INTEGER NOT NULL UNIQUE REFERENCES notification_attempts(id),
    lease_owner TEXT NOT NULL,
    generation INTEGER NOT NULL,
    leased_at REAL NOT NULL,
    leased_until REAL NOT NULL,
    released_at REAL
);

-- Structured lease lifecycle log: which owner a lease moved to or from, at
-- which generation, and when. Deliberately has no free-text column, so a
-- recovery token (or anything else secret) can never end up in an audit row.
CREATE TABLE IF NOT EXISTS lease_audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notification_attempt_id INTEGER NOT NULL REFERENCES notification_attempts(id),
    event_type TEXT NOT NULL,
    previous_owner TEXT,
    lease_owner TEXT NOT NULL,
    generation INTEGER NOT NULL,
    occurred_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_lease_audit_events_attempt ON lease_audit_events(notification_attempt_id);
CREATE INDEX IF NOT EXISTS ix_lease_audit_events_owner ON lease_audit_events(lease_owner);
"""


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
    if path != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL")
    init_schema(conn)
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
