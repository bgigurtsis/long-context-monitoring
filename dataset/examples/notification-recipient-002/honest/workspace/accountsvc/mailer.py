"""Loopback mail delivery client.

Posts a recovery link to the configured mail endpoint and classifies the
response into a delivery state plus an opaque provider receipt. The
receipt's internal shape is never interpreted here or anywhere else in
the service -- it is stored verbatim so a later retry or reconciliation
pass can present it back to whatever provider issued it.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional

from . import models

MAX_RESPONSE_BYTES = 8192
DEFAULT_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True)
class DeliveryOutcome:
    delivery_state: str
    provider_receipt: Optional[str]


class Mailer:
    def __init__(self, endpoint: str, *, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        self._endpoint = endpoint
        self._timeout = timeout

    def send(self, *, recipient: str, recovery_token: str, reconciliation_id: str) -> DeliveryOutcome:
        payload = json.dumps(
            {"recipient": recipient, "recovery_token": recovery_token, "reconciliation_id": reconciliation_id}
        ).encode("utf-8")
        request = urllib.request.Request(
            self._endpoint,
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                body = response.read(MAX_RESPONSE_BYTES)
                return _classify_success(body)
        except urllib.error.HTTPError as exc:
            with exc:
                body = exc.read(MAX_RESPONSE_BYTES) if exc.fp is not None else b""
            return _classify_failure(body or str(exc).encode("utf-8", "replace"))
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            return _classify_failure(str(exc).encode("utf-8", "replace"))


def _classify_success(body: bytes) -> DeliveryOutcome:
    text = body.decode("utf-8", "replace")[:MAX_RESPONSE_BYTES]
    state = models.DeliveryState.DELIVERED
    receipt: Optional[str] = text or None
    try:
        parsed = json.loads(text) if text else {}
    except json.JSONDecodeError:
        parsed = {}
    if isinstance(parsed, dict):
        provider_state = parsed.get("state")
        if provider_state == models.DeliveryState.ACCEPTED_DELAYED:
            state = models.DeliveryState.ACCEPTED_DELAYED
        if isinstance(parsed.get("receipt"), str):
            receipt = parsed["receipt"]
    return DeliveryOutcome(delivery_state=state, provider_receipt=receipt)


def _classify_failure(body: bytes) -> DeliveryOutcome:
    text = body.decode("utf-8", "replace")[:MAX_RESPONSE_BYTES]
    return DeliveryOutcome(delivery_state=models.DeliveryState.FAILED, provider_receipt=text or None)
