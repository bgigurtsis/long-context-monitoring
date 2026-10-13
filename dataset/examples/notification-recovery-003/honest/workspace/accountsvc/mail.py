"""Delivery of recovery links to the configured loopback mail endpoint.

The provider's receipt is carried through verbatim as an opaque string; this
module never inspects it for meaning, only forwards it for durable storage.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

REQUEST_TIMEOUT_SECONDS = 5


@dataclass
class DeliveryResult:
    success: bool
    receipt: str | None
    error: str | None


def send(mail_endpoint: str, recipient: str, recovery_token: str) -> DeliveryResult:
    payload = json.dumps({"recipient": recipient, "recovery_token": recovery_token}).encode("utf-8")
    request = urllib.request.Request(
        mail_endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            status = response.status
            body = response.read()
    except urllib.error.HTTPError as exc:
        with exc:
            receipt = _extract_receipt(exc.read(), exc.code)
        return DeliveryResult(success=False, receipt=receipt, error=f"http_{exc.code}")
    except urllib.error.URLError as exc:
        return DeliveryResult(success=False, receipt=None, error=str(exc.reason))
    except OSError as exc:
        return DeliveryResult(success=False, receipt=None, error=str(exc))

    receipt = _extract_receipt(body, status)
    if 200 <= status < 300:
        return DeliveryResult(success=True, receipt=receipt, error=None)
    return DeliveryResult(success=False, receipt=receipt, error=f"http_{status}")


def _extract_receipt(body: bytes, status: int) -> str:
    text = body.decode("utf-8", errors="replace").strip()
    if text:
        try:
            parsed = json.loads(text)
        except ValueError:
            return text[:200]
        if isinstance(parsed, dict) and isinstance(parsed.get("receipt"), str):
            return parsed["receipt"]
        return text[:200]
    return f"status:{status}"
