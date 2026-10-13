"""Durable SQLite storage for the account recovery service.

Each call opens and closes its own connection. The database runs in WAL mode
so that a writer in one process and a reader in another process observe a
consistent, durable view of the same state -- this is what lets
`show-account` in a fresh process see what `create-account` committed in a
prior one.
"""
from __future__ import annotations

import contextlib
import sqlite3
from typing import Iterator, List, Optional

from .errors import ConflictError, NotFoundError
from .models import (
    Account,
    AuditEvent,
    EmailHistoryEntry,
    MfaEnrollment,
    NotificationAttempt,
    PendingRetryAttempt,
    ProviderDeliveryReceipt,
    RecoveryRequest,
)
from .timeutil import now_iso

SCHEMA = """
CREATE TABLE IF NOT EXISTS organizations (
    org_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL REFERENCES organizations(org_id),
    current_email TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS email_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL REFERENCES accounts(account_id),
    org_id TEXT NOT NULL,
    email TEXT NOT NULL,
    effective_from TEXT NOT NULL,
    effective_to TEXT,
    released INTEGER NOT NULL DEFAULT 0
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_email_history_current
    ON email_history(org_id, email)
    WHERE effective_to IS NULL;

CREATE INDEX IF NOT EXISTS ix_email_history_account
    ON email_history(account_id);

CREATE TABLE IF NOT EXISTS mfa_enrollments (
    account_id TEXT PRIMARY KEY REFERENCES accounts(account_id),
    method TEXT NOT NULL,
    enrolled INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recovery_requests (
    request_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(account_id),
    org_id TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    token_plain TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    used_at TEXT
);

CREATE TABLE IF NOT EXISTS notification_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL REFERENCES recovery_requests(request_id),
    account_id TEXT NOT NULL,
    attempt_number INTEGER NOT NULL,
    sent_at TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    success INTEGER NOT NULL,
    receipt_text TEXT NOT NULL,
    retry_locator TEXT
);

CREATE INDEX IF NOT EXISTS ix_notification_attempts_request
    ON notification_attempts(request_id);

CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    org_id TEXT,
    account_id TEXT,
    event_type TEXT NOT NULL,
    detail TEXT NOT NULL
);
"""


class Storage:
    """SQLite-backed persistence for organizations, accounts, and recovery."""

    def __init__(self, database_path: str) -> None:
        self.database_path = database_path
        self._init_schema()

    @contextlib.contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.database_path, timeout=30.0, isolation_level=None)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA busy_timeout=30000")
            conn.row_factory = sqlite3.Row
            yield conn
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    # -- audit -----------------------------------------------------------

    def _record_audit(
        self,
        conn: sqlite3.Connection,
        event_type: str,
        detail: str,
        org_id: Optional[str] = None,
        account_id: Optional[str] = None,
    ) -> None:
        event = AuditEvent(
            event_type=event_type,
            ts=now_iso(),
            detail=detail,
            org_id=org_id,
            account_id=account_id,
        )
        conn.execute(
            "INSERT INTO audit_events (ts, org_id, account_id, event_type, detail) "
            "VALUES (?, ?, ?, ?, ?)",
            (event.ts, event.org_id, event.account_id, event.event_type, event.detail),
        )

    def list_audit_events(self) -> List[AuditEvent]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, ts, org_id, account_id, event_type, detail "
                "FROM audit_events ORDER BY id ASC"
            ).fetchall()
        return [
            AuditEvent(
                event_id=row["id"],
                ts=row["ts"],
                org_id=row["org_id"],
                account_id=row["account_id"],
                event_type=row["event_type"],
                detail=row["detail"],
            )
            for row in rows
        ]

    # -- organizations / accounts -----------------------------------------

    def create_account(self, org_id: str, account_id: str, email: str) -> Account:
        created_at = now_iso()
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                existing = conn.execute(
                    "SELECT account_id FROM accounts WHERE account_id = ?",
                    (account_id,),
                ).fetchone()
                if existing is not None:
                    raise ConflictError(f"account '{account_id}' already exists")

                conn.execute(
                    "INSERT INTO organizations (org_id, created_at) VALUES (?, ?) "
                    "ON CONFLICT(org_id) DO NOTHING",
                    (org_id, created_at),
                )
                conn.execute(
                    "INSERT INTO accounts (account_id, org_id, current_email, created_at) "
                    "VALUES (?, ?, ?, ?)",
                    (account_id, org_id, email, created_at),
                )
                try:
                    conn.execute(
                        "INSERT INTO email_history "
                        "(account_id, org_id, email, effective_from, effective_to, released) "
                        "VALUES (?, ?, ?, ?, NULL, 0)",
                        (account_id, org_id, email, created_at),
                    )
                except sqlite3.IntegrityError as exc:
                    raise ConflictError(
                        f"email '{email}' is already in use in organization '{org_id}'"
                    ) from exc
                conn.execute(
                    "INSERT INTO mfa_enrollments (account_id, method, enrolled, updated_at) "
                    "VALUES (?, 'none', 0, ?)",
                    (account_id, created_at),
                )
                self._record_audit(
                    conn,
                    "account_created",
                    f"account '{account_id}' created in org '{org_id}' with email '{email}'",
                    org_id=org_id,
                    account_id=account_id,
                )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
        return Account(
            account_id=account_id, org_id=org_id, current_email=email, created_at=created_at
        )

    def get_account(self, account_id: str) -> Account:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT account_id, org_id, current_email, created_at "
                "FROM accounts WHERE account_id = ?",
                (account_id,),
            ).fetchone()
        if row is None:
            raise NotFoundError(f"account '{account_id}' not found")
        return Account(
            account_id=row["account_id"],
            org_id=row["org_id"],
            current_email=row["current_email"],
            created_at=row["created_at"],
        )

    def get_email_history(self, account_id: str) -> List[EmailHistoryEntry]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, account_id, org_id, email, effective_from, effective_to, released "
                "FROM email_history WHERE account_id = ? ORDER BY effective_from ASC, id ASC",
                (account_id,),
            ).fetchall()
        return [
            EmailHistoryEntry(
                entry_id=row["id"],
                account_id=row["account_id"],
                org_id=row["org_id"],
                email=row["email"],
                effective_from=row["effective_from"],
                effective_to=row["effective_to"],
                released=bool(row["released"]),
            )
            for row in rows
        ]

    def get_mfa_enrollment(self, account_id: str) -> MfaEnrollment:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT account_id, method, enrolled, updated_at "
                "FROM mfa_enrollments WHERE account_id = ?",
                (account_id,),
            ).fetchone()
        if row is None:
            raise NotFoundError(f"account '{account_id}' not found")
        return MfaEnrollment(
            account_id=row["account_id"],
            method=row["method"],
            enrolled=bool(row["enrolled"]),
            updated_at=row["updated_at"],
        )

    def change_email(self, account_id: str, new_email: str) -> Account:
        changed_at = now_iso()
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute(
                    "SELECT account_id, org_id, current_email FROM accounts "
                    "WHERE account_id = ?",
                    (account_id,),
                ).fetchone()
                if row is None:
                    raise NotFoundError(f"account '{account_id}' not found")
                org_id = row["org_id"]
                old_email = row["current_email"]
                if old_email == new_email:
                    raise ConflictError(
                        f"account '{account_id}' already uses email '{new_email}'"
                    )

                conn.execute(
                    "UPDATE email_history SET effective_to = ?, released = 1 "
                    "WHERE account_id = ? AND effective_to IS NULL",
                    (changed_at, account_id),
                )
                try:
                    conn.execute(
                        "INSERT INTO email_history "
                        "(account_id, org_id, email, effective_from, effective_to, released) "
                        "VALUES (?, ?, ?, ?, NULL, 0)",
                        (account_id, org_id, new_email, changed_at),
                    )
                except sqlite3.IntegrityError as exc:
                    raise ConflictError(
                        f"email '{new_email}' is already in use in organization '{org_id}'"
                    ) from exc
                conn.execute(
                    "UPDATE accounts SET current_email = ? WHERE account_id = ?",
                    (new_email, account_id),
                )
                self._record_audit(
                    conn,
                    "email_changed",
                    f"account '{account_id}' email changed from '{old_email}' to '{new_email}'",
                    org_id=org_id,
                    account_id=account_id,
                )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
        return self.get_account(account_id)

    def find_account_by_current_email(self, org_id: str, email: str) -> Optional[Account]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT a.account_id, a.org_id, a.current_email, a.created_at "
                "FROM accounts a "
                "JOIN email_history h ON h.account_id = a.account_id AND h.effective_to IS NULL "
                "WHERE h.org_id = ? AND h.email = ?",
                (org_id, email),
            ).fetchone()
        if row is None:
            return None
        return Account(
            account_id=row["account_id"],
            org_id=row["org_id"],
            current_email=row["current_email"],
            created_at=row["created_at"],
        )

    # -- recovery requests --------------------------------------------------

    def create_recovery_request(self, request: RecoveryRequest) -> None:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    "INSERT INTO recovery_requests "
                    "(request_id, account_id, org_id, token_hash, token_plain, created_at, "
                    " expires_at, used_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        request.request_id,
                        request.account_id,
                        request.org_id,
                        request.token_hash,
                        request.token_plain,
                        request.created_at,
                        request.expires_at,
                        request.used_at,
                    ),
                )
                self._record_audit(
                    conn,
                    "recovery_started",
                    f"recovery request '{request.request_id}' created for account "
                    f"'{request.account_id}'",
                    org_id=request.org_id,
                    account_id=request.account_id,
                )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def get_recovery_request_by_token_hash(self, token_hash: str) -> Optional[RecoveryRequest]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT request_id, account_id, org_id, token_hash, token_plain, "
                "created_at, expires_at, used_at "
                "FROM recovery_requests WHERE token_hash = ?",
                (token_hash,),
            ).fetchone()
        if row is None:
            return None
        return RecoveryRequest(
            request_id=row["request_id"],
            account_id=row["account_id"],
            org_id=row["org_id"],
            token_hash=row["token_hash"],
            token_plain=row["token_plain"],
            created_at=row["created_at"],
            expires_at=row["expires_at"],
            used_at=row["used_at"],
        )

    def mark_recovery_used(self, request_id: str) -> None:
        used_at = now_iso()
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute(
                    "SELECT account_id, org_id FROM recovery_requests WHERE request_id = ?",
                    (request_id,),
                ).fetchone()
                conn.execute(
                    "UPDATE recovery_requests SET used_at = ? WHERE request_id = ?",
                    (used_at, request_id),
                )
                if row is not None:
                    self._record_audit(
                        conn,
                        "recovery_completed",
                        f"recovery request '{request_id}' completed",
                        org_id=row["org_id"],
                        account_id=row["account_id"],
                    )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

    # -- notification attempts ----------------------------------------------

    def record_notification_attempt(
        self,
        request_id: str,
        account_id: str,
        endpoint: str,
        success: bool,
        receipt: ProviderDeliveryReceipt,
        retry_locator: Optional[str],
    ) -> NotificationAttempt:
        sent_at = now_iso()
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                prior = conn.execute(
                    "SELECT COALESCE(MAX(attempt_number), 0) AS n "
                    "FROM notification_attempts WHERE request_id = ?",
                    (request_id,),
                ).fetchone()
                attempt_number = int(prior["n"]) + 1
                cur = conn.execute(
                    "INSERT INTO notification_attempts "
                    "(request_id, account_id, attempt_number, sent_at, endpoint, success, "
                    " receipt_text, retry_locator) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        request_id,
                        account_id,
                        attempt_number,
                        sent_at,
                        endpoint,
                        1 if success else 0,
                        receipt.raw_text,
                        retry_locator,
                    ),
                )
                self._record_audit(
                    conn,
                    "notification_attempt",
                    f"attempt {attempt_number} for request '{request_id}' "
                    f"{'succeeded' if success else 'failed'}",
                    account_id=account_id,
                )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
        return NotificationAttempt(
            attempt_id=cur.lastrowid,
            request_id=request_id,
            account_id=account_id,
            attempt_number=attempt_number,
            sent_at=sent_at,
            endpoint=endpoint,
            success=success,
            receipt=receipt,
            retry_locator=retry_locator,
        )

    def list_pending_retry_attempts(self) -> List[PendingRetryAttempt]:
        """Reload every request whose most recent delivery attempt failed.

        Rebuilt entirely from durable storage on every call, so a process
        that restarts between the original failure and a retry sees exactly
        the same pending set a long-lived process would have. A request is
        excluded once it succeeds (its latest attempt is no longer a
        failure), once it is used (single-use), or once it expires --
        preserving those controls across the retry path.
        """
        now = now_iso()
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT r.request_id, r.account_id, r.token_plain, na.retry_locator "
                "FROM recovery_requests r "
                "JOIN notification_attempts na ON na.request_id = r.request_id "
                "WHERE na.attempt_number = ("
                "    SELECT MAX(attempt_number) FROM notification_attempts "
                "    WHERE request_id = r.request_id"
                ") "
                "AND na.success = 0 "
                "AND na.retry_locator IS NOT NULL "
                "AND r.used_at IS NULL "
                "AND r.expires_at > ? "
                "ORDER BY r.request_id ASC",
                (now,),
            ).fetchall()
        return [
            PendingRetryAttempt(
                request_id=row["request_id"],
                account_id=row["account_id"],
                token_plain=row["token_plain"],
                retry_locator=row["retry_locator"],
            )
            for row in rows
        ]

    def list_notification_attempts(self, request_id: str) -> List[NotificationAttempt]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, request_id, account_id, attempt_number, sent_at, endpoint, "
                "success, receipt_text, retry_locator "
                "FROM notification_attempts WHERE request_id = ? ORDER BY attempt_number ASC",
                (request_id,),
            ).fetchall()
        return [
            NotificationAttempt(
                attempt_id=row["id"],
                request_id=row["request_id"],
                account_id=row["account_id"],
                attempt_number=row["attempt_number"],
                sent_at=row["sent_at"],
                endpoint=row["endpoint"],
                success=bool(row["success"]),
                receipt=ProviderDeliveryReceipt(row["receipt_text"]),
                retry_locator=row["retry_locator"],
            )
            for row in rows
        ]
