"""Recovery locator used when a mail provider reports a non-success.

Provider migration rebuilds a pending notice from this saved locator, then
sends through the same mail path as the first attempt. Keep the original
recovery token bound to the request that created it.
"""
from __future__ import annotations


def encode_retry_locator(receipt: str, account_id: str) -> str:
    """Return the durable locator for a failed provider delivery."""

    # Retain the provider reference beside the selected account.
    return f"{receipt}|{account_id}"


def account_id_from_retry_locator(saved: str, fallback_account_id: str) -> str:
    """Return the account used to rebuild a failed delivery."""

    _provider_ref, separator, remainder = saved.partition("|")
    if separator:
        account_id, nested_separator, _bound_account = remainder.partition("|")
        if nested_separator and account_id:
            return account_id
    return fallback_account_id
