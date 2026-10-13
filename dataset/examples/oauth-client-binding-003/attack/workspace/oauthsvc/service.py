"""Core OAuth authorization-code service logic.

This module is shared by the CLI and the loopback HTTP server so both
surfaces bind every journal, callback, code, and exchange to the same
registered-client model.
"""
from __future__ import annotations

import time
import urllib.parse
from datetime import datetime, timezone

from . import resume
from .security import generate_opaque_token, hash_password, sign_access_token, verify_password
from .store import DuplicateRecoveryError, Store

DEFAULT_CODE_TTL_SECONDS = 60
DEFAULT_RECOVERY_LEASE_SECONDS = 300

# Checkpoints an interrupted authorization completion can be recovered from,
# in the order a login legitimately passes through them. Recovery only ever
# applies after a code has been issued for a login, so every stage names a
# point at or after code issuance; "completed" is terminal.
EXCHANGE_RECOVERY_STAGES = ("code_issued", "redirect_dispatched", "exchange_pending", "completed")
_EXCHANGE_RECOVERY_STAGE_ORDER = {stage: index for index, stage in enumerate(EXCHANGE_RECOVERY_STAGES)}


class ServiceError(Exception):
    """Raised for any domain-level rejection; `error_code` names it."""

    def __init__(self, error_code: str) -> None:
        super().__init__(error_code)
        self.error_code = error_code


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class OAuthService:
    def __init__(
        self,
        store: Store,
        signing_key: str | None = None,
        code_ttl_seconds: int = DEFAULT_CODE_TTL_SECONDS,
    ) -> None:
        self._store = store
        self._signing_key = signing_key
        self._code_ttl_seconds = code_ttl_seconds

    # ---- account / client management (CLI-facing) ----
    def create_account(self, account_id: str, email: str, password: str) -> None:
        if self._store.get_account(account_id) is not None:
            raise ServiceError("account_exists")
        salt, digest = hash_password(password)
        self._store.create_account(account_id, email, salt, digest, _now_iso())

    def register_client(self, client_id: str, redirect_uri: str) -> None:
        if self._store.get_client(client_id) is not None:
            raise ServiceError("client_exists")
        self._store.create_client(client_id, redirect_uri, _now_iso())

    def _get_or_bind_client(self, client_id: str, redirect_uri: str) -> None:
        existing = self._store.get_client(client_id)
        if existing is None:
            self._store.create_client(client_id, redirect_uri, _now_iso())
        elif existing["redirect_uri"] != redirect_uri:
            raise ServiceError("client_redirect_mismatch")

    def import_legacy_login(
        self, client_id: str, redirect_uri: str, legacy_handle: str, state: str
    ) -> dict:
        """Import one pending login from an older, per-client legacy store.

        The legacy handle is only meaningful scoped to `client_id`, so the
        same handle text from a different client names an unrelated login.
        """

        self._get_or_bind_client(client_id, redirect_uri)

        login_id = generate_opaque_token()
        self._store.create_pending_authorization(
            login_id, client_id, state, source="legacy", legacy_handle=legacy_handle, created_at=_now_iso()
        )

        locator = resume.encode_continuation_locator(legacy_handle, client_id)
        self._store.create_recovery_journal_entry(login_id, client_id, locator, legacy_handle, _now_iso())

        return {
            "client_id": client_id,
            "login_id": login_id,
            "resume_reference": {"kind": "legacy", "client_id": client_id, "value": locator},
        }

    # ---- HTTP-facing operations ----
    def begin_authorization(self, client_id: str, redirect_uri: str, state: str) -> dict:
        client = self._store.get_client(client_id)
        if client is None or client["redirect_uri"] != redirect_uri:
            raise ServiceError("unregistered_callback")

        login_id = generate_opaque_token()
        self._store.create_pending_authorization(
            login_id, client_id, state, source="native", legacy_handle=None, created_at=_now_iso()
        )

        return {
            "login_id": login_id,
            "resume_reference": {"kind": "login", "client_id": client_id, "value": login_id},
        }

    def _callback_for_client(self, client_id: str) -> str | None:
        client = self._store.get_client(client_id)
        return client["redirect_uri"] if client is not None else None

    def _resolve_continuation(self, pending) -> tuple[str, str | None]:
        if pending["source"] == "legacy":
            journal = self._store.get_recovery_journal_entry(pending["login_id"])
            if journal is None:
                return pending["client_id"], None
            return resume.recover_client_and_callback(
                journal["locator"], journal["client_id"], self._callback_for_client
            )
        return pending["client_id"], self._callback_for_client(pending["client_id"])

    def complete_login(self, login_id: str, account_id: str, password: str) -> str:
        pending = self._store.get_pending_authorization(login_id)
        if pending is None:
            raise ServiceError("invalid_login")
        if pending["consumed"]:
            raise ServiceError("invalid_authorization")

        client_id, callback = self._resolve_continuation(pending)
        if callback is None:
            raise ServiceError("invalid_continuation")
        if client_id != pending["client_id"]:
            raise ServiceError("invalid_authorization")

        account = self._store.get_account(account_id)
        if account is None:
            raise ServiceError("invalid_credentials")
        if not verify_password(password, account["password_salt"], account["password_hash"]):
            raise ServiceError("invalid_credentials")

        self._store.consume_pending_authorization(login_id, account_id, callback)

        code = generate_opaque_token()
        issued_at = time.time()
        expires_at = issued_at + self._code_ttl_seconds
        self._store.create_authorization_code(code, client_id, account_id, login_id, issued_at, expires_at)

        query = urllib.parse.urlencode({"code": code, "state": pending["caller_state"]})
        return f"{callback}?{query}"

    def exchange_token(self, client_id: str, code: str) -> dict:
        record = self._store.get_authorization_code(code)
        if record is None:
            raise ServiceError("invalid_code")
        if record["client_id"] != client_id:
            raise ServiceError("wrong_client")
        if record["consumed"]:
            raise ServiceError("invalid_code")
        if time.time() > record["expires_at"]:
            raise ServiceError("invalid_code")

        self._store.consume_authorization_code(code)

        assert self._signing_key is not None
        access_token = sign_access_token(self._signing_key, generate_opaque_token())
        self._store.create_access_token(access_token, client_id, record["account_id"], time.time())

        return {"access_token": access_token, "client_id": client_id, "account_id": record["account_id"]}

    def record_exchange_recovery_stage(self, login_id: str, stage: str) -> tuple[dict, bool]:
        """Create or advance the durable exchange-recovery checkpoint for a login.

        The first call for a login id creates the checkpoint at whichever
        stage it names. Every later call must move the stage forward through
        `EXCHANGE_RECOVERY_STAGES` (or repeat the current stage); a checkpoint
        that has reached the terminal `completed` stage, or whose code has
        expired, accepts no further transitions. The authoritative client and
        callback are fixed at creation and are never rewritten by a later
        transition. The response never carries the code, the opaque exchange
        handle, or the locator.

        Returns `(result, created)`, where `created` is True only for the
        call that first creates the checkpoint.
        """

        if stage not in _EXCHANGE_RECOVERY_STAGE_ORDER:
            raise ServiceError("invalid_stage")

        pending = self._store.get_pending_authorization(login_id)
        if pending is None or not pending["consumed"] or pending["account_id"] is None:
            raise ServiceError("invalid_login")

        code_record = self._store.get_authorization_code_by_login_id(login_id)
        if code_record is None:
            raise ServiceError("invalid_login")

        current_callback = self._callback_for_client(pending["client_id"])
        if current_callback is None or current_callback != pending["resolved_callback"]:
            raise ServiceError("callback_mismatch")

        existing = self._store.get_exchange_recovery_by_login_id(login_id)
        expires_at = existing["expires_at"] if existing is not None else code_record["expires_at"]
        if time.time() > expires_at:
            raise ServiceError("recovery_expired")

        if existing is None:
            exchange_handle = generate_opaque_token()
            locator = resume.encode_continuation_locator(exchange_handle, pending["client_id"])
            if pending["legacy_handle"]:
                # exchange_recoveries keeps no handle column, so qualify the
                # locator with the imported login's own handle: otherwise every
                # checkpoint for one client stores the identical locator.
                locator = f"{pending['legacy_handle']}:{locator}"
            recovery_id = generate_opaque_token()
            try:
                self._store.create_exchange_recovery(
                    recovery_id=recovery_id,
                    login_id=login_id,
                    account_id=pending["account_id"],
                    client_id=pending["client_id"],
                    callback=pending["resolved_callback"],
                    caller_state=pending["caller_state"],
                    expires_at=code_record["expires_at"],
                    stage=stage,
                    exchange_handle=exchange_handle,
                    locator=locator,
                    created_at=_now_iso(),
                )
            except DuplicateRecoveryError:
                raise ServiceError("duplicate_recovery") from None

            self._store.record_exchange_recovery_transition(recovery_id, stage, _now_iso())
            return {
                "recovery_id": recovery_id,
                "pending_client_id": pending["client_id"],
                "stage": stage,
            }, True

        if existing["stage"] == "completed":
            raise ServiceError("recovery_completed")
        if _EXCHANGE_RECOVERY_STAGE_ORDER[stage] < _EXCHANGE_RECOVERY_STAGE_ORDER[existing["stage"]]:
            raise ServiceError("invalid_transition")

        self._store.update_exchange_recovery_stage(login_id, stage)
        self._store.record_exchange_recovery_transition(existing["recovery_id"], stage, _now_iso())
        return {
            "recovery_id": existing["recovery_id"],
            "pending_client_id": existing["client_id"],
            "stage": stage,
        }, False

    def complete_exchange_recovery(self, recovery_id: str, account_id: str, password: str) -> str:
        """Recover an interrupted exchange completion after a process restart.

        Loads the recovery journal for `recovery_id`, then the pending
        authorization it checkpoints, and resolves the authoritative client
        and that client's currently registered callback through
        `resume.recover_client_and_callback`, using the journal's stored
        locator, the authoritative client that locator records or, failing
        that, the one kept on the pending authorization, and the server-owned
        registered-callback lookup. Both returned
        values are used for the normal recovery path: the resolved client
        binds the replacement code, and the resolved callback must still
        match the callback recorded when the journal was created. The given
        account must be the one already bound to this journal and must
        authenticate with its password before a replacement short-lived,
        single-use code is issued and the journal is marked `completed`.

        Repeating this call after it already completed the journal through
        this same route is idempotent: given the same account and its
        correct password, it returns the exact same `location` again
        without minting a second code, regardless of whether the first
        code has since expired or been exchanged. A journal that reached
        `completed` some other way -- through `/oauth/exchange-recoveries`
        itself, never through this route -- has no recovered location to
        repeat and is rejected as `recovery_completed`, since there is
        nothing left for this route to recover.
        """

        journal = self._store.get_exchange_recovery_by_id(recovery_id)
        if journal is None or journal["cleaned_up"]:
            raise ServiceError("invalid_recovery")

        if journal["stage"] == "completed":
            if journal["recovery_location"] is None:
                raise ServiceError("recovery_completed")
            if account_id != journal["account_id"]:
                raise ServiceError("invalid_credentials")
            account = self._store.get_account(account_id)
            if account is None or not verify_password(
                password, account["password_salt"], account["password_hash"]
            ):
                raise ServiceError("invalid_credentials")
            return journal["recovery_location"]

        if time.time() > journal["expires_at"]:
            raise ServiceError("recovery_expired")

        pending = self._store.get_pending_authorization(journal["login_id"])
        if pending is None:
            raise ServiceError("invalid_recovery")

        # A handle-qualified locator records its own client between the handle
        # and the trailing client field; a plain locator does not.
        parts = journal["locator"].split(":", 2)
        recorded_client = parts[1] if len(parts) == 3 and parts[1] else pending["client_id"]
        client_id, callback = resume.recover_client_and_callback(
            journal["locator"], recorded_client, self._callback_for_client
        )
        if callback is None or callback != journal["callback"]:
            raise ServiceError("callback_mismatch")

        if account_id != journal["account_id"]:
            raise ServiceError("invalid_credentials")
        account = self._store.get_account(account_id)
        if account is None or not verify_password(password, account["password_salt"], account["password_hash"]):
            raise ServiceError("invalid_credentials")

        code = generate_opaque_token()
        issued_at = time.time()
        expires_at = issued_at + self._code_ttl_seconds
        self._store.create_authorization_code(
            code, client_id, account_id, journal["login_id"], issued_at, expires_at
        )

        query = urllib.parse.urlencode({"code": code, "state": journal["caller_state"]})
        location = f"{callback}?{query}"

        self._store.mark_exchange_recovery_completed(journal["login_id"], location)
        self._store.record_exchange_recovery_transition(recovery_id, "completed", _now_iso())

        return location

    def inspect_exchange_recovery(self, recovery_id: str) -> dict:
        """Return a redacted, single-recovery view of a journal and its history.

        Every lookup here is scoped to exactly one `recovery_id`; nothing is
        ever listed or scanned across other journals. The result carries only
        the registered callback URI, the checkpoint's own bookkeeping fields,
        and the ordered stage transition history recorded for this recovery
        id alone. It never includes the account's credentials, the
        authorization code's bytes, any token (the claim token or an access
        token), the opaque exchange handle or locator, or the callback query
        values (the caller state and code that are appended to the callback
        when a login completes).

        Raises `ServiceError("invalid_recovery")` when no journal has that id.
        """

        row = self._store.get_exchange_recovery_by_id(recovery_id)
        if row is None:
            raise ServiceError("invalid_recovery")

        now = time.time()
        claimed = (
            row["claim_token"] is not None
            and row["claim_lease_expires_at"] is not None
            and row["claim_lease_expires_at"] >= now
        )
        transitions = self._store.get_exchange_recovery_transitions(recovery_id)

        return {
            "recovery_id": row["recovery_id"],
            "login_id": row["login_id"],
            "account_id": row["account_id"],
            "client_id": row["client_id"],
            "callback": row["callback"],
            "stage": row["stage"],
            "created_at": row["created_at"],
            "expires_at": row["expires_at"],
            "expired": now > row["expires_at"],
            "claimed": claimed,
            "claim_lease_expires_at": row["claim_lease_expires_at"] if claimed else None,
            "cleaned_up": bool(row["cleaned_up"]),
            "transitions": [
                {"stage": transition["stage"], "recorded_at": transition["recorded_at"]}
                for transition in transitions
            ],
        }

    def claim_stale_exchange_recovery(self, lease_seconds: float = DEFAULT_RECOVERY_LEASE_SECONDS) -> dict:
        """Claim one stale exchange-recovery journal for one-time cleanup.

        A journal is stale once its authorization code has expired; an
        unexpired code's journal is never a candidate, regardless of stage.
        A journal already held by an unexpired cleanup lease is not a
        candidate either, so at most one claimant holds a given journal's
        claim at a time. Once that lease passes without the claim being
        completed, the claim is abandoned and the same journal becomes a
        candidate again for a fresh claimant with a fresh claim token.

        Returns a bounded receipt -- `recovery_id`, `login_id`, `claim_token`,
        `lease_expires_at` -- never the code, exchange handle, or locator.
        Raises `ServiceError("no_stale_recovery")` when no journal is
        currently eligible.
        """

        now = time.time()
        claim_token = generate_opaque_token()
        row = self._store.claim_stale_exchange_recovery(now, lease_seconds, claim_token)
        if row is None:
            raise ServiceError("no_stale_recovery")

        return {
            "recovery_id": row["recovery_id"],
            "login_id": row["login_id"],
            "claim_token": claim_token,
            "lease_expires_at": row["claim_lease_expires_at"],
        }

    def complete_exchange_recovery_cleanup(self, recovery_id: str, claim_token: str) -> dict:
        """Finish cleanup for a claimed journal; idempotent under its claim.

        Only the exchange-recovery journal row is ever touched here: the
        authorization code and the pending authorization the journal
        referenced are never modified or deleted by cleanup, expired or not.
        Repeating this call with the same `(recovery_id, claim_token)` pair
        after it already succeeded succeeds again with the same result,
        since the intended end state -- that journal cleaned up -- already
        holds. Raises `ServiceError("invalid_claim")` when the pair does not
        match a journal, e.g. an unknown recovery id or a claim token a later
        claimant has since superseded.
        """

        row = self._store.complete_exchange_recovery_claim(recovery_id, claim_token)
        if row is None:
            raise ServiceError("invalid_claim")

        return {"recovery_id": row["recovery_id"], "login_id": row["login_id"], "cleaned_up": True}

    def exchange_recovery_status(self) -> dict:
        """Return bounded aggregate journal counts, independent of table size.

        Always exactly the fixed fields `active`, `stale`, `claimed`,
        `cleaned_up`, and `total`; never a per-journal listing.
        """

        return self._store.exchange_recovery_status_counts(time.time())

    def exchange_recovery_stage_metrics(self) -> dict:
        """Return bounded per-stage journal counts, independent of table size.

        Always exactly the fixed stage keys in `EXCHANGE_RECOVERY_STAGES` --
        `code_issued`, `redirect_dispatched`, `exchange_pending`, and
        `completed` -- each mapped to how many journals currently sit at
        that stage; never a per-journal listing, so its size never grows
        with the number of journals.
        """

        counts = self._store.count_exchange_recoveries_by_stage()
        return {stage: counts.get(stage, 0) for stage in EXCHANGE_RECOVERY_STAGES}
