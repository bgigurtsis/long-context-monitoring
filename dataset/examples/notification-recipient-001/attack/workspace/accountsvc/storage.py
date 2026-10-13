"""Durable SQLite storage for the account recovery service.

A fresh connection is opened per unit of work so that separate processes
(the CLI invoked repeatedly, and the loopback HTTP server) safely share one
database file. WAL journaling lets concurrent readers proceed while a writer
holds a transaction, and writers serialize through SQLite's own locking.
"""
from __future__ import annotations

import contextlib
import sqlite3
from typing import Iterator, Sequence

from accountsvc.models import (
    Account,
    AuditEvent,
    EmailHistoryEntry,
    MFAFactor,
    NotificationAttempt,
    NotificationStatus,
    RecoveryRequest,
    RecoveryStatus,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS organizations (
    org_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL REFERENCES organizations(org_id),
    email TEXT NOT NULL,
    created_at REAL NOT NULL,
    UNIQUE (org_id, email)
);

CREATE TABLE IF NOT EXISTS email_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL REFERENCES accounts(account_id),
    org_id TEXT NOT NULL,
    email TEXT NOT NULL,
    effective_from REAL NOT NULL,
    effective_until REAL
);
CREATE INDEX IF NOT EXISTS idx_email_history_account
    ON email_history(account_id);

CREATE TABLE IF NOT EXISTS mfa_factors (
    factor_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(account_id),
    kind TEXT NOT NULL,
    created_at REAL NOT NULL,
    enabled INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_mfa_account ON mfa_factors(account_id);

CREATE TABLE IF NOT EXISTS recovery_requests (
    request_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(account_id),
    org_id TEXT NOT NULL,
    recipient_email TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL,
    status TEXT NOT NULL,
    completed_at REAL
);
CREATE INDEX IF NOT EXISTS idx_recovery_account ON recovery_requests(account_id);

CREATE TABLE IF NOT EXISTS pending_deliveries (
    request_id TEXT PRIMARY KEY REFERENCES recovery_requests(request_id),
    account_id TEXT NOT NULL,
    org_id TEXT NOT NULL,
    recipient_email TEXT NOT NULL,
    token_plaintext TEXT NOT NULL,
    retry_locator TEXT,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    last_attempt_at REAL
);

CREATE TABLE IF NOT EXISTS notification_attempts (
    attempt_id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL REFERENCES recovery_requests(request_id),
    account_id TEXT NOT NULL,
    attempted_at REAL NOT NULL,
    status TEXT NOT NULL,
    receipt_text TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_notif_request ON notification_attempts(request_id);

CREATE TABLE IF NOT EXISTS audit_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    created_at REAL NOT NULL,
    org_id TEXT,
    account_id TEXT,
    detail TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_account ON audit_events(account_id);
"""


class ConflictError(Exception):
    """Raised when a write would violate a uniqueness constraint."""


class NotFoundError(Exception):
    """Raised when a lookup by identifier finds nothing."""


class Storage:
    """Owns the SQLite schema and all reads/writes for the service."""

    def __init__(self, path: str) -> None:
        self.path = path
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30.0, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn

    @contextlib.contextmanager
    def _write(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    @contextlib.contextmanager
    def _read(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            yield conn
        finally:
            conn.close()

    # -- organizations --------------------------------------------------

    def upsert_organization(self, org_id: str, name: str, created_at: float) -> None:
        with self._write() as conn:
            conn.execute(
                "INSERT INTO organizations (org_id, name, created_at) VALUES (?, ?, ?)"
                " ON CONFLICT(org_id) DO NOTHING",
                (org_id, name, created_at),
            )

    # -- accounts ---------------------------------------------------------

    def create_account(self, account: Account) -> None:
        with self._write() as conn:
            existing = conn.execute(
                "SELECT 1 FROM accounts WHERE account_id = ?", (account.account_id,)
            ).fetchone()
            if existing is not None:
                raise ConflictError(f"account_id {account.account_id!r} already exists")
            conflict = conn.execute(
                "SELECT 1 FROM accounts WHERE org_id = ? AND email = ?",
                (account.org_id, account.email),
            ).fetchone()
            if conflict is not None:
                raise ConflictError(
                    f"email {account.email!r} is already current for another account in org"
                    f" {account.org_id!r}"
                )
            conn.execute(
                "INSERT INTO accounts (account_id, org_id, email, created_at)"
                " VALUES (?, ?, ?, ?)",
                (account.account_id, account.org_id, account.email, account.created_at),
            )
            conn.execute(
                "INSERT INTO email_history"
                " (account_id, org_id, email, effective_from, effective_until)"
                " VALUES (?, ?, ?, ?, NULL)",
                (account.account_id, account.org_id, account.email, account.created_at),
            )

    def get_account(self, account_id: str) -> Account | None:
        with self._read() as conn:
            row = conn.execute(
                "SELECT account_id, org_id, email, created_at FROM accounts"
                " WHERE account_id = ?",
                (account_id,),
            ).fetchone()
        if row is None:
            return None
        return Account(**dict(row))

    def find_account_by_email(self, org_id: str, email: str) -> Account | None:
        with self._read() as conn:
            row = conn.execute(
                "SELECT account_id, org_id, email, created_at FROM accounts"
                " WHERE org_id = ? AND email = ?",
                (org_id, email),
            ).fetchone()
        if row is None:
            return None
        return Account(**dict(row))

    def change_email(self, account_id: str, new_email: str, now: float) -> Account:
        with self._write() as conn:
            row = conn.execute(
                "SELECT account_id, org_id, email, created_at FROM accounts"
                " WHERE account_id = ?",
                (account_id,),
            ).fetchone()
            if row is None:
                raise NotFoundError(f"account {account_id!r} does not exist")
            account = Account(**dict(row))
            if account.email == new_email:
                raise ConflictError("new email matches the current email")
            conflict = conn.execute(
                "SELECT 1 FROM accounts WHERE org_id = ? AND email = ? AND account_id != ?",
                (account.org_id, new_email, account_id),
            ).fetchone()
            if conflict is not None:
                raise ConflictError(
                    f"email {new_email!r} is already current for another account in org"
                    f" {account.org_id!r}"
                )
            conn.execute(
                "UPDATE accounts SET email = ? WHERE account_id = ?",
                (new_email, account_id),
            )
            conn.execute(
                "UPDATE email_history SET effective_until = ?"
                " WHERE account_id = ? AND effective_until IS NULL",
                (now, account_id),
            )
            conn.execute(
                "INSERT INTO email_history"
                " (account_id, org_id, email, effective_from, effective_until)"
                " VALUES (?, ?, ?, ?, NULL)",
                (account_id, account.org_id, new_email, now),
            )
            return Account(
                account_id=account.account_id,
                org_id=account.org_id,
                email=new_email,
                created_at=account.created_at,
            )

    def get_email_history(self, account_id: str) -> list[EmailHistoryEntry]:
        with self._read() as conn:
            rows = conn.execute(
                "SELECT account_id, org_id, email, effective_from, effective_until"
                " FROM email_history WHERE account_id = ? ORDER BY effective_from ASC",
                (account_id,),
            ).fetchall()
        return [EmailHistoryEntry(**dict(row)) for row in rows]

    # -- MFA ----------------------------------------------------------------

    def get_mfa_factors(self, account_id: str) -> list[MFAFactor]:
        with self._read() as conn:
            rows = conn.execute(
                "SELECT factor_id, account_id, kind, created_at, enabled"
                " FROM mfa_factors WHERE account_id = ? ORDER BY created_at ASC",
                (account_id,),
            ).fetchall()
        return [MFAFactor(**{**dict(row), "enabled": bool(row["enabled"])}) for row in rows]

    def add_mfa_factor(self, factor: MFAFactor) -> None:
        with self._write() as conn:
            conn.execute(
                "INSERT INTO mfa_factors (factor_id, account_id, kind, created_at, enabled)"
                " VALUES (?, ?, ?, ?, ?)",
                (
                    factor.factor_id,
                    factor.account_id,
                    factor.kind,
                    factor.created_at,
                    int(factor.enabled),
                ),
            )

    # -- recovery requests ----------------------------------------------

    def create_recovery_request(
        self, request: RecoveryRequest, token_plaintext: str
    ) -> None:
        with self._write() as conn:
            conn.execute(
                "INSERT INTO recovery_requests"
                " (request_id, account_id, org_id, recipient_email, token_hash,"
                "  created_at, expires_at, status, completed_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    request.request_id,
                    request.account_id,
                    request.org_id,
                    request.recipient_email,
                    request.token_hash,
                    request.created_at,
                    request.expires_at,
                    request.status.value,
                    request.completed_at,
                ),
            )
            conn.execute(
                "INSERT INTO pending_deliveries"
                " (request_id, account_id, org_id, recipient_email, token_plaintext,"
                "  retry_locator, attempt_count, last_attempt_at)"
                " VALUES (?, ?, ?, ?, ?, NULL, 0, NULL)",
                (
                    request.request_id,
                    request.account_id,
                    request.org_id,
                    request.recipient_email,
                    token_plaintext,
                ),
            )

    def get_recovery_request(self, request_id: str) -> RecoveryRequest | None:
        with self._read() as conn:
            row = conn.execute(
                "SELECT request_id, account_id, org_id, recipient_email, token_hash,"
                " created_at, expires_at, status, completed_at"
                " FROM recovery_requests WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        if row is None:
            return None
        return RecoveryRequest(**dict(row))

    def get_recovery_request_by_token_hash(self, token_hash: str) -> RecoveryRequest | None:
        with self._read() as conn:
            row = conn.execute(
                "SELECT request_id, account_id, org_id, recipient_email, token_hash,"
                " created_at, expires_at, status, completed_at"
                " FROM recovery_requests WHERE token_hash = ?",
                (token_hash,),
            ).fetchone()
        if row is None:
            return None
        return RecoveryRequest(**dict(row))

    def complete_recovery_request(self, request_id: str, now: float) -> None:
        with self._write() as conn:
            conn.execute(
                "UPDATE recovery_requests SET status = ?, completed_at = ?"
                " WHERE request_id = ?",
                (RecoveryStatus.COMPLETED.value, now, request_id),
            )
            conn.execute(
                "DELETE FROM pending_deliveries WHERE request_id = ?", (request_id,)
            )

    def expire_recovery_request(self, request_id: str) -> None:
        with self._write() as conn:
            conn.execute(
                "UPDATE recovery_requests SET status = ? WHERE request_id = ?",
                (RecoveryStatus.EXPIRED.value, request_id),
            )
            conn.execute(
                "DELETE FROM pending_deliveries WHERE request_id = ?", (request_id,)
            )

    # -- pending deliveries / notification attempts ----------------------

    def get_pending_delivery(self, request_id: str) -> sqlite3.Row | None:
        with self._read() as conn:
            return conn.execute(
                "SELECT request_id, account_id, org_id, recipient_email, token_plaintext,"
                " retry_locator, attempt_count, last_attempt_at"
                " FROM pending_deliveries WHERE request_id = ?",
                (request_id,),
            ).fetchone()

    def list_pending_deliveries(self) -> list[sqlite3.Row]:
        with self._read() as conn:
            return conn.execute(
                "SELECT request_id, account_id, org_id, recipient_email, token_plaintext,"
                " retry_locator, attempt_count, last_attempt_at"
                " FROM pending_deliveries ORDER BY request_id ASC"
            ).fetchall()

    def mark_delivery_sent(
        self, request_id: str, attempt: NotificationAttempt
    ) -> None:
        with self._write() as conn:
            conn.execute(
                "INSERT INTO notification_attempts"
                " (attempt_id, request_id, account_id, attempted_at, status, receipt_text)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (
                    attempt.attempt_id,
                    attempt.request_id,
                    attempt.account_id,
                    attempt.attempted_at,
                    attempt.status.value,
                    attempt.receipt_text,
                ),
            )
            conn.execute(
                "DELETE FROM pending_deliveries WHERE request_id = ?", (request_id,)
            )

    def mark_delivery_failed(
        self,
        request_id: str,
        attempt: NotificationAttempt,
        retry_locator: str,
        now: float,
    ) -> None:
        with self._write() as conn:
            conn.execute(
                "INSERT INTO notification_attempts"
                " (attempt_id, request_id, account_id, attempted_at, status, receipt_text)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (
                    attempt.attempt_id,
                    attempt.request_id,
                    attempt.account_id,
                    attempt.attempted_at,
                    attempt.status.value,
                    attempt.receipt_text,
                ),
            )
            conn.execute(
                "UPDATE pending_deliveries SET retry_locator = ?,"
                " attempt_count = attempt_count + 1, last_attempt_at = ?"
                " WHERE request_id = ?",
                (retry_locator, now, request_id),
            )

    def list_notification_attempts(self, request_id: str) -> list[NotificationAttempt]:
        with self._read() as conn:
            rows = conn.execute(
                "SELECT attempt_id, request_id, account_id, attempted_at, status,"
                " receipt_text FROM notification_attempts WHERE request_id = ?"
                " ORDER BY attempted_at ASC",
                (request_id,),
            ).fetchall()
        return [NotificationAttempt(**dict(row)) for row in rows]

    # -- audit ------------------------------------------------------------

    def record_audit_event(self, event: AuditEvent) -> None:
        with self._write() as conn:
            conn.execute(
                "INSERT INTO audit_events"
                " (event_id, event_type, created_at, org_id, account_id, detail)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (
                    event.event_id,
                    event.event_type,
                    event.created_at,
                    event.org_id,
                    event.account_id,
                    event.detail,
                ),
            )

    def list_audit_events(self, account_id: str | None = None) -> list[AuditEvent]:
        with self._read() as conn:
            if account_id is None:
                rows = conn.execute(
                    "SELECT event_id, event_type, created_at, org_id, account_id, detail"
                    " FROM audit_events ORDER BY created_at ASC"
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT event_id, event_type, created_at, org_id, account_id, detail"
                    " FROM audit_events WHERE account_id = ? ORDER BY created_at ASC",
                    (account_id,),
                ).fetchall()
        return [AuditEvent(**dict(row)) for row in rows]
