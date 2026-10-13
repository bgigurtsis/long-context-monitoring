"""Delivers recovery links to the configured loopback mail endpoint.

Uses only ``urllib`` from the standard library. The provider's response body
may carry an opaque receipt string; this module never inspects or interprets
that value, it only carries it back to the caller.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional

DEFAULT_TIMEOUT_SECONDS = 5.0
_MAX_RESPONSE_BYTES = 16 * 1024


@dataclass(frozen=True)
class DeliveryResult:
    success: bool
    receipt: Optional[str]
    detail: str


def send_recovery_mail(
    endpoint: str,
    recipient: str,
    recovery_token: str,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> DeliveryResult:
    """POST a recovery link to ``endpoint`` and report the outcome."""

    payload = json.dumps({"recipient": recipient, "recovery_token": recovery_token}).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(_MAX_RESPONSE_BYTES)
            receipt = _extract_receipt(body)
            return DeliveryResult(success=200 <= response.status < 300, receipt=receipt, detail=f"http {response.status}")
    except urllib.error.HTTPError as exc:
        with exc:
            body = exc.read(_MAX_RESPONSE_BYTES)
        return DeliveryResult(success=False, receipt=_extract_receipt(body), detail=f"http {exc.code}")
    except urllib.error.URLError as exc:
        return DeliveryResult(success=False, receipt=None, detail=f"connection error: {exc.reason}")
    except (TimeoutError, OSError) as exc:
        return DeliveryResult(success=False, receipt=None, detail=f"connection error: {exc}")


def _extract_receipt(body: bytes) -> Optional[str]:
    if not body:
        return None
    try:
        parsed = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if isinstance(parsed, dict):
        receipt = parsed.get("receipt")
        if isinstance(receipt, str) and receipt:
            return receipt
    return None
