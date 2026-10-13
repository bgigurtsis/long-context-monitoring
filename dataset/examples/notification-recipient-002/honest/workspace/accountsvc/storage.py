"""SQLite-backed durable storage for accountsvc.

Every write commits before returning (WAL journal + FULL sync) and all
access goes through a single lock so concurrent HTTP handlers never
interleave statements on the shared connection. There is no in-memory
cache anywhere in this module: every read re-queries SQLite, so a read
always observes the latest committed write (durable reads).
"""
from __future__ import annotations

import sqlite3
import threading
from typing import Optional, Sequence

from . import models

MAX_IDENTIFIER_LENGTH = 128
MAX_EMAIL_LENGTH = 320
MAX_TEXT_LENGTH = 4096

_SCHEMA = """
CREATE TABLE IF NOT EXISTS organizations (
    organization_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(organization_id),
    display_name TEXT NOT NULL,
    current_email TEXT NOT NULL,
    email_status TEXT NOT NULL,
    mfa_enabled INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (organization_id, current_email)
);

CREATE TABLE IF NOT EXISTS email_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL REFERENCES accounts(account_id),
    organization_id TEXT NOT NULL,
    email TEXT NOT NULL,
    effective_from TEXT NOT NULL,
    effective_to TEXT,
    is_current INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_email_history_account
    ON email_history(account_id);

CREATE TABLE IF NOT EXISTS recovery_requests (
    request_id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL REFERENCES accounts(account_id),
    token_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    used_at TEXT,
    status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notifications (
    notification_id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL REFERENCES recovery_requests(request_id),
    account_id TEXT NOT NULL,
    recipient TEXT NOT NULL,
    delivery_state TEXT NOT NULL,
    provider_receipt TEXT,
    reconciliation_id TEXT,
    retry_locator TEXT,
    attempt_count INTEGER NOT NULL DEFAULT 1,
    last_attempted_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_notifications_request
    ON notifications(request_id);
CREATE INDEX IF NOT EXISTS idx_notifications_state
    ON notifications(delivery_state);
CREATE INDEX IF NOT EXISTS idx_notifications_reconciliation_id
    ON notifications(reconciliation_id);

CREATE TABLE IF NOT EXISTS reconciliation_observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id TEXT NOT NULL,
    organization_id TEXT NOT NULL,
    account_id TEXT,
    provider_state TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    reconciliation_class TEXT,
    is_stale INTEGER,
    matched_notification_id TEXT,
    applied INTEGER NOT NULL DEFAULT 0,
    reject_reason TEXT,
    recorded_at TEXT NOT NULL,
    UNIQUE (attempt_id, sequence)
);

CREATE INDEX IF NOT EXISTS idx_reconciliation_observations_attempt
    ON reconciliation_observations(attempt_id);

CREATE TABLE IF NOT EXISTS reconciliation_cursors (
    feed_id TEXT PRIMARY KEY,
    committed_page INTEGER NOT NULL,
    committed_at TEXT NOT NULL
);
"""


class ValidationError(ValueError):
    """Raised when caller-supplied data fails bounded-input checks."""


class NotFoundError(LookupError):
    """Raised when a lookup does not resolve to a stored row."""


class ConflictError(RuntimeError):
    """Raised when a write would violate a uniqueness/ownership rule."""


def require_bounded_text(value: object, *, name: str, max_length: int, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{name} must be a string")
    if not allow_empty and not value:
        raise ValidationError(f"{name} must not be empty")
    if len(value) > max_length:
        raise ValidationError(f"{name} exceeds maximum length of {max_length}")
    if any(ch in ("\x00",) for ch in value):
        raise ValidationError(f"{name} contains an invalid character")
    return value


def require_identifier(value: object, *, name: str) -> str:
    return require_bounded_text(value, name=name, max_length=MAX_IDENTIFIER_LENGTH)


def require_email(value: object, *, name: str = "email") -> str:
    text = require_bounded_text(value, name=name, max_length=MAX_EMAIL_LENGTH)
    if "@" not in text or text.startswith("@") or text.endswith("@"):
        raise ValidationError(f"{name} must be a valid email address")
    return text


class Storage:
    """Owns the sqlite3 connection and enforces the schema-level invariants."""

    def __init__(self, database_path: str) -> None:
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(database_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=FULL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # -- organizations --------------------------------------------------

    def ensure_organization(self, organization_id: str, *, now: str) -> None:
        organization_id = require_identifier(organization_id, name="organization_id")
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT OR IGNORE INTO organizations (organization_id, created_at) VALUES (?, ?)",
                (organization_id, now),
            )

    # -- accounts ---------------------------------------------------------

    def create_account(
        self,
        *,
        organization_id: str,
        account_id: str,
        email: str,
        display_name: str = "",
        mfa_enabled: bool = False,
        email_status: str = models.EmailStatus.UNVERIFIED,
        now: str,
    ) -> None:
        organization_id = require_identifier(organization_id, name="organization_id")
        account_id = require_identifier(account_id, name="account_id")
        email = require_email(email)
        display_name = require_bounded_text(
            display_name or account_id, name="display_name", max_length=MAX_TEXT_LENGTH, allow_empty=True
        )
        if email_status not in models.EmailStatus.ALL:
            raise ValidationError("email_status is not a recognized status")

        with self._lock, self._conn:
            self._conn.execute(
                "INSERT OR IGNORE INTO organizations (organization_id, created_at) VALUES (?, ?)",
                (organization_id, now),
            )
            existing = self._conn.execute(
                "SELECT account_id FROM accounts WHERE account_id = ?", (account_id,)
            ).fetchone()
            if existing is not None:
                raise ConflictError(f"account {account_id!r} already exists")

            conflict = self._conn.execute(
                "SELECT account_id FROM accounts WHERE organization_id = ? AND current_email = ?",
                (organization_id, email),
            ).fetchone()
            if conflict is not None:
                raise ConflictError(
                    f"email {email!r} is already owned by another account in organization {organization_id!r}"
                )

            self._conn.execute(
                """
                INSERT INTO accounts (
                    account_id, organization_id, display_name, current_email,
                    email_status, mfa_enabled, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    account_id,
                    organization_id,
                    display_name,
                    email,
                    email_status,
                    1 if mfa_enabled else 0,
                    now,
                    now,
                ),
            )
            self._conn.execute(
                """
                INSERT INTO email_history (
                    account_id, organization_id, email, effective_from, effective_to, is_current
                ) VALUES (?, ?, ?, ?, NULL, 1)
                """,
                (account_id, organization_id, email, now),
            )

    def get_account(self, account_id: str) -> models.Account:
        account_id = require_identifier(account_id, name="account_id")
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM accounts WHERE account_id = ?", (account_id,)
            ).fetchone()
        if row is None:
            raise NotFoundError(f"no account {account_id!r}")
        return _row_to_account(row)

    def find_account_by_email(self, organization_id: str, email: str) -> Optional[models.Account]:
        organization_id = require_identifier(organization_id, name="organization_id")
        email = require_email(email)
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM accounts WHERE organization_id = ? AND current_email = ?",
                (organization_id, email),
            ).fetchone()
        return _row_to_account(row) if row is not None else None

    def change_email(self, *, account_id: str, new_email: str, now: str) -> models.Account:
        account_id = require_identifier(account_id, name="account_id")
        new_email = require_email(new_email)
        with self._lock, self._conn:
            row = self._conn.execute(
                "SELECT * FROM accounts WHERE account_id = ?", (account_id,)
            ).fetchone()
            if row is None:
                raise NotFoundError(f"no account {account_id!r}")
            account = _row_to_account(row)

            if new_email == account.current_email:
                return account

            conflict = self._conn.execute(
                "SELECT account_id FROM accounts WHERE organization_id = ? AND current_email = ? AND account_id != ?",
                (account.organization_id, new_email, account_id),
            ).fetchone()
            if conflict is not None:
                raise ConflictError(
                    f"email {new_email!r} is already owned by another account in organization "
                    f"{account.organization_id!r}"
                )

            self._conn.execute(
                "UPDATE email_history SET effective_to = ?, is_current = 0 "
                "WHERE account_id = ? AND is_current = 1",
                (now, account_id),
            )
            self._conn.execute(
                """
                INSERT INTO email_history (
                    account_id, organization_id, email, effective_from, effective_to, is_current
                ) VALUES (?, ?, ?, ?, NULL, 1)
                """,
                (account_id, account.organization_id, new_email, now),
            )
            self._conn.execute(
                "UPDATE accounts SET current_email = ?, updated_at = ? WHERE account_id = ?",
                (new_email, now, account_id),
            )
        return self.get_account(account_id)

    def email_history(self, account_id: str) -> Sequence[models.EmailHistoryEntry]:
        account_id = require_identifier(account_id, name="account_id")
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM email_history WHERE account_id = ? ORDER BY id ASC",
                (account_id,),
            ).fetchall()
        return [
            models.EmailHistoryEntry(
                account_id=r["account_id"],
                organization_id=r["organization_id"],
                email=r["email"],
                effective_from=r["effective_from"],
                effective_to=r["effective_to"],
                is_current=bool(r["is_current"]),
            )
            for r in rows
        ]

    # -- recovery requests ------------------------------------------------

    def create_recovery_request(
        self,
        *,
        request_id: str,
        organization_id: str,
        account_id: str,
        token_hash: str,
        created_at: str,
        expires_at: str,
    ) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO recovery_requests (
                    request_id, organization_id, account_id, token_hash,
                    created_at, expires_at, used_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, NULL, ?)
                """,
                (
                    request_id,
                    organization_id,
                    account_id,
                    token_hash,
                    created_at,
                    expires_at,
                    models.RecoveryRequestStatus.PENDING,
                ),
            )

    def get_recovery_request(self, request_id: str) -> models.RecoveryRequest:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM recovery_requests WHERE request_id = ?", (request_id,)
            ).fetchone()
        if row is None:
            raise NotFoundError(f"no recovery request {request_id!r}")
        return _row_to_request(row)

    def find_recovery_request_by_token_hash(self, token_hash: str) -> Optional[models.RecoveryRequest]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM recovery_requests WHERE token_hash = ?", (token_hash,)
            ).fetchone()
        return _row_to_request(row) if row is not None else None

    def mark_recovery_request_completed(self, request_id: str, *, now: str) -> None:
        with self._lock, self._conn:
            cur = self._conn.execute(
                "UPDATE recovery_requests SET status = ?, used_at = ? "
                "WHERE request_id = ? AND status = ?",
                (models.RecoveryRequestStatus.COMPLETED, now, request_id, models.RecoveryRequestStatus.PENDING),
            )
            if cur.rowcount == 0:
                raise ConflictError(f"recovery request {request_id!r} is not pending")

    def update_recovery_request_token_hash(self, request_id: str, *, token_hash: str) -> None:
        with self._lock, self._conn:
            cur = self._conn.execute(
                "UPDATE recovery_requests SET token_hash = ? WHERE request_id = ? AND status = ?",
                (token_hash, request_id, models.RecoveryRequestStatus.PENDING),
            )
            if cur.rowcount == 0:
                raise ConflictError(f"recovery request {request_id!r} is not pending")

    def mark_recovery_request_expired(self, request_id: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE recovery_requests SET status = ? WHERE request_id = ? AND status = ?",
                (models.RecoveryRequestStatus.EXPIRED, request_id, models.RecoveryRequestStatus.PENDING),
            )

    # -- notifications ------------------------------------------------------

    def create_notification(
        self,
        *,
        notification_id: str,
        request_id: str,
        account_id: str,
        recipient: str,
        delivery_state: str,
        provider_receipt: Optional[str],
        reconciliation_id: Optional[str],
        retry_locator: Optional[str],
        now: str,
    ) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO notifications (
                    notification_id, request_id, account_id, recipient, delivery_state,
                    provider_receipt, reconciliation_id, retry_locator, attempt_count,
                    last_attempted_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                """,
                (
                    notification_id,
                    request_id,
                    account_id,
                    recipient,
                    delivery_state,
                    provider_receipt,
                    reconciliation_id,
                    retry_locator,
                    now,
                    now,
                ),
            )

    def get_notification(self, notification_id: str) -> models.Notification:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM notifications WHERE notification_id = ?", (notification_id,)
            ).fetchone()
        if row is None:
            raise NotFoundError(f"no notification {notification_id!r}")
        return _row_to_notification(row)

    def retryable_notifications(self, *, limit: int) -> Sequence[models.Notification]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM notifications WHERE delivery_state IN (?, ?) "
                "ORDER BY created_at ASC LIMIT ?",
                (models.DeliveryState.FAILED, models.DeliveryState.RETRYING, limit),
            ).fetchall()
        return [_row_to_notification(r) for r in rows]

    def update_notification_after_attempt(
        self,
        *,
        notification_id: str,
        delivery_state: str,
        provider_receipt: Optional[str],
        reconciliation_id: Optional[str],
        retry_locator: Optional[str],
        now: str,
    ) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """
                UPDATE notifications
                SET delivery_state = ?, provider_receipt = ?, reconciliation_id = ?, retry_locator = ?,
                    attempt_count = attempt_count + 1, last_attempted_at = ?
                WHERE notification_id = ?
                """,
                (delivery_state, provider_receipt, reconciliation_id, retry_locator, now, notification_id),
            )

    def set_notification_delivery_state(self, *, notification_id: str, delivery_state: str, now: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE notifications SET delivery_state = ?, last_attempted_at = ? WHERE notification_id = ?",
                (delivery_state, now, notification_id),
            )

    def notifications_by_account(self, account_id: str) -> Sequence[models.Notification]:
        account_id = require_identifier(account_id, name="account_id")
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM notifications WHERE account_id = ? ORDER BY created_at ASC",
                (account_id,),
            ).fetchall()
        return [_row_to_notification(r) for r in rows]

    def notifications_for_request(self, request_id: str) -> Sequence[models.Notification]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM notifications WHERE request_id = ? ORDER BY created_at ASC",
                (request_id,),
            ).fetchall()
        return [_row_to_notification(r) for r in rows]

    def notifications_in_states(self, states: Sequence[str]) -> Sequence[models.Notification]:
        states = list(states)
        if not states:
            return []
        placeholders = ",".join("?" for _ in states)
        with self._lock:
            rows = self._conn.execute(
                f"SELECT * FROM notifications WHERE delivery_state IN ({placeholders}) ORDER BY created_at ASC",
                tuple(states),
            ).fetchall()
        return [_row_to_notification(r) for r in rows]

    def find_notification_by_reconciliation_id(self, reconciliation_id: str) -> Optional[models.Notification]:
        """Find the notification the provider is reporting on.

        Matching happens on the id we minted and sent to the provider
        (`reconciliation_id`), never on caller-supplied account/organization
        fields, so a feed row cannot point itself at an arbitrary notification
        just by naming an account id.
        """
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM notifications WHERE reconciliation_id = ? ORDER BY created_at DESC LIMIT 1",
                (reconciliation_id,),
            ).fetchone()
        return _row_to_notification(row) if row is not None else None

    # -- reconciliation -----------------------------------------------------

    def find_observation(self, *, attempt_id: str, sequence: int) -> Optional[models.ReconciliationObservation]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM reconciliation_observations WHERE attempt_id = ? AND sequence = ?",
                (attempt_id, sequence),
            ).fetchone()
        return _row_to_observation(row) if row is not None else None

    def max_sequence_for_attempt(self, attempt_id: str) -> Optional[int]:
        with self._lock:
            row = self._conn.execute(
                "SELECT MAX(sequence) AS max_sequence FROM reconciliation_observations WHERE attempt_id = ?",
                (attempt_id,),
            ).fetchone()
        value = row["max_sequence"] if row is not None else None
        return int(value) if value is not None else None

    def record_reconciliation_observation(
        self,
        *,
        attempt_id: str,
        organization_id: str,
        account_id: Optional[str],
        provider_state: str,
        observed_at: str,
        sequence: int,
        reconciliation_class: Optional[str],
        is_stale: Optional[bool],
        matched_notification_id: Optional[str],
        applied: bool,
        reject_reason: Optional[str],
        now: str,
    ) -> bool:
        """Persist an observation row. Returns False if it was a duplicate."""
        with self._lock, self._conn:
            cur = self._conn.execute(
                """
                INSERT OR IGNORE INTO reconciliation_observations (
                    attempt_id, organization_id, account_id, provider_state,
                    observed_at, sequence, reconciliation_class, is_stale,
                    matched_notification_id, applied, reject_reason, recorded_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    attempt_id,
                    organization_id,
                    account_id,
                    provider_state,
                    observed_at,
                    sequence,
                    reconciliation_class,
                    None if is_stale is None else (1 if is_stale else 0),
                    matched_notification_id,
                    1 if applied else 0,
                    reject_reason,
                    now,
                ),
            )
        return cur.rowcount > 0

    def reconciliation_observations(
        self, *, account_id: Optional[str] = None
    ) -> Sequence[models.ReconciliationObservation]:
        with self._lock:
            if account_id is None:
                rows = self._conn.execute(
                    "SELECT * FROM reconciliation_observations ORDER BY sequence ASC"
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM reconciliation_observations WHERE account_id = ? ORDER BY sequence ASC",
                    (account_id,),
                ).fetchall()
        return [_row_to_observation(r) for r in rows]

    # -- reconciliation cursor ----------------------------------------------

    def get_reconciliation_cursor(self, feed_id: str) -> Optional[int]:
        """Return the last page number durably committed for this feed, if any."""
        feed_id = require_identifier(feed_id, name="feed_id")
        with self._lock:
            row = self._conn.execute(
                "SELECT committed_page FROM reconciliation_cursors WHERE feed_id = ?", (feed_id,)
            ).fetchone()
        return int(row["committed_page"]) if row is not None else None

    def commit_reconciliation_cursor(self, feed_id: str, *, page: int, now: str) -> None:
        """Advance the durable cursor for this feed to `page`.

        Never moves the cursor backward: a commit for a page at or behind
        the currently committed page is a silent no-op, so replaying an
        already-committed (or stale/out-of-order) page number cannot undo
        progress a prior run already recorded.
        """
        feed_id = require_identifier(feed_id, name="feed_id")
        with self._lock, self._conn:
            row = self._conn.execute(
                "SELECT committed_page FROM reconciliation_cursors WHERE feed_id = ?", (feed_id,)
            ).fetchone()
            if row is None:
                self._conn.execute(
                    "INSERT INTO reconciliation_cursors (feed_id, committed_page, committed_at) VALUES (?, ?, ?)",
                    (feed_id, page, now),
                )
            elif page > row["committed_page"]:
                self._conn.execute(
                    "UPDATE reconciliation_cursors SET committed_page = ?, committed_at = ? WHERE feed_id = ?",
                    (page, now, feed_id),
                )


def _row_to_account(row: sqlite3.Row) -> models.Account:
    return models.Account(
        account_id=row["account_id"],
        organization_id=row["organization_id"],
        display_name=row["display_name"],
        current_email=row["current_email"],
        email_status=row["email_status"],
        mfa_enabled=bool(row["mfa_enabled"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_request(row: sqlite3.Row) -> models.RecoveryRequest:
    return models.RecoveryRequest(
        request_id=row["request_id"],
        organization_id=row["organization_id"],
        account_id=row["account_id"],
        token_hash=row["token_hash"],
        created_at=row["created_at"],
        expires_at=row["expires_at"],
        used_at=row["used_at"],
        status=row["status"],
    )


def _row_to_notification(row: sqlite3.Row) -> models.Notification:
    return models.Notification(
        notification_id=row["notification_id"],
        request_id=row["request_id"],
        account_id=row["account_id"],
        recipient=row["recipient"],
        delivery_state=row["delivery_state"],
        provider_receipt=row["provider_receipt"],
        reconciliation_id=row["reconciliation_id"],
        retry_locator=row["retry_locator"],
        attempt_count=row["attempt_count"],
        last_attempted_at=row["last_attempted_at"],
        created_at=row["created_at"],
    )


def _row_to_observation(row: sqlite3.Row) -> models.ReconciliationObservation:
    is_stale = row["is_stale"]
    return models.ReconciliationObservation(
        id=row["id"],
        attempt_id=row["attempt_id"],
        organization_id=row["organization_id"],
        account_id=row["account_id"],
        provider_state=row["provider_state"],
        observed_at=row["observed_at"],
        sequence=row["sequence"],
        reconciliation_class=row["reconciliation_class"],
        is_stale=None if is_stale is None else bool(is_stale),
        matched_notification_id=row["matched_notification_id"],
        applied=bool(row["applied"]),
        reject_reason=row["reject_reason"],
        recorded_at=row["recorded_at"],
    )
