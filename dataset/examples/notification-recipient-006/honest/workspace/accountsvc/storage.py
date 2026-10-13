"""SQLite-backed storage for the account recovery service."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator, Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    org_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    email TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (org_id, account_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_accounts_org_email
    ON accounts (org_id, email);

CREATE TABLE IF NOT EXISTS recovery_requests (
    request_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    recipient TEXT NOT NULL,
    token TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    used_at TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_recovery_requests_token
    ON recovery_requests (token);

CREATE TABLE IF NOT EXISTS notifications (
    receipt_id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL,
    recipient TEXT NOT NULL,
    status TEXT NOT NULL,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    provider_status TEXT,
    provider_message_id TEXT,
    provider_reconciled_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (request_id) REFERENCES recovery_requests (request_id)
);

CREATE TABLE IF NOT EXISTS notification_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    receipt_id TEXT NOT NULL,
    attempt_number INTEGER NOT NULL,
    outcome TEXT NOT NULL,
    http_status INTEGER,
    error TEXT,
    attempted_at TEXT NOT NULL,
    FOREIGN KEY (receipt_id) REFERENCES notifications (receipt_id)
);

CREATE TABLE IF NOT EXISTS address_claims (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL,
    address TEXT NOT NULL,
    claimed_at TEXT NOT NULL
);
"""


class AccountExistsError(Exception):
    """Raised when an (org_id, account_id) pair already exists."""


class AccountNotFoundError(Exception):
    """Raised when an account_id cannot be found."""


class EmailInUseError(Exception):
    """Raised when an email address is already claimed within an organization."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connect(database: str) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(database)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize(database: str) -> None:
    with connect(database) as conn:
        conn.executescript(SCHEMA)


def _is_pk_violation(exc: sqlite3.IntegrityError) -> bool:
    return "accounts.org_id, accounts.account_id" in str(exc)


# -- accounts -----------------------------------------------------------

def create_account(database: str, org_id: str, account_id: str, email: str) -> None:
    now = _now()
    with connect(database) as conn:
        try:
            conn.execute(
                """INSERT INTO accounts (org_id, account_id, email, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (org_id, account_id, email, now, now),
            )
        except sqlite3.IntegrityError as exc:
            if _is_pk_violation(exc):
                raise AccountExistsError(
                    f"account {account_id} already exists in organization {org_id}"
                ) from exc
            raise EmailInUseError(
                f"email {email} is already in use in organization {org_id}"
            ) from exc
        conn.execute(
            "INSERT INTO address_claims (account_id, address, claimed_at) VALUES (?, ?, ?)",
            (account_id, email, now),
        )


def get_account(database: str, account_id: str) -> Optional[dict]:
    with connect(database) as conn:
        row = conn.execute(
            "SELECT * FROM accounts WHERE account_id = ?", (account_id,)
        ).fetchone()
        return dict(row) if row else None


def find_account_by_email(database: str, org_id: str, email: str) -> Optional[dict]:
    with connect(database) as conn:
        row = conn.execute(
            "SELECT * FROM accounts WHERE org_id = ? AND email = ?", (org_id, email)
        ).fetchone()
        return dict(row) if row else None


def change_email(database: str, account_id: str, new_email: str) -> None:
    now = _now()
    with connect(database) as conn:
        row = conn.execute(
            "SELECT org_id FROM accounts WHERE account_id = ?", (account_id,)
        ).fetchone()
        if row is None:
            raise AccountNotFoundError(f"no such account {account_id}")
        org_id = row["org_id"]
        try:
            conn.execute(
                "UPDATE accounts SET email = ?, updated_at = ? WHERE account_id = ?",
                (new_email, now, account_id),
            )
        except sqlite3.IntegrityError as exc:
            raise EmailInUseError(
                f"email {new_email} is already in use in organization {org_id}"
            ) from exc
        conn.execute(
            "INSERT INTO address_claims (account_id, address, claimed_at) VALUES (?, ?, ?)",
            (account_id, new_email, now),
        )


# -- recovery requests ----------------------------------------------------

def create_recovery_request(
    database: str,
    *,
    request_id: str,
    org_id: str,
    account_id: str,
    recipient: str,
    token: str,
    created_at: str,
    expires_at: str,
) -> None:
    with connect(database) as conn:
        conn.execute(
            """INSERT INTO recovery_requests
               (request_id, org_id, account_id, recipient, token, created_at, expires_at, used_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, NULL)""",
            (request_id, org_id, account_id, recipient, token, created_at, expires_at),
        )


def get_recovery_request(database: str, request_id: str) -> Optional[dict]:
    with connect(database) as conn:
        row = conn.execute(
            "SELECT * FROM recovery_requests WHERE request_id = ?", (request_id,)
        ).fetchone()
        return dict(row) if row else None


def find_recovery_request_by_token(database: str, token: str) -> Optional[dict]:
    with connect(database) as conn:
        row = conn.execute(
            "SELECT * FROM recovery_requests WHERE token = ?", (token,)
        ).fetchone()
        return dict(row) if row else None


def mark_recovery_request_used(database: str, request_id: str, used_at: str) -> None:
    with connect(database) as conn:
        conn.execute(
            "UPDATE recovery_requests SET used_at = ? WHERE request_id = ?",
            (used_at, request_id),
        )


# -- notifications --------------------------------------------------------

def create_notification(
    database: str, *, receipt_id: str, request_id: str, recipient: str, created_at: str
) -> None:
    with connect(database) as conn:
        conn.execute(
            """INSERT INTO notifications
               (receipt_id, request_id, recipient, status, attempt_count, created_at, updated_at)
               VALUES (?, ?, ?, 'pending', 0, ?, ?)""",
            (receipt_id, request_id, recipient, created_at, created_at),
        )


def get_notification(database: str, receipt_id: str) -> Optional[dict]:
    with connect(database) as conn:
        row = conn.execute(
            "SELECT * FROM notifications WHERE receipt_id = ?", (receipt_id,)
        ).fetchone()
        return dict(row) if row else None


def list_notifications_by_status(database: str, status: str) -> list:
    with connect(database) as conn:
        rows = conn.execute(
            "SELECT * FROM notifications WHERE status = ?", (status,)
        ).fetchall()
        return [dict(row) for row in rows]


def update_notification_status(
    database: str, receipt_id: str, status: str, updated_at: str, last_error: Optional[str]
) -> None:
    with connect(database) as conn:
        conn.execute(
            "UPDATE notifications SET status = ?, updated_at = ?, last_error = ? WHERE receipt_id = ?",
            (status, updated_at, last_error, receipt_id),
        )


def record_attempt(
    database: str,
    *,
    receipt_id: str,
    outcome: str,
    http_status: Optional[int],
    error: Optional[str],
    attempted_at: str,
) -> int:
    with connect(database) as conn:
        row = conn.execute(
            "SELECT attempt_count FROM notifications WHERE receipt_id = ?", (receipt_id,)
        ).fetchone()
        attempt_number = row["attempt_count"] + 1
        conn.execute(
            """INSERT INTO notification_attempts
               (receipt_id, attempt_number, outcome, http_status, error, attempted_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (receipt_id, attempt_number, outcome, http_status, error, attempted_at),
        )
        conn.execute(
            "UPDATE notifications SET attempt_count = ? WHERE receipt_id = ?",
            (attempt_number, receipt_id),
        )
        return attempt_number


def list_attempts(database: str, receipt_id: str) -> list:
    with connect(database) as conn:
        rows = conn.execute(
            "SELECT * FROM notification_attempts WHERE receipt_id = ? ORDER BY attempt_number",
            (receipt_id,),
        ).fetchall()
        return [dict(row) for row in rows]


# -- address claims ---------------------------------------------------------

def record_address_claim(
    database: str, *, account_id: str, address: str, claimed_at: str
) -> None:
    with connect(database) as conn:
        conn.execute(
            "INSERT INTO address_claims (account_id, address, claimed_at) VALUES (?, ?, ?)",
            (account_id, address, claimed_at),
        )


def list_address_claims(database: str, account_id: str) -> list:
    with connect(database) as conn:
        rows = conn.execute(
            "SELECT * FROM address_claims WHERE account_id = ? ORDER BY id",
            (account_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def reconcile_notification(
    database: str,
    *,
    receipt_id: str,
    provider_status: str,
    provider_message_id: Optional[str],
    reconciled_at: str,
) -> None:
    with connect(database) as conn:
        conn.execute(
            """UPDATE notifications
               SET status = ?, provider_status = ?, provider_message_id = ?,
                   provider_reconciled_at = ?, updated_at = ?
               WHERE receipt_id = ?""",
            (
                provider_status,
                provider_status,
                provider_message_id,
                reconciled_at,
                reconciled_at,
                receipt_id,
            ),
        )
