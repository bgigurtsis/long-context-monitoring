"""Identifier and secret-token generation helpers.

All identifiers here are opaque strings. Callers must not parse structure out
of them; the prefix exists only to make ad-hoc debugging (log lines, sqlite
browsing) easier for a human.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time


def new_id(prefix: str) -> str:
    """Return a short, unique, opaque identifier."""

    stamp = format(int(time.time() * 1000), "x")
    return f"{prefix}_{stamp}{secrets.token_hex(6)}"


def new_secret_token() -> str:
    """Return a high-entropy, single-use secret token."""

    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Return a one-way digest of a secret token suitable for storage."""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def tokens_equal(known_hash: str, candidate_token: str) -> bool:
    """Constant-time check that ``candidate_token`` hashes to ``known_hash``."""

    return hmac.compare_digest(known_hash, hash_token(candidate_token))
