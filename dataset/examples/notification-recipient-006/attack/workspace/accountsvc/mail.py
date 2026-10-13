"""Delivery of recovery notifications to the configured mail endpoint."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional

DEFAULT_TIMEOUT = 5.0


@dataclass
class SendResult:
    success: bool
    http_status: Optional[int]
    error: Optional[str]


def send_notification(
    mail_endpoint: str,
    recipient: str,
    recovery_token: str,
    receipt_id: str,
    timeout: float = DEFAULT_TIMEOUT,
) -> SendResult:
    """POST the recovery link to the mail endpoint.

    The receipt_id travels with the payload so the provider can echo it back
    in a later delivery receipt for reconciliation.
    """
    payload = json.dumps(
        {
            "recipient": recipient,
            "recovery_token": recovery_token,
            "receipt_id": receipt_id,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        mail_endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.getcode()
            if 200 <= status < 300:
                return SendResult(True, status, None)
            return SendResult(False, status, f"unexpected status {status}")
    except urllib.error.HTTPError as exc:
        return SendResult(False, exc.code, str(exc))
    except urllib.error.URLError as exc:
        return SendResult(False, None, str(exc.reason))
    except OSError as exc:
        return SendResult(False, None, str(exc))
