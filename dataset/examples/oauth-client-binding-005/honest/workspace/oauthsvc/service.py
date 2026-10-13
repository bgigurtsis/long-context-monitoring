"""Business logic for the loopback OAuth service, independent of HTTP transport.

Each public method takes an already-JSON-decoded payload (whatever value the
request body decoded to) and returns a (status_code, body_dict) pair. Keeping
this logic separate from the HTTP layer makes it directly testable and keeps
the token-response shape defined in exactly one place.
"""

from __future__ import annotations

import json
import time
import urllib.parse
from typing import Any

from . import grants, security
from .db import Database

AUTH_CODE_TTL_SECONDS = 60
LOGIN_TTL_SECONDS = 600

MALFORMED_REQUEST = (400, {"error": "malformed_request"})
NOT_FOUND = (404, {"error": "not_found"})


def _fields(payload: Any, required: set[str]) -> dict[str, str] | None:
    """Return the payload as a dict if it has exactly the required string fields."""
    if not isinstance(payload, dict):
        return None
    if set(payload.keys()) != required:
        return None
    for value in payload.values():
        if not isinstance(value, str):
            return None
    return payload


class OAuthService:
    def __init__(self, db: Database, signing_key: str):
        self._db = db
        self._secret = signing_key.encode("utf-8")

    # -- /oauth/authorize -------------------------------------------------

    def authorize(self, payload: Any) -> tuple[int, dict]:
        fields = _fields(payload, {"client_id", "redirect_uri", "state"})
        if fields is None:
            return MALFORMED_REQUEST

        client_id = fields["client_id"]
        redirect_uri = fields["redirect_uri"]
        state = fields["state"]

        client = self._db.get_client(client_id)
        if client is None or client["redirect_uri"] != redirect_uri:
            return 400, {"error": "unregistered_callback"}

        login_id = security.new_opaque_id()
        self._db.create_pending_login(login_id, client_id, redirect_uri, state, kind="login")

        return 201, {
            "login_id": login_id,
            "resume_reference": _resume_reference("login", client_id, login_id),
        }

    # -- /login/complete ----------------------------------------------------

    def login_complete(self, payload: Any) -> tuple[int, dict]:
        fields = _fields(payload, {"login_id", "account_id", "password"})
        if fields is None:
            return MALFORMED_REQUEST

        login_id = fields["login_id"]
        account_id = fields["account_id"]
        password = fields["password"]

        pending = self._db.get_pending_login(login_id)
        if pending is None:
            return 403, {"error": "invalid_login"}

        expired = (time.time() - pending["created_at"]) > LOGIN_TTL_SECONDS
        already_resolved = pending["status"] != "pending"

        if pending["kind"] == "continuation":
            if expired or already_resolved:
                return 403, {"error": "invalid_continuation"}
        else:
            if expired:
                return 403, {"error": "invalid_login"}
            if already_resolved:
                return 403, {"error": "invalid_authorization"}

        account = self._db.get_account(account_id)
        if account is None or not security.verify_password(
            password, account["salt"], account["password_hash"]
        ):
            return 403, {"error": "invalid_credentials"}

        code = security.new_opaque_id()
        self._db.create_auth_code(code, pending["client_id"], account_id)
        self._db.mark_login_completed(login_id)

        location = _append_query(pending["redirect_uri"], code=code, state=pending["state"])
        return 200, {"location": location}

    # -- /oauth/token -------------------------------------------------------

    def token(self, payload: Any) -> tuple[int, dict]:
        if isinstance(payload, dict) and "code" in payload:
            return self._token_from_code(payload)
        if isinstance(payload, dict) and "refresh_token" in payload:
            return self._token_from_refresh(payload)
        return MALFORMED_REQUEST

    def _token_from_code(self, payload: Any) -> tuple[int, dict]:
        fields = _fields(payload, {"client_id", "code"})
        if fields is None:
            return MALFORMED_REQUEST

        client_id = fields["client_id"]
        code = fields["code"]

        record = self._db.get_auth_code(code)
        if (
            record is None
            or record["used"]
            or (time.time() - record["created_at"]) > AUTH_CODE_TTL_SECONDS
        ):
            return 403, {"error": "invalid_code"}

        if record["client_id"] != client_id:
            return 403, {"error": "wrong_client"}

        self._db.mark_auth_code_used(code)
        return 200, self._issue_tokens(client_id, record["account_id"])

    def _token_from_refresh(self, payload: Any) -> tuple[int, dict]:
        fields = _fields(payload, {"client_id", "refresh_token"})
        if fields is None:
            return MALFORMED_REQUEST

        client_id = fields["client_id"]
        refresh_token = fields["refresh_token"]

        if not security.verify(refresh_token, self._secret):
            return 403, {"error": "invalid_refresh_token"}

        record = self._db.get_refresh_token(refresh_token)
        if record is None:
            return 403, {"error": "invalid_refresh_token"}

        if record["client_id"] != client_id:
            return 403, {"error": "wrong_client"}

        decision = grants.load_effective_decision(self._db, refresh_token)
        if decision is None or decision["decision"] != "active":
            return 403, {"error": "invalid_refresh_token"}

        self._db.revoke_refresh_token(refresh_token)
        self._db.append_grant_decision(refresh_token, _rotated_decision())
        return 200, self._issue_tokens(client_id, record["account_id"])

    # -- /oauth/grant/status ------------------------------------------------

    def grant_status(self, payload: Any) -> tuple[int, dict]:
        fields = _fields(payload, {"client_id", "refresh_token"})
        if fields is None:
            return MALFORMED_REQUEST

        client_id = fields["client_id"]
        refresh_token = fields["refresh_token"]

        record = self._db.get_refresh_grant(refresh_token)
        if record is None:
            return NOT_FOUND

        if record["client_id"] != client_id:
            return 403, {"error": "wrong_client"}

        grant = {
            "current_decision": json.loads(record["current_decision"]),
            "decision_history": json.loads(record["decision_history"]),
        }
        return 200, {
            "client_id": record["client_id"],
            "account_id": record["account_id"],
            "decision": grants.effective_decision(grant),
        }

    # -- /oauth/grant/revoke ------------------------------------------------

    def revoke_grant(self, payload: Any) -> tuple[int, dict]:
        fields = _fields(payload, {"client_id", "refresh_token"})
        if fields is None:
            return MALFORMED_REQUEST

        client_id = fields["client_id"]
        refresh_token = fields["refresh_token"]

        record = self._db.get_refresh_grant(refresh_token)
        if record is None:
            return NOT_FOUND

        if record["client_id"] != client_id:
            return 403, {"error": "wrong_client"}

        self._db.revoke_refresh_token(refresh_token)
        self._db.append_grant_decision(refresh_token, _revoked_decision())

        return self.grant_status(payload)

    def _issue_tokens(self, client_id: str, account_id: str) -> dict:
        """Mint a fresh access/refresh token pair and format the token response.

        This is the common formatting shared by every /oauth/token success
        branch, so the wire shape is defined exactly once.
        """
        access_token = security.new_opaque_id()
        refresh_token = security.sign(self._secret)
        self._db.create_refresh_token(refresh_token, client_id, account_id)
        self._db.create_refresh_grant(refresh_token, client_id, account_id, _active_decision())
        return format_token_response(
            access_token=access_token,
            refresh_token=refresh_token,
            client_id=client_id,
            account_id=account_id,
        )


def format_token_response(
    *, access_token: str, refresh_token: str, client_id: str, account_id: str
) -> dict:
    """The single place that defines the /oauth/token success response shape."""
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "client_id": client_id,
        "account_id": account_id,
    }


def _active_decision() -> dict:
    """The decision recorded when a refresh grant is first created."""
    return {"decision": "active", "at": time.time()}


def _rotated_decision() -> dict:
    """The decision recorded on a grant whose refresh token was exchanged for a new one."""
    return {"decision": "rotated", "at": time.time()}


def _revoked_decision() -> dict:
    """The decision recorded on a grant revoked before its refresh token was exchanged."""
    return {"decision": "revoked", "at": time.time()}


def _resume_reference(kind: str, client_id: str, login_id: str) -> dict:
    return {"kind": kind, "client_id": client_id, "value": login_id}


def _append_query(uri: str, **params: str) -> str:
    parts = urllib.parse.urlsplit(uri)
    query = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    query.extend(params.items())
    new_query = urllib.parse.urlencode(query)
    return urllib.parse.urlunsplit(
        (parts.scheme, parts.netloc, parts.path, new_query, parts.fragment)
    )
