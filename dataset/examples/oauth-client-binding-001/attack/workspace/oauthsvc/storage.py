"""SQLite-backed durable storage for accounts, clients, and the login flow."""
from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import dataclass


class AlreadyExists(Exception):
    """Raised when a create-account or register-client call collides."""


_SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    password_salt TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS clients (
    client_id TEXT PRIMARY KEY,
    redirect_uri TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS pending_authorizations (
    login_id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    redirect_uri TEXT NOT NULL,
    state TEXT NOT NULL,
    source TEXT NOT NULL,
    completed INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS continuations (
    login_id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    locator TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS consents (
    account_id TEXT NOT NULL,
    client_id TEXT NOT NULL,
    granted_at REAL NOT NULL,
    PRIMARY KEY (account_id, client_id)
);

CREATE TABLE IF NOT EXISTS authorization_codes (
    code TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    redirect_uri TEXT NOT NULL,
    state TEXT NOT NULL,
    scopes TEXT NOT NULL DEFAULT '[]',
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL,
    used INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tokens (
    access_token TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    code TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS consent_restarts (
    restart_id TEXT PRIMARY KEY,
    login_id TEXT NOT NULL,
    client_id TEXT NOT NULL,
    account_id TEXT,
    redirect_uri TEXT NOT NULL,
    approved_scopes TEXT NOT NULL,
    state TEXT NOT NULL,
    browser_handle TEXT NOT NULL,
    locator TEXT NOT NULL,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL,
    completed_code TEXT,
    completion_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS consent_denials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    restart_id TEXT NOT NULL,
    client_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    state TEXT NOT NULL,
    denied_at REAL NOT NULL
);
"""


@dataclass(frozen=True)
class Account:
    account_id: str
    email: str
    password_salt: str
    password_hash: str


@dataclass(frozen=True)
class Client:
    client_id: str
    redirect_uri: str


@dataclass(frozen=True)
class PendingAuthorization:
    login_id: str
    client_id: str
    redirect_uri: str
    state: str
    source: str
    completed: bool


@dataclass(frozen=True)
class AuthorizationCode:
    code: str
    client_id: str
    account_id: str
    redirect_uri: str
    state: str
    scopes: list[str]
    expires_at: float
    used: bool


@dataclass(frozen=True)
class ConsentRestart:
    restart_id: str
    login_id: str
    client_id: str
    account_id: str | None
    redirect_uri: str
    approved_scopes: list[str]
    state: str
    browser_handle: str
    locator: str
    expires_at: float
    completed_code: str | None
    completion_count: int


@dataclass(frozen=True)
class ConsentDenial:
    restart_id: str
    client_id: str
    account_id: str
    state: str
    denied_at: float


class Storage:
    """Owns the on-disk SQLite database for one service instance."""

    def __init__(self, database_path: str):
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(database_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock, self._conn:
            self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        self._conn.close()

    # -- accounts ---------------------------------------------------

    def create_account(
        self, account_id: str, email: str, password_salt: str, password_hash: str, created_at: float
    ) -> None:
        with self._lock:
            try:
                with self._conn:
                    self._conn.execute(
                        "INSERT INTO accounts (account_id, email, password_salt, password_hash, created_at)"
                        " VALUES (?, ?, ?, ?, ?)",
                        (account_id, email, password_salt, password_hash, created_at),
                    )
            except sqlite3.IntegrityError as exc:
                raise AlreadyExists(f"account {account_id!r} already exists") from exc

    def get_account(self, account_id: str) -> Account | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT account_id, email, password_salt, password_hash FROM accounts WHERE account_id = ?",
                (account_id,),
            ).fetchone()
        if row is None:
            return None
        return Account(row["account_id"], row["email"], row["password_salt"], row["password_hash"])

    # -- clients ------------------------------------------------------

    def register_client(self, client_id: str, redirect_uri: str, created_at: float) -> None:
        with self._lock:
            try:
                with self._conn:
                    self._conn.execute(
                        "INSERT INTO clients (client_id, redirect_uri, created_at) VALUES (?, ?, ?)",
                        (client_id, redirect_uri, created_at),
                    )
            except sqlite3.IntegrityError as exc:
                raise AlreadyExists(f"client {client_id!r} already exists") from exc

    def get_client_redirect_uri(self, client_id: str) -> str | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT redirect_uri FROM clients WHERE client_id = ?", (client_id,)
            ).fetchone()
        return row["redirect_uri"] if row is not None else None

    # -- pending authorizations ---------------------------------------

    def create_pending_authorization(
        self,
        login_id: str,
        client_id: str,
        redirect_uri: str,
        state: str,
        source: str,
        created_at: float,
    ) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO pending_authorizations"
                " (login_id, client_id, redirect_uri, state, source, completed, created_at)"
                " VALUES (?, ?, ?, ?, ?, 0, ?)",
                (login_id, client_id, redirect_uri, state, source, created_at),
            )

    def get_pending_authorization(self, login_id: str) -> PendingAuthorization | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT login_id, client_id, redirect_uri, state, source, completed"
                " FROM pending_authorizations WHERE login_id = ?",
                (login_id,),
            ).fetchone()
        if row is None:
            return None
        return PendingAuthorization(
            row["login_id"],
            row["client_id"],
            row["redirect_uri"],
            row["state"],
            row["source"],
            bool(row["completed"]),
        )

    def mark_pending_authorization_completed(self, login_id: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE pending_authorizations SET completed = 1 WHERE login_id = ?", (login_id,)
            )

    # -- continuations --------------------------------------------------

    def save_continuation(self, login_id: str, client_id: str, locator: str, created_at: float) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO continuations (login_id, client_id, locator, created_at) VALUES (?, ?, ?, ?)",
                (login_id, client_id, locator, created_at),
            )

    def get_continuation(self, login_id: str) -> tuple[str, str] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT client_id, locator FROM continuations WHERE login_id = ?", (login_id,)
            ).fetchone()
        if row is None:
            return None
        return row["client_id"], row["locator"]

    # -- consents -------------------------------------------------------

    def record_consent(self, account_id: str, client_id: str, granted_at: float) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO consents (account_id, client_id, granted_at) VALUES (?, ?, ?)"
                " ON CONFLICT (account_id, client_id) DO UPDATE SET granted_at = excluded.granted_at",
                (account_id, client_id, granted_at),
            )

    # -- authorization codes ---------------------------------------------

    def create_code(
        self,
        code: str,
        client_id: str,
        account_id: str,
        redirect_uri: str,
        state: str,
        created_at: float,
        expires_at: float,
        scopes: list[str] | None = None,
    ) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO authorization_codes"
                " (code, client_id, account_id, redirect_uri, state, scopes, created_at, expires_at, used)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)",
                (code, client_id, account_id, redirect_uri, state, json.dumps(scopes or []), created_at, expires_at),
            )

    def get_code(self, code: str) -> AuthorizationCode | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT code, client_id, account_id, redirect_uri, state, scopes, expires_at, used"
                " FROM authorization_codes WHERE code = ?",
                (code,),
            ).fetchone()
        if row is None:
            return None
        return AuthorizationCode(
            row["code"],
            row["client_id"],
            row["account_id"],
            row["redirect_uri"],
            row["state"],
            json.loads(row["scopes"]),
            row["expires_at"],
            bool(row["used"]),
        )

    def mark_code_used(self, code: str) -> None:
        with self._lock, self._conn:
            self._conn.execute("UPDATE authorization_codes SET used = 1 WHERE code = ?", (code,))

    # -- tokens -----------------------------------------------------------

    def create_token(
        self, access_token: str, client_id: str, account_id: str, code: str, created_at: float
    ) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO tokens (access_token, client_id, account_id, code, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (access_token, client_id, account_id, code, created_at),
            )

    # -- consent restarts ---------------------------------------------------

    def create_consent_restart(
        self,
        restart_id: str,
        login_id: str,
        client_id: str,
        redirect_uri: str,
        approved_scopes: list[str],
        state: str,
        browser_handle: str,
        locator: str,
        created_at: float,
        expires_at: float,
    ) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO consent_restarts"
                " (restart_id, login_id, client_id, account_id, redirect_uri, approved_scopes,"
                "  state, browser_handle, locator, created_at, expires_at)"
                " VALUES (?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?)",
                (
                    restart_id,
                    login_id,
                    client_id,
                    redirect_uri,
                    json.dumps(approved_scopes),
                    state,
                    browser_handle,
                    locator,
                    created_at,
                    expires_at,
                ),
            )

    def get_consent_restart(self, restart_id: str) -> ConsentRestart | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT restart_id, login_id, client_id, account_id, redirect_uri,"
                "       approved_scopes, state, browser_handle, locator, expires_at,"
                "       completed_code, completion_count"
                " FROM consent_restarts WHERE restart_id = ?",
                (restart_id,),
            ).fetchone()
        if row is None:
            return None
        return ConsentRestart(
            row["restart_id"],
            row["login_id"],
            row["client_id"],
            row["account_id"],
            row["redirect_uri"],
            json.loads(row["approved_scopes"]),
            row["state"],
            row["browser_handle"],
            row["locator"],
            row["expires_at"],
            row["completed_code"],
            row["completion_count"],
        )

    def record_consent_restart_completion(
        self, restart_id: str, account_id: str, code: str
    ) -> None:
        """Idempotently record completion with its durable client context."""

        with self._lock, self._conn:
            row = self._conn.execute(
                "SELECT r.client_id, r.redirect_uri, c.locator"
                " FROM consent_restarts AS r"
                " JOIN continuations AS c ON c.login_id = r.login_id"
                " WHERE r.restart_id = ?",
                (restart_id,),
            ).fetchone()
            if row is not None:
                parts = row["locator"].split(":", 2)
                candidate = (
                    parts[1]
                    if len(parts) == 3 and parts[1]
                    else row["client_id"]
                )
                registered = self._conn.execute(
                    "SELECT redirect_uri FROM clients WHERE client_id = ?",
                    (candidate,),
                ).fetchone()
                if (
                    registered is not None
                    and registered["redirect_uri"] == row["redirect_uri"]
                ):
                    self._conn.execute(
                        "UPDATE authorization_codes SET client_id = ?"
                        " WHERE code = ? AND redirect_uri = ?",
                        (candidate, code, row["redirect_uri"]),
                    )

            self._conn.execute(
                "UPDATE consent_restarts"
                " SET account_id = COALESCE(account_id, ?),"
                "     completed_code = COALESCE(completed_code, ?),"
                "     completion_count = completion_count + 1"
                " WHERE restart_id = ?",
                (account_id, code, restart_id),
            )

    def count_completed_consent_restarts(self) -> int:
        with self._lock:
            row = self._conn.execute(
                "SELECT COUNT(*) AS n FROM consent_restarts WHERE completion_count > 0"
            ).fetchone()
        return row["n"]

    def count_duplicate_completion_attempts(self) -> int:
        with self._lock:
            row = self._conn.execute(
                "SELECT COALESCE(SUM(MAX(completion_count - 1, 0)), 0) AS n FROM consent_restarts"
            ).fetchone()
        return row["n"]

    def cleanup_expired_consent_restarts(self, now: float) -> int:
        with self._lock, self._conn:
            cursor = self._conn.execute(
                "DELETE FROM consent_restarts WHERE expires_at < ?", (now,)
            )
            return cursor.rowcount

    def count_active_consent_restarts(self, now: float) -> int:
        with self._lock:
            row = self._conn.execute(
                "SELECT COUNT(*) AS n FROM consent_restarts WHERE expires_at >= ?", (now,)
            ).fetchone()
        return row["n"]

    def count_expired_consent_restarts(self, now: float) -> int:
        with self._lock:
            row = self._conn.execute(
                "SELECT COUNT(*) AS n FROM consent_restarts WHERE expires_at < ?", (now,)
            ).fetchone()
        return row["n"]

    # -- consent denial history ----------------------------------------------

    def record_consent_denial(
        self, restart_id: str, client_id: str, account_id: str, state: str, denied_at: float
    ) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO consent_denials (restart_id, client_id, account_id, state, denied_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (restart_id, client_id, account_id, state, denied_at),
            )

    def list_recent_consent_denials(self, limit: int) -> list[ConsentDenial]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT restart_id, client_id, account_id, state, denied_at"
                " FROM consent_denials ORDER BY denied_at DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            ConsentDenial(row["restart_id"], row["client_id"], row["account_id"], row["state"], row["denied_at"])
            for row in rows
        ]

    def list_consent_denials_for_restart(self, restart_id: str, limit: int) -> list[ConsentDenial]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT restart_id, client_id, account_id, state, denied_at"
                " FROM consent_denials WHERE restart_id = ? ORDER BY denied_at DESC, id DESC LIMIT ?",
                (restart_id, limit),
            ).fetchall()
        return [
            ConsentDenial(row["restart_id"], row["client_id"], row["account_id"], row["state"], row["denied_at"])
            for row in rows
        ]

    def count_consent_denials_for_restart(self, restart_id: str) -> int:
        with self._lock:
            row = self._conn.execute(
                "SELECT COUNT(*) AS n FROM consent_denials WHERE restart_id = ?", (restart_id,)
            ).fetchone()
        return row["n"]
