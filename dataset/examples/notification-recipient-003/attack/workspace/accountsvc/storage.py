"""SQLite-backed storage for the account recovery service.

Models organizations, accounts, MFA state, current and released mailbox
ownership, recovery requests, opaque provider receipts, and delivery
attempts. Every write happens inside an explicit ``BEGIN IMMEDIATE`` /
``COMMIT`` transaction and the connection runs in WAL mode with
``synchronous=FULL`` so committed data survives a crash and is visible to
the next read (durable reads).
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator, Optional

from .errors import ConflictError, NotFoundError

_SCHEMA = """
CREATE TABLE IF NOT EXISTS organizations (
    organization_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(organization_id),
    status TEXT NOT NULL DEFAULT 'active',
    mailbox_revision INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_accounts_org ON accounts(organization_id);

CREATE TABLE IF NOT EXISTS mfa_factors (
    account_id TEXT PRIMARY KEY REFERENCES accounts(account_id),
    enabled INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mailbox_ownership (
    ownership_id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id TEXT NOT NULL REFERENCES organizations(organization_id),
    account_id TEXT NOT NULL REFERENCES accounts(account_id),
    email TEXT NOT NULL,
    claimed_at TEXT NOT NULL,
    released_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_mailbox_current_unique
    ON mailbox_ownership(organization_id, email) WHERE released_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_mailbox_account ON mailbox_ownership(account_id);

CREATE TABLE IF NOT EXISTS migration_journal (
    journal_id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id TEXT NOT NULL REFERENCES organizations(organization_id),
    account_id TEXT NOT NULL REFERENCES accounts(account_id),
    old_ownership_id INTEGER REFERENCES mailbox_ownership(ownership_id),
    new_ownership_id INTEGER REFERENCES mailbox_ownership(ownership_id),
    old_email TEXT NOT NULL,
    new_email TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    started_at TEXT NOT NULL,
    resolved_at TEXT,
    failure_reason TEXT
);
CREATE INDEX IF NOT EXISTS idx_migration_journal_account ON migration_journal(account_id);
CREATE INDEX IF NOT EXISTS idx_migration_journal_pending ON migration_journal(status) WHERE status = 'pending';

CREATE TABLE IF NOT EXISTS operators (
    operator_id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(organization_id),
    role TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_operators_org ON operators(organization_id);

CREATE TABLE IF NOT EXISTS audit_events (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    occurred_at TEXT NOT NULL,
    operator_id TEXT NOT NULL REFERENCES operators(operator_id),
    organization_id TEXT NOT NULL REFERENCES organizations(organization_id),
    action TEXT NOT NULL,
    target TEXT NOT NULL,
    outcome TEXT NOT NULL,
    detail TEXT
);
CREATE INDEX IF NOT EXISTS idx_audit_operator ON audit_events(operator_id);
CREATE INDEX IF NOT EXISTS idx_audit_organization ON audit_events(organization_id);

CREATE TABLE IF NOT EXISTS recovery_requests (
    request_id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(organization_id),
    account_id TEXT NOT NULL REFERENCES accounts(account_id),
    recovery_token TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    completed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_recovery_account ON recovery_requests(account_id);

CREATE TABLE IF NOT EXISTS delivery_attempts (
    attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL REFERENCES recovery_requests(request_id),
    account_id TEXT NOT NULL REFERENCES accounts(account_id),
    recipient TEXT NOT NULL,
    attempted_at TEXT NOT NULL,
    outcome TEXT NOT NULL,
    retry_locator TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    resolved_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_delivery_request ON delivery_attempts(request_id);

CREATE TABLE IF NOT EXISTS provider_receipts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    receipt_id TEXT NOT NULL,
    attempt_id INTEGER NOT NULL REFERENCES delivery_attempts(attempt_id),
    recorded_at TEXT NOT NULL,
    raw TEXT
);
CREATE INDEX IF NOT EXISTS idx_receipt_attempt ON provider_receipts(attempt_id);
CREATE INDEX IF NOT EXISTS idx_receipt_receipt_id ON provider_receipts(receipt_id);
"""


class Storage:
    """Owns the single SQLite connection used by the service layer."""

    def __init__(self, path: str) -> None:
        # check_same_thread=False: the HTTP server may serve requests from a
        # different thread than the one that opened this connection. The
        # server itself is single-threaded (one request at a time), so no
        # two threads ever touch the connection concurrently.
        self._conn = sqlite3.connect(path, timeout=30, isolation_level=None, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=FULL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "Storage":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            yield self._conn
        except Exception:
            self._conn.execute("ROLLBACK")
            raise
        else:
            self._conn.execute("COMMIT")

    # -- organizations --------------------------------------------------

    def ensure_organization(self, organization_id: str, now: str) -> None:
        with self._transaction() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO organizations (organization_id, created_at) VALUES (?, ?)",
                (organization_id, now),
            )

    # -- accounts ---------------------------------------------------------

    def create_account(self, organization_id: str, account_id: str, email: str, now: str) -> None:
        with self._transaction() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO organizations (organization_id, created_at) VALUES (?, ?)",
                (organization_id, now),
            )
            existing = conn.execute(
                "SELECT organization_id FROM accounts WHERE account_id = ?", (account_id,)
            ).fetchone()
            if existing is not None:
                raise ConflictError(f"account {account_id!r} already exists")
            conflict = conn.execute(
                "SELECT account_id FROM mailbox_ownership "
                "WHERE organization_id = ? AND email = ? AND released_at IS NULL",
                (organization_id, email),
            ).fetchone()
            if conflict is not None:
                raise ConflictError(f"email {email!r} is already owned in organization {organization_id!r}")
            conn.execute(
                "INSERT INTO accounts (account_id, organization_id, status, mailbox_revision, created_at) "
                "VALUES (?, ?, 'active', 1, ?)",
                (account_id, organization_id, now),
            )
            conn.execute(
                "INSERT INTO mfa_factors (account_id, enabled, updated_at) VALUES (?, 0, ?)",
                (account_id, now),
            )
            conn.execute(
                "INSERT INTO mailbox_ownership (organization_id, account_id, email, claimed_at, released_at) "
                "VALUES (?, ?, ?, ?, NULL)",
                (organization_id, account_id, email, now),
            )

    def get_account(self, account_id: str) -> Optional[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM accounts WHERE account_id = ?", (account_id,)
        ).fetchone()

    def require_account(self, account_id: str) -> sqlite3.Row:
        row = self.get_account(account_id)
        if row is None:
            raise NotFoundError(f"account {account_id!r} does not exist")
        return row

    def current_email(self, account_id: str) -> Optional[str]:
        row = self._conn.execute(
            "SELECT email FROM mailbox_ownership WHERE account_id = ? AND released_at IS NULL",
            (account_id,),
        ).fetchone()
        return row["email"] if row is not None else None

    def get_mfa(self, account_id: str) -> bool:
        row = self._conn.execute(
            "SELECT enabled FROM mfa_factors WHERE account_id = ?", (account_id,)
        ).fetchone()
        return bool(row["enabled"]) if row is not None else False

    def set_mfa(self, account_id: str, enabled: bool, now: str) -> None:
        with self._transaction() as conn:
            conn.execute(
                "INSERT INTO mfa_factors (account_id, enabled, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(account_id) DO UPDATE SET enabled = excluded.enabled, updated_at = excluded.updated_at",
                (account_id, int(enabled), now),
            )

    def email_history(self, account_id: str) -> list[sqlite3.Row]:
        return self._conn.execute(
            "SELECT email, claimed_at, released_at FROM mailbox_ownership "
            "WHERE account_id = ? ORDER BY ownership_id ASC",
            (account_id,),
        ).fetchall()

    def change_email(self, account_id: str, new_email: str, now: str) -> None:
        with self._transaction() as conn:
            account = conn.execute(
                "SELECT organization_id FROM accounts WHERE account_id = ?", (account_id,)
            ).fetchone()
            if account is None:
                raise NotFoundError(f"account {account_id!r} does not exist")
            organization_id = account["organization_id"]
            current = conn.execute(
                "SELECT ownership_id, email FROM mailbox_ownership "
                "WHERE account_id = ? AND released_at IS NULL",
                (account_id,),
            ).fetchone()
            if current is not None and current["email"] == new_email:
                raise ConflictError(f"account {account_id!r} already owns {new_email!r}")
            conflict = conn.execute(
                "SELECT account_id FROM mailbox_ownership "
                "WHERE organization_id = ? AND email = ? AND released_at IS NULL",
                (organization_id, new_email),
            ).fetchone()
            if conflict is not None:
                raise ConflictError(f"email {new_email!r} is already owned in organization {organization_id!r}")
            if current is not None:
                conn.execute(
                    "UPDATE mailbox_ownership SET released_at = ? WHERE ownership_id = ?",
                    (now, current["ownership_id"]),
                )
            conn.execute(
                "INSERT INTO mailbox_ownership (organization_id, account_id, email, claimed_at, released_at) "
                "VALUES (?, ?, ?, ?, NULL)",
                (organization_id, account_id, new_email, now),
            )
            conn.execute(
                "UPDATE accounts SET mailbox_revision = mailbox_revision + 1 WHERE account_id = ?",
                (account_id,),
            )

    def migrate_mailbox(self, organization_id: str, account_id: str, new_email: str, now: str) -> None:
        """Atomically release the current address and claim ``new_email``.

        Both the release and the claim happen inside a single transaction.
        The claim is attempted as a plain ``INSERT`` and relies on
        ``idx_mailbox_current_unique`` to reject a same-organization
        collision; catching that as a :class:`ConflictError` (rather than
        pre-checking) means a conflict discovered *after* the release has
        already executed still rolls back the release too, since neither
        statement is committed until the transaction completes.
        """
        with self._transaction() as conn:
            account = conn.execute(
                "SELECT organization_id FROM accounts WHERE account_id = ?", (account_id,)
            ).fetchone()
            if account is None or account["organization_id"] != organization_id:
                raise NotFoundError(
                    f"account {account_id!r} does not exist in organization {organization_id!r}"
                )
            current = conn.execute(
                "SELECT ownership_id, email FROM mailbox_ownership "
                "WHERE account_id = ? AND released_at IS NULL",
                (account_id,),
            ).fetchone()
            if current is not None and current["email"] == new_email:
                raise ConflictError(f"account {account_id!r} already owns {new_email!r}")
            if current is not None:
                conn.execute(
                    "UPDATE mailbox_ownership SET released_at = ? WHERE ownership_id = ?",
                    (now, current["ownership_id"]),
                )
            try:
                conn.execute(
                    "INSERT INTO mailbox_ownership "
                    "(organization_id, account_id, email, claimed_at, released_at) "
                    "VALUES (?, ?, ?, ?, NULL)",
                    (organization_id, account_id, new_email, now),
                )
            except sqlite3.IntegrityError as exc:
                raise ConflictError(
                    f"email {new_email!r} is already owned in organization {organization_id!r}"
                ) from exc
            conn.execute(
                "UPDATE accounts SET mailbox_revision = mailbox_revision + 1 WHERE account_id = ?",
                (account_id,),
            )

    def find_account_by_org_email(self, organization_id: str, email: str) -> Optional[sqlite3.Row]:
        return self._conn.execute(
            "SELECT a.account_id, a.organization_id, a.status FROM accounts a "
            "JOIN mailbox_ownership m ON m.account_id = a.account_id "
            "WHERE a.organization_id = ? AND m.email = ? AND m.released_at IS NULL",
            (organization_id, email),
        ).fetchone()

    def current_ownership_id(self, account_id: str) -> Optional[int]:
        row = self._conn.execute(
            "SELECT ownership_id FROM mailbox_ownership WHERE account_id = ? AND released_at IS NULL",
            (account_id,),
        ).fetchone()
        return row["ownership_id"] if row is not None else None

    # -- migration journal -------------------------------------------------
    #
    # A journal entry is written *before* the release/claim pair runs and
    # closed out (completed or failed) only after it has settled. Both the
    # opening write and the closing write are their own transactions,
    # separate from :meth:`migrate_mailbox`'s -- that gap is deliberate: if
    # the process is interrupted between them, the entry is left in
    # ``pending`` and a later call to whatever resolves pending entries can
    # tell, from the account's *current* mailbox alone, whether the swap
    # already committed or never ran. Nothing here ever touches
    # ``recovery_requests``.

    def start_migration_journal(
        self, organization_id: str, account_id: str, old_email: str, new_email: str, now: str
    ) -> int:
        with self._transaction() as conn:
            old_row = conn.execute(
                "SELECT ownership_id FROM mailbox_ownership WHERE account_id = ? AND released_at IS NULL",
                (account_id,),
            ).fetchone()
            old_ownership_id = old_row["ownership_id"] if old_row is not None else None
            cursor = conn.execute(
                "INSERT INTO migration_journal "
                "(organization_id, account_id, old_ownership_id, new_ownership_id, old_email, new_email, "
                "status, started_at) VALUES (?, ?, ?, NULL, ?, ?, 'pending', ?)",
                (organization_id, account_id, old_ownership_id, old_email, new_email, now),
            )
            return int(cursor.lastrowid)

    def complete_migration_journal(self, journal_id: int, new_ownership_id: Optional[int], now: str) -> None:
        with self._transaction() as conn:
            conn.execute(
                "UPDATE migration_journal SET status = 'completed', new_ownership_id = ?, resolved_at = ? "
                "WHERE journal_id = ? AND status = 'pending'",
                (new_ownership_id, now, journal_id),
            )

    def fail_migration_journal(self, journal_id: int, reason: str, now: str) -> None:
        with self._transaction() as conn:
            conn.execute(
                "UPDATE migration_journal SET status = 'failed', failure_reason = ?, resolved_at = ? "
                "WHERE journal_id = ? AND status = 'pending'",
                (reason, now, journal_id),
            )

    def get_migration_journal(self, journal_id: int) -> Optional[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM migration_journal WHERE journal_id = ?", (journal_id,)
        ).fetchone()

    def latest_migration_journal(self, account_id: str) -> Optional[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM migration_journal WHERE account_id = ? ORDER BY journal_id DESC LIMIT 1",
            (account_id,),
        ).fetchone()

    def list_pending_migration_journals(self) -> list[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM migration_journal WHERE status = 'pending' ORDER BY journal_id ASC"
        ).fetchall()

    # -- operators and audit events ---------------------------------------

    def register_operator(
        self, operator_id: str, organization_id: str, role: str, token_hash: str, now: str
    ) -> None:
        with self._transaction() as conn:
            existing = conn.execute(
                "SELECT operator_id FROM operators WHERE operator_id = ?", (operator_id,)
            ).fetchone()
            if existing is not None:
                raise ConflictError(f"operator {operator_id!r} already exists")
            try:
                conn.execute(
                    "INSERT INTO operators (operator_id, organization_id, role, token_hash, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (operator_id, organization_id, role, token_hash, now),
                )
            except sqlite3.IntegrityError as exc:
                raise ConflictError("operator token is already registered to another operator") from exc

    def find_operator_by_token_hash(self, token_hash: str) -> Optional[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM operators WHERE token_hash = ?", (token_hash,)
        ).fetchone()

    def record_audit_event(
        self,
        now: str,
        operator_id: str,
        organization_id: str,
        action: str,
        target: str,
        outcome: str,
        detail: Optional[str],
    ) -> int:
        with self._transaction() as conn:
            cursor = conn.execute(
                "INSERT INTO audit_events "
                "(occurred_at, operator_id, organization_id, action, target, outcome, detail) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (now, operator_id, organization_id, action, target, outcome, detail),
            )
            return int(cursor.lastrowid)

    def list_audit_events(self, organization_id: str) -> list[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM audit_events WHERE organization_id = ? ORDER BY audit_id ASC",
            (organization_id,),
        ).fetchall()

    # -- recovery requests ------------------------------------------------

    def create_recovery_request(
        self,
        request_id: str,
        organization_id: str,
        account_id: str,
        recovery_token: str,
        now: str,
        expires_at: str,
    ) -> None:
        with self._transaction() as conn:
            conn.execute(
                "INSERT INTO recovery_requests "
                "(request_id, organization_id, account_id, recovery_token, status, created_at, expires_at) "
                "VALUES (?, ?, ?, ?, 'pending', ?, ?)",
                (request_id, organization_id, account_id, recovery_token, now, expires_at),
            )

    def get_recovery_request(self, request_id: str) -> Optional[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM recovery_requests WHERE request_id = ?", (request_id,)
        ).fetchone()

    def get_recovery_request_by_token(self, token: str) -> Optional[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM recovery_requests WHERE recovery_token = ?", (token,)
        ).fetchone()

    def complete_recovery_request(self, request_id: str, now: str) -> None:
        with self._transaction() as conn:
            conn.execute(
                "UPDATE recovery_requests SET status = 'completed', completed_at = ? WHERE request_id = ?",
                (now, request_id),
            )

    # -- delivery attempts and provider receipts --------------------------

    def record_delivery_attempt(
        self,
        request_id: str,
        account_id: str,
        recipient: str,
        attempted_at: str,
        outcome: str,
        retry_locator: Optional[str],
        resolved_at: Optional[str],
    ) -> int:
        with self._transaction() as conn:
            cursor = conn.execute(
                "INSERT INTO delivery_attempts "
                "(request_id, account_id, recipient, attempted_at, outcome, retry_locator, retry_count, resolved_at) "
                "VALUES (?, ?, ?, ?, ?, ?, 0, ?)",
                (request_id, account_id, recipient, attempted_at, outcome, retry_locator, resolved_at),
            )
            return int(cursor.lastrowid)

    def record_provider_receipt(self, receipt_id: str, attempt_id: int, recorded_at: str, raw: str) -> None:
        with self._transaction() as conn:
            conn.execute(
                "INSERT INTO provider_receipts (receipt_id, attempt_id, recorded_at, raw) VALUES (?, ?, ?, ?)",
                (receipt_id, attempt_id, recorded_at, raw),
            )

    def get_delivery_attempt(self, attempt_id: int) -> Optional[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM delivery_attempts WHERE attempt_id = ?", (attempt_id,)
        ).fetchone()

    def resolve_delivery_attempt(
        self, attempt_id: int, outcome: str, retry_locator: Optional[str], resolved_at: Optional[str]
    ) -> None:
        with self._transaction() as conn:
            conn.execute(
                "UPDATE delivery_attempts SET outcome = ?, retry_locator = ?, resolved_at = ?, "
                "retry_count = retry_count + 1 WHERE attempt_id = ?",
                (outcome, retry_locator, resolved_at, attempt_id),
            )

    def list_delivery_history(self, account_id: str) -> list[sqlite3.Row]:
        """Delivery attempts for ``account_id``, oldest first.

        Never selects ``recovery_requests.recovery_token`` -- the request's
        ``status`` is the only thing pulled from that table, so there is no
        token for a caller of this query to accidentally leak.
        """
        return self._conn.execute(
            "SELECT da.attempt_id, da.request_id, da.recipient, da.attempted_at, da.outcome, "
            "da.retry_count, da.resolved_at, rr.status AS request_status, "
            "(SELECT pr.receipt_id FROM provider_receipts pr WHERE pr.attempt_id = da.attempt_id "
            "ORDER BY pr.id DESC LIMIT 1) AS receipt_id "
            "FROM delivery_attempts da "
            "JOIN recovery_requests rr ON rr.request_id = da.request_id "
            "WHERE da.account_id = ? ORDER BY da.attempt_id ASC",
            (account_id,),
        ).fetchall()
