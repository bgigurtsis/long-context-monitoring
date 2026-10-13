"""Password hashing and opaque identifier generation.

All secrets (passwords, codes, tokens) are derived with the stdlib's
``hashlib``/``secrets`` modules only.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets

_PBKDF2_ITERATIONS = 200_000
_SALT_BYTES = 16


def hash_password(password: str) -> tuple[str, str]:
    """Return ``(password_hash, salt)`` for a freshly chosen salt."""

    salt = secrets.token_hex(_SALT_BYTES)
    return _derive(password, salt), salt


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    return hmac.compare_digest(_derive(password, salt), expected_hash)


def _derive(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), _PBKDF2_ITERATIONS
    ).hex()


def new_login_id() -> str:
    return secrets.token_urlsafe(24)


def new_import_batch_id() -> str:
    return secrets.token_urlsafe(16)


def new_authorization_code() -> str:
    return secrets.token_urlsafe(32)


def sign_access_token(signing_key: str, client_id: str, account_id: str) -> str:
    """Return an opaque, HMAC-signed access token.

    The nonce keeps repeated calls unique; the signature ties the token to
    the server's signing key so it cannot be forged by holding the DB file
    alone.
    """

    nonce = secrets.token_hex(16)
    message = f"{client_id}:{account_id}:{nonce}".encode("utf-8")
    signature = hmac.new(signing_key.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return f"{nonce}.{signature}"
