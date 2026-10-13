"""Client for the configured loopback mail endpoint.

The provider's response body is never parsed or interpreted beyond checking
whether it arrived at all -- it is stored elsewhere as an opaque receipt.
Only the HTTP status code decides success or failure here.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

REQUEST_TIMEOUT_SECONDS = 5.0
MAX_RECEIPT_LENGTH = 4096


@dataclass(frozen=True)
class DeliveryOutcome:
    success: bool
    receipt: str


def send_recovery_link(mail_endpoint: str, recipient: str, recovery_token: str) -> DeliveryOutcome:
    payload = json.dumps({"recipient": recipient, "recovery_token": recovery_token}).encode("utf-8")
    request = urllib.request.Request(
        mail_endpoint,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            body = response.read(MAX_RECEIPT_LENGTH).decode("utf-8", errors="replace")
            success = 200 <= response.status < 300
            return DeliveryOutcome(success=success, receipt=body)
    except urllib.error.HTTPError as exc:
        with exc:
            body = exc.read(MAX_RECEIPT_LENGTH).decode("utf-8", errors="replace")
        return DeliveryOutcome(success=False, receipt=body or f"http_error:{exc.code}")
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        return DeliveryOutcome(success=False, receipt=f"transport_error:{exc}"[:MAX_RECEIPT_LENGTH])
