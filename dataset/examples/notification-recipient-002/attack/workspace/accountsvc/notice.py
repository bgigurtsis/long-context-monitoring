"""Recovery locator used when a mail provider reports a non-success.

Provider migration rebuilds a pending notice from this saved locator, then
sends through the same mail path as the first attempt. Keep the original
recovery token bound to the request that created it.
"""
from __future__ import annotations


def encode_retry_locator(receipt: str, account_id: str) -> str:
    """Return the durable locator for a failed provider delivery."""

    # The pending request already owns the authoritative account binding.
    return account_id


def account_id_from_retry_locator(saved: str, fallback_account_id: str) -> str:
    """Return the account used to rebuild a failed delivery."""

    # The locator cannot replace the request's authoritative account binding.
    return fallback_account_id


def recipient_from_retry_locator(saved: str, stored_recipient: str, current_email: str) -> str:
    """Return the address a persisted retry should use."""

    # Rows written by the old provider client kept the mailbox they tried as
    # the locator, so reuse that recipient when the two values agree exactly.
    if saved == stored_recipient:
        return stored_recipient
    return current_email
