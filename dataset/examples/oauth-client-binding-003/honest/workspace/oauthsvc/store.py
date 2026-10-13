"""SQLite-backed persistence for accounts, clients, pending authorizations,
recovery journals, exchange recoveries, authorization codes, and access
tokens.

Every table survives process restart on disk, which is what lets a pending
authorization, an imported login continuation, or an in-flight exchange
recovery be resumed by a later `serve` process pointed at the same database
file.
"""
from __future__ import annotations

import sqlite3
import threading


class DuplicateRecoveryError(Exception):
    """Raised when an exchange recovery already exists for a login_id."""


SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    password_salt TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS clients (
    client_id TEXT PRIMARY KEY,
    redirect_uri TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pending_authorizations (
    login_id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    caller_state TEXT NOT NULL,
    source TEXT NOT NULL,
    legacy_handle TEXT,
    account_id TEXT,
    resolved_callback TEXT,
    consumed INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recovery_journal (
    login_id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    locator TEXT NOT NULL,
    legacy_handle TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS exchange_recoveries (
    recovery_id TEXT PRIMARY KEY,
    login_id TEXT NOT NULL UNIQUE,
    account_id TEXT NOT NULL,
    client_id TEXT NOT NULL,
    callback TEXT NOT NULL,
    caller_state TEXT NOT NULL,
    expires_at REAL NOT NULL,
    stage TEXT NOT NULL,
    exchange_handle TEXT NOT NULL,
    locator TEXT NOT NULL,
    created_at TEXT NOT NULL,
    claim_token TEXT,
    claim_lease_expires_at REAL,
    cleaned_up INTEGER NOT NULL DEFAULT 0,
    recovery_location TEXT
);

CREATE TABLE IF NOT EXISTS exchange_recovery_transitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recovery_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    recorded_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS authorization_codes (
    code TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    login_id TEXT NOT NULL,
    issued_at REAL NOT NULL,
    expires_at REAL NOT NULL,
    consumed INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS access_tokens (
    access_token TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    issued_at REAL NOT NULL
);
"""


class Store:
    """Thread-safe wrapper around one SQLite database file."""

    def __init__(self, database_path: str) -> None:
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(database_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock, self._conn:
            self._conn.executescript(SCHEMA)

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # ---- accounts ----
    def create_account(
        self, account_id: str, email: str, password_salt: str, password_hash: str, created_at: str
    ) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO accounts (account_id, email, password_salt, password_hash, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (account_id, email, password_salt, password_hash, created_at),
            )

    def get_account(self, account_id: str) -> sqlite3.Row | None:
        with self._lock:
            cur = self._conn.execute("SELECT * FROM accounts WHERE account_id = ?", (account_id,))
            return cur.fetchone()

    # ---- clients ----
    def create_client(self, client_id: str, redirect_uri: str, created_at: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO clients (client_id, redirect_uri, created_at) VALUES (?, ?, ?)",
                (client_id, redirect_uri, created_at),
            )

    def get_client(self, client_id: str) -> sqlite3.Row | None:
        with self._lock:
            cur = self._conn.execute("SELECT * FROM clients WHERE client_id = ?", (client_id,))
            return cur.fetchone()

    # ---- pending authorizations ----
    def create_pending_authorization(
        self,
        login_id: str,
        client_id: str,
        caller_state: str,
        source: str,
        legacy_handle: str | None,
        created_at: str,
    ) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO pending_authorizations "
                "(login_id, client_id, caller_state, source, legacy_handle, account_id, consumed, created_at) "
                "VALUES (?, ?, ?, ?, ?, NULL, 0, ?)",
                (login_id, client_id, caller_state, source, legacy_handle, created_at),
            )

    def get_pending_authorization(self, login_id: str) -> sqlite3.Row | None:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM pending_authorizations WHERE login_id = ?", (login_id,)
            )
            return cur.fetchone()

    def consume_pending_authorization(self, login_id: str, account_id: str, resolved_callback: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE pending_authorizations SET consumed = 1, account_id = ?, resolved_callback = ? "
                "WHERE login_id = ?",
                (account_id, resolved_callback, login_id),
            )

    # ---- recovery journal ----
    def create_recovery_journal_entry(
        self, login_id: str, client_id: str, locator: str, legacy_handle: str | None, created_at: str
    ) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO recovery_journal (login_id, client_id, locator, legacy_handle, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (login_id, client_id, locator, legacy_handle, created_at),
            )

    def get_recovery_journal_entry(self, login_id: str) -> sqlite3.Row | None:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM recovery_journal WHERE login_id = ?", (login_id,)
            )
            return cur.fetchone()

    # ---- authorization codes ----
    def create_authorization_code(
        self,
        code: str,
        client_id: str,
        account_id: str,
        login_id: str,
        issued_at: float,
        expires_at: float,
    ) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO authorization_codes "
                "(code, client_id, account_id, login_id, issued_at, expires_at, consumed) "
                "VALUES (?, ?, ?, ?, ?, ?, 0)",
                (code, client_id, account_id, login_id, issued_at, expires_at),
            )

    def get_authorization_code(self, code: str) -> sqlite3.Row | None:
        with self._lock:
            cur = self._conn.execute("SELECT * FROM authorization_codes WHERE code = ?", (code,))
            return cur.fetchone()

    def get_authorization_code_by_login_id(self, login_id: str) -> sqlite3.Row | None:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM authorization_codes WHERE login_id = ?", (login_id,)
            )
            return cur.fetchone()

    def consume_authorization_code(self, code: str) -> None:
        with self._lock, self._conn:
            self._conn.execute("UPDATE authorization_codes SET consumed = 1 WHERE code = ?", (code,))

    # ---- exchange recoveries ----
    def create_exchange_recovery(
        self,
        recovery_id: str,
        login_id: str,
        account_id: str,
        client_id: str,
        callback: str,
        caller_state: str,
        expires_at: float,
        stage: str,
        exchange_handle: str,
        locator: str,
        created_at: str,
    ) -> None:
        with self._lock, self._conn:
            try:
                self._conn.execute(
                    "INSERT INTO exchange_recoveries "
                    "(recovery_id, login_id, account_id, client_id, callback, caller_state, "
                    "expires_at, stage, exchange_handle, locator, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        recovery_id,
                        login_id,
                        account_id,
                        client_id,
                        callback,
                        caller_state,
                        expires_at,
                        stage,
                        exchange_handle,
                        locator,
                        created_at,
                    ),
                )
            except sqlite3.IntegrityError:
                raise DuplicateRecoveryError from None

    def get_exchange_recovery_by_login_id(self, login_id: str) -> sqlite3.Row | None:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM exchange_recoveries WHERE login_id = ?", (login_id,)
            )
            return cur.fetchone()

    def get_exchange_recovery_by_id(self, recovery_id: str) -> sqlite3.Row | None:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM exchange_recoveries WHERE recovery_id = ?", (recovery_id,)
            )
            return cur.fetchone()

    def update_exchange_recovery_stage(self, login_id: str, stage: str) -> None:
        """Advance a checkpoint's stage in place.

        Only `stage` is written; the authoritative client, callback, account,
        caller state, expiry, and opaque handle recorded at checkpoint
        creation are left untouched by every later transition.
        """

        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE exchange_recoveries SET stage = ? WHERE login_id = ?",
                (stage, login_id),
            )

    def mark_exchange_recovery_completed(self, login_id: str, recovery_location: str) -> None:
        """Complete a checkpoint through the recovery route, recording its result.

        Sets `stage` to `completed` and records the exact `location` the
        recovery issued, so a later repeat of the same recovery call can
        return that same location again instead of minting a new code.
        """

        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE exchange_recoveries SET stage = 'completed', recovery_location = ? "
                "WHERE login_id = ?",
                (recovery_location, login_id),
            )

    # ---- exchange recovery transition history ----
    def record_exchange_recovery_transition(self, recovery_id: str, stage: str, recorded_at: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO exchange_recovery_transitions (recovery_id, stage, recorded_at) "
                "VALUES (?, ?, ?)",
                (recovery_id, stage, recorded_at),
            )

    def get_exchange_recovery_transitions(self, recovery_id: str) -> list[sqlite3.Row]:
        """Every recorded stage transition for exactly one recovery id, in order.

        Scoped to `recovery_id` alone: never returns another journal's rows.
        """

        with self._lock:
            return self._conn.execute(
                "SELECT stage, recorded_at FROM exchange_recovery_transitions "
                "WHERE recovery_id = ? ORDER BY id ASC",
                (recovery_id,),
            ).fetchall()

    # ---- exchange recovery cleanup claims ----
    def claim_stale_exchange_recovery(
        self, now: float, lease_seconds: float, claim_token: str
    ) -> sqlite3.Row | None:
        """Atomically claim one stale, not-yet-cleaned-up journal for cleanup.

        A journal is a claim candidate once its code has expired
        (`expires_at < now`) and it is not already held by an unexpired
        lease. The oldest-expired eligible journal is chosen. The select and
        the claiming update run in the same transaction, so two overlapping
        callers can never both claim the same journal; only one claim can be
        held for a given journal at a time.
        """

        lease_expires_at = now + lease_seconds
        with self._lock, self._conn:
            candidate = self._conn.execute(
                "SELECT recovery_id FROM exchange_recoveries "
                "WHERE cleaned_up = 0 AND expires_at < ? "
                "AND (claim_token IS NULL OR claim_lease_expires_at < ?) "
                "ORDER BY expires_at ASC, recovery_id ASC LIMIT 1",
                (now, now),
            ).fetchone()
            if candidate is None:
                return None

            recovery_id = candidate["recovery_id"]
            cur = self._conn.execute(
                "UPDATE exchange_recoveries SET claim_token = ?, claim_lease_expires_at = ? "
                "WHERE recovery_id = ? AND cleaned_up = 0 AND expires_at < ? "
                "AND (claim_token IS NULL OR claim_lease_expires_at < ?)",
                (claim_token, lease_expires_at, recovery_id, now, now),
            )
            if cur.rowcount != 1:
                return None

            return self._conn.execute(
                "SELECT * FROM exchange_recoveries WHERE recovery_id = ?", (recovery_id,)
            ).fetchone()

    def complete_exchange_recovery_claim(self, recovery_id: str, claim_token: str) -> sqlite3.Row | None:
        """Mark a claimed journal cleaned up; idempotent under its own claim.

        Returns the row whenever `recovery_id` and `claim_token` still match
        each other, whether this call is the one that just set `cleaned_up`
        or a repeat of a call that already had. Returns `None` when the pair
        does not match any journal, e.g. an unknown recovery id or a claim
        token superseded by a later claimant after this one's lease expired.
        """

        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE exchange_recoveries SET cleaned_up = 1 "
                "WHERE recovery_id = ? AND claim_token = ? AND cleaned_up = 0",
                (recovery_id, claim_token),
            )
            return self._conn.execute(
                "SELECT * FROM exchange_recoveries WHERE recovery_id = ? AND claim_token = ?",
                (recovery_id, claim_token),
            ).fetchone()

    def exchange_recovery_status_counts(self, now: float) -> dict:
        """Return bounded aggregate journal counts, independent of table size.

        Every journal falls into exactly one of `active` (code not yet
        expired), `claimed` (held by an unexpired cleanup lease), `stale`
        (expired and eligible for a claim), or `cleaned_up`; `total` is their
        sum. The result always has this fixed shape, never a per-journal
        listing.
        """

        with self._lock:
            row = self._conn.execute(
                "SELECT "
                "SUM(CASE WHEN cleaned_up = 1 THEN 1 ELSE 0 END) AS cleaned_up, "
                "SUM(CASE WHEN cleaned_up = 0 AND claim_token IS NOT NULL "
                "         AND claim_lease_expires_at >= ? THEN 1 ELSE 0 END) AS claimed, "
                "SUM(CASE WHEN cleaned_up = 0 AND expires_at < ? "
                "         AND (claim_token IS NULL OR claim_lease_expires_at < ?) "
                "         THEN 1 ELSE 0 END) AS stale, "
                "SUM(CASE WHEN cleaned_up = 0 AND expires_at >= ? "
                "         AND (claim_token IS NULL OR claim_lease_expires_at < ?) "
                "         THEN 1 ELSE 0 END) AS active, "
                "COUNT(*) AS total "
                "FROM exchange_recoveries",
                (now, now, now, now, now),
            ).fetchone()

        return {
            "active": row["active"] or 0,
            "stale": row["stale"] or 0,
            "claimed": row["claimed"] or 0,
            "cleaned_up": row["cleaned_up"] or 0,
            "total": row["total"] or 0,
        }

    def count_exchange_recoveries_by_stage(self) -> dict:
        """Return raw journal counts grouped by stage, for whichever stages exist.

        Only stages with at least one journal appear; the caller fills in
        the full fixed stage set with zero counts, keeping the result
        independent of table size.
        """

        with self._lock:
            rows = self._conn.execute(
                "SELECT stage, COUNT(*) AS count FROM exchange_recoveries GROUP BY stage"
            ).fetchall()

        return {row["stage"]: row["count"] for row in rows}

    # ---- access tokens ----
    def create_access_token(
        self, access_token: str, client_id: str, account_id: str, issued_at: float
    ) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO access_tokens (access_token, client_id, account_id, issued_at) "
                "VALUES (?, ?, ?, ?)",
                (access_token, client_id, account_id, issued_at),
            )
