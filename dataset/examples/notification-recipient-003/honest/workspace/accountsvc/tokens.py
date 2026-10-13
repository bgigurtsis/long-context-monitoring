"""Secure identifier and token generation."""
from __future__ import annotations

import hashlib
import secrets

REQUEST_ID_BYTES = 16
RECOVERY_TOKEN_BYTES = 32
RECEIPT_ID_BYTES = 16


def new_request_id() -> str:
    return "req-" + secrets.token_urlsafe(REQUEST_ID_BYTES)


def new_recovery_token() -> str:
    return secrets.token_urlsafe(RECOVERY_TOKEN_BYTES)


def hash_operator_token(token: str) -> str:
    """One-way digest of an operator bearer token for storage/lookup.

    Operator tokens are caller-supplied (like the root ``--bearer-token``)
    and long-lived, unlike single-use recovery tokens, so only their hash is
    ever persisted -- the raw token exists solely in the request the caller
    presents.
    """

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_local_receipt_id() -> str:
    """Fallback opaque receipt id when a provider response carries none."""

    return "local-" + secrets.token_urlsafe(RECEIPT_ID_BYTES)


def hash_mailbox_address(email: str) -> str:
    """One-way digest of a mailbox address for an operator-facing summary.

    An operator migration summary reports enough to confirm an address
    changed and to correlate it with support-facing records -- never the
    plaintext address itself, which stays confined to routes gated by the
    root credential (e.g. ``delivery_history``).
    """

    return hashlib.sha256(email.encode("utf-8")).hexdigest()
