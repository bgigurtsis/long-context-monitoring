"""SQLite-backed persistence for the OAuth authorization-code service.

Models import batches, accounts, clients, pending authorizations,
authorization codes, and issued tokens in one durable state file.
"""
from __future__ import annotations

import sqlite3
import threading
import time
from dataclasses import dataclass

_SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    password_salt TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS clients (
    client_id TEXT PRIMARY KEY,
    redirect_uri TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS import_batches (
    batch_id TEXT PRIMARY KEY,
    row_count INTEGER NOT NULL,
    status TEXT NOT NULL,
    imported_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS import_batch_rows (
    batch_id TEXT NOT NULL,
    row_index INTEGER NOT NULL,
    outcome TEXT NOT NULL,
    error TEXT,
    account_id TEXT,
    client_id TEXT,
    state TEXT,
    resume_value TEXT,
    legacy_handle TEXT,
    login_id TEXT,
    PRIMARY KEY (batch_id, row_index)
);

CREATE TABLE IF NOT EXISTS pending_authorizations (
    login_id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    state TEXT NOT NULL,
    resume_kind TEXT NOT NULL,
    resume_value TEXT NOT NULL,
    import_batch_id TEXT,
    legacy_handle TEXT,
    source_account_id TEXT,
    status TEXT NOT NULL,
    account_id TEXT,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS authorization_codes (
    code TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    login_id TEXT NOT NULL,
    used INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS tokens (
    access_token TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    code TEXT NOT NULL,
    issued_at REAL NOT NULL
);
"""


@dataclass
class Account:
    account_id: str
    email: str
    password_hash: str
    password_salt: str


@dataclass
class Client:
    client_id: str
    redirect_uri: str


@dataclass
class PendingAuthorization:
    login_id: str
    client_id: str
    state: str
    resume_kind: str
    resume_value: str
    import_batch_id: str | None
    legacy_handle: str | None
    source_account_id: str | None
    status: str
    account_id: str | None
    expires_at: float


@dataclass
class AuthorizationCode:
    code: str
    client_id: str
    account_id: str
    login_id: str
    used: bool
    expires_at: float


class Store:
    """Thread-safe access to one SQLite-backed state file."""

    def __init__(self, database_path: str) -> None:
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(database_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock, self._conn:
            self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # -- accounts ---------------------------------------------------
    def create_account(
        self, account_id: str, email: str, password_hash: str, password_salt: str
    ) -> bool:
        with self._lock, self._conn:
            try:
                self._conn.execute(
                    "INSERT INTO accounts"
                    " (account_id, email, password_hash, password_salt, created_at)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (account_id, email, password_hash, password_salt, time.time()),
                )
            except sqlite3.IntegrityError:
                return False
            return True

    def get_account(self, account_id: str) -> Account | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT account_id, email, password_hash, password_salt"
                " FROM accounts WHERE account_id = ?",
                (account_id,),
            ).fetchone()
        return Account(**dict(row)) if row else None

    # -- clients ------------------------------------------------------
    def register_client(self, client_id: str, redirect_uri: str) -> bool:
        with self._lock, self._conn:
            try:
                self._conn.execute(
                    "INSERT INTO clients (client_id, redirect_uri, created_at) VALUES (?, ?, ?)",
                    (client_id, redirect_uri, time.time()),
                )
            except sqlite3.IntegrityError:
                return False
            return True

    def get_client(self, client_id: str) -> Client | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT client_id, redirect_uri FROM clients WHERE client_id = ?",
                (client_id,),
            ).fetchone()
        return Client(**dict(row)) if row else None

    # -- import batches ------------------------------------------------
    def create_single_row_import(
        self,
        batch_id: str,
        login_id: str,
        client_id: str,
        state: str,
        resume_kind: str,
        resume_value: str,
        ttl_seconds: float,
        legacy_handle: str,
    ) -> bool:
        """Atomically record one immediately-committed batch and its
        pending authorization for the single-row legacy importer, but only
        if no committed provenance record already exists for this (client,
        legacy handle) identity. Returns False and creates nothing on
        conflict, preserving whichever provenance record was accepted
        first; returns True once the pending authorization is written and
        completable."""

        now = time.time()
        with self._lock, self._conn:
            conflict = self._conn.execute(
                "SELECT 1 FROM pending_authorizations"
                " WHERE resume_kind = 'import' AND client_id = ? AND legacy_handle = ? LIMIT 1",
                (client_id, legacy_handle),
            ).fetchone()
            if conflict is not None:
                return False

            self._conn.execute(
                "INSERT INTO import_batches (batch_id, row_count, status, imported_at)"
                " VALUES (?, 1, 'committed', ?)",
                (batch_id, now),
            )
            self._conn.execute(
                "INSERT INTO import_batch_rows"
                " (batch_id, row_index, outcome, error, account_id, client_id,"
                "  state, resume_value, legacy_handle, login_id)"
                " VALUES (?, 0, 'committed', NULL, NULL, ?, ?, ?, ?, ?)",
                (batch_id, client_id, state, resume_value, legacy_handle, login_id),
            )
            self._conn.execute(
                "INSERT INTO pending_authorizations"
                " (login_id, client_id, state, resume_kind, resume_value, import_batch_id,"
                "  legacy_handle, source_account_id, status, account_id, created_at, expires_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, NULL, 'pending', NULL, ?, ?)",
                (
                    login_id,
                    client_id,
                    state,
                    resume_kind,
                    resume_value,
                    batch_id,
                    legacy_handle,
                    now,
                    now + ttl_seconds,
                ),
            )
            return True

    def get_import_batch(self, batch_id: str) -> dict | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT batch_id, row_count, status, imported_at FROM import_batches WHERE batch_id = ?",
                (batch_id,),
            ).fetchone()
        return dict(row) if row else None

    def create_quarantined_batch(self, batch_id: str, rows: list[dict]) -> None:
        """Atomically record one dry-run batch and the accept/reject
        outcome of every row it contained. Accepted rows are held in
        `import_batch_rows` only; they are not written into
        `pending_authorizations` (and so cannot be completed) until
        :meth:`commit_import_batch` promotes them."""

        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO import_batches (batch_id, row_count, status, imported_at)"
                " VALUES (?, ?, 'quarantined', ?)",
                (batch_id, len(rows), time.time()),
            )
            self._conn.executemany(
                "INSERT INTO import_batch_rows"
                " (batch_id, row_index, outcome, error, account_id, client_id,"
                "  state, resume_value, legacy_handle, login_id)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        batch_id,
                        row["row_index"],
                        row["outcome"],
                        row.get("error"),
                        row.get("account_id"),
                        row.get("client_id"),
                        row.get("state"),
                        row.get("resume_value"),
                        row.get("legacy_handle"),
                        row.get("login_id"),
                    )
                    for row in rows
                ],
            )

    def commit_import_batch(self, batch_id: str, ttl_seconds: float) -> dict | None:
        """Atomically commit a quarantined batch. Every accepted row is
        reconciled, in row-index order, against whichever provenance
        record already holds its (client, legacy handle) identity —
        either an earlier row already promoted in this same pass, or a
        record some other batch (or the single-row importer) already
        committed. The first accepted row to reach commit for a given
        identity is promoted into a completable pending authorization and
        its outcome becomes ``committed``; every later row for that same
        identity is left out of ``pending_authorizations`` entirely and its
        outcome becomes ``conflict``, so no already-accepted pending
        authorization is ever changed by a later commit.

        Returns None for a repeated or concurrent call on an
        already-committed batch (no change). Otherwise returns
        ``{"committed_row_indexes": [...], "conflicted_row_indexes": [...]}``
        for the caller that performs the reconciliation."""

        now = time.time()
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "UPDATE import_batches SET status = 'committed'"
                " WHERE batch_id = ? AND status != 'committed'",
                (batch_id,),
            )
            if cursor.rowcount == 0:
                return None

            rows = self._conn.execute(
                "SELECT row_index, login_id, client_id, state, resume_value,"
                " legacy_handle, account_id"
                " FROM import_batch_rows WHERE batch_id = ? AND outcome = 'accepted'"
                " ORDER BY row_index",
                (batch_id,),
            ).fetchall()

            committed_row_indexes = []
            conflicted_row_indexes = []
            promoted_in_pass = set()
            for row in rows:
                identity = (row["client_id"], row["legacy_handle"])
                already_committed = self._conn.execute(
                    "SELECT 1 FROM pending_authorizations"
                    " WHERE resume_kind = 'import' AND client_id = ? AND legacy_handle = ? LIMIT 1",
                    identity,
                ).fetchone()
                if already_committed is not None or identity in promoted_in_pass:
                    self._conn.execute(
                        "UPDATE import_batch_rows SET outcome = 'conflict'"
                        " WHERE batch_id = ? AND row_index = ?",
                        (batch_id, row["row_index"]),
                    )
                    conflicted_row_indexes.append(row["row_index"])
                    continue

                self._conn.execute(
                    "INSERT INTO pending_authorizations"
                    " (login_id, client_id, state, resume_kind, resume_value, import_batch_id,"
                    "  legacy_handle, source_account_id, status, account_id, created_at, expires_at)"
                    " VALUES (?, ?, ?, 'import', ?, ?, ?, ?, 'pending', NULL, ?, ?)",
                    (
                        row["login_id"],
                        row["client_id"],
                        row["state"],
                        row["resume_value"],
                        batch_id,
                        row["legacy_handle"],
                        row["account_id"],
                        now,
                        now + ttl_seconds,
                    ),
                )
                self._conn.execute(
                    "UPDATE import_batch_rows SET outcome = 'committed'"
                    " WHERE batch_id = ? AND row_index = ?",
                    (batch_id, row["row_index"]),
                )
                promoted_in_pass.add(identity)
                committed_row_indexes.append(row["row_index"])

            return {
                "committed_row_indexes": committed_row_indexes,
                "conflicted_row_indexes": conflicted_row_indexes,
            }

    def get_import_batch_row_counts(self, batch_id: str) -> dict:
        """Bounded (fixed-size) row-outcome counts for one batch: never
        grows with batch size and never carries any row's identifiers or
        opaque legacy handle, only per-outcome totals."""

        with self._lock:
            rows = self._conn.execute(
                "SELECT outcome, COUNT(*) AS n FROM import_batch_rows"
                " WHERE batch_id = ? GROUP BY outcome",
                (batch_id,),
            ).fetchall()
        counts = {"rejected": 0, "accepted": 0, "committed": 0, "conflict": 0}
        for row in rows:
            counts[row["outcome"]] = row["n"]
        return counts

    def get_import_batch_row_receipt(self, batch_id: str, row_index: int) -> dict | None:
        """Read-only receipt lookup for one source row, scoped to
        (batch_id, row_index). Returns None if no row exists at that
        position in that batch. Only ever selects columns already safe to
        return to a caller elsewhere in this service — the row's opaque
        legacy handle and encoded resume locator are never part of the
        query, so redaction cannot be forgotten downstream."""

        with self._lock:
            row = self._conn.execute(
                "SELECT outcome, error, account_id, client_id, login_id"
                " FROM import_batch_rows WHERE batch_id = ? AND row_index = ?",
                (batch_id, row_index),
            ).fetchone()
            if row is None:
                return None

            pending_status = None
            if row["login_id"] is not None:
                pending = self._conn.execute(
                    "SELECT status FROM pending_authorizations WHERE login_id = ?",
                    (row["login_id"],),
                ).fetchone()
                if pending is not None:
                    pending_status = pending["status"]

        return {
            "outcome": row["outcome"],
            "error": row["error"],
            "account_id": row["account_id"],
            "client_id": row["client_id"],
            "login_id": row["login_id"],
            "pending_status": pending_status,
        }

    def find_import_by_client_and_legacy_handle(self, client_id: str, legacy_handle: str) -> bool:
        """True if this (client, legacy handle) pair has already been
        committed (imported directly or promoted from a batch), regardless
        of whether that import has since completed."""

        with self._lock:
            row = self._conn.execute(
                "SELECT 1 FROM pending_authorizations"
                " WHERE resume_kind = 'import' AND client_id = ? AND legacy_handle = ? LIMIT 1",
                (client_id, legacy_handle),
            ).fetchone()
        return row is not None

    def find_quarantined_import_by_client_and_legacy_handle(
        self, client_id: str, legacy_handle: str
    ) -> bool:
        """True if this (client, legacy handle) pair was already accepted
        into some batch's quarantine, whether or not that batch has since
        been committed."""

        with self._lock:
            row = self._conn.execute(
                "SELECT 1 FROM import_batch_rows"
                " WHERE outcome = 'accepted' AND client_id = ? AND legacy_handle = ? LIMIT 1",
                (client_id, legacy_handle),
            ).fetchone()
        return row is not None

    # -- pending authorizations -----------------------------------------
    def create_pending_authorization(
        self,
        login_id: str,
        client_id: str,
        state: str,
        resume_kind: str,
        resume_value: str,
        import_batch_id: str | None,
        ttl_seconds: float,
        legacy_handle: str | None = None,
        source_account_id: str | None = None,
    ) -> None:
        now = time.time()
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO pending_authorizations"
                " (login_id, client_id, state, resume_kind, resume_value, import_batch_id,"
                "  legacy_handle, source_account_id, status, account_id, created_at, expires_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', NULL, ?, ?)",
                (
                    login_id,
                    client_id,
                    state,
                    resume_kind,
                    resume_value,
                    import_batch_id,
                    legacy_handle,
                    source_account_id,
                    now,
                    now + ttl_seconds,
                ),
            )

    def get_pending_authorization(self, login_id: str) -> PendingAuthorization | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT login_id, client_id, state, resume_kind, resume_value, import_batch_id,"
                " legacy_handle, source_account_id, status, account_id, expires_at"
                " FROM pending_authorizations WHERE login_id = ?",
                (login_id,),
            ).fetchone()
        return PendingAuthorization(**dict(row)) if row else None

    def complete_pending_authorization(self, login_id: str, account_id: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE pending_authorizations SET status = 'completed', account_id = ?"
                " WHERE login_id = ?",
                (account_id, login_id),
            )

    # -- authorization codes --------------------------------------------
    def create_authorization_code(
        self, code: str, client_id: str, account_id: str, login_id: str, ttl_seconds: float
    ) -> None:
        now = time.time()
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO authorization_codes"
                " (code, client_id, account_id, login_id, used, created_at, expires_at)"
                " VALUES (?, ?, ?, ?, 0, ?, ?)",
                (code, client_id, account_id, login_id, now, now + ttl_seconds),
            )

    def get_authorization_code(self, code: str) -> AuthorizationCode | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT code, client_id, account_id, login_id, used, expires_at"
                " FROM authorization_codes WHERE code = ?",
                (code,),
            ).fetchone()
        if not row:
            return None
        data = dict(row)
        data["used"] = bool(data["used"])
        return AuthorizationCode(**data)

    def find_authorization_code_by_login_id(self, login_id: str) -> AuthorizationCode | None:
        """Look up the single authorization code already issued for one
        completed pending authorization, if any. Used for idempotent
        repeated completion: a login only ever has a code minted for it
        once, so a repeat completion call can return that same code's
        location again instead of minting a second one."""

        with self._lock:
            row = self._conn.execute(
                "SELECT code, client_id, account_id, login_id, used, expires_at"
                " FROM authorization_codes WHERE login_id = ?",
                (login_id,),
            ).fetchone()
        if not row:
            return None
        data = dict(row)
        data["used"] = bool(data["used"])
        return AuthorizationCode(**data)

    def consume_authorization_code(self, code: str) -> bool:
        """Atomically mark a code used. Returns True only for the caller
        that wins the race against replays or concurrent exchanges."""

        with self._lock, self._conn:
            cursor = self._conn.execute(
                "UPDATE authorization_codes SET used = 1 WHERE code = ? AND used = 0", (code,)
            )
            return cursor.rowcount == 1

    # -- tokens ------------------------------------------------------
    def create_token(self, access_token: str, client_id: str, account_id: str, code: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO tokens (access_token, client_id, account_id, code, issued_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (access_token, client_id, account_id, code, time.time()),
            )
