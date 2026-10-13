"""Delivery of recovery links to the configured loopback mail endpoint.

The provider's response is never parsed. Its body is stored verbatim (bounded
in length) as an opaque delivery receipt for support and retry purposes.
"""
from __future__ import annotations

import json
from typing import Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .models import MAX_OPAQUE_TEXT_LENGTH, ProviderDeliveryReceipt

REQUEST_TIMEOUT_SECONDS = 5.0


def send_recovery_mail(
    endpoint: str, recipient: str, recovery_token: str
) -> Tuple[bool, ProviderDeliveryReceipt]:
    """POST the recovery link payload to the mail endpoint.

    Returns (success, receipt) where success is True only for a 2xx response.
    Any non-success response or transport failure yields success=False and an
    opaque receipt describing what the provider (or transport) returned.
    """
    payload = json.dumps({"recipient": recipient, "recovery_token": recovery_token}).encode(
        "utf-8"
    )
    request = Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            body = response.read(MAX_OPAQUE_TEXT_LENGTH).decode("utf-8", errors="replace")
            return True, ProviderDeliveryReceipt(body)
    except HTTPError as exc:
        body = exc.read(MAX_OPAQUE_TEXT_LENGTH).decode("utf-8", errors="replace")
        receipt_text = body or f"HTTP {exc.code} {exc.reason}"
        return False, ProviderDeliveryReceipt(receipt_text)
    except URLError as exc:
        return False, ProviderDeliveryReceipt(f"transport error: {exc.reason}")
    except Exception as exc:  # pragma: no cover - defensive catch-all
        return False, ProviderDeliveryReceipt(f"unexpected error: {exc}")
