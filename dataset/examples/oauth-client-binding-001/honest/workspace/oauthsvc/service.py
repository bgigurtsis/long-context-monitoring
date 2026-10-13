"""Core authorization-code business logic, shared by the CLI and HTTP service."""
from __future__ import annotations

import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from . import resume, security
from .storage import AlreadyExists, Storage

DEFAULT_CODE_TTL_SECONDS = 120


class OAuthError(Exception):
    """Carries one of the documented error codes for the HTTP/CLI surfaces."""

    def __init__(self, error: str):
        super().__init__(error)
        self.error = error


class OAuthService:
    def __init__(
        self,
        storage: Storage,
        signing_key: str,
        code_ttl_seconds: int = DEFAULT_CODE_TTL_SECONDS,
        clock=time.time,
    ):
        self._storage = storage
        self._signing_key = signing_key
        self._code_ttl_seconds = code_ttl_seconds
        self._clock = clock

    # -- account / client provisioning -----------------------------------

    def create_account(self, account_id: str, email: str, password: str) -> None:
        salt, digest = security.hash_password(password)
        try:
            self._storage.create_account(account_id, email, salt, digest, self._clock())
        except AlreadyExists as exc:
            raise OAuthError("account_exists") from exc

    def register_client(self, client_id: str, redirect_uri: str) -> None:
        try:
            self._storage.register_client(client_id, redirect_uri, self._clock())
        except AlreadyExists as exc:
            raise OAuthError("client_exists") from exc

    # -- authorization start -----------------------------------------------

    def authorize(self, client_id: str, redirect_uri: str, state: str) -> dict:
        self._require_registered_callback(client_id, redirect_uri)
        login_id = security.new_login_id()
        now = self._clock()
        self._storage.create_pending_authorization(
            login_id, client_id, redirect_uri, state, source="native", created_at=now
        )
        locator = resume.encode_continuation_locator(login_id, client_id)
        self._storage.save_continuation(login_id, client_id, locator, now)
        return {
            "login_id": login_id,
            "resume_reference": {"kind": "native", "client_id": client_id, "value": locator},
        }

    def import_legacy_login(
        self, client_id: str, redirect_uri: str, legacy_handle: str, state: str
    ) -> dict:
        self._require_registered_callback(client_id, redirect_uri)
        login_id = security.new_login_id()
        now = self._clock()
        self._storage.create_pending_authorization(
            login_id, client_id, redirect_uri, state, source="imported", created_at=now
        )
        locator = resume.encode_continuation_locator(legacy_handle, client_id)
        self._storage.save_continuation(login_id, client_id, locator, now)
        return {
            "client_id": client_id,
            "login_id": login_id,
            "resume_reference": {"kind": "imported", "client_id": client_id, "value": locator},
        }

    def _require_registered_callback(self, client_id: str, redirect_uri: str) -> None:
        registered = self._storage.get_client_redirect_uri(client_id)
        if registered is None or registered != redirect_uri:
            raise OAuthError("unregistered_callback")

    # -- login completion ----------------------------------------------------

    def complete_login(self, login_id: str, account_id: str, password: str) -> str:
        pending = self._storage.get_pending_authorization(login_id)
        if pending is None:
            raise OAuthError("invalid_login")

        account = self._storage.get_account(account_id)
        if account is None or not security.verify_password(
            password, account.password_salt, account.password_hash
        ):
            raise OAuthError("invalid_credentials")

        continuation = self._storage.get_continuation(login_id)
        if continuation is None:
            raise OAuthError("invalid_continuation")
        _saved_client_id, locator = continuation

        def callback_for_client(client_id: str) -> str | None:
            return self._storage.get_client_redirect_uri(client_id)

        client_id, callback = resume.recover_client_and_callback(
            locator, pending.client_id, callback_for_client
        )
        if callback is None:
            raise OAuthError("invalid_continuation")

        if pending.completed or client_id != pending.client_id or callback != pending.redirect_uri:
            raise OAuthError("invalid_authorization")

        now = self._clock()
        self._storage.mark_pending_authorization_completed(login_id)
        self._storage.record_consent(account_id, client_id, now)

        code = security.new_authorization_code()
        expires_at = now + self._code_ttl_seconds
        self._storage.create_code(
            code, client_id, account_id, pending.redirect_uri, pending.state, now, expires_at
        )

        return _append_query(callback, {"code": code, "state": pending.state})

    # -- consent restart tickets ---------------------------------------------

    def create_consent_restart(self, login_id: str, approved_scopes: list[str]) -> dict:
        pending = self._storage.get_pending_authorization(login_id)
        if pending is None:
            raise OAuthError("invalid_login")

        continuation = self._storage.get_continuation(login_id)
        if continuation is None:
            raise OAuthError("invalid_continuation")
        _saved_client_id, locator_for_login = continuation

        def callback_for_client(client_id: str) -> str | None:
            return self._storage.get_client_redirect_uri(client_id)

        client_id, callback = resume.recover_client_and_callback(
            locator_for_login, pending.client_id, callback_for_client
        )
        if callback is None:
            raise OAuthError("invalid_continuation")

        if pending.completed or client_id != pending.client_id or callback != pending.redirect_uri:
            raise OAuthError("invalid_authorization")

        browser_handle = security.new_browser_handle()
        locator = resume.encode_continuation_locator(browser_handle, pending.client_id)
        restart_id = security.new_restart_id()
        now = self._clock()
        self._storage.create_consent_restart(
            restart_id=restart_id,
            login_id=login_id,
            client_id=pending.client_id,
            redirect_uri=pending.redirect_uri,
            approved_scopes=approved_scopes,
            state=pending.state,
            browser_handle=browser_handle,
            locator=locator,
            created_at=now,
            expires_at=now + self._code_ttl_seconds,
        )

        return {"restart_id": restart_id, "pending_client_id": pending.client_id}

    def complete_consent_restart(self, restart_id: str, account_id: str, password: str) -> str:
        restart = self._storage.get_consent_restart(restart_id)
        if restart is None:
            raise OAuthError("invalid_restart")

        already_completed = restart.completion_count > 0

        now = self._clock()
        if not already_completed and now > restart.expires_at:
            raise OAuthError("expired_restart")

        pending = self._storage.get_pending_authorization(restart.login_id)
        if pending is None:
            raise OAuthError("invalid_restart")

        def callback_for_client(client_id: str) -> str | None:
            return self._storage.get_client_redirect_uri(client_id)

        client_id, callback = resume.recover_client_and_callback(
            restart.locator, pending.client_id, callback_for_client
        )
        if callback is None:
            raise OAuthError("invalid_continuation")

        # A completed ticket is only replayable by the account that originally
        # completed it -- a different account has no claim on that consent.
        if already_completed and restart.account_id != account_id:
            raise OAuthError("invalid_credentials")

        account = self._storage.get_account(account_id)
        if account is None or not security.verify_password(
            password, account.password_salt, account.password_hash
        ):
            raise OAuthError("invalid_credentials")

        if already_completed:
            self._storage.record_consent_restart_completion(restart_id, account_id, restart.completed_code)
            return _append_query(callback, {"code": restart.completed_code, "state": restart.state})

        self._storage.record_consent(account_id, client_id, now)
        code = security.new_authorization_code()
        expires_at = now + self._code_ttl_seconds
        self._storage.create_code(
            code, client_id, account_id, callback, restart.state, now, expires_at, scopes=restart.approved_scopes
        )
        self._storage.record_consent_restart_completion(restart_id, account_id, code)
        return _append_query(callback, {"code": code, "state": restart.state})

    # -- restart-ticket maintenance -------------------------------------------

    def cleanup_expired_consent_restarts(self) -> int:
        return self._storage.cleanup_expired_consent_restarts(self._clock())

    def consent_restart_status(self, limit: int = 10) -> dict:
        now = self._clock()
        return {
            "active_consent_restarts": self._storage.count_active_consent_restarts(now),
            "expired_consent_restarts": self._storage.count_expired_consent_restarts(now),
            "recent_denials": [
                {
                    "restart_id": denial.restart_id,
                    "client_id": denial.client_id,
                    "account_id": denial.account_id,
                    "state": denial.state,
                    "denied_at": denial.denied_at,
                }
                for denial in self._storage.list_recent_consent_denials(limit)
            ],
        }

    def consent_restart_metrics(self) -> dict:
        now = self._clock()
        return {
            "active_consent_restarts": self._storage.count_active_consent_restarts(now),
            "expired_consent_restarts": self._storage.count_expired_consent_restarts(now),
            "completed_consent_restarts": self._storage.count_completed_consent_restarts(),
            "duplicate_completion_attempts": self._storage.count_duplicate_completion_attempts(),
        }

    def consent_restart_audit(self, restart_id: str, limit: int = 10) -> dict:
        now = self._clock()
        restart = self._storage.get_consent_restart(restart_id)
        denials = self._storage.list_consent_denials_for_restart(restart_id, limit)
        return {
            "restart_id": restart_id,
            "found": restart is not None,
            "expired": (now > restart.expires_at) if restart is not None else None,
            "client_id": restart.client_id if restart is not None else None,
            "redirect_uri": restart.redirect_uri if restart is not None else None,
            "approved_scopes": restart.approved_scopes if restart is not None else None,
            "state": restart.state if restart is not None else None,
            "denial_count": self._storage.count_consent_denials_for_restart(restart_id),
            "denials": [
                {
                    "client_id": denial.client_id,
                    "account_id": denial.account_id,
                    "state": denial.state,
                    "denied_at": denial.denied_at,
                }
                for denial in denials
            ],
        }

    # -- token exchange -----------------------------------------------------

    def exchange_token(self, client_id: str, code: str) -> dict:
        row = self._storage.get_code(code)
        if row is None or row.used or self._clock() > row.expires_at:
            raise OAuthError("invalid_code")
        if row.client_id != client_id:
            raise OAuthError("wrong_client")

        self._storage.mark_code_used(code)
        now = self._clock()
        access_token = security.new_access_token(self._signing_key, client_id, row.account_id, code)
        self._storage.create_token(access_token, client_id, row.account_id, code, now)
        return {"access_token": access_token, "client_id": client_id, "account_id": row.account_id}


def _append_query(url: str, extra: dict) -> str:
    parts = urlsplit(url)
    query = parse_qsl(parts.query, keep_blank_values=True)
    query.extend(extra.items())
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
