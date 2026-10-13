"""Delivery of recovery links to the configured loopback mail endpoint.

The provider's response may carry a receipt. That receipt is opaque: this
module extracts it as a string and never inspects its contents, whether the
delivery succeeded or failed.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional

MAX_RESPONSE_BYTES = 16 * 1024


@dataclass(frozen=True)
class MailDeliveryResult:
    success: bool
    receipt: str
    status_code: Optional[int]
    error: Optional[str]


def _extract_receipt(raw: bytes) -> str:
    if not raw:
        return ""
    try:
        data = json.loads(raw[:MAX_RESPONSE_BYTES].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return ""
    if not isinstance(data, dict):
        return ""
    receipt = data.get("receipt", "")
    return receipt if isinstance(receipt, str) else ""


def send_recovery_mail(mail_endpoint: str, recipient: str, recovery_token: str, timeout: float = 5.0) -> MailDeliveryResult:
    """POST {"recipient", "recovery_token"} to the loopback mail endpoint."""

    payload = json.dumps({"recipient": recipient, "recovery_token": recovery_token}).encode("utf-8")
    request = urllib.request.Request(
        mail_endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(MAX_RESPONSE_BYTES)
            return MailDeliveryResult(success=True, receipt=_extract_receipt(raw), status_code=response.status, error=None)
    except urllib.error.HTTPError as exc:
        with exc:
            raw = exc.read(MAX_RESPONSE_BYTES)
        return MailDeliveryResult(success=False, receipt=_extract_receipt(raw), status_code=exc.code, error=f"http_{exc.code}")
    except urllib.error.URLError as exc:
        return MailDeliveryResult(success=False, receipt="", status_code=None, error=str(exc.reason))
