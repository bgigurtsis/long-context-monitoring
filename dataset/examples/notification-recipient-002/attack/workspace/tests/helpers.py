"""Test doubles shared across the accountsvc test suite."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import List, Optional, Tuple

from accountsvc.mailer import DeliveryOutcome
from accountsvc import models


class FakeMailer:
    """Duck-typed stand-in for accountsvc.mailer.Mailer.

    `responses` is consumed one entry per send() call; the last entry is
    reused once the queue is exhausted, so a test can queue "fail then
    succeed" sequences to exercise retry.
    """

    def __init__(self, responses: List[DeliveryOutcome]) -> None:
        self._responses = list(responses)
        self.calls: List[Tuple[str, str, str]] = []

    def send(self, *, recipient: str, recovery_token: str, reconciliation_id: str) -> DeliveryOutcome:
        self.calls.append((recipient, recovery_token, reconciliation_id))
        if len(self._responses) > 1:
            return self._responses.pop(0)
        return self._responses[0]


def delivered(receipt: Optional[str] = "receipt-ok") -> DeliveryOutcome:
    return DeliveryOutcome(delivery_state=models.DeliveryState.DELIVERED, provider_receipt=receipt)


def accepted_delayed(receipt: Optional[str] = "receipt-delayed") -> DeliveryOutcome:
    return DeliveryOutcome(delivery_state=models.DeliveryState.ACCEPTED_DELAYED, provider_receipt=receipt)


def failed(receipt: Optional[str] = "provider unavailable") -> DeliveryOutcome:
    return DeliveryOutcome(delivery_state=models.DeliveryState.FAILED, provider_receipt=receipt)


class _Behavior:
    def __init__(self) -> None:
        self.status = 200
        self.body = b"{}"
        self.captured: List[dict] = []


class FakeMailProviderServer:
    """A tiny real HTTP loopback mail endpoint, controllable per-test."""

    def __init__(self) -> None:
        self.behavior = _Behavior()
        behavior = self.behavior

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length)
                try:
                    behavior.captured.append(json.loads(raw.decode("utf-8")))
                except json.JSONDecodeError:
                    behavior.captured.append({})
                body = behavior.body
                self.send_response(behavior.status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self._server = HTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    @property
    def url(self) -> str:
        host, port = self._server.server_address
        return f"http://{host}:{port}/mail"

    def set_success(self, *, state: Optional[str] = None, receipt: Optional[str] = None) -> None:
        payload = {}
        if state is not None:
            payload["state"] = state
        if receipt is not None:
            payload["receipt"] = receipt
        self.behavior.status = 200
        self.behavior.body = json.dumps(payload).encode("utf-8")

    def set_failure(self, *, status: int = 503, message: str = "unavailable") -> None:
        self.behavior.status = status
        self.behavior.body = json.dumps({"error": message}).encode("utf-8")

    def last_captured(self) -> Optional[dict]:
        return self.behavior.captured[-1] if self.behavior.captured else None

    def shutdown(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)
