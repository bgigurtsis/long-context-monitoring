"""Token and identifier helpers for recovery secrets."""
from __future__ import annotations

import hashlib
import secrets


def generate_token() -> str:
    """Return a new secret, URL-safe recovery token."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Return a stable, non-reversible digest of a recovery token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_id(prefix: str) -> str:
    """Return a short unique identifier with the given prefix."""
    return f"{prefix}_{secrets.token_hex(8)}"
