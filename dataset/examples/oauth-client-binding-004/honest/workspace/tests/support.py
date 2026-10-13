"""Shared helpers for oauthsvc tests."""
from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from contextlib import contextmanager

from oauthsvc import httpserver


@contextmanager
def running_server(database, signing_key="test-signing-key", code_ttl_seconds=120):
    server = httpserver.create_server(
        database, signing_key, code_ttl_seconds=code_ttl_seconds, port=0
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def post_json(base_url, path, payload):
    body = json.dumps(payload).encode("utf-8")
    return post_raw(base_url, path, body)


def post_raw(base_url, path, raw_body, content_type="application/json"):
    request = urllib.request.Request(
        base_url + path,
        data=raw_body,
        headers={"Content-Type": content_type},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        with exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))
