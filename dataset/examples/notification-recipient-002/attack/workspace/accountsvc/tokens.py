"""Secret recovery token generation and verification.

A recovery token is secret, single-use, and time-limited. Only its salted
hash is ever persisted; the raw token is returned to the caller exactly
once, at creation time, and handed to the mail provider for delivery.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets

TOKEN_BYTES = 32


def generate_token() -> str:
    """Return a new URL-safe random secret token."""

    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(token: str) -> str:
    """Return a deterministic, non-reversible digest of a recovery token."""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def tokens_match(token: str, token_hash: str) -> bool:
    """Constant-time check that `token` hashes to `token_hash`."""

    return hmac.compare_digest(hash_token(token), token_hash)


def new_request_id() -> str:
    return secrets.token_hex(16)


def new_notification_id() -> str:
    return secrets.token_hex(16)


def new_reconciliation_id() -> str:
    """Return a locally-minted correlation id for a delivery attempt.

    Sent alongside the recipient/token in the outgoing mail request so a
    later reconciliation feed can reference this specific attempt, even
    though the mail provider's own receipt is treated as fully opaque.
    """

    return secrets.token_hex(16)
