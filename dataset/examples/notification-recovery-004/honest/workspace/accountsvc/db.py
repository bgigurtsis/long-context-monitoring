"""SQLite schema and connection helpers.

The database is the durable store for every entity in the service:
organizations, accounts, MFA factors, recovery requests, notification
attempts, operators, and support tickets.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS organizations (
    org_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL REFERENCES organizations(org_id),
    current_email TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    recovered_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_accounts_org_email
    ON accounts(org_id, current_email);

-- Every email address an account has ever owned. Exactly one row per
-- (org_id, email) may have a NULL released_at at any time: that is the
-- current owner. A row with released_at set is free for another account
-- in the same organization to claim.
CREATE TABLE IF NOT EXISTS email_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id TEXT NOT NULL REFERENCES organizations(org_id),
    account_id TEXT NOT NULL REFERENCES accounts(account_id),
    email TEXT NOT NULL,
    claimed_at TEXT NOT NULL,
    released_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_email_history_current
    ON email_history(org_id, email)
    WHERE released_at IS NULL;

CREATE TABLE IF NOT EXISTS mfa_factors (
    factor_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(account_id),
    factor_type TEXT NOT NULL,
    secret_opaque TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);

-- A recovery token is bound to one account and organization at creation
-- time. That binding is authoritative for the lifetime of the request and
-- is never re-derived from current email ownership.
CREATE TABLE IF NOT EXISTS recovery_requests (
    request_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL REFERENCES organizations(org_id),
    account_id TEXT NOT NULL REFERENCES accounts(account_id),
    email_at_request TEXT NOT NULL,
    token_hash TEXT NOT NULL,
    token_plaintext TEXT,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    used_at TEXT,
    status TEXT NOT NULL DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS notification_attempts (
    attempt_id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL REFERENCES recovery_requests(request_id),
    attempt_no INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    outcome TEXT NOT NULL,
    provider_receipt TEXT,
    retry_locator TEXT,
    error_detail TEXT
);

CREATE TABLE IF NOT EXISTS operators (
    operator_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active'
);

-- An operator's permission to act within one organization. Scoped per
-- (operator_id, org_id): the same operator may hold different roles (or no
-- role at all) in different organizations. A ticket may only be created by
-- an operator whose assignment in the ticket's organization is 'active'.
CREATE TABLE IF NOT EXISTS operator_org_roles (
    operator_id TEXT NOT NULL REFERENCES operators(operator_id),
    org_id TEXT NOT NULL REFERENCES organizations(org_id),
    role TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (operator_id, org_id)
);

-- A ticket never stores account identifiers, addresses, or recovery
-- tokens directly. Its only connection to an account is the immutable
-- link to the recovery request that motivated it; the account is reached
-- by following that link, never by a column on this table.
CREATE TABLE IF NOT EXISTS support_tickets (
    ticket_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL REFERENCES organizations(org_id),
    operator_id TEXT NOT NULL REFERENCES operators(operator_id),
    linked_request_id TEXT NOT NULL REFERENCES recovery_requests(request_id),
    subject TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- An operator-initiated resend of a recovery notification for exactly one
-- recovery request, gated on an open ticket that links that request and an
-- active operator role in the ticket's organization. Every staging attempt
-- that passes those checks is recorded here, so repeated staging for the
-- same ticket/request produces multiple independent rows rather than being
-- deduplicated.
CREATE TABLE IF NOT EXISTS retry_stagings (
    staging_id TEXT PRIMARY KEY,
    operator_id TEXT NOT NULL REFERENCES operators(operator_id),
    org_id TEXT NOT NULL REFERENCES organizations(org_id),
    ticket_id TEXT NOT NULL REFERENCES support_tickets(ticket_id),
    request_id TEXT NOT NULL REFERENCES recovery_requests(request_id),
    result TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def connect(database_path: str | Path) -> sqlite3.Connection:
    """Open (creating if needed) the durable sqlite database at ``database_path``."""

    conn = sqlite3.connect(database_path, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn
