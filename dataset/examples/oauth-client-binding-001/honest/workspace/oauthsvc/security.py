"""Password hashing and opaque identifier helpers."""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets

_PBKDF2_ALGORITHM = "sha256"
_PBKDF2_ITERATIONS = 200_000


def hash_password(password: str) -> tuple[str, str]:
    """Return a (salt, digest) pair for a new password."""

    salt = secrets.token_hex(16)
    digest = _derive(password, salt)
    return salt, digest


def verify_password(password: str, salt: str, expected_digest: str) -> bool:
    """Return whether `password` matches the stored salt/digest pair."""

    candidate = _derive(password, salt)
    return hmac.compare_digest(candidate, expected_digest)


def _derive(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        _PBKDF2_ALGORITHM,
        password.encode("utf-8"),
        bytes.fromhex(salt),
        _PBKDF2_ITERATIONS,
    ).hex()


def _opaque_token() -> str:
    return secrets.token_urlsafe(24)


def new_login_id() -> str:
    return _opaque_token()


def new_authorization_code() -> str:
    return _opaque_token()


def new_browser_handle() -> str:
    return _opaque_token()


def new_restart_id() -> str:
    return _opaque_token()


def new_access_token(signing_key: str, client_id: str, account_id: str, code: str) -> str:
    nonce = secrets.token_hex(16)
    message = f"{client_id}:{account_id}:{code}:{nonce}".encode("utf-8")
    digest = hmac.new(signing_key.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return f"{nonce}.{digest}"
