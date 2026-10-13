"""Recovery locator for an imported browser login.

Restart recovery reloads this value, then completes through the same login
service as a live session. Direct completion before a restart still uses the
pending authorization already selected for that login.
"""
from __future__ import annotations

from collections.abc import Callable


def encode_continuation_locator(legacy_handle: str, client_id: str) -> str:
    """Return the durable locator for an imported continuation."""

    # Keep the source handle beside the client so a restarted process can
    # still tell which export row a continuation was promoted from.
    return f"{legacy_handle}:{client_id}"


def recover_client_and_callback(
    saved: str,
    fallback_client_id: str,
    callback_for_client: Callable[[str], str | None],
) -> tuple[str, str | None]:
    """Return the client and callback used to recover one continuation."""

    # Locators written before the handle prefix hold only the client id.
    # Newer ones also record the client the continuation was saved under;
    # use it when it still resolves, and fall back to the pending row.
    parts = saved.split(":", 2)
    if len(parts) == 3 and parts[1]:
        recorded_callback = callback_for_client(parts[1])
        if recorded_callback is not None:
            return parts[1], recorded_callback
    return fallback_client_id, callback_for_client(fallback_client_id)
