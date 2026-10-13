"""Shared scaffolding for oauthsvc tests."""
from __future__ import annotations

import contextlib
import json
import os
import tempfile
import threading
from http.client import HTTPConnection

from oauthsvc.server import make_server
from oauthsvc.service import OAuthService
from oauthsvc.storage import Storage

ACCOUNT_ID = "acct-alex"
ACCOUNT_EMAIL = "alex@example.com"
ACCOUNT_PASSWORD = "correct horse battery staple"

CLIENT_ID = "client-a"
CLIENT_CALLBACK = "http://127.0.0.1:4311/callback"

OTHER_CLIENT_ID = "client-b"
OTHER_CLIENT_CALLBACK = "http://127.0.0.1:4312/callback"


@contextlib.contextmanager
def temp_storage():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    storage = Storage(path)
    try:
        yield storage
    finally:
        storage.close()
        if os.path.exists(path):
            os.remove(path)


def seed(storage: Storage) -> None:
    service = OAuthService(storage, signing_key="unused")
    service.create_account(ACCOUNT_ID, ACCOUNT_EMAIL, ACCOUNT_PASSWORD)
    service.register_client(CLIENT_ID, CLIENT_CALLBACK)
    service.register_client(OTHER_CLIENT_ID, OTHER_CLIENT_CALLBACK)


class RunningServer:
    def __init__(
        self,
        storage: Storage,
        signing_key: str = "test-signing-key",
        code_ttl_seconds: int = 120,
        clock=None,
    ):
        self._server = make_server(storage, signing_key, code_ttl_seconds=code_ttl_seconds, clock=clock)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def service(self) -> OAuthService:
        return self._server.service

    def __enter__(self) -> "RunningServer":
        self._thread.start()
        return self

    def __exit__(self, *exc_info) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)

    def post(self, path: str, payload: dict) -> tuple[int, dict]:
        host, port = self._server.server_address[:2]
        conn = HTTPConnection(host, port, timeout=5)
        try:
            body = json.dumps(payload).encode("utf-8")
            conn.request("POST", path, body=body, headers={"Content-Type": "application/json"})
            response = conn.getresponse()
            raw = response.read()
            return response.status, json.loads(raw.decode("utf-8"))
        finally:
            conn.close()

    def post_raw(self, path: str, raw_body: bytes) -> tuple[int, dict]:
        host, port = self._server.server_address[:2]
        conn = HTTPConnection(host, port, timeout=5)
        try:
            conn.request("POST", path, body=raw_body, headers={"Content-Type": "application/json"})
            response = conn.getresponse()
            raw = response.read()
            return response.status, json.loads(raw.decode("utf-8"))
        finally:
            conn.close()
