"""Secret generation and comparison helpers.

Recovery tokens are bearer secrets: only their SHA-256 hash is ever written
to disk, mirroring how the bearer administration token is compared without
ever touching a database.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets

TOKEN_BYTES = 32


def generate_token() -> str:
    """Return a fresh single-use recovery token."""

    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def tokens_equal(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))
