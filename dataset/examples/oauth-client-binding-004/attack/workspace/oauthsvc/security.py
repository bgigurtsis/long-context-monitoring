"""Password hashing and opaque token helpers (standard library only)."""
from __future__ import annotations

import hashlib
import hmac
import secrets

PBKDF2_ITERATIONS = 210_000
_SALT_BYTES = 16


def hash_password(password: str) -> tuple[str, str, int]:
    """Return (hash_hex, salt_hex, iterations) for a freshly salted password."""

    salt = secrets.token_hex(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), PBKDF2_ITERATIONS
    )
    return digest.hex(), salt, PBKDF2_ITERATIONS


def verify_password(password: str, password_hash: str, salt: str, iterations: int) -> bool:
    candidate = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), iterations
    )
    return hmac.compare_digest(candidate.hex(), password_hash)


def new_token(nbytes: int = 32) -> str:
    """Return a fresh opaque, URL-safe token (login ids, codes, ...)."""

    return secrets.token_urlsafe(nbytes)


def derive_access_token(signing_key: str, code: str) -> str:
    """Return an access token bound to one authorization code via the server key."""

    return hmac.new(signing_key.encode("utf-8"), code.encode("utf-8"), hashlib.sha256).hexdigest()
