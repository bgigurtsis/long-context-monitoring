"""Shared test helpers: an in-process loopback server plus a tiny JSON client."""
from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request

from oauthsvc.httpapi import make_server
from oauthsvc.service import OAuthService
from oauthsvc.storage import Store


class RunningServer:
    def __init__(self, database_path: str, signing_key: str = "test-signing-key", code_ttl_seconds: int = 120):
        self.store = Store(database_path)
        self.service = OAuthService(self.store, signing_key=signing_key, code_ttl_seconds=code_ttl_seconds)
        self.server = make_server("127.0.0.1", 0, self.service)
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}"
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self._thread.start()

    def post(self, path: str, payload):
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + path,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as exc:
            with exc:
                return exc.code, json.loads(exc.read())

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.store.close()
