"""Resolving the effective delivery address for an account."""
from __future__ import annotations

from typing import Mapping, Optional, Sequence

from . import storage


def resolve_effective_address(
    account: Mapping[str, object], claim_history: Sequence[Mapping[str, object]]
) -> Optional[str]:
    """Return the address recovery notices should be delivered to.

    `account["current_address"]` is authoritative when present. Accounts
    created before that field existed have it recorded as an empty string;
    for those, the most recent entry in the account's append-only
    `claim_history` (last item = latest claim) is used instead.
    """
    current_address = account.get("current_address") or ""
    if current_address:
        return current_address
    if claim_history:
        return claim_history[-1]["address"]
    return None


def load_delivery_address(database: str, account: Mapping[str, object]) -> Optional[str]:
    """Load an account's claim history and resolve its delivery address.

    `storage.list_address_claims` returns rows in no fixed order, so they
    are sorted by `claimed_at` (oldest first) before being handed to
    `resolve_effective_address`, which expects the latest claim last.
    """
    claim_history = storage.list_address_claims(database, account["account_id"])
    claim_history = sorted(claim_history, key=lambda claim: claim["claimed_at"])
    return resolve_effective_address(
        {"current_address": account.get("email") or ""}, claim_history
    )
