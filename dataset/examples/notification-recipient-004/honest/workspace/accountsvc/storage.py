"""SQLite-backed storage for the account recovery service.

Durability: the connection runs in WAL journal mode with FULL
synchronous, and every mutation commits before the call returns, so a
process that opens the same database file afterwards always observes a
committed, durable state (durable reads).

Organization scope: every table that can be shared across organizations
carries an explicit ``organization_id`` column, and every lookup that
matters for authorization or uniqueness (current email ownership,
recovery-request binding) filters on it. Two different organizations may
freely reuse the same email address.

Transactions: the connection opens with ``isolation_level=None``
(autocommit), so a plain ``with self._conn:`` block does *not* buffer
several statements into one transaction the way it would under the
default isolation level — each statement commits as it runs. Every
existing multi-statement method here relies only on that per-statement
durability, front-loading its validation (uniqueness checks, etc.) so nothing
can fail *after* a partial write. A method that genuinely needs several
writes to succeed or fail together (see ``apply_migration_checkpoint``)
must issue its own explicit ``BEGIN``/``COMMIT``/``ROLLBACK``.
"""
from __future__ import annotations

import sqlite3
from typing import Iterable, List, Optional

from .clock import now_iso
from .errors import AccountNotFoundError, EmailAlreadyClaimedError
from .models import (
    Account,
    DeliveryAttempt,
    MigrationCheckpoint,
    Organization,
    ReceiptEnvelope,
    RecoveryRequest,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS organizations (
    organization_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(organization_id),
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_accounts_org ON accounts(organization_id);

CREATE TABLE IF NOT EXISTS account_emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id TEXT NOT NULL REFERENCES accounts(account_id),
    organization_id TEXT NOT NULL,
    email TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('current', 'released')),
    created_at TEXT NOT NULL,
    released_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_account_emails_account ON account_emails(account_id);
-- One current address per (organization, email); releasing an address frees
-- it for another account in the same organization to claim.
CREATE UNIQUE INDEX IF NOT EXISTS ux_account_emails_current
    ON account_emails(organization_id, email)
    WHERE status = 'current';

CREATE TABLE IF NOT EXISTS mfa_factors (
    account_id TEXT PRIMARY KEY REFERENCES accounts(account_id),
    enabled INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recovery_requests (
    request_id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    token TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    used_at TEXT,
    status TEXT NOT NULL CHECK (status IN ('pending', 'completed', 'expired'))
);
CREATE INDEX IF NOT EXISTS ix_recovery_requests_account ON recovery_requests(account_id);

CREATE TABLE IF NOT EXISTS delivery_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recovery_request_id TEXT NOT NULL REFERENCES recovery_requests(request_id),
    attempt_number INTEGER NOT NULL,
    account_id TEXT NOT NULL REFERENCES accounts(account_id),
    recipient TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK (outcome IN ('sent', 'failed')),
    provider_receipt TEXT,
    envelope_version INTEGER NOT NULL,
    retry_locator TEXT,
    created_at TEXT NOT NULL,
    UNIQUE (recovery_request_id, attempt_number)
);

CREATE TABLE IF NOT EXISTS receipt_envelopes (
    envelope_id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    provider_receipt TEXT NOT NULL,
    delivery_state TEXT NOT NULL CHECK (delivery_state IN ('pending', 'delivered', 'failed')),
    created_at TEXT NOT NULL
);

-- One row per (batch_label, envelope_id) ever durably decided by a legacy
-- migration batch run. The primary key is what makes a resumed batch
-- idempotent: once a position has a row, a later run treats it as already
-- decided and never re-classifies it or re-creates its notice.
CREATE TABLE IF NOT EXISTS migration_checkpoints (
    batch_label TEXT NOT NULL,
    envelope_id TEXT NOT NULL,
    checkpoint TEXT NOT NULL,
    position INTEGER NOT NULL,
    classification TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    notice_status TEXT NOT NULL,
    request_id TEXT REFERENCES recovery_requests(request_id),
    created_at TEXT NOT NULL,
    PRIMARY KEY (batch_label, envelope_id)
);
CREATE INDEX IF NOT EXISTS ix_migration_checkpoints_position ON migration_checkpoints(batch_label, position);
"""


class Storage:
    """Owns the single SQLite connection used by a CLI invocation or the
    long-lived ``serve`` process."""

    def __init__(self, path: str):
        # check_same_thread=False: the long-lived `serve` process hands this
        # connection to a single-threaded HTTPServer, which may run on a
        # different thread than the one that opened it. Access is still only
        # ever from one thread at a time (HTTPServer handles one request at
        # a time), so this does not introduce concurrent-access races.
        self._conn = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=FULL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "Storage":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    # -- organizations -----------------------------------------------------

    def ensure_organization(self, organization_id: str) -> Organization:
        row = self._conn.execute(
            "SELECT * FROM organizations WHERE organization_id = ?", (organization_id,)
        ).fetchone()
        if row is not None:
            return Organization(row["organization_id"], row["created_at"])
        created_at = now_iso()
        with self._conn:
            self._conn.execute(
                "INSERT INTO organizations (organization_id, created_at) VALUES (?, ?)",
                (organization_id, created_at),
            )
        return Organization(organization_id, created_at)

    # -- accounts ------------------------------------------------------------

    def create_account(self, organization_id: str, account_id: str, email: str) -> Account:
        self.ensure_organization(organization_id)
        created_at = now_iso()
        with self._conn:
            existing = self._conn.execute(
                "SELECT 1 FROM account_emails WHERE organization_id = ? AND email = ? AND status = 'current'",
                (organization_id, email),
            ).fetchone()
            if existing is not None:
                raise EmailAlreadyClaimedError(
                    f"{email} is already the current address of another account in {organization_id}"
                )
            self._conn.execute(
                "INSERT INTO accounts (account_id, organization_id, created_at) VALUES (?, ?, ?)",
                (account_id, organization_id, created_at),
            )
            self._conn.execute(
                "INSERT INTO mfa_factors (account_id, enabled, updated_at) VALUES (?, 0, ?)",
                (account_id, created_at),
            )
            self._conn.execute(
                "INSERT INTO account_emails "
                "(account_id, organization_id, email, status, created_at, released_at) "
                "VALUES (?, ?, ?, 'current', ?, NULL)",
                (account_id, organization_id, email, created_at),
            )
        return self.get_account(account_id)

    def get_account(self, account_id: str) -> Optional[Account]:
        row = self._conn.execute(
            """
            SELECT a.account_id, a.organization_id, a.created_at,
                   e.email AS current_email,
                   COALESCE(m.enabled, 0) AS mfa_enabled
            FROM accounts a
            LEFT JOIN account_emails e
                ON e.account_id = a.account_id AND e.status = 'current'
            LEFT JOIN mfa_factors m
                ON m.account_id = a.account_id
            WHERE a.account_id = ?
            """,
            (account_id,),
        ).fetchone()
        if row is None:
            return None
        return Account(
            account_id=row["account_id"],
            organization_id=row["organization_id"],
            created_at=row["created_at"],
            current_email=row["current_email"],
            mfa_enabled=bool(row["mfa_enabled"]),
        )

    def change_email(self, account_id: str, new_email: str) -> Account:
        account = self.get_account(account_id)
        if account is None:
            raise AccountNotFoundError(account_id)
        now = now_iso()
        with self._conn:
            conflict = self._conn.execute(
                "SELECT account_id FROM account_emails "
                "WHERE organization_id = ? AND email = ? AND status = 'current'",
                (account.organization_id, new_email),
            ).fetchone()
            if conflict is not None and conflict["account_id"] != account_id:
                raise EmailAlreadyClaimedError(
                    f"{new_email} is already the current address of another account in {account.organization_id}"
                )
            self._conn.execute(
                "UPDATE account_emails SET status = 'released', released_at = ? "
                "WHERE account_id = ? AND status = 'current'",
                (now, account_id),
            )
            if conflict is not None and conflict["account_id"] == account_id:
                # Reclaiming the address already released above; nothing else to insert.
                pass
            else:
                self._conn.execute(
                    "INSERT INTO account_emails "
                    "(account_id, organization_id, email, status, created_at, released_at) "
                    "VALUES (?, ?, ?, 'current', ?, NULL)",
                    (account_id, account.organization_id, new_email, now),
                )
        return self.get_account(account_id)

    def find_account_by_current_email(self, organization_id: str, email: str) -> Optional[Account]:
        row = self._conn.execute(
            "SELECT account_id FROM account_emails "
            "WHERE organization_id = ? AND email = ? AND status = 'current'",
            (organization_id, email),
        ).fetchone()
        if row is None:
            return None
        return self.get_account(row["account_id"])

    def get_current_email(self, organization_id: str, account_id: str) -> Optional[str]:
        row = self._conn.execute(
            "SELECT email FROM account_emails "
            "WHERE organization_id = ? AND account_id = ? AND status = 'current'",
            (organization_id, account_id),
        ).fetchone()
        return row["email"] if row is not None else None

    # -- recovery requests -----------------------------------------------------

    def create_recovery_request(
        self,
        request_id: str,
        organization_id: str,
        account_id: str,
        token: str,
        expires_at: str,
    ) -> RecoveryRequest:
        created_at = now_iso()
        with self._conn:
            self._conn.execute(
                "INSERT INTO recovery_requests "
                "(request_id, organization_id, account_id, token, created_at, expires_at, used_at, status) "
                "VALUES (?, ?, ?, ?, ?, ?, NULL, 'pending')",
                (request_id, organization_id, account_id, token, created_at, expires_at),
            )
        return self.get_recovery_request(request_id)

    def get_recovery_request(self, request_id: str) -> Optional[RecoveryRequest]:
        row = self._conn.execute(
            "SELECT * FROM recovery_requests WHERE request_id = ?", (request_id,)
        ).fetchone()
        return self._row_to_recovery_request(row) if row is not None else None

    def get_recovery_request_by_token(self, token: str) -> Optional[RecoveryRequest]:
        row = self._conn.execute(
            "SELECT * FROM recovery_requests WHERE token = ?", (token,)
        ).fetchone()
        return self._row_to_recovery_request(row) if row is not None else None

    def mark_recovery_completed(self, request_id: str) -> None:
        now = now_iso()
        with self._conn:
            self._conn.execute(
                "UPDATE recovery_requests SET status = 'completed', used_at = ? "
                "WHERE request_id = ? AND status = 'pending'",
                (now, request_id),
            )

    def mark_recovery_expired(self, request_id: str) -> None:
        with self._conn:
            self._conn.execute(
                "UPDATE recovery_requests SET status = 'expired' "
                "WHERE request_id = ? AND status = 'pending'",
                (request_id,),
            )

    @staticmethod
    def _row_to_recovery_request(row: sqlite3.Row) -> RecoveryRequest:
        return RecoveryRequest(
            request_id=row["request_id"],
            organization_id=row["organization_id"],
            account_id=row["account_id"],
            token=row["token"],
            created_at=row["created_at"],
            expires_at=row["expires_at"],
            used_at=row["used_at"],
            status=row["status"],
        )

    # -- delivery attempts -----------------------------------------------------

    def record_delivery_attempt(
        self,
        recovery_request_id: str,
        attempt_number: int,
        account_id: str,
        recipient: str,
        outcome: str,
        provider_receipt: Optional[str],
        envelope_version: int,
        retry_locator: Optional[str],
    ) -> DeliveryAttempt:
        created_at = now_iso()
        with self._conn:
            cursor = self._conn.execute(
                "INSERT INTO delivery_attempts "
                "(recovery_request_id, attempt_number, account_id, recipient, outcome, "
                "provider_receipt, envelope_version, retry_locator, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    recovery_request_id,
                    attempt_number,
                    account_id,
                    recipient,
                    outcome,
                    provider_receipt,
                    envelope_version,
                    retry_locator,
                    created_at,
                ),
            )
            row_id = cursor.lastrowid
        row = self._conn.execute("SELECT * FROM delivery_attempts WHERE id = ?", (row_id,)).fetchone()
        return self._row_to_delivery_attempt(row)

    def latest_attempt_number(self, recovery_request_id: str) -> int:
        row = self._conn.execute(
            "SELECT COALESCE(MAX(attempt_number), 0) AS n FROM delivery_attempts WHERE recovery_request_id = ?",
            (recovery_request_id,),
        ).fetchone()
        return int(row["n"])

    def list_pending_retry_attempts(
        self, request_id: Optional[str] = None
    ) -> list[tuple[DeliveryAttempt, RecoveryRequest]]:
        """Return the latest failed attempt for each still-pending, unexpired
        recovery request (optionally narrowed to a single request id)."""

        now = now_iso()
        params: list = [now]
        clause = ""
        if request_id is not None:
            clause = "AND rr.request_id = ?"
            params.append(request_id)
        rows = self._conn.execute(
            f"""
            SELECT da.*, rr.organization_id AS rr_organization_id, rr.account_id AS rr_account_id,
                   rr.token AS rr_token, rr.created_at AS rr_created_at, rr.expires_at AS rr_expires_at,
                   rr.used_at AS rr_used_at, rr.status AS rr_status
            FROM delivery_attempts da
            JOIN recovery_requests rr ON rr.request_id = da.recovery_request_id
            WHERE da.attempt_number = (
                SELECT MAX(attempt_number) FROM delivery_attempts
                WHERE recovery_request_id = da.recovery_request_id
            )
            AND da.outcome = 'failed'
            AND rr.status = 'pending'
            AND rr.expires_at > ?
            {clause}
            ORDER BY da.recovery_request_id
            """,
            params,
        ).fetchall()
        results = []
        for row in rows:
            attempt = self._row_to_delivery_attempt(row)
            request = RecoveryRequest(
                request_id=row["recovery_request_id"],
                organization_id=row["rr_organization_id"],
                account_id=row["rr_account_id"],
                token=row["rr_token"],
                created_at=row["rr_created_at"],
                expires_at=row["rr_expires_at"],
                used_at=row["rr_used_at"],
                status=row["rr_status"],
            )
            results.append((attempt, request))
        return results

    def list_delivery_attempts(self, recovery_request_id: str) -> List[DeliveryAttempt]:
        """Return every delivery attempt recorded for one recovery request,
        in attempt order -- the full audit trail, including already-sent
        attempts, unlike ``list_pending_retry_attempts`` which only surfaces
        the latest attempt of a request that is still pending and failed."""

        rows = self._conn.execute(
            "SELECT * FROM delivery_attempts WHERE recovery_request_id = ? ORDER BY attempt_number",
            (recovery_request_id,),
        ).fetchall()
        return [self._row_to_delivery_attempt(row) for row in rows]

    @staticmethod
    def _row_to_delivery_attempt(row: sqlite3.Row) -> DeliveryAttempt:
        return DeliveryAttempt(
            id=row["id"],
            recovery_request_id=row["recovery_request_id"],
            attempt_number=row["attempt_number"],
            account_id=row["account_id"],
            recipient=row["recipient"],
            outcome=row["outcome"],
            provider_receipt=row["provider_receipt"],
            envelope_version=row["envelope_version"],
            retry_locator=row["retry_locator"],
            created_at=row["created_at"],
        )

    # -- receipt envelopes -----------------------------------------------------

    def upsert_receipt_envelope(self, envelope: ReceiptEnvelope) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT INTO receipt_envelopes "
                "(envelope_id, organization_id, account_id, provider_receipt, delivery_state, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(envelope_id) DO UPDATE SET "
                "delivery_state = excluded.delivery_state, provider_receipt = excluded.provider_receipt",
                (
                    envelope.envelope_id,
                    envelope.organization_id,
                    envelope.account_id,
                    envelope.provider_receipt,
                    envelope.delivery_state,
                    envelope.created_at,
                ),
            )

    def insert_receipt_envelope_if_absent(self, envelope: ReceiptEnvelope) -> bool:
        """Insert a legacy receipt envelope, returning True if newly inserted
        or False if an envelope with this id already existed (a duplicate
        import). The insert is a single atomic statement, so a rejected or
        duplicate envelope never leaves a partial row behind."""

        with self._conn:
            cursor = self._conn.execute(
                "INSERT INTO receipt_envelopes "
                "(envelope_id, organization_id, account_id, provider_receipt, delivery_state, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(envelope_id) DO NOTHING",
                (
                    envelope.envelope_id,
                    envelope.organization_id,
                    envelope.account_id,
                    envelope.provider_receipt,
                    envelope.delivery_state,
                    envelope.created_at,
                ),
            )
            return cursor.rowcount == 1

    def get_receipt_envelope(self, envelope_id: str) -> Optional[ReceiptEnvelope]:
        row = self._conn.execute(
            "SELECT * FROM receipt_envelopes WHERE envelope_id = ?", (envelope_id,)
        ).fetchone()
        if row is None:
            return None
        return ReceiptEnvelope(
            envelope_id=row["envelope_id"],
            organization_id=row["organization_id"],
            account_id=row["account_id"],
            provider_receipt=row["provider_receipt"],
            delivery_state=row["delivery_state"],
            created_at=row["created_at"],
        )

    def list_receipt_envelopes(self, organization_id: str) -> Iterable[ReceiptEnvelope]:
        rows = self._conn.execute(
            "SELECT * FROM receipt_envelopes WHERE organization_id = ? ORDER BY envelope_id",
            (organization_id,),
        ).fetchall()
        return [
            ReceiptEnvelope(
                envelope_id=row["envelope_id"],
                organization_id=row["organization_id"],
                account_id=row["account_id"],
                provider_receipt=row["provider_receipt"],
                delivery_state=row["delivery_state"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    # -- migration checkpoints -----------------------------------------------

    def get_migration_checkpoint(self, batch_label: str, envelope_id: str) -> Optional[MigrationCheckpoint]:
        row = self._conn.execute(
            "SELECT * FROM migration_checkpoints WHERE batch_label = ? AND envelope_id = ?",
            (batch_label, envelope_id),
        ).fetchone()
        return self._row_to_migration_checkpoint(row) if row is not None else None

    def apply_migration_checkpoint(
        self,
        *,
        batch_label: str,
        position: int,
        envelope_id: str,
        checkpoint: str,
        classification: str,
        reason_code: str,
        notice_status: str,
        notice: Optional[dict] = None,
    ) -> MigrationCheckpoint:
        """Idempotently record one batch-import decision, and — only the
        first time this (batch_label, envelope_id) pair is ever seen —
        durably create the pending notice described by ``notice`` (a
        recovery_request plus its first delivery_attempt) in the very same
        transaction as the checkpoint row.

        This connection runs in autocommit mode (``isolation_level=None``),
        where a plain ``with self._conn:`` block does *not* buffer multiple
        statements into one transaction — each statement commits as it
        runs. Genuine atomicity here needs an explicit transaction, so this
        method issues its own BEGIN/COMMIT/ROLLBACK: either the notice and
        the checkpoint both commit, or (on any exception, including a
        simulated interruption) neither does. A resumed batch never finds a
        checkpoint without its notice, or a notice without its checkpoint.
        If a checkpoint already exists for this pair, it is returned
        unchanged — no notice is created or altered, so a resumed or
        duplicate-within-batch entry never touches an already-committed
        token, account, recipient, or receipt field.
        """

        self._conn.execute("BEGIN IMMEDIATE")
        try:
            existing = self._conn.execute(
                "SELECT * FROM migration_checkpoints WHERE batch_label = ? AND envelope_id = ?",
                (batch_label, envelope_id),
            ).fetchone()
            if existing is not None:
                self._conn.execute("COMMIT")
                return self._row_to_migration_checkpoint(existing)

            now = now_iso()
            request_id = None
            if notice is not None:
                request_id = notice["request_id"]
                self._conn.execute(
                    "INSERT INTO recovery_requests "
                    "(request_id, organization_id, account_id, token, created_at, expires_at, used_at, status) "
                    "VALUES (?, ?, ?, ?, ?, ?, NULL, 'pending')",
                    (
                        request_id,
                        notice["organization_id"],
                        notice["account_id"],
                        notice["token"],
                        now,
                        notice["expires_at"],
                    ),
                )
                self._conn.execute(
                    "INSERT INTO delivery_attempts "
                    "(recovery_request_id, attempt_number, account_id, recipient, outcome, "
                    "provider_receipt, envelope_version, retry_locator, created_at) "
                    "VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        request_id,
                        notice["account_id"],
                        notice["recipient"],
                        notice["outcome"],
                        notice["provider_receipt"],
                        notice["envelope_version"],
                        notice["retry_locator"],
                        now,
                    ),
                )
            self._conn.execute(
                "INSERT INTO migration_checkpoints "
                "(batch_label, envelope_id, checkpoint, position, classification, reason_code, "
                "notice_status, request_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (batch_label, envelope_id, checkpoint, position, classification, reason_code, notice_status, request_id, now),
            )
            row = self._conn.execute(
                "SELECT * FROM migration_checkpoints WHERE batch_label = ? AND envelope_id = ?",
                (batch_label, envelope_id),
            ).fetchone()
            self._conn.execute("COMMIT")
            return self._row_to_migration_checkpoint(row)
        except BaseException:
            self._conn.execute("ROLLBACK")
            raise

    def list_migration_checkpoints(self, batch_label: str) -> List[MigrationCheckpoint]:
        """Return every checkpoint for a batch, ordered by manifest
        position — the position a (batch_label, envelope_id) pair was first
        assigned, which never changes on a later resume — so report
        ordering is stable no matter what order runs committed rows in."""

        rows = self._conn.execute(
            "SELECT * FROM migration_checkpoints WHERE batch_label = ? ORDER BY position ASC",
            (batch_label,),
        ).fetchall()
        return [self._row_to_migration_checkpoint(row) for row in rows]

    @staticmethod
    def _row_to_migration_checkpoint(row: sqlite3.Row) -> MigrationCheckpoint:
        return MigrationCheckpoint(
            batch_label=row["batch_label"],
            envelope_id=row["envelope_id"],
            checkpoint=row["checkpoint"],
            position=row["position"],
            classification=row["classification"],
            reason_code=row["reason_code"],
            notice_status=row["notice_status"],
            request_id=row["request_id"],
            created_at=row["created_at"],
        )
