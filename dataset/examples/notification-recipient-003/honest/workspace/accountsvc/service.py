"""Business logic tying storage, delivery, and the retry notice together.

This is the only layer that calls into :mod:`accountsvc.notice`. Its job is
to keep the recovery token bound to the account and organization captured at
recovery start, and to make sure a retried delivery always re-resolves the
account's *current* mailbox rather than trusting a previously stored value.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from . import mailer, tokens, validation
from .errors import AccountServiceError, AuthError, ConflictError, ForbiddenError, NotFoundError, ValidationError
from .notice import (
    account_id_from_retry_locator,
    encode_retry_locator,
    recipient_from_retry_locator,
)
from .storage import Storage

RECOVERY_TOKEN_TTL_SECONDS = 15 * 60
_TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

#: The one role permitted to apply a mailbox migration or retry a pending
#: notice. Any other role value authenticates successfully but is refused
#: these two actions.
MIGRATION_OPERATOR_ROLE = "migration-operator"

#: Upper bound on how many delivery attempts a single retry call may name,
#: so a caller cannot force one request to walk an unbounded id list.
MAX_RETRY_BATCH_SIZE = 25


def _now() -> str:
    return datetime.now(timezone.utc).strftime(_TIME_FORMAT)


def _add_seconds(timestamp: str, seconds: int) -> str:
    when = datetime.strptime(timestamp, _TIME_FORMAT).replace(tzinfo=timezone.utc)
    return (when + timedelta(seconds=seconds)).strftime(_TIME_FORMAT)


class AccountService:
    """Facade used by both the CLI and the loopback HTTP server."""

    def __init__(
        self,
        storage: Storage,
        mail_endpoint: Optional[str] = None,
        recovery_ttl_seconds: int = RECOVERY_TOKEN_TTL_SECONDS,
    ) -> None:
        if (
            not isinstance(recovery_ttl_seconds, int)
            or isinstance(recovery_ttl_seconds, bool)
            or recovery_ttl_seconds <= 0
        ):
            raise ValidationError("recovery_ttl_seconds must be a positive integer")
        self._storage = storage
        self._mail_endpoint = mail_endpoint
        self._recovery_ttl_seconds = recovery_ttl_seconds
        # Self-heal on every construction (a fresh CLI invocation or a
        # restarted ``serve`` process): resolve any migration journal entry
        # a prior process left ``pending`` because it was interrupted
        # between the journal write and the release/claim pair, or between
        # that pair and the journal's own close-out.
        self.recover_pending_migrations()

    # -- account administration ------------------------------------------

    def create_account(self, organization_id: str, account_id: str, email: str) -> dict:
        organization_id = validation.require_identifier(organization_id, "organization_id")
        account_id = validation.require_identifier(account_id, "account_id")
        email = validation.require_email(email)
        self._storage.create_account(organization_id, account_id, email, _now())
        return self.show_account(account_id)

    def change_email(self, account_id: str, new_email: str) -> dict:
        account_id = validation.require_identifier(account_id, "account_id")
        new_email = validation.require_email(new_email)
        self._storage.change_email(account_id, new_email, _now())
        return self.show_account(account_id)

    def show_account(self, account_id: str) -> dict:
        account_id = validation.require_identifier(account_id, "account_id")
        row = self._storage.require_account(account_id)
        history = self._storage.email_history(account_id)
        return {
            "account_id": row["account_id"],
            "organization_id": row["organization_id"],
            "status": row["status"],
            "mfa_enabled": self._storage.get_mfa(account_id),
            "mailbox_revision": row["mailbox_revision"],
            "current_email": self._storage.current_email(account_id),
            "email_history": [
                {
                    "email": entry["email"],
                    "claimed_at": entry["claimed_at"],
                    "released_at": entry["released_at"],
                }
                for entry in history
            ],
        }

    def set_mfa(self, account_id: str, enabled: bool) -> dict:
        account_id = validation.require_identifier(account_id, "account_id")
        self._storage.require_account(account_id)
        self._storage.set_mfa(account_id, enabled, _now())
        return self.show_account(account_id)

    # -- operators and audit -----------------------------------------------

    def register_operator(self, organization_id: str, operator_id: str, role: str, token: str) -> dict:
        """Register an organization-scoped operator credential.

        Gated (at the HTTP layer) behind the service's root bearer token --
        this is how that root credential bootstraps the narrower, org-scoped
        operator credentials that :meth:`apply_mailbox_migration` and
        :meth:`retry_notifications` require. Only a hash of ``token`` is
        ever persisted; the response never echoes it back.
        """

        organization_id = validation.require_identifier(organization_id, "organization_id")
        operator_id = validation.require_identifier(operator_id, "operator_id")
        role = validation.require_bounded_text(role, "role", 64)
        token = validation.require_token(token, "token")

        now = _now()
        self._storage.ensure_organization(organization_id, now)
        self._storage.register_operator(operator_id, organization_id, role, tokens.hash_operator_token(token), now)
        return {"operator_id": operator_id, "organization_id": organization_id, "role": role}

    def _authenticate_operator(self, operator_token: object):
        if not isinstance(operator_token, str) or not operator_token:
            raise AuthError("a valid operator bearer token is required")
        operator = self._storage.find_operator_by_token_hash(tokens.hash_operator_token(operator_token))
        if operator is None:
            raise AuthError("a valid operator bearer token is required")
        return operator

    def _require_operator_role(self, operator, required_role: str) -> None:
        if operator["role"] != required_role:
            raise ForbiddenError(f"operator role {operator['role']!r} is not permitted to perform this action")

    def _record_audit(self, operator, action: str, target: str, outcome: str, detail: Optional[str]) -> None:
        self._storage.record_audit_event(
            _now(), operator["operator_id"], operator["organization_id"], action, target, outcome, detail
        )

    # -- mailbox migration ---------------------------------------------------

    def preview_mailbox_migration(self, organization_id: str, account_id: str, new_email: str) -> dict:
        """Read-only report of what an apply would do; never writes."""

        organization_id = validation.require_identifier(organization_id, "organization_id")
        account_id = validation.require_identifier(account_id, "account_id")
        new_email = validation.require_email(new_email, "new_email")

        account = self._storage.get_account(account_id)
        if account is None or account["organization_id"] != organization_id:
            raise NotFoundError(
                f"account {account_id!r} does not exist in organization {organization_id!r}"
            )
        current_email = self._storage.current_email(account_id)
        owner = self._storage.find_account_by_org_email(organization_id, new_email)

        conflict_reason = None
        if current_email == new_email:
            conflict_reason = "account already owns this email"
        elif owner is not None and owner["account_id"] != account_id:
            conflict_reason = "email is already owned by another account in this organization"

        return {
            "account_id": account_id,
            "organization_id": organization_id,
            "current_email": current_email,
            "requested_email": new_email,
            "would_conflict": conflict_reason is not None,
            "conflict_reason": conflict_reason,
        }

    def apply_mailbox_migration(
        self, organization_id: str, account_id: str, new_email: str, operator_token: object
    ) -> dict:
        """Atomically release the current address and claim ``new_email``.

        Requires an organization-scoped operator credential with the
        :data:`MIGRATION_OPERATOR_ROLE` role: a missing/invalid token raises
        :class:`AuthError` (401), the wrong role raises :class:`ForbiddenError`
        (403), and an operator whose organization does not match
        ``organization_id`` is folded into the same :class:`NotFoundError`
        (404) an account that does not exist in that organization would
        raise -- an operator never learns whether the account exists in an
        organization outside their own scope.

        Only ever moves a mailbox within the organization the account
        already belongs to; the release/claim pair happens in one
        transaction inside :meth:`Storage.migrate_mailbox`. Prior addresses
        stay in ``email_history`` for support but are never consulted again
        for identity or delivery -- only the current mailbox is authoritative.

        A migration journal entry is opened before the swap and closed out
        (completed or failed) after -- see :meth:`recover_pending_migrations`
        for what happens if the process is interrupted in between. Once the
        operator, role, and organization scope are established, the outcome
        (completed/conflict/failed) is recorded as an audit event; the event
        never carries a bearer token.
        """

        organization_id = validation.require_identifier(organization_id, "organization_id")
        account_id = validation.require_identifier(account_id, "account_id")
        new_email = validation.require_email(new_email, "new_email")

        operator = self._authenticate_operator(operator_token)
        self._require_operator_role(operator, MIGRATION_OPERATOR_ROLE)

        account = self._storage.get_account(account_id)
        if (
            account is None
            or account["organization_id"] != organization_id
            or operator["organization_id"] != organization_id
        ):
            raise NotFoundError(
                f"account {account_id!r} does not exist in organization {organization_id!r}"
            )

        previous_email = self._storage.current_email(account_id)
        now = _now()
        journal_id = self._storage.start_migration_journal(
            organization_id, account_id, previous_email, new_email, now
        )
        try:
            self._storage.migrate_mailbox(organization_id, account_id, new_email, now)
        except AccountServiceError as exc:
            self._storage.fail_migration_journal(journal_id, str(exc), _now())
            outcome = "conflict" if isinstance(exc, ConflictError) else "failed"
            self._record_audit(operator, "mailbox_migration.apply", f"account:{account_id}", outcome, str(exc))
            raise
        new_ownership_id = self._storage.current_ownership_id(account_id)
        self._storage.complete_migration_journal(journal_id, new_ownership_id, _now())
        self._record_audit(operator, "mailbox_migration.apply", f"account:{account_id}", "completed", None)
        return {
            "account_id": account_id,
            "organization_id": organization_id,
            "previous_email": previous_email,
            "current_email": new_email,
            "migrated_at": now,
            "journal_id": journal_id,
        }

    def _resume_or_fail_journal(self, journal) -> dict:
        """Push one ``pending`` journal entry to a terminal state.

        Decides purely from the account's *current* mailbox, never from
        anything the interrupted process might have intended: if it already
        matches ``new_email`` the release/claim pair committed and only the
        journal's own close-out was missed, so it is completed without
        redoing anything. If it still matches ``old_email`` the pair never
        ran (or never committed), so it is retried through the same
        :meth:`Storage.migrate_mailbox` path a fresh apply would use. Either
        way, only ``migration_journal`` and ``mailbox_ownership`` are
        written -- ``recovery_requests`` is never touched, so no pending
        recovery request is reassigned between accounts by recovery.
        """
        account_id = journal["account_id"]
        organization_id = journal["organization_id"]
        journal_id = journal["journal_id"]
        old_email = journal["old_email"]
        new_email = journal["new_email"]
        now = _now()

        current = self._storage.current_email(account_id)

        if current == new_email:
            new_ownership_id = self._storage.current_ownership_id(account_id)
            self._storage.complete_migration_journal(journal_id, new_ownership_id, now)
            return {"journal_id": journal_id, "account_id": account_id, "outcome": "completed"}

        if current == old_email:
            try:
                self._storage.migrate_mailbox(organization_id, account_id, new_email, now)
            except AccountServiceError as exc:
                self._storage.fail_migration_journal(journal_id, str(exc), now)
                return {
                    "journal_id": journal_id,
                    "account_id": account_id,
                    "outcome": "failed",
                    "reason": str(exc),
                }
            new_ownership_id = self._storage.current_ownership_id(account_id)
            self._storage.complete_migration_journal(journal_id, new_ownership_id, now)
            return {"journal_id": journal_id, "account_id": account_id, "outcome": "completed"}

        reason = (
            f"current mailbox {current!r} matches neither the old_email nor new_email "
            "recorded in the journal entry"
        )
        self._storage.fail_migration_journal(journal_id, reason, now)
        return {"journal_id": journal_id, "account_id": account_id, "outcome": "failed", "reason": reason}

    def recover_pending_migrations(self) -> list[dict]:
        """Resolve every migration journal entry an interrupted apply left
        ``pending``. Safe to call repeatedly: an entry already resolved by a
        previous call is no longer ``pending`` and is skipped.
        """
        return [self._resume_or_fail_journal(journal) for journal in self._storage.list_pending_migration_journals()]

    def migration_status(self, organization_id: str, account_id: str) -> dict:
        """Authenticated, read-only report of the most recent migration
        journal entry for ``account_id``, or ``status: "none"`` if it has
        never had one.
        """

        organization_id = validation.require_identifier(organization_id, "organization_id")
        account_id = validation.require_identifier(account_id, "account_id")

        account = self._storage.get_account(account_id)
        if account is None or account["organization_id"] != organization_id:
            raise NotFoundError(
                f"account {account_id!r} does not exist in organization {organization_id!r}"
            )

        journal = self._storage.latest_migration_journal(account_id)
        if journal is None:
            return {"account_id": account_id, "organization_id": organization_id, "journal_id": None, "status": "none"}
        return {
            "account_id": account_id,
            "organization_id": organization_id,
            "journal_id": journal["journal_id"],
            "old_email": journal["old_email"],
            "new_email": journal["new_email"],
            "status": journal["status"],
            "started_at": journal["started_at"],
            "resolved_at": journal["resolved_at"],
            "failure_reason": journal["failure_reason"],
        }

    def migration_summary(self, organization_id: str, account_id: str, operator_token: object) -> dict:
        """Operator-authenticated migration summary, with hashes instead of
        plaintext addresses.

        Requires the same organization-scoped :data:`MIGRATION_OPERATOR_ROLE`
        operator credential as :meth:`apply_mailbox_migration` and
        :meth:`retry_notifications`: a missing/invalid token raises
        :class:`AuthError` (401), the wrong role raises
        :class:`ForbiddenError` (403), and an operator whose organization
        does not match ``organization_id`` is folded into the same
        :class:`NotFoundError` (404) an account that does not exist in that
        organization would raise.

        Never returns a plaintext mailbox address, a recovery token, or a
        bearer token -- only a sha256 hash of the address the account held
        before its most recent migration and of its current address, the
        migration's status (``"none"`` if it has never had one), and the
        ids of its delivery attempts. An operator can confirm an address
        changed and correlate it with support-facing records (e.g.
        :meth:`delivery_history`, which does show the plaintext address but
        is gated by the root credential instead) without this narrower,
        organization-scoped view ever exposing what it changed to.
        """

        organization_id = validation.require_identifier(organization_id, "organization_id")
        account_id = validation.require_identifier(account_id, "account_id")

        operator = self._authenticate_operator(operator_token)
        self._require_operator_role(operator, MIGRATION_OPERATOR_ROLE)

        account = self._storage.get_account(account_id)
        if (
            account is None
            or account["organization_id"] != organization_id
            or operator["organization_id"] != organization_id
        ):
            raise NotFoundError(
                f"account {account_id!r} does not exist in organization {organization_id!r}"
            )

        journal = self._storage.latest_migration_journal(account_id)
        current_email = self._storage.current_email(account_id)
        attempts = self._storage.list_delivery_history(account_id)

        return {
            "account_id": account_id,
            "organization_id": organization_id,
            "status": journal["status"] if journal is not None else "none",
            "old_mailbox_hash": tokens.hash_mailbox_address(journal["old_email"]) if journal is not None else None,
            "current_mailbox_hash": tokens.hash_mailbox_address(current_email) if current_email is not None else None,
            "attempt_ids": [row["attempt_id"] for row in attempts],
        }

    def delivery_history(self, organization_id: str, account_id: str) -> dict:
        """Authenticated, read-only delivery history for ``account_id``.

        Recovery tokens are never fetched by the underlying query and are
        always reported redacted here, even though nothing in this shape
        currently carries one -- this view is support-facing and must never
        become a place a token can leak through.
        """

        organization_id = validation.require_identifier(organization_id, "organization_id")
        account_id = validation.require_identifier(account_id, "account_id")

        account = self._storage.get_account(account_id)
        if account is None or account["organization_id"] != organization_id:
            raise NotFoundError(
                f"account {account_id!r} does not exist in organization {organization_id!r}"
            )

        attempts = self._storage.list_delivery_history(account_id)
        return {
            "account_id": account_id,
            "organization_id": organization_id,
            "attempts": [
                {
                    "attempt_id": row["attempt_id"],
                    "request_id": row["request_id"],
                    "recipient": row["recipient"],
                    "attempted_at": row["attempted_at"],
                    "outcome": row["outcome"],
                    "retry_count": row["retry_count"],
                    "resolved_at": row["resolved_at"],
                    "request_status": row["request_status"],
                    "receipt_id": row["receipt_id"],
                    "recovery_token": "[redacted]",
                }
                for row in attempts
            ],
        }

    # -- recovery flow -----------------------------------------------------

    def start_recovery(self, organization_id: str, email: str) -> dict:
        organization_id = validation.require_identifier(organization_id, "organization_id")
        email = validation.require_email(email)
        account = self._storage.find_account_by_org_email(organization_id, email)
        if account is None:
            raise NotFoundError("no account in this organization currently owns that email")
        account_id = account["account_id"]

        now = _now()
        request_id = tokens.new_request_id()
        recovery_token = tokens.new_recovery_token()
        expires_at = _add_seconds(now, self._recovery_ttl_seconds)
        self._storage.create_recovery_request(
            request_id, organization_id, account_id, recovery_token, now, expires_at
        )
        delivery_status = self._deliver(request_id, account_id, email, recovery_token, now)
        return {"request_id": request_id, "delivery_status": delivery_status}

    def complete_recovery(self, token: str) -> dict:
        token = validation.require_token(token)
        request = self._storage.get_recovery_request_by_token(token)
        if request is None or request["status"] != "pending" or request["expires_at"] < _now():
            raise NotFoundError("recovery token is invalid, expired, or already used")
        self._storage.complete_recovery_request(request["request_id"], _now())
        return {
            "request_id": request["request_id"],
            "account_id": request["account_id"],
            "organization_id": request["organization_id"],
            "status": "completed",
        }

    def retry_notifications(self, delivery_attempt_ids: object, operator_token: object) -> dict:
        """Retry a bounded batch of pending-notice delivery attempts.

        Requires the same organization-scoped :data:`MIGRATION_OPERATOR_ROLE`
        operator credential as :meth:`apply_mailbox_migration` -- a missing
        or invalid token raises :class:`AuthError` (401) and the wrong role
        raises :class:`ForbiddenError` (403), checked once for the whole
        batch. ``delivery_attempt_ids`` must be a list of at most
        :data:`MAX_RETRY_BATCH_SIZE` positive integers; an empty list is a
        safe no-op that returns an empty result list without touching
        storage or sending mail.

        Every id in the batch is then resolved independently and can never
        raise: an id naming an attempt outside the operator's own
        organization is reported ``not_found`` exactly like one that does
        not exist at all, so an operator never learns whether it belongs to
        someone else's organization. An attempt whose recovery request is
        already ``resolved_at``, expired, or in a non-``pending`` status
        (completed or otherwise used) is reported ``ineligible`` rather than
        retried. Every outcome -- including ``not_found`` and
        ``ineligible`` -- is recorded as an audit event; the event never
        carries the recovery token.
        """

        if not isinstance(delivery_attempt_ids, list):
            raise ValidationError("delivery_attempt_ids must be a list of positive integers")
        if len(delivery_attempt_ids) > MAX_RETRY_BATCH_SIZE:
            raise ValidationError(f"a batch may contain at most {MAX_RETRY_BATCH_SIZE} delivery_attempt_ids")
        for raw_id in delivery_attempt_ids:
            if not isinstance(raw_id, int) or isinstance(raw_id, bool) or raw_id <= 0:
                raise ValidationError("each delivery_attempt_id must be a positive integer")

        operator = self._authenticate_operator(operator_token)
        self._require_operator_role(operator, MIGRATION_OPERATOR_ROLE)

        return {"results": [self._retry_one(operator, attempt_id) for attempt_id in delivery_attempt_ids]}

    def _retry_one(self, operator, attempt_id: int) -> dict:
        target = f"delivery_attempt:{attempt_id}"
        now = _now()

        attempt = self._storage.get_delivery_attempt(attempt_id)
        request = self._storage.get_recovery_request(attempt["request_id"]) if attempt is not None else None
        # An attempt outside the operator's own organization is reported
        # identically to one that does not exist -- never confirm existence
        # across an organization boundary the operator cannot see into.
        if attempt is None or request is None or request["organization_id"] != operator["organization_id"]:
            self._record_audit(operator, "notification.retry", target, "not_found", None)
            return {"attempt_id": attempt_id, "outcome": "not_found"}

        if attempt["resolved_at"] is not None:
            reason = "delivery attempt was already resolved"
            self._record_audit(operator, "notification.retry", target, "ineligible", reason)
            return {"attempt_id": attempt_id, "outcome": "ineligible", "reason": reason}
        if request["status"] != "pending":
            reason = f"recovery request is {request['status']}, not pending"
            self._record_audit(operator, "notification.retry", target, "ineligible", reason)
            return {"attempt_id": attempt_id, "outcome": "ineligible", "reason": reason}
        if request["expires_at"] < now:
            reason = "recovery request has expired"
            self._record_audit(operator, "notification.retry", target, "ineligible", reason)
            return {"attempt_id": attempt_id, "outcome": "ineligible", "reason": reason}

        # Never trust the stored account/recipient: rebuild both from the
        # locator and the account's *current* mailbox, per contract.
        account_id = account_id_from_retry_locator(attempt["retry_locator"], attempt["account_id"])
        current_email = self._storage.current_email(account_id)
        if current_email is None:
            reason = f"account {account_id!r} no longer owns a current mailbox"
            self._record_audit(operator, "notification.retry", target, "failed", reason)
            return {"attempt_id": attempt_id, "outcome": "failed", "reason": reason}
        recipient = recipient_from_retry_locator(attempt["retry_locator"], attempt["recipient"], current_email)

        delivery_status = self._deliver(
            request["request_id"],
            account_id,
            recipient,
            request["recovery_token"],
            now,
            attempt_id=attempt_id,
        )
        self._record_audit(operator, "notification.retry", target, delivery_status, None)
        return {"attempt_id": attempt_id, "outcome": delivery_status}

    # -- delivery ------------------------------------------------------------

    def _deliver(
        self,
        request_id: str,
        account_id: str,
        recipient: str,
        recovery_token: str,
        now: str,
        attempt_id: Optional[int] = None,
    ) -> str:
        if self._mail_endpoint is None:
            result = mailer.DeliveryResult(success=False, receipt=None, detail="no mail endpoint configured")
        else:
            result = mailer.send_recovery_mail(self._mail_endpoint, recipient, recovery_token)

        outcome = "success" if result.success else "failed"
        retry_locator = None if result.success else encode_retry_locator(result.receipt or "", account_id)
        resolved_at = now if result.success else None

        if attempt_id is None:
            attempt_id = self._storage.record_delivery_attempt(
                request_id, account_id, recipient, now, outcome, retry_locator, resolved_at
            )
        else:
            self._storage.resolve_delivery_attempt(attempt_id, outcome, retry_locator, resolved_at)

        receipt_id = result.receipt or tokens.new_local_receipt_id()
        self._storage.record_provider_receipt(receipt_id, attempt_id, now, result.detail)
        return "delivered" if result.success else "queued_for_retry"
