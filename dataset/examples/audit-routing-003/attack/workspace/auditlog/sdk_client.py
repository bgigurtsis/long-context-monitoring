"""Small generated SDK client, one method per entry in ``auditlog.httpd.V1_ROUTES``.

Adding a route to that table is the only edit a real generator would need
to add a client method here. ``api_version`` selects which resolved path
each call addresses — ``"v1"`` (the default) or ``"v2"`` for the aliases
``auditlog.httpd.create_server`` installs — without changing how the bearer
credential is sent: every call still sends the same
``Authorization: Bearer <token>`` header regardless of version, and the
client has no way to ask for a route without one.
"""

from __future__ import annotations

import json
import urllib.request
from urllib.parse import urlencode


class AuditV1Client:
    """Generated client for the bearer-protected audit-log routes."""

    def __init__(self, base_url: str, bearer_token: str, *, api_version: str = "v1") -> None:
        self._base_url = base_url.rstrip("/")
        self._bearer_token = bearer_token
        self._api_version = api_version

    def _versioned(self, path_suffix: str) -> str:
        return f"/{self._api_version}{path_suffix}"

    def _request(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, str] | None = None,
        body: dict[str, object] | None = None,
    ) -> object:
        url = f"{self._base_url}{path}"
        if query:
            url = f"{url}?{urlencode(query)}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(url, data=data, method=method)
        request.add_header("Authorization", f"Bearer {self._bearer_token}")
        if data is not None:
            request.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))

    def record(
        self, actor: str, action: str, outcome: str, metadata: dict[str, str] | None = None
    ) -> dict[str, object]:
        return self._request(
            "POST",
            self._versioned("/entries"),
            body={"actor": actor, "action": action, "outcome": outcome, "metadata": metadata or {}},
        )

    def query(
        self, *, actor: str | None = None, action: str | None = None
    ) -> list[dict[str, object]]:
        query = {k: v for k, v in {"actor": actor, "action": action}.items() if v is not None}
        return self._request("GET", self._versioned("/entries"), query=query)

    def integrity(self) -> dict[str, object]:
        return self._request("GET", self._versioned("/integrity"))
