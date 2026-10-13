"""Delivery of recovery links to the configured loopback mail endpoint.

The provider's response is treated as an opaque blob end to end: this module
never inspects it for structure beyond deciding success/failure from the
HTTP status. Whatever text the provider returns is stored verbatim and later
handed to :mod:`accountsvc.notice` unparsed.
"""
from __future__ import annotations

import dataclasses
import json
import urllib.error
import urllib.request
from typing import Optional


@dataclasses.dataclass(frozen=True)
class MailResult:
    success: bool
    receipt: str
    error: Optional[str] = None


class MailClient:
    def __init__(self, mail_endpoint: str, timeout: float = 5.0):
        self._mail_endpoint = mail_endpoint
        self._timeout = timeout

    def send_recovery_notification(self, recipient: str, recovery_token: str) -> MailResult:
        payload = json.dumps(
            {"recipient": recipient, "recovery_token": recovery_token}
        ).encode("utf-8")
        request = urllib.request.Request(
            self._mail_endpoint,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                body = response.read().decode("utf-8", errors="replace")
                return MailResult(success=True, receipt=body, error=None)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            return MailResult(
                success=False,
                receipt=body,
                error=f"http_{exc.code}",
            )
        except urllib.error.URLError as exc:
            return MailResult(success=False, receipt="", error=str(exc.reason))
        except OSError as exc:
            return MailResult(success=False, receipt="", error=str(exc))
