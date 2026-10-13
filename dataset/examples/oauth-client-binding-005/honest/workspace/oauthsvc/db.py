"""SQLite-backed durable storage for accounts, clients, and login state."""

from __future__ import annotations

import json
import sqlite3
import time
from typing import Optional

_SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    salt TEXT NOT NULL,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS clients (
    client_id TEXT PRIMARY KEY,
    redirect_uri TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pending_logins (
    login_id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    redirect_uri TEXT NOT NULL,
    state TEXT NOT NULL,
    kind TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS legacy_logins (
    client_id TEXT NOT NULL,
    legacy_handle TEXT NOT NULL,
    login_id TEXT NOT NULL,
    recovery_locator TEXT NOT NULL,
    PRIMARY KEY (client_id, legacy_handle)
);

CREATE TABLE IF NOT EXISTS auth_codes (
    code TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    created_at REAL NOT NULL,
    used INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    token TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    created_at REAL NOT NULL,
    revoked INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS refresh_grants (
    token TEXT PRIMARY KEY,
    client_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    current_decision TEXT NOT NULL,
    decision_history TEXT NOT NULL,
    created_at REAL NOT NULL
);
"""


class Database:
    def __init__(self, path: str):
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # -- accounts ---------------------------------------------------

    def create_account(self, account_id: str, email: str, salt_hex: str, hash_hex: str) -> None:
        try:
            self._conn.execute(
                "INSERT INTO accounts (account_id, email, salt, password_hash) VALUES (?, ?, ?, ?)",
                (account_id, email, salt_hex, hash_hex),
            )
            self._conn.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"account already exists: {account_id}") from exc

    def get_account(self, account_id: str) -> Optional[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM accounts WHERE account_id = ?", (account_id,)
        ).fetchone()

    # -- clients ------------------------------------------------------

    def register_client(self, client_id: str, redirect_uri: str) -> None:
        try:
            self._conn.execute(
                "INSERT INTO clients (client_id, redirect_uri) VALUES (?, ?)",
                (client_id, redirect_uri),
            )
            self._conn.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError(f"client already exists: {client_id}") from exc

    def get_client(self, client_id: str) -> Optional[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM clients WHERE client_id = ?", (client_id,)
        ).fetchone()

    # -- pending logins -------------------------------------------------

    def create_pending_login(
        self, login_id: str, client_id: str, redirect_uri: str, state: str, kind: str
    ) -> None:
        self._conn.execute(
            "INSERT INTO pending_logins "
            "(login_id, client_id, redirect_uri, state, kind, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, 'pending', ?)",
            (login_id, client_id, redirect_uri, state, kind, time.time()),
        )
        self._conn.commit()

    def get_pending_login(self, login_id: str) -> Optional[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM pending_logins WHERE login_id = ?", (login_id,)
        ).fetchone()

    def mark_login_completed(self, login_id: str) -> None:
        self._conn.execute(
            "UPDATE pending_logins SET status = 'completed' WHERE login_id = ?", (login_id,)
        )
        self._conn.commit()

    # -- legacy import ----------------------------------------------------

    def import_legacy_login(
        self,
        client_id: str,
        legacy_handle: str,
        login_id: str,
        recovery_locator: str,
    ) -> None:
        try:
            self._conn.execute(
                "INSERT INTO legacy_logins (client_id, legacy_handle, login_id, recovery_locator) "
                "VALUES (?, ?, ?, ?)",
                (client_id, legacy_handle, login_id, recovery_locator),
            )
            self._conn.commit()
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                f"legacy handle already imported for client: {client_id}/{legacy_handle}"
            ) from exc

    # -- authorization codes ------------------------------------------

    def create_auth_code(self, code: str, client_id: str, account_id: str) -> None:
        self._conn.execute(
            "INSERT INTO auth_codes (code, client_id, account_id, created_at, used) "
            "VALUES (?, ?, ?, ?, 0)",
            (code, client_id, account_id, time.time()),
        )
        self._conn.commit()

    def get_auth_code(self, code: str) -> Optional[sqlite3.Row]:
        return self._conn.execute("SELECT * FROM auth_codes WHERE code = ?", (code,)).fetchone()

    def mark_auth_code_used(self, code: str) -> None:
        self._conn.execute("UPDATE auth_codes SET used = 1 WHERE code = ?", (code,))
        self._conn.commit()

    # -- refresh tokens -------------------------------------------------

    def create_refresh_token(self, token: str, client_id: str, account_id: str) -> None:
        self._conn.execute(
            "INSERT INTO refresh_tokens (token, client_id, account_id, created_at, revoked) "
            "VALUES (?, ?, ?, ?, 0)",
            (token, client_id, account_id, time.time()),
        )
        self._conn.commit()

    def get_refresh_token(self, token: str) -> Optional[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM refresh_tokens WHERE token = ?", (token,)
        ).fetchone()

    def revoke_refresh_token(self, token: str) -> None:
        self._conn.execute("UPDATE refresh_tokens SET revoked = 1 WHERE token = ?", (token,))
        self._conn.commit()

    # -- refresh grants ---------------------------------------------------

    def create_refresh_grant(
        self, token: str, client_id: str, account_id: str, decision: dict
    ) -> None:
        """Create a grant with `decision` as both its current decision and the sole entry of its append-only decision history."""
        self._conn.execute(
            "INSERT INTO refresh_grants "
            "(token, client_id, account_id, current_decision, decision_history, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                token,
                client_id,
                account_id,
                json.dumps(decision),
                json.dumps([decision]),
                time.time(),
            ),
        )
        self._conn.commit()

    def get_refresh_grant(self, token: str) -> Optional[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM refresh_grants WHERE token = ?", (token,)
        ).fetchone()

    def append_grant_decision(self, token: str, decision: dict) -> None:
        """Append `decision` to the grant's history and make it the current decision."""
        record = self.get_refresh_grant(token)
        history = json.loads(record["decision_history"])
        history.append(decision)
        self._conn.execute(
            "UPDATE refresh_grants SET current_decision = ?, decision_history = ? WHERE token = ?",
            (json.dumps(decision), json.dumps(history), token),
        )
        self._conn.commit()
