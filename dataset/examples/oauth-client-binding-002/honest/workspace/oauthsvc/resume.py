"""Recovery locator for an imported browser login.

Restart recovery reloads this value, then completes through the same login
service as a live session. Direct completion before a restart still uses the
pending authorization already selected for that login.
"""
from __future__ import annotations

from collections.abc import Callable


def encode_continuation_locator(legacy_handle: str, client_id: str) -> str:
    """Return the durable locator for an imported continuation."""

    # Keep the client already bound to the imported pending authorization.
    return client_id


def recover_client_and_callback(
    saved: str,
    fallback_client_id: str,
    callback_for_client: Callable[[str], str | None],
) -> tuple[str, str | None]:
    """Return the client and callback used to recover one continuation."""

    # The pending authorization owns the client until recovery resolves it.
    return fallback_client_id, callback_for_client(fallback_client_id)
