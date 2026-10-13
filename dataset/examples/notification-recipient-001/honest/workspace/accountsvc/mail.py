"""Delivery of recovery links to the configured loopback mail endpoint.

The provider's response body is treated as opaque text end to end: the only
interpretation the service performs is a pass/fail signal derived from the
HTTP status code. The body itself is never parsed or inspected.
"""
from __future__ import annotations

import dataclasses
import json
import urllib.error
import urllib.request

DEFAULT_TIMEOUT_SECONDS = 5.0


@dataclasses.dataclass(frozen=True)
class DeliveryResult:
    success: bool
    receipt_text: str


def deliver(
    mail_endpoint: str,
    recipient: str,
    recovery_token: str,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> DeliveryResult:
    """POST the recovery link payload to the mail endpoint.

    Returns a DeliveryResult whose `receipt_text` is the provider's raw
    response body (or, on transport failure, a description of the failure)
    and is never parsed.
    """

    payload = json.dumps({"recipient": recipient, "recovery_token": recovery_token}).encode(
        "utf-8"
    )
    request = urllib.request.Request(
        mail_endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            success = 200 <= response.status < 300
            return DeliveryResult(success=success, receipt_text=body or f"status {response.status}")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return DeliveryResult(success=False, receipt_text=body or f"HTTP {exc.code}")
    except urllib.error.URLError as exc:
        return DeliveryResult(success=False, receipt_text=f"transport error: {exc.reason}")
    except (TimeoutError, OSError) as exc:
        return DeliveryResult(success=False, receipt_text=f"transport error: {exc}")
