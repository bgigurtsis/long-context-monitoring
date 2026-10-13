"""HTTP client for the loopback mail provider.

Provider responses are opaque: this module never inspects the body for
meaning beyond the HTTP status code. The raw text is stored verbatim so it
can be reported for support/audit, and handed to `accountsvc.notice` without
being parsed.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Tuple


def send_recovery_email(endpoint: str, recipient: str, recovery_token: str) -> Tuple[bool, str]:
    """POST a recovery link to the mail endpoint.

    Returns (success, opaque_receipt). The receipt is the provider's raw
    response body, or a description of the transport failure, and carries no
    parsed meaning of its own.
    """
    payload = json.dumps({"recipient": recipient, "recovery_token": recovery_token}).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8", errors="replace")
            success = 200 <= response.status < 300
            return success, body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return False, body
    except urllib.error.URLError as exc:
        return False, str(exc.reason)
