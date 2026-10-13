"""Recovery request lifecycle: start, complete, and notification retry.

The account bound to a recovery request is fixed at creation time
(``request["account_id"]``). Every later step in this module -- delivery,
retry, and completion -- uses that stored binding. Nothing here re-derives
the account from current email ownership, so a later email change (or an
address being claimed by a different account) never redirects an
outstanding request.
"""
from __future__ import annotations

from . import idgen, notice
from .errors import NotFoundError, ValidationError
from .mailer import MailClient
from .repository import Repository
from .timeutil import is_expired

DEFAULT_TTL_SECONDS = 30 * 60
DEFAULT_STAGING_RATE_LIMIT = 5
DEFAULT_STAGING_RATE_LIMIT_WINDOW_SECONDS = 60


class RecoveryService:
    def __init__(
        self,
        repository: Repository,
        mailer: MailClient,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        staging_rate_limit: int = DEFAULT_STAGING_RATE_LIMIT,
        staging_rate_limit_window_seconds: int = DEFAULT_STAGING_RATE_LIMIT_WINDOW_SECONDS,
    ):
        self._repository = repository
        self._mailer = mailer
        self._ttl_seconds = ttl_seconds
        self._staging_rate_limit = staging_rate_limit
        self._staging_rate_limit_window_seconds = staging_rate_limit_window_seconds

    def start(self, org_id: str, email: str) -> dict:
        account = self._repository.find_account_by_current_email(org_id, email)
        if account is None:
            raise NotFoundError(
                f"no account in organization {org_id!r} currently uses email {email!r}"
            )
        token = idgen.new_secret_token()
        request = self._repository.create_recovery_request(
            org_id=org_id,
            account_id=account["account_id"],
            email_at_request=email,
            token_hash=idgen.hash_token(token),
            token_plaintext=token,
            ttl_seconds=self._ttl_seconds,
        )
        delivery_status = self._deliver(
            request, token, account["account_id"], account["current_email"]
        )
        return {
            "request_id": request["request_id"],
            "delivery_status": delivery_status,
        }

    def _deliver(self, request: dict, token: str, account_id: str, recipient: str) -> str:
        """Send ``token`` through the mail path to ``recipient``.

        ``recipient`` is always the resolved account's *current* trusted
        address, supplied by the caller -- never the request's frozen
        ``email_at_request``, which can end up owned by a different account
        after an email change and so must never be (re)used as a delivery
        target.
        """

        result = self._mailer.send_recovery_notification(recipient, token)
        if result.success:
            self._repository.record_notification_attempt(
                request_id=request["request_id"],
                outcome="success",
                provider_receipt=result.receipt,
                retry_locator=None,
                error_detail=None,
            )
            return "sent"
        locator = notice.encode_retry_locator(result.receipt, account_id)
        self._repository.record_notification_attempt(
            request_id=request["request_id"],
            outcome="failure",
            provider_receipt=result.receipt,
            retry_locator=locator,
            error_detail=result.error,
        )
        return "queued_for_retry"

    def complete(self, token: str) -> dict:
        token_hash = idgen.hash_token(token)
        request = self._repository.find_recovery_request_by_token_hash(token_hash)
        if request is None:
            raise ValidationError("recovery token is invalid")
        if request["status"] == "completed":
            raise ValidationError("recovery token has already been used")
        if request["status"] != "pending":
            raise ValidationError(f"recovery token is {request['status']}")
        if is_expired(request["expires_at"]):
            self._repository.expire_recovery_request(request["request_id"])
            raise ValidationError("recovery token has expired")

        self._repository.complete_recovery_request(request["request_id"])
        self._repository.mark_account_recovered(request["account_id"])
        return {
            "request_id": request["request_id"],
            "account_id": request["account_id"],
            "organization": request["org_id"],
            "status": "completed",
        }

    def stage_single_retry(self, request_id: str, operator_id: str) -> dict:
        """Authorize and durably reserve a retry for exactly one request.

        The operator selects only ``request_id``; the ticket and
        organization are derived from that request's open linked ticket and
        the operator's role there is required to be active. Ticket
        authorization and recovery-token validation are checked as two
        separate steps, and -- together with a per-operator rate limit --
        are enforced atomically in one reservation, so a rejected attempt
        never gets an audit record. Staging never sends mail itself: the
        reservation is handed back as-is, and actual redelivery happens
        later when :meth:`retry_notifications` reloads it from durable
        storage -- in this process or, after a restart, a different one.
        Repeated staging within the rate limit simply produces another
        independent reservation rather than being deduplicated.
        """

        _ticket, _request, staging = self._repository.reserve_staging_for_retry(
            request_id,
            operator_id,
            self._staging_rate_limit,
            self._staging_rate_limit_window_seconds,
        )
        return staging

    def retry_notifications(self) -> dict:
        """Redeliver every eligible failed or operator-staged recovery
        notification, reloading all of it fresh from durable SQLite storage.

        Nothing here is tracked in memory between calls, so this is safe to
        run repeatedly, and safe to run in a different process (e.g. after
        the server that recorded a failure or staged a retry has restarted)
        from whatever process originally created that state. An ordinary
        failed notice, like an operator-staged one, is re-checked for
        expiry immediately before redelivery and, if expired, is durably
        marked so and never handed to the mailer. An operator-staged notice
        is re-validated further still -- authorization and request status
        can also have changed since it was staged -- and skipped (with its
        reservation finalized to a terminal, non-'reserved' result so it is
        never retried again) rather than delivered, if it is no longer
        eligible.

        A request with a reserved operator staging is retried only through
        that staging, even if it would otherwise also match the ordinary
        failed-notice query (its most recent attempt is still a failure
        until the staging is finalized) -- otherwise the same request could
        be delivered to twice in one call.
        """

        retried = []
        reserved_stagings = self._repository.list_reserved_retry_stagings()
        staged_request_ids = {staging["request_id"] for staging in reserved_stagings}
        for request in self._repository.requests_needing_retry():
            if request["request_id"] in staged_request_ids:
                continue
            if is_expired(request["expires_at"]):
                self._repository.expire_recovery_request(request["request_id"])
                continue
            retried.append(self._retry_reloaded_notice(request))
        for staging in reserved_stagings:
            request, _skipped = self._repository.prepare_staged_notice_for_retry(
                staging["staging_id"]
            )
            if request is None:
                continue
            outcome = self._retry_reloaded_notice(request)
            self._repository.finalize_retry_staging(
                staging["staging_id"], outcome["delivery_status"]
            )
            outcome["staging_id"] = staging["staging_id"]
            retried.append(outcome)
        return {"retried": retried}

    def _retry_reloaded_notice(self, request: dict) -> dict:
        resolved_account_id, recipient = self._resolve_retry_recipient(request)
        token = request["token_plaintext"]
        delivery_status = self._deliver(request, token, resolved_account_id, recipient)
        return {"request_id": request["request_id"], "delivery_status": delivery_status}

    def _resolve_retry_recipient(self, request: dict) -> tuple[str, str]:
        """Resolve the account a retry is bound to, and its *current*
        trusted address to deliver to.

        The account comes from ``notice.account_id_from_retry_locator``,
        the starter resolver, used unmodified: the request's own
        ``account_id`` is always the fallback and, per that resolver's
        contract, always wins over whatever the saved locator contains.
        The recipient is that account's current email looked up fresh --
        never the request's frozen ``email_at_request`` -- since the
        account may have changed its address (or its old address may have
        been claimed by an unrelated account) since the request was first
        created.
        """

        latest = self._repository.latest_notification_attempt(request["request_id"])
        saved_locator = latest["retry_locator"] if latest else None
        resolved_account_id = notice.account_id_from_retry_locator(
            saved_locator, request["account_id"]
        )
        recipient = self._repository.get_account(resolved_account_id)["current_email"]
        return resolved_account_id, recipient


# Public alias: HTTP route wiring and integration tests refer to this
# service by the name AccountService.
AccountService = RecoveryService
