"""SQLite-backed persistence for accounts, clients, callbacks, legacy-import
migration plans, pending authorizations, client migration plans, the
pending-authorization inventory, authorization codes, and access tokens.

Every pending row, code, and token carries a ``client_id`` column, so each is
bound to exactly one registered client at the schema level. A pending row's
``client_id`` is its authoritative, owning client. Creating a migration plan
(``create_client_migration``) never rewrites it; only committing that plan,
one member at a time (``commit_migration_member``), does — and only once
that member's own atomic checkpoint completes, never before.
``client_migration_pending_authorizations.owning_client_id`` snapshots the
pre-commit owner separately from the plan's destination client, so a
not-yet-committed or rolled-back member's registration never merges with
the destination.
"""
from __future__ import annotations

import sqlite3
import time

_SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    password_salt TEXT NOT NULL,
    password_iterations INTEGER NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS clients (
    client_id TEXT PRIMARY KEY,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS callbacks (
    client_id TEXT PRIMARY KEY REFERENCES clients(client_id),
    redirect_uri TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS migration_plans (
    login_id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL REFERENCES clients(client_id),
    legacy_handle TEXT NOT NULL,
    state TEXT NOT NULL,
    locator TEXT NOT NULL,
    created_at REAL NOT NULL,
    UNIQUE (client_id, legacy_handle)
);

CREATE TABLE IF NOT EXISTS pending_authorizations (
    login_id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL REFERENCES clients(client_id),
    callback TEXT NOT NULL,
    state TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('native', 'imported')),
    status TEXT NOT NULL CHECK (status IN ('pending', 'completed')) DEFAULT 'pending',
    account_id TEXT REFERENCES accounts(account_id),
    expires_at REAL NOT NULL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS client_migration_plans (
    migration_id TEXT PRIMARY KEY,
    destination_client_id TEXT NOT NULL REFERENCES clients(client_id),
    status TEXT NOT NULL CHECK (status IN ('pending', 'committed', 'rolled_back')) DEFAULT 'pending',
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS client_migration_pending_authorizations (
    login_id TEXT PRIMARY KEY REFERENCES pending_authorizations(login_id),
    migration_id TEXT NOT NULL REFERENCES client_migration_plans(migration_id),
    account_id TEXT REFERENCES accounts(account_id),
    owning_client_id TEXT NOT NULL REFERENCES clients(client_id),
    callback TEXT NOT NULL,
    state TEXT NOT NULL,
    expires_at REAL NOT NULL,
    status TEXT NOT NULL,
    migration_handle TEXT NOT NULL,
    locator TEXT NOT NULL,
    cutover_status TEXT NOT NULL CHECK (cutover_status IN ('pending', 'committed', 'rolled_back')) DEFAULT 'pending',
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS authorization_codes (
    code TEXT PRIMARY KEY,
    client_id TEXT NOT NULL REFERENCES clients(client_id),
    account_id TEXT NOT NULL REFERENCES accounts(account_id),
    login_id TEXT NOT NULL REFERENCES pending_authorizations(login_id),
    expires_at REAL NOT NULL,
    used INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS access_tokens (
    access_token TEXT PRIMARY KEY,
    client_id TEXT NOT NULL REFERENCES clients(client_id),
    account_id TEXT NOT NULL REFERENCES accounts(account_id),
    code TEXT NOT NULL REFERENCES authorization_codes(code),
    created_at REAL NOT NULL
);
"""


class Store:
    """One store instance per call; every method opens its own connection.

    Short-lived connections keep concurrent loopback requests safe without a
    process-wide lock, and critical sections use ``BEGIN IMMEDIATE`` so
    single-use redemption and login completion are race-free across threads.
    """

    def __init__(self, path: str):
        self.path = path
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_schema(self) -> None:
        conn = self._connect()
        try:
            conn.executescript(_SCHEMA)
        finally:
            conn.close()

    # -- accounts ---------------------------------------------------

    def create_account(
        self, account_id: str, email: str, password_hash: str, salt: str, iterations: int
    ) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO accounts"
                " (account_id, email, password_hash, password_salt, password_iterations, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (account_id, email, password_hash, salt, iterations, time.time()),
            )
        finally:
            conn.close()

    def get_account(self, account_id: str) -> sqlite3.Row | None:
        conn = self._connect()
        try:
            return conn.execute(
                "SELECT * FROM accounts WHERE account_id = ?", (account_id,)
            ).fetchone()
        finally:
            conn.close()

    # -- clients / callbacks -----------------------------------------

    def register_client(self, client_id: str, redirect_uri: str) -> None:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "INSERT INTO clients (client_id, created_at) VALUES (?, ?)",
                (client_id, time.time()),
            )
            conn.execute(
                "INSERT INTO callbacks (client_id, redirect_uri) VALUES (?, ?)",
                (client_id, redirect_uri),
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    def get_callback(self, client_id: str) -> str | None:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT redirect_uri FROM callbacks WHERE client_id = ?", (client_id,)
            ).fetchone()
            return row["redirect_uri"] if row else None
        finally:
            conn.close()

    # -- pending authorizations / migration plans ---------------------

    def create_native_pending_authorization(
        self, login_id: str, client_id: str, callback: str, state: str, expires_at: float
    ) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO pending_authorizations"
                " (login_id, client_id, callback, state, kind, status, expires_at, created_at)"
                " VALUES (?, ?, ?, ?, 'native', 'pending', ?, ?)",
                (login_id, client_id, callback, state, expires_at, time.time()),
            )
        finally:
            conn.close()

    def create_imported_pending_authorization(
        self,
        login_id: str,
        client_id: str,
        callback: str,
        state: str,
        legacy_handle: str,
        locator: str,
        expires_at: float,
    ) -> None:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            now = time.time()
            conn.execute(
                "INSERT INTO pending_authorizations"
                " (login_id, client_id, callback, state, kind, status, expires_at, created_at)"
                " VALUES (?, ?, ?, ?, 'imported', 'pending', ?, ?)",
                (login_id, client_id, callback, state, expires_at, now),
            )
            conn.execute(
                "INSERT INTO migration_plans"
                " (login_id, client_id, legacy_handle, state, locator, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (login_id, client_id, legacy_handle, state, locator, now),
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    def get_pending_authorization(self, login_id: str) -> sqlite3.Row | None:
        conn = self._connect()
        try:
            return conn.execute(
                "SELECT * FROM pending_authorizations WHERE login_id = ?", (login_id,)
            ).fetchone()
        finally:
            conn.close()

    def get_migration_plan(self, login_id: str) -> sqlite3.Row | None:
        conn = self._connect()
        try:
            return conn.execute(
                "SELECT * FROM migration_plans WHERE login_id = ?", (login_id,)
            ).fetchone()
        finally:
            conn.close()

    def mark_pending_completed(self, login_id: str, account_id: str) -> bool:
        """Flip one pending row to completed and record its account.

        Returns False if the row was already completed/missing.
        """

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            cur = conn.execute(
                "UPDATE pending_authorizations SET status = 'completed', account_id = ?"
                " WHERE login_id = ? AND status = 'pending'",
                (account_id, login_id),
            )
            conn.execute("COMMIT")
            return cur.rowcount == 1
        except Exception:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    # -- client migration plans / pending-authorization inventory -----

    def is_login_migrated(self, login_id: str) -> bool:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT 1 FROM client_migration_pending_authorizations WHERE login_id = ?",
                (login_id,),
            ).fetchone()
            return row is not None
        finally:
            conn.close()

    def create_client_migration(
        self, migration_id: str, destination_client_id: str, entries: list[dict], now: float
    ) -> None:
        """Atomically create one migration plan and its inventory rows.

        ``entries`` snapshots the account, owning client, exact callback,
        state, expiry, status, and opaque migration handle for each pending
        authorization included in the plan. The ``login_id`` primary key on
        ``client_migration_pending_authorizations`` makes a duplicate
        membership fail with ``sqlite3.IntegrityError`` even under races.
        """

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "INSERT INTO client_migration_plans"
                " (migration_id, destination_client_id, created_at) VALUES (?, ?, ?)",
                (migration_id, destination_client_id, now),
            )
            for entry in entries:
                conn.execute(
                    "INSERT INTO client_migration_pending_authorizations"
                    " (login_id, migration_id, account_id, owning_client_id, callback, state,"
                    "  expires_at, status, migration_handle, locator, created_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        entry["login_id"],
                        migration_id,
                        entry["account_id"],
                        entry["owning_client_id"],
                        entry["callback"],
                        entry["state"],
                        entry["expires_at"],
                        entry["status"],
                        entry["migration_handle"],
                        entry["locator"],
                        now,
                    ),
                )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    def get_client_migration_plan(self, migration_id: str) -> sqlite3.Row | None:
        conn = self._connect()
        try:
            return conn.execute(
                "SELECT * FROM client_migration_plans WHERE migration_id = ?", (migration_id,)
            ).fetchone()
        finally:
            conn.close()

    def get_client_migration_member(self, login_id: str) -> sqlite3.Row | None:
        conn = self._connect()
        try:
            return conn.execute(
                "SELECT * FROM client_migration_pending_authorizations WHERE login_id = ?",
                (login_id,),
            ).fetchone()
        finally:
            conn.close()

    def get_client_migration_members(
        self, migration_id: str, limit: int | None = None
    ) -> list[sqlite3.Row]:
        conn = self._connect()
        try:
            query = (
                "SELECT * FROM client_migration_pending_authorizations"
                " WHERE migration_id = ? ORDER BY created_at, login_id"
            )
            params: list = [migration_id]
            if limit is not None:
                query += " LIMIT ?"
                params.append(limit)
            return conn.execute(query, params).fetchall()
        finally:
            conn.close()

    def count_client_migration_members(self, migration_id: str) -> int:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM client_migration_pending_authorizations"
                " WHERE migration_id = ?",
                (migration_id,),
            ).fetchone()
            return row["n"]
        finally:
            conn.close()

    def get_client_migration_members_with_continuation(
        self, migration_id: str, limit: int | None = None
    ) -> list[sqlite3.Row]:
        """Members of one plan joined against each login's live continuation status.

        ``client_migration_pending_authorizations.status`` is a frozen
        snapshot taken at plan-creation time (always ``'pending'``, since
        ``create_client_migration`` only ever admits already-pending
        logins); this joins ``pending_authorizations`` instead, so
        ``continuation_status`` reflects whether the login has completed
        since. Every row is scoped to ``migration_id`` alone.
        """

        conn = self._connect()
        try:
            query = (
                "SELECT m.login_id AS login_id, m.owning_client_id AS owning_client_id,"
                " m.callback AS callback, m.cutover_status AS cutover_status,"
                " p.status AS continuation_status"
                " FROM client_migration_pending_authorizations AS m"
                " JOIN pending_authorizations AS p ON p.login_id = m.login_id"
                " WHERE m.migration_id = ?"
                " ORDER BY m.created_at, m.login_id"
            )
            params: list = [migration_id]
            if limit is not None:
                query += " LIMIT ?"
                params.append(limit)
            return conn.execute(query, params).fetchall()
        finally:
            conn.close()

    def count_client_migration_pending_continuations(self, migration_id: str) -> int:
        """True total, scoped to ``migration_id``, of not-yet-completed logins."""

        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT COUNT(*) AS n"
                " FROM client_migration_pending_authorizations AS m"
                " JOIN pending_authorizations AS p ON p.login_id = m.login_id"
                " WHERE m.migration_id = ? AND p.status = 'pending'",
                (migration_id,),
            ).fetchone()
            return row["n"]
        finally:
            conn.close()

    def count_client_migration_members_by_cutover_status(self, migration_id: str) -> dict[str, int]:
        """Grouped member counts by ``cutover_status``, scoped to one plan.

        Only statuses actually present among the plan's members appear in
        the result; a caller wanting every known status filled in (even at
        zero) should default the missing keys itself.
        """

        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT cutover_status, COUNT(*) AS n"
                " FROM client_migration_pending_authorizations"
                " WHERE migration_id = ? GROUP BY cutover_status",
                (migration_id,),
            ).fetchall()
            return {row["cutover_status"]: row["n"] for row in rows}
        finally:
            conn.close()

    def count_client_migration_members_by_continuation_status(
        self, migration_id: str
    ) -> dict[str, int]:
        """Grouped member counts by live continuation status, scoped to one plan.

        Joins ``pending_authorizations`` for the same reason
        ``get_client_migration_members_with_continuation`` does: the
        inventory row's own ``status`` column is a frozen, always-``pending``
        snapshot, never the live value.
        """

        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT p.status AS continuation_status, COUNT(*) AS n"
                " FROM client_migration_pending_authorizations AS m"
                " JOIN pending_authorizations AS p ON p.login_id = m.login_id"
                " WHERE m.migration_id = ? GROUP BY p.status",
                (migration_id,),
            ).fetchall()
            return {row["continuation_status"]: row["n"] for row in rows}
        finally:
            conn.close()

    def set_client_migration_member_account(
        self, migration_id: str, login_id: str, account_id: str
    ) -> None:
        """Record one member's account once it becomes known (post-resume)."""

        conn = self._connect()
        try:
            conn.execute(
                "UPDATE client_migration_pending_authorizations SET account_id = ?"
                " WHERE login_id = ? AND migration_id = ?",
                (account_id, login_id, migration_id),
            )
        finally:
            conn.close()

    def set_client_migration_plan_status(self, migration_id: str, status: str) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "UPDATE client_migration_plans SET status = ? WHERE migration_id = ?",
                (status, migration_id),
            )
        finally:
            conn.close()

    def commit_migration_member(
        self, migration_id: str, login_id: str, destination_client_id: str
    ) -> bool:
        """Atomically cut one member over to the destination client.

        This is the commit checkpoint: the pending row's ``client_id`` and
        the member's ``cutover_status`` flip together in one transaction, so
        a login's ownership is preserved right up until this checkpoint
        completes, never before. Returns False if the member is missing or
        its checkpoint already left the 'pending' state (already committed
        or rolled back), so a caller can safely re-invoke this after a
        crash or restart without re-applying a finished checkpoint.
        """

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            member = conn.execute(
                "SELECT owning_client_id, cutover_status"
                " FROM client_migration_pending_authorizations"
                " WHERE login_id = ? AND migration_id = ?",
                (login_id, migration_id),
            ).fetchone()
            if member is None or member["cutover_status"] != "pending":
                conn.execute("ROLLBACK")
                return False
            cur = conn.execute(
                "UPDATE pending_authorizations SET client_id = ?"
                " WHERE login_id = ? AND client_id = ?",
                (destination_client_id, login_id, member["owning_client_id"]),
            )
            if cur.rowcount != 1:
                conn.execute("ROLLBACK")
                return False
            conn.execute(
                "UPDATE client_migration_pending_authorizations SET cutover_status = 'committed'"
                " WHERE login_id = ? AND migration_id = ?",
                (login_id, migration_id),
            )
            conn.execute("COMMIT")
            return True
        except Exception:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    def rollback_migration_member(self, migration_id: str, login_id: str) -> bool:
        """Atomically revert one member's checkpoint and mark it rolled back.

        If the member's checkpoint had already completed, its pending row's
        ``client_id`` is reverted back to ``owning_client_id`` in the same
        transaction as the ``cutover_status`` flip. A member never committed
        is only marked rolled back, with no ownership change. Returns False
        if the member is missing or already rolled back.
        """

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            member = conn.execute(
                "SELECT owning_client_id, cutover_status"
                " FROM client_migration_pending_authorizations"
                " WHERE login_id = ? AND migration_id = ?",
                (login_id, migration_id),
            ).fetchone()
            if member is None or member["cutover_status"] == "rolled_back":
                conn.execute("ROLLBACK")
                return False
            if member["cutover_status"] == "committed":
                conn.execute(
                    "UPDATE pending_authorizations SET client_id = ? WHERE login_id = ?",
                    (member["owning_client_id"], login_id),
                )
            conn.execute(
                "UPDATE client_migration_pending_authorizations SET cutover_status = 'rolled_back'"
                " WHERE login_id = ? AND migration_id = ?",
                (login_id, migration_id),
            )
            conn.execute("COMMIT")
            return True
        except Exception:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    # -- authorization codes / access tokens ---------------------------

    def create_authorization_code(
        self, code: str, client_id: str, account_id: str, login_id: str, expires_at: float
    ) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO authorization_codes"
                " (code, client_id, account_id, login_id, expires_at, used, created_at)"
                " VALUES (?, ?, ?, ?, ?, 0, ?)",
                (code, client_id, account_id, login_id, expires_at, time.time()),
            )
        finally:
            conn.close()

    def redeem_authorization_code(
        self, code: str, client_id: str, now: float
    ) -> tuple[str, sqlite3.Row | None]:
        """Atomically validate and consume one code.

        Returns ("ok", row), ("not_found", None), ("wrong_client", None), or
        ("invalid", None) for an expired or already-used code.
        """

        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM authorization_codes WHERE code = ?", (code,)
            ).fetchone()
            if row is None:
                conn.execute("ROLLBACK")
                return "not_found", None
            if row["client_id"] != client_id:
                conn.execute("ROLLBACK")
                return "wrong_client", None
            cur = conn.execute(
                "UPDATE authorization_codes SET used = 1"
                " WHERE code = ? AND used = 0 AND expires_at >= ?",
                (code, now),
            )
            if cur.rowcount != 1:
                conn.execute("ROLLBACK")
                return "invalid", None
            conn.execute("COMMIT")
            return "ok", row
        except Exception:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    def create_access_token(
        self, access_token: str, client_id: str, account_id: str, code: str
    ) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO access_tokens (access_token, client_id, account_id, code, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (access_token, client_id, account_id, code, time.time()),
            )
        finally:
            conn.close()
