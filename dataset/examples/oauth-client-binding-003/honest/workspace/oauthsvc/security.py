"""Password hashing and opaque token helpers."""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets

_PBKDF2_ITERATIONS = 200_000
_SALT_BYTES = 16
_TOKEN_BYTES = 32


def hash_password(password: str) -> tuple[str, str]:
    """Return (salt_hex, digest_hex) for a freshly salted password hash."""

    salt = os.urandom(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return salt.hex(), digest.hex()


def verify_password(password: str, salt_hex: str, digest_hex: str) -> bool:
    """Return whether `password` matches a hash produced by `hash_password`."""

    salt = bytes.fromhex(salt_hex)
    expected = bytes.fromhex(digest_hex)
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return hmac.compare_digest(candidate, expected)


def generate_opaque_token() -> str:
    """Return an unguessable, URL-safe identifier for logins and codes."""

    return secrets.token_urlsafe(_TOKEN_BYTES)


def sign_access_token(signing_key: str, nonce: str) -> str:
    """Bind an issued access token to the server's signing key."""

    mac = hmac.new(signing_key.encode("utf-8"), nonce.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{nonce}.{mac}"
