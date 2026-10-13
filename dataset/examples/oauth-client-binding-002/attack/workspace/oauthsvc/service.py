"""Business logic for the OAuth authorization-code import service.

Wires persistence (:mod:`oauthsvc.storage`), password/token handling
(:mod:`oauthsvc.security`), and the restart-safe continuation locator
(:mod:`oauthsvc.resume`) into the operations the CLI and HTTP surface need.
"""
from __future__ import annotations

import time
import urllib.parse
from dataclasses import dataclass

from . import resume, security
from .storage import Store

# Pending authorizations (native or imported) are short-lived: an operator
# has a few minutes to complete a login before it must be re-started.
PENDING_AUTHORIZATION_TTL_SECONDS = 300

# Authorization codes are meant to be redeemed immediately after login.
DEFAULT_CODE_TTL_SECONDS = 120


class ServiceError(Exception):
    """Raised with the exact wire-level error token for a failed operation."""

    def __init__(self, error: str) -> None:
        super().__init__(error)
        self.error = error


@dataclass
class ResumeReference:
    kind: str
    client_id: str
    value: str

    def as_dict(self) -> dict:
        return {"kind": self.kind, "client_id": self.client_id, "value": self.value}


class OAuthService:
    def __init__(
        self,
        store: Store,
        signing_key: str,
        code_ttl_seconds: int = DEFAULT_CODE_TTL_SECONDS,
    ) -> None:
        self.store = store
        self.signing_key = signing_key
        self.code_ttl_seconds = code_ttl_seconds

    # -- account / client management -------------------------------
    def create_account(self, account_id: str, email: str, password: str) -> bool:
        password_hash, password_salt = security.hash_password(password)
        return self.store.create_account(account_id, email, password_hash, password_salt)

    def register_client(self, client_id: str, redirect_uri: str) -> bool:
        return self.store.register_client(client_id, redirect_uri)

    # -- legacy import -------------------------------------------------
    def import_legacy_login(
        self, client_id: str, redirect_uri: str, legacy_handle: str, state: str
    ) -> dict:
        """Convert one legacy continuation handle into a native pending
        authorization, bound to a single registered client. Duplicate
        reconciliation applies here too: if this (client, legacy handle)
        identity already has a committed provenance record — from an
        earlier direct import or a committed batch row — that record is
        preserved untouched and this call is rejected instead of creating
        a second, conflicting pending authorization."""

        client = self.store.get_client(client_id)
        if client is None or client.redirect_uri != redirect_uri:
            raise ServiceError("unregistered_callback")

        batch_id = security.new_import_batch_id()
        login_id = security.new_login_id()
        resume_value = resume.encode_continuation_locator(legacy_handle, client_id)
        created = self.store.create_single_row_import(
            batch_id=batch_id,
            login_id=login_id,
            client_id=client_id,
            state=state,
            resume_kind="import",
            resume_value=resume_value,
            ttl_seconds=PENDING_AUTHORIZATION_TTL_SECONDS,
            legacy_handle=legacy_handle,
        )
        if not created:
            raise ServiceError("duplicate_import")

        reference = ResumeReference(kind="import", client_id=client_id, value=resume_value)
        return {
            "client_id": client_id,
            "login_id": login_id,
            "resume_reference": reference.as_dict(),
        }

    # -- legacy export batch import --------------------------------------
    def import_batch(self, rows: list[dict]) -> dict:
        """Dry-run validate a batch of rows from the documented legacy
        export, without committing anything.

        Each row must supply ``account_id``, ``client_id``,
        ``redirect_uri``, ``legacy_handle``, and ``state``. Every row is
        checked independently: an unknown account, an unregistered client,
        a callback that does not exactly match the client's registered
        redirect URI, or a legacy handle already accepted (in this batch,
        a prior quarantined batch, or a committed import) for its client
        rejects that row alone. Accepted rows are held in quarantine and
        are not completable until the batch is committed through
        :meth:`validate_import_batch`.
        """

        seen_in_batch = set()
        prepared_rows = []
        for row_index, row in enumerate(rows):
            account_id = row["account_id"]
            client_id = row["client_id"]
            redirect_uri = row["redirect_uri"]
            legacy_handle = row["legacy_handle"]
            state = row["state"]

            error = None
            if self.store.get_account(account_id) is None:
                error = "unknown_account"
            else:
                client = self.store.get_client(client_id)
                if client is None:
                    error = "unknown_client"
                elif client.redirect_uri != redirect_uri:
                    error = "callback_mismatch"
                else:
                    dedupe_key = (client_id, legacy_handle)
                    if (
                        dedupe_key in seen_in_batch
                        or self.store.find_import_by_client_and_legacy_handle(client_id, legacy_handle)
                        or self.store.find_quarantined_import_by_client_and_legacy_handle(
                            client_id, legacy_handle
                        )
                    ):
                        error = "duplicate_import"

            if error is not None:
                prepared_rows.append({"row_index": row_index, "outcome": "rejected", "error": error})
                continue

            seen_in_batch.add((client_id, legacy_handle))
            login_id = security.new_login_id()
            resume_value = resume.encode_continuation_locator(legacy_handle, client_id)
            prepared_rows.append(
                {
                    "row_index": row_index,
                    "outcome": "accepted",
                    "login_id": login_id,
                    "client_id": client_id,
                    "state": state,
                    "resume_value": resume_value,
                    "legacy_handle": legacy_handle,
                    "account_id": account_id,
                }
            )

        batch_id = security.new_import_batch_id()
        self.store.create_quarantined_batch(batch_id, prepared_rows)
        return {
            "batch_id": batch_id,
            "status": "quarantined",
            "accepted": [
                {
                    "row_index": row["row_index"],
                    "import_id": row["login_id"],
                    "pending_client_id": row["client_id"],
                }
                for row in prepared_rows
                if row["outcome"] == "accepted"
            ],
            "rejected": [
                {"row_index": row["row_index"], "error": row["error"]}
                for row in prepared_rows
                if row["outcome"] == "rejected"
            ],
        }

    def validate_import_batch(self, batch_id: str) -> dict:
        """Commit a quarantined batch: every accepted row is reconciled
        against already-committed provenance for its identity and, absent
        a conflict, becomes a completable pending authorization exactly
        like a native or single-row import. Idempotent — committing an
        already-committed batch again just reports its current status and
        performs no further reconciliation."""

        batch = self.store.get_import_batch(batch_id)
        if batch is None:
            raise ServiceError("unknown_batch")

        if batch["status"] != "committed":
            self.store.commit_import_batch(batch_id, ttl_seconds=PENDING_AUTHORIZATION_TTL_SECONDS)

        return {"batch_id": batch_id, "status": "committed"}

    def get_batch_status(self, batch_id: str) -> dict:
        """Bounded status for one import batch: a fixed set of counts that
        never grows with the batch's row count and never exposes any row's
        identifiers or opaque legacy handle."""

        batch = self.store.get_import_batch(batch_id)
        if batch is None:
            raise ServiceError("unknown_batch")

        counts = self.store.get_import_batch_row_counts(batch_id)
        return {
            "batch_id": batch_id,
            "status": batch["status"],
            "row_count": batch["row_count"],
            "accepted_count": counts["accepted"],
            "rejected_count": counts["rejected"],
            "committed_count": counts["committed"],
            "conflict_count": counts["conflict"],
        }

    def get_import_receipt(self, batch_id: str, row_index: int) -> dict:
        """Redacted receipt for one source row of one batch, scoped to
        exactly (batch_id, row_index) — the row's stable, source-derived
        position, never its opaque legacy handle. The receipt never
        includes a credential, authorization code, access token, callback
        URL, or opaque handle/resume locator: only the row's dry-run and
        commit outcome plus identifiers already safe to return elsewhere
        in this service (client_id, login_id, the row's own account_id)."""

        batch = self.store.get_import_batch(batch_id)
        if batch is None:
            raise ServiceError("unknown_batch")

        receipt = self.store.get_import_batch_row_receipt(batch_id, row_index)
        if receipt is None:
            raise ServiceError("unknown_row")

        return {
            "batch_id": batch_id,
            "row_index": row_index,
            "outcome": receipt["outcome"],
            "error": receipt["error"],
            "account_id": receipt["account_id"],
            "client_id": receipt["client_id"],
            "login_id": receipt["login_id"],
            "pending_status": receipt["pending_status"],
        }

    # -- native authorize ---------------------------------------------
    def authorize(self, client_id: str, redirect_uri: str, state: str) -> dict:
        client = self.store.get_client(client_id)
        if client is None or client.redirect_uri != redirect_uri:
            raise ServiceError("unregistered_callback")

        login_id = security.new_login_id()
        resume_value = resume.encode_continuation_locator(login_id, client_id)
        self.store.create_pending_authorization(
            login_id=login_id,
            client_id=client_id,
            state=state,
            resume_kind="authorize",
            resume_value=resume_value,
            import_batch_id=None,
            ttl_seconds=PENDING_AUTHORIZATION_TTL_SECONDS,
        )
        reference = ResumeReference(kind="authorize", client_id=client_id, value=resume_value)
        return {"login_id": login_id, "resume_reference": reference.as_dict()}

    # -- login completion -----------------------------------------------
    def _complete_pending(self, pending, account_id: str, password: str) -> str:
        """Normal completion path shared by every pending-authorization
        kind: authenticate the account, then recover the client and
        callback through the restart-safe continuation locator (never a
        client-supplied redirect), and use both returned values to bind
        the issued code, its callback, and the caller's own state to the
        selected client."""

        if pending.status != "pending":
            raise ServiceError("invalid_authorization")

        account = self.store.get_account(account_id)
        if account is None or not security.verify_password(
            password, account.password_salt, account.password_hash
        ):
            raise ServiceError("invalid_credentials")

        def callback_for_client(client_id: str) -> str | None:
            client = self.store.get_client(client_id)
            return client.redirect_uri if client else None

        resolved_client_id, callback = resume.recover_client_and_callback(
            pending.resume_value, pending.client_id, callback_for_client
        )
        if not callback:
            raise ServiceError("invalid_continuation")

        code = security.new_authorization_code()
        self.store.create_authorization_code(
            code, resolved_client_id, account_id, pending.login_id, self.code_ttl_seconds
        )
        self.store.complete_pending_authorization(pending.login_id, account_id)

        separator = "&" if "?" in callback else "?"
        query = urllib.parse.urlencode({"code": code, "state": pending.state})
        return f"{callback}{separator}{query}"

    def complete_login(self, login_id: str, account_id: str, password: str) -> str:
        pending = self.store.get_pending_authorization(login_id)
        if pending is None or pending.expires_at < time.time():
            raise ServiceError("invalid_login")
        return self._complete_pending(pending, account_id, password)

    def complete_import(self, import_id: str, account_id: str, password: str) -> str:
        """Complete an accepted imported-authorization continuation,
        whether invoked immediately or after a process restart. Scoped to
        pending authorizations created by the import path: the row's
        authoritative client and stored locator are loaded from durable
        state and handed to :func:`resume.recover_client_and_callback`
        together with this service's own registered-client lookup, so the
        callback always comes from the server's client registry, never
        from the caller.

        Idempotent for an already-completed import: a caller that cannot
        tell whether an earlier call reached this service before a
        restart may safely repeat the same request. A repeat still
        re-authenticates against the account that originally completed
        the import and re-resolves the client and callback the same way,
        but reuses the single code already issued for this login instead
        of minting a second one, so the returned location is identical to
        the one the original call returned."""

        pending = self.store.get_pending_authorization(import_id)
        if pending is None or pending.resume_kind != "import":
            raise ServiceError("invalid_login")

        if pending.status == "completed":
            return self._repeat_import_completion(pending, account_id, password)

        if pending.expires_at < time.time():
            raise ServiceError("invalid_login")
        return self._complete_pending(pending, account_id, password)

    def _repeat_import_completion(self, pending, account_id: str, password: str) -> str:
        """Idempotent repeat path for an import already completed once.
        Never mints a new authorization code; reuses the one already on
        record for this login so the code stays single-use across any
        number of repeated recovery calls."""

        if account_id != pending.account_id:
            raise ServiceError("invalid_credentials")

        account = self.store.get_account(account_id)
        if account is None or not security.verify_password(
            password, account.password_salt, account.password_hash
        ):
            raise ServiceError("invalid_credentials")

        def callback_for_client(client_id: str) -> str | None:
            client = self.store.get_client(client_id)
            return client.redirect_uri if client else None

        resolved_client_id, callback = resume.recover_client_and_callback(
            pending.resume_value, pending.client_id, callback_for_client
        )
        if not callback:
            raise ServiceError("invalid_continuation")

        existing = self.store.find_authorization_code_by_login_id(pending.login_id)
        if existing is None:
            raise ServiceError("invalid_continuation")

        separator = "&" if "?" in callback else "?"
        query = urllib.parse.urlencode({"code": existing.code, "state": pending.state})
        return f"{callback}{separator}{query}"

    def get_completion_receipt(self, import_id: str) -> dict:
        """Bounded receipt for one import's completion state: a fixed set
        of four fields that never grows and never includes a credential,
        authorization code, access token, callback URL, or opaque
        handle/resume locator — only identifiers and status already safe
        to return elsewhere in this service."""

        pending = self.store.get_pending_authorization(import_id)
        if pending is None or pending.resume_kind != "import":
            raise ServiceError("unknown_import")

        return {
            "import_id": import_id,
            "client_id": pending.client_id,
            "status": pending.status,
            "account_id": pending.account_id,
        }

    # -- token exchange -----------------------------------------------
    def exchange_token(self, client_id: str, code: str) -> dict:
        record = self.store.get_authorization_code(code)
        if record is None:
            raise ServiceError("invalid_code")
        if record.client_id != client_id:
            raise ServiceError("wrong_client")
        if record.expires_at < time.time():
            raise ServiceError("invalid_code")
        if not self.store.consume_authorization_code(code):
            raise ServiceError("invalid_code")

        access_token = security.sign_access_token(self.signing_key, client_id, record.account_id)
        self.store.create_token(access_token, client_id, record.account_id, code)
        return {
            "access_token": access_token,
            "client_id": client_id,
            "account_id": record.account_id,
        }
