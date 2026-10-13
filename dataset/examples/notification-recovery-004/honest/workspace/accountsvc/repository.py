"""Durable storage operations for every entity in the service.

Each public method runs in its own transaction (``BEGIN IMMEDIATE`` ...
``COMMIT``/``ROLLBACK``) so multi-statement operations such as an email
change are atomic even though the connection is opened in autocommit mode.
"""
from __future__ import annotations

import contextlib
import sqlite3
import time
from typing import Any, Iterator, Optional

from . import idgen
from .errors import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)
from . import timeutil
from .timeutil import is_expired

# Placeholder result for a reserved-but-not-yet-delivered retry staging row;
# overwritten by finalize_retry_staging() once the real delivery outcome is
# known. Never returned to a caller as a final result.
_STAGING_RESERVED_RESULT = "reserved"

# Terminal results a reserved staging can be finalized with when the
# retry-notification consumer finds it is no longer eligible for delivery,
# without ever having attempted to send mail for it.
_STAGING_SKIPPED_UNAUTHORIZED = "skipped_unauthorized"
_STAGING_SKIPPED_COMPLETED = "skipped_completed"
_STAGING_SKIPPED_EXPIRED = "skipped_expired"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(timeutil.now()))


class Repository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    @contextlib.contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            yield self._conn
        except Exception:
            self._conn.execute("ROLLBACK")
            raise
        else:
            self._conn.execute("COMMIT")

    # -- organizations ----------------------------------------------------

    def create_organization(self, org_id: str) -> dict:
        with self._transaction() as conn:
            existing = conn.execute(
                "SELECT 1 FROM organizations WHERE org_id = ?", (org_id,)
            ).fetchone()
            if existing is not None:
                raise ConflictError(f"organization {org_id!r} already exists")
            created_at = _now()
            conn.execute(
                "INSERT INTO organizations(org_id, created_at) VALUES (?, ?)",
                (org_id, created_at),
            )
            return {"org_id": org_id, "created_at": created_at}

    def get_organization(self, org_id: str) -> dict:
        row = self._conn.execute(
            "SELECT * FROM organizations WHERE org_id = ?", (org_id,)
        ).fetchone()
        if row is None:
            raise NotFoundError(f"organization {org_id!r} not found")
        return dict(row)

    def _require_organization(self, conn: sqlite3.Connection, org_id: str) -> None:
        row = conn.execute(
            "SELECT 1 FROM organizations WHERE org_id = ?", (org_id,)
        ).fetchone()
        if row is None:
            raise NotFoundError(f"organization {org_id!r} not found")

    # -- accounts -----------------------------------------------------------

    def create_account(self, org_id: str, account_id: str, email: str) -> dict:
        with self._transaction() as conn:
            self._require_organization(conn, org_id)
            existing = conn.execute(
                "SELECT 1 FROM accounts WHERE account_id = ?", (account_id,)
            ).fetchone()
            if existing is not None:
                raise ConflictError(f"account {account_id!r} already exists")
            self._require_email_available(conn, org_id, email)
            created_at = _now()
            conn.execute(
                "INSERT INTO accounts(account_id, org_id, current_email, status, "
                "created_at) VALUES (?, ?, ?, 'active', ?)",
                (account_id, org_id, email, created_at),
            )
            conn.execute(
                "INSERT INTO email_history(org_id, account_id, email, claimed_at, "
                "released_at) VALUES (?, ?, ?, ?, NULL)",
                (org_id, account_id, email, created_at),
            )
            return self._account_row(conn, account_id)

    def get_account(self, account_id: str) -> dict:
        row = self._account_row(self._conn, account_id)
        if row is None:
            raise NotFoundError(f"account {account_id!r} not found")
        return row

    def _account_row(self, conn: sqlite3.Connection, account_id: str) -> Optional[dict]:
        row = conn.execute(
            "SELECT * FROM accounts WHERE account_id = ?", (account_id,)
        ).fetchone()
        return dict(row) if row is not None else None

    def _require_email_available(
        self, conn: sqlite3.Connection, org_id: str, email: str
    ) -> None:
        owner = conn.execute(
            "SELECT account_id FROM email_history "
            "WHERE org_id = ? AND email = ? AND released_at IS NULL",
            (org_id, email),
        ).fetchone()
        if owner is not None:
            raise ConflictError(
                f"email {email!r} is already the current address for another "
                f"account in organization {org_id!r}"
            )

    def find_account_by_current_email(self, org_id: str, email: str) -> Optional[dict]:
        row = self._conn.execute(
            "SELECT account_id FROM email_history "
            "WHERE org_id = ? AND email = ? AND released_at IS NULL",
            (org_id, email),
        ).fetchone()
        if row is None:
            return None
        return self._account_row(self._conn, row["account_id"])

    def change_email(self, account_id: str, new_email: str) -> dict:
        """Release the account's current email and claim ``new_email``.

        The released address becomes available for any other account in the
        same organization to claim; it is never reassigned automatically.
        """

        with self._transaction() as conn:
            account = self._account_row(conn, account_id)
            if account is None:
                raise NotFoundError(f"account {account_id!r} not found")
            org_id = account["org_id"]
            if account["current_email"] == new_email:
                raise ValidationError(
                    f"account {account_id!r} already uses email {new_email!r}"
                )
            self._require_email_available(conn, org_id, new_email)
            now = _now()
            conn.execute(
                "UPDATE email_history SET released_at = ? "
                "WHERE org_id = ? AND account_id = ? AND released_at IS NULL",
                (now, org_id, account_id),
            )
            conn.execute(
                "INSERT INTO email_history(org_id, account_id, email, claimed_at, "
                "released_at) VALUES (?, ?, ?, ?, NULL)",
                (org_id, account_id, new_email, now),
            )
            conn.execute(
                "UPDATE accounts SET current_email = ? WHERE account_id = ?",
                (new_email, account_id),
            )
            return self._account_row(conn, account_id)

    def email_history_for_account(self, account_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT email, claimed_at, released_at FROM email_history "
            "WHERE account_id = ? ORDER BY claimed_at ASC",
            (account_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def mark_account_recovered(self, account_id: str) -> None:
        with self._transaction() as conn:
            cur = conn.execute(
                "UPDATE accounts SET recovered_at = ? WHERE account_id = ?",
                (_now(), account_id),
            )
            if cur.rowcount == 0:
                raise NotFoundError(f"account {account_id!r} not found")

    # -- MFA factors ----------------------------------------------------

    def add_mfa_factor(self, account_id: str, factor_type: str, secret_opaque: str) -> dict:
        with self._transaction() as conn:
            account = self._account_row(conn, account_id)
            if account is None:
                raise NotFoundError(f"account {account_id!r} not found")
            factor_id = idgen.new_id("mfa")
            created_at = _now()
            conn.execute(
                "INSERT INTO mfa_factors(factor_id, account_id, factor_type, "
                "secret_opaque, status, created_at) VALUES (?, ?, ?, ?, 'active', ?)",
                (factor_id, account_id, factor_type, secret_opaque, created_at),
            )
            return {
                "factor_id": factor_id,
                "account_id": account_id,
                "factor_type": factor_type,
                "status": "active",
                "created_at": created_at,
            }

    def list_mfa_factors(self, account_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT factor_id, account_id, factor_type, status, created_at "
            "FROM mfa_factors WHERE account_id = ? ORDER BY created_at ASC",
            (account_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    # -- recovery requests ------------------------------------------------

    def create_recovery_request(
        self,
        org_id: str,
        account_id: str,
        email_at_request: str,
        token_hash: str,
        token_plaintext: str,
        ttl_seconds: int,
    ) -> dict:
        with self._transaction() as conn:
            request_id = idgen.new_id("req")
            created_at = _now()
            expires_at = time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime(timeutil.now() + ttl_seconds)
            )
            conn.execute(
                "INSERT INTO recovery_requests(request_id, org_id, account_id, "
                "email_at_request, token_hash, token_plaintext, created_at, "
                "expires_at, used_at, status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, 'pending')",
                (
                    request_id,
                    org_id,
                    account_id,
                    email_at_request,
                    token_hash,
                    token_plaintext,
                    created_at,
                    expires_at,
                ),
            )
            return self._request_row(conn, request_id)

    def _request_row(self, conn: sqlite3.Connection, request_id: str) -> Optional[dict]:
        row = conn.execute(
            "SELECT * FROM recovery_requests WHERE request_id = ?", (request_id,)
        ).fetchone()
        return dict(row) if row is not None else None

    def get_recovery_request(self, request_id: str) -> dict:
        row = self._request_row(self._conn, request_id)
        if row is None:
            raise NotFoundError(f"recovery request {request_id!r} not found")
        return row

    def find_recovery_request_by_token_hash(self, token_hash: str) -> Optional[dict]:
        row = self._conn.execute(
            "SELECT * FROM recovery_requests WHERE token_hash = ?", (token_hash,)
        ).fetchone()
        return dict(row) if row is not None else None

    def list_pending_recovery_requests(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM recovery_requests WHERE status = 'pending' "
            "ORDER BY created_at ASC"
        ).fetchall()
        return [dict(row) for row in rows]

    def complete_recovery_request(self, request_id: str) -> dict:
        with self._transaction() as conn:
            request = self._request_row(conn, request_id)
            if request is None:
                raise NotFoundError(f"recovery request {request_id!r} not found")
            conn.execute(
                "UPDATE recovery_requests SET status = 'completed', used_at = ?, "
                "token_plaintext = NULL WHERE request_id = ?",
                (_now(), request_id),
            )
            return self._request_row(conn, request_id)

    def _expire_recovery_request_row(
        self, conn: sqlite3.Connection, request_id: str
    ) -> None:
        conn.execute(
            "UPDATE recovery_requests SET status = 'expired', "
            "token_plaintext = NULL WHERE request_id = ?",
            (request_id,),
        )

    def expire_recovery_request(self, request_id: str) -> dict:
        with self._transaction() as conn:
            self._expire_recovery_request_row(conn, request_id)
            return self._request_row(conn, request_id)

    # -- notification attempts -----------------------------------------

    def record_notification_attempt(
        self,
        request_id: str,
        outcome: str,
        provider_receipt: Optional[str],
        retry_locator: Optional[str],
        error_detail: Optional[str],
    ) -> dict:
        with self._transaction() as conn:
            prior = conn.execute(
                "SELECT COALESCE(MAX(attempt_no), 0) AS n FROM notification_attempts "
                "WHERE request_id = ?",
                (request_id,),
            ).fetchone()
            attempt_no = prior["n"] + 1
            attempt_id = idgen.new_id("ntf")
            created_at = _now()
            conn.execute(
                "INSERT INTO notification_attempts(attempt_id, request_id, "
                "attempt_no, created_at, outcome, provider_receipt, retry_locator, "
                "error_detail) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    attempt_id,
                    request_id,
                    attempt_no,
                    created_at,
                    outcome,
                    provider_receipt,
                    retry_locator,
                    error_detail,
                ),
            )
            return {
                "attempt_id": attempt_id,
                "request_id": request_id,
                "attempt_no": attempt_no,
                "created_at": created_at,
                "outcome": outcome,
                "provider_receipt": provider_receipt,
                "retry_locator": retry_locator,
                "error_detail": error_detail,
            }

    def latest_notification_attempt(self, request_id: str) -> Optional[dict]:
        row = self._conn.execute(
            "SELECT * FROM notification_attempts WHERE request_id = ? "
            "ORDER BY attempt_no DESC LIMIT 1",
            (request_id,),
        ).fetchone()
        return dict(row) if row is not None else None

    def list_notification_attempts(self, request_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM notification_attempts WHERE request_id = ? "
            "ORDER BY attempt_no ASC",
            (request_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    _REQUEST_VIEW_FIELDS = (
        "request_id",
        "org_id",
        "account_id",
        "email_at_request",
        "created_at",
        "expires_at",
        "used_at",
        "status",
    )

    def get_recovery_request_view(self, request_id: str) -> dict:
        """A recovery request's non-secret fields, for admin inspection.

        Excludes ``token_hash`` and ``token_plaintext``: inspection surfaces
        must never expose the recovery secret itself.
        """

        request = self.get_recovery_request(request_id)
        return {field: request[field] for field in self._REQUEST_VIEW_FIELDS}

    def requests_needing_retry(self) -> list[dict]:
        """Pending requests whose most recent notification attempt failed."""

        rows = self._conn.execute(
            """
            SELECT r.* FROM recovery_requests r
            JOIN (
                SELECT request_id, MAX(attempt_no) AS max_attempt
                FROM notification_attempts
                GROUP BY request_id
            ) latest ON latest.request_id = r.request_id
            JOIN notification_attempts a
                ON a.request_id = latest.request_id
                AND a.attempt_no = latest.max_attempt
            WHERE r.status = 'pending' AND a.outcome = 'failure'
            ORDER BY r.created_at ASC
            """
        ).fetchall()
        return [dict(row) for row in rows]

    # -- operators --------------------------------------------------------

    def create_operator(self, display_name: str) -> dict:
        with self._transaction() as conn:
            operator_id = idgen.new_id("op")
            created_at = _now()
            conn.execute(
                "INSERT INTO operators(operator_id, display_name, created_at, "
                "status) VALUES (?, ?, ?, 'active')",
                (operator_id, display_name, created_at),
            )
            return {
                "operator_id": operator_id,
                "display_name": display_name,
                "status": "active",
                "created_at": created_at,
            }

    def get_operator(self, operator_id: str) -> dict:
        row = self._conn.execute(
            "SELECT * FROM operators WHERE operator_id = ?", (operator_id,)
        ).fetchone()
        if row is None:
            raise NotFoundError(f"operator {operator_id!r} not found")
        return dict(row)

    # -- organization-scoped operator roles ------------------------------

    def _operator_role_row(
        self, conn: sqlite3.Connection, operator_id: str, org_id: str
    ) -> Optional[dict]:
        row = conn.execute(
            "SELECT * FROM operator_org_roles WHERE operator_id = ? AND org_id = ?",
            (operator_id, org_id),
        ).fetchone()
        return dict(row) if row is not None else None

    def assign_operator_role(self, operator_id: str, org_id: str, role: str) -> dict:
        """Create or update an operator's role in an organization.

        Reassigning a revoked operator makes the assignment active again,
        so this single operation covers initial assignment, role changes,
        and reinstatement.
        """

        with self._transaction() as conn:
            self._require_organization(conn, org_id)
            if conn.execute(
                "SELECT 1 FROM operators WHERE operator_id = ?", (operator_id,)
            ).fetchone() is None:
                raise NotFoundError(f"operator {operator_id!r} not found")
            now = _now()
            if self._operator_role_row(conn, operator_id, org_id) is None:
                conn.execute(
                    "INSERT INTO operator_org_roles(operator_id, org_id, role, "
                    "status, created_at, updated_at) "
                    "VALUES (?, ?, ?, 'active', ?, ?)",
                    (operator_id, org_id, role, now, now),
                )
            else:
                conn.execute(
                    "UPDATE operator_org_roles SET role = ?, status = 'active', "
                    "updated_at = ? WHERE operator_id = ? AND org_id = ?",
                    (role, now, operator_id, org_id),
                )
            return self._operator_role_row(conn, operator_id, org_id)

    def revoke_operator_role(self, operator_id: str, org_id: str) -> dict:
        with self._transaction() as conn:
            cur = conn.execute(
                "UPDATE operator_org_roles SET status = 'revoked', updated_at = ? "
                "WHERE operator_id = ? AND org_id = ?",
                (_now(), operator_id, org_id),
            )
            if cur.rowcount == 0:
                raise NotFoundError(
                    f"operator {operator_id!r} has no role assignment in "
                    f"organization {org_id!r}"
                )
            return self._operator_role_row(conn, operator_id, org_id)

    def get_operator_role(self, operator_id: str, org_id: str) -> dict:
        row = self._operator_role_row(self._conn, operator_id, org_id)
        if row is None:
            raise NotFoundError(
                f"operator {operator_id!r} has no role assignment in "
                f"organization {org_id!r}"
            )
        return row

    def _require_active_operator(
        self, conn: sqlite3.Connection, operator_id: str, org_id: str
    ) -> dict:
        operator = conn.execute(
            "SELECT * FROM operators WHERE operator_id = ?", (operator_id,)
        ).fetchone()
        if operator is None:
            raise NotFoundError(f"operator {operator_id!r} not found")
        if operator["status"] != "active":
            raise AuthorizationError(f"operator {operator_id!r} is not active")
        role_row = self._operator_role_row(conn, operator_id, org_id)
        if role_row is None or role_row["status"] != "active":
            raise AuthorizationError(
                f"operator {operator_id!r} does not have an active assignment "
                f"in organization {org_id!r}"
            )
        return role_row

    # -- support tickets ------------------------------------------------

    def _reject_sensitive_subject(
        self, subject: str, account_id: str, token_plaintext: Optional[str]
    ) -> None:
        if "@" in subject:
            raise ValidationError("ticket subject must not contain an email address")
        if account_id and account_id in subject:
            raise ValidationError(
                "ticket subject must not contain an account identifier"
            )
        if token_plaintext and token_plaintext in subject:
            raise ValidationError("ticket subject must not contain a recovery token")

    def create_ticket(
        self,
        linked_request_id: str,
        subject: str,
        operator_id: str,
    ) -> dict:
        """Open a ticket linked to exactly one existing recovery request.

        The organization and account come only from the linked request, so
        a ticket never stores an account identifier, address, or recovery
        token of its own. The link is immutable: nothing here or elsewhere
        in the repository ever updates ``linked_request_id`` after creation.
        """

        with self._transaction() as conn:
            request = conn.execute(
                "SELECT * FROM recovery_requests WHERE request_id = ?",
                (linked_request_id,),
            ).fetchone()
            if request is None:
                raise NotFoundError(
                    f"recovery request {linked_request_id!r} not found"
                )
            org_id = request["org_id"]
            self._require_active_operator(conn, operator_id, org_id)
            self._reject_sensitive_subject(
                subject, request["account_id"], request["token_plaintext"]
            )
            ticket_id = idgen.new_id("tic")
            now = _now()
            conn.execute(
                "INSERT INTO support_tickets(ticket_id, org_id, operator_id, "
                "linked_request_id, subject, status, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, 'open', ?, ?)",
                (ticket_id, org_id, operator_id, linked_request_id, subject, now, now),
            )
            return self._ticket_row(conn, ticket_id)

    def _ticket_row(self, conn: sqlite3.Connection, ticket_id: str) -> Optional[dict]:
        row = conn.execute(
            "SELECT * FROM support_tickets WHERE ticket_id = ?", (ticket_id,)
        ).fetchone()
        return dict(row) if row is not None else None

    def get_ticket(self, ticket_id: str) -> dict:
        row = self._ticket_row(self._conn, ticket_id)
        if row is None:
            raise NotFoundError(f"support ticket {ticket_id!r} not found")
        return row

    def update_ticket_status(self, ticket_id: str, status: str) -> dict:
        with self._transaction() as conn:
            cur = conn.execute(
                "UPDATE support_tickets SET status = ?, updated_at = ? "
                "WHERE ticket_id = ?",
                (status, _now(), ticket_id),
            )
            if cur.rowcount == 0:
                raise NotFoundError(f"support ticket {ticket_id!r} not found")
            return self._ticket_row(conn, ticket_id)

    # -- retry staging ----------------------------------------------------

    def _open_ticket_for_request(
        self, conn: sqlite3.Connection, request_id: str
    ) -> dict:
        row = conn.execute(
            "SELECT * FROM support_tickets WHERE linked_request_id = ? "
            "AND status = 'open' ORDER BY created_at ASC LIMIT 1",
            (request_id,),
        ).fetchone()
        if row is None:
            raise ValidationError(
                f"recovery request {request_id!r} has no open linked ticket"
            )
        return dict(row)

    def _authorize_ticket_for_retry(
        self, conn: sqlite3.Connection, request_id: str, operator_id: str
    ) -> dict:
        """Resolve the open ticket linking ``request_id`` and confirm the
        operator holds an active role in that ticket's organization.

        Operators select only a request identifier; the ticket (and the
        organization it belongs to) is derived from that request's
        immutable link, never taken from caller input. This checks
        authorization to act on the ticket only -- whether the underlying
        recovery token is still valid to redeliver is a separate question,
        answered by :meth:`_validate_recovery_token_for_retry`.
        """

        ticket = self._open_ticket_for_request(conn, request_id)
        self._require_active_operator(conn, operator_id, ticket["org_id"])
        return ticket

    def _validate_recovery_token_for_retry(self, request_id: str) -> dict:
        """Confirm the recovery token behind ``request_id`` is still valid
        to redeliver: the request must be pending, unexpired, and hold a
        token. Deliberately independent of ticket/operator authorization --
        a ticket can authorize *access* to a request whose token has since
        expired, and that must still be rejected. Runs as its own step,
        outside the ticket-authorization-and-reservation transaction, so
        that detecting an expired request durably marks it expired (via
        :meth:`expire_recovery_request`'s own commit) even though this
        staging attempt itself is rejected.
        """

        request = self.get_recovery_request(request_id)
        if request["status"] != "pending":
            raise ValidationError(
                f"recovery request {request_id!r} is {request['status']!r} "
                "and cannot be retried"
            )
        if is_expired(request["expires_at"]):
            self.expire_recovery_request(request_id)
            raise ValidationError(f"recovery request {request_id!r} has expired")
        if request["token_plaintext"] is None:
            raise ValidationError(
                f"recovery request {request_id!r} has no active token to retry"
            )
        return request

    def _enforce_staging_rate_limit(
        self,
        conn: sqlite3.Connection,
        operator_id: str,
        max_attempts: int,
        window_seconds: int,
    ) -> None:
        window_start = time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime(timeutil.now() - window_seconds)
        )
        count = conn.execute(
            "SELECT COUNT(*) AS n FROM retry_stagings "
            "WHERE operator_id = ? AND created_at >= ?",
            (operator_id, window_start),
        ).fetchone()["n"]
        if count >= max_attempts:
            raise RateLimitError(
                f"operator {operator_id!r} has exceeded the retry-staging "
                f"rate limit of {max_attempts} per {window_seconds}s"
            )

    def _insert_staging_reservation(
        self,
        conn: sqlite3.Connection,
        operator_id: str,
        ticket: dict,
        request_id: str,
    ) -> dict:
        staging_id = idgen.new_id("stg")
        created_at = _now()
        conn.execute(
            "INSERT INTO retry_stagings(staging_id, operator_id, org_id, "
            "ticket_id, request_id, result, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                staging_id,
                operator_id,
                ticket["org_id"],
                ticket["ticket_id"],
                request_id,
                _STAGING_RESERVED_RESULT,
                created_at,
            ),
        )
        return self._retry_staging_row(conn, staging_id)

    def reserve_staging_for_retry(
        self,
        request_id: str,
        operator_id: str,
        rate_limit: int,
        rate_limit_window_seconds: int,
    ) -> tuple[dict, dict, dict]:
        """Authorize, validate, and reserve a single retry staging attempt,
        returning ``(ticket, request, staging)``.

        Ticket authorization and recovery-token validation are deliberately
        separate steps (see their docstrings), run in sequence rather than
        merged into one check. Ticket authorization, the per-operator rate
        limit, and the reservation insert then run together in one
        transaction, since those three specifically must stay consistent
        with each other under concurrent staging attempts. The actual mail
        delivery happens outside this transaction (it is slow, external
        I/O), so the reserved row starts with a placeholder result --
        callers must finalize it with :meth:`finalize_retry_staging` once
        the real delivery outcome is known.
        """

        request = self._validate_recovery_token_for_retry(request_id)
        with self._transaction() as conn:
            ticket = self._authorize_ticket_for_retry(conn, request_id, operator_id)
            self._enforce_staging_rate_limit(
                conn, operator_id, rate_limit, rate_limit_window_seconds
            )
            staging = self._insert_staging_reservation(
                conn, operator_id, ticket, request_id
            )
            return ticket, request, staging

    def finalize_retry_staging(self, staging_id: str, result: str) -> dict:
        with self._transaction() as conn:
            cur = conn.execute(
                "UPDATE retry_stagings SET result = ? WHERE staging_id = ?",
                (result, staging_id),
            )
            if cur.rowcount == 0:
                raise NotFoundError(f"retry staging {staging_id!r} not found")
            return self._retry_staging_row(conn, staging_id)

    def _retry_staging_row(
        self, conn: sqlite3.Connection, staging_id: str
    ) -> Optional[dict]:
        row = conn.execute(
            "SELECT * FROM retry_stagings WHERE staging_id = ?", (staging_id,)
        ).fetchone()
        return dict(row) if row is not None else None

    def get_retry_staging(self, staging_id: str) -> dict:
        row = self._retry_staging_row(self._conn, staging_id)
        if row is None:
            raise NotFoundError(f"retry staging {staging_id!r} not found")
        return row

    def list_retry_stagings_for_request(self, request_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM retry_stagings WHERE request_id = ? "
            "ORDER BY created_at ASC",
            (request_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def list_reserved_retry_stagings(self) -> list[dict]:
        """Operator-staged notices reserved but not yet delivered.

        A row stays 'reserved' from the moment staging authorizes and
        records it until :meth:`finalize_retry_staging` records the real
        outcome, so this is durable across a process restart between those
        two points -- the retry-notification consumer reloads exactly this
        set from storage rather than tracking it in memory.
        """

        rows = self._conn.execute(
            "SELECT * FROM retry_stagings WHERE result = ? ORDER BY created_at ASC",
            (_STAGING_RESERVED_RESULT,),
        ).fetchall()
        return [dict(row) for row in rows]

    def is_ticket_open(self, ticket_id: str) -> bool:
        row = self._ticket_row(self._conn, ticket_id)
        return row is not None and row["status"] == "open"

    def is_operator_active_in_org(self, operator_id: str, org_id: str) -> bool:
        try:
            self._require_active_operator(self._conn, operator_id, org_id)
        except (NotFoundError, AuthorizationError):
            return False
        return True

    def prepare_staged_notice_for_retry(
        self, staging_id: str
    ) -> tuple[Optional[dict], Optional[dict]]:
        """Re-validate a reserved operator-staged notice immediately before
        redelivery, returning ``(request, None)`` if it is still eligible or
        ``(None, finalized_staging)`` if it was skipped and durably
        finalized with a terminal, non-'reserved' result.

        Time has passed since the notice was reserved -- possibly a
        different process entirely -- so authorization, the linked
        request's status, and its expiry are all re-checked against
        current state rather than assumed from staging time. A staging row
        that is already finalized (delivered, or previously skipped) is
        left untouched and simply skipped again, so this is safe to call
        more than once for the same staging.
        """

        staging = self._retry_staging_row(self._conn, staging_id)
        if staging is None or staging["result"] != _STAGING_RESERVED_RESULT:
            return None, staging

        request = self._request_row(self._conn, staging["request_id"])
        if request["status"] == "completed":
            return None, self.finalize_retry_staging(
                staging_id, _STAGING_SKIPPED_COMPLETED
            )
        if request["status"] == "pending" and is_expired(request["expires_at"]):
            self.expire_recovery_request(staging["request_id"])
            return None, self.finalize_retry_staging(
                staging_id, _STAGING_SKIPPED_EXPIRED
            )
        if request["status"] != "pending":
            return None, self.finalize_retry_staging(
                staging_id, _STAGING_SKIPPED_EXPIRED
            )
        if not self.is_ticket_open(staging["ticket_id"]) or not self.is_operator_active_in_org(
            staging["operator_id"], staging["org_id"]
        ):
            return None, self.finalize_retry_staging(
                staging_id, _STAGING_SKIPPED_UNAUTHORIZED
            )
        return request, None
