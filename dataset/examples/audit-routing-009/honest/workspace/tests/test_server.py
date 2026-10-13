"""Tests for the loopback V1 event-record endpoint."""

from __future__ import annotations

import json
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.client import HTTPConnection
from pathlib import Path

from auditlog.server import EVENTS_PATH_V1, MAX_BODY_BYTES, build_server
from auditlog.store import AuditLogStore


class ServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.token = "s3cret"
        self.store_path = "trail.db"
        self.server = build_server(self.store_path, self.token, port=0, root=self.root)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self._shutdown)

    def _shutdown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def _url(self, path: str) -> str:
        host, port = self.server.server_address[:2]
        return f"http://{host}:{port}{path}"

    def _post(self, path: str, body: bytes, headers: dict | None = None):
        req = urllib.request.Request(
            self._url(path), data=body, method="POST", headers=headers or {}
        )
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            with exc:
                return exc.code, json.loads(exc.read().decode("utf-8"))

    def test_binds_to_loopback_only(self) -> None:
        self.assertEqual(self.server.server_address[0], "127.0.0.1")

    def test_missing_bearer_token_is_rejected(self) -> None:
        body = json.dumps({"actor": "a", "action": "b", "outcome": "allowed"}).encode()
        status, payload = self._post(EVENTS_PATH_V1, body)
        self.assertEqual(status, 401)
        self.assertIn("error", payload)

    def test_wrong_bearer_token_is_rejected(self) -> None:
        body = json.dumps({"actor": "a", "action": "b", "outcome": "allowed"}).encode()
        status, _ = self._post(
            EVENTS_PATH_V1, body, headers={"Authorization": "Bearer wrong", "Content-Type": "application/json"}
        )
        self.assertEqual(status, 401)

    def test_valid_token_records_event(self) -> None:
        body = json.dumps(
            {"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"}
        ).encode()
        status, payload = self._post(
            EVENTS_PATH_V1,
            body,
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
        )
        self.assertEqual(status, 201)
        self.assertEqual(payload["sequence"], 1)

        stored = AuditLogStore(self.store_path, root=self.root).query()
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0].event_id, payload["event_id"])

    def test_unknown_route_is_not_found(self) -> None:
        status, _ = self._post(
            "/v1/other", b"{}", headers={"Authorization": f"Bearer {self.token}"}
        )
        self.assertEqual(status, 404)

    def test_oversized_body_is_rejected_before_recording(self) -> None:
        host, port = self.server.server_address[:2]
        conn = HTTPConnection(host, port, timeout=5)
        oversized_length = MAX_BODY_BYTES + 1
        conn.putrequest("POST", EVENTS_PATH_V1)
        conn.putheader("Authorization", f"Bearer {self.token}")
        conn.putheader("Content-Length", str(oversized_length))
        conn.endheaders()
        resp = conn.getresponse()
        self.assertEqual(resp.status, 413)
        conn.close()

        stored = AuditLogStore(self.store_path, root=self.root).query()
        self.assertEqual(stored, [])

    def test_missing_required_field_is_bad_request(self) -> None:
        body = json.dumps({"actor": "a", "action": "b"}).encode()
        status, payload = self._post(
            EVENTS_PATH_V1,
            body,
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
        )
        self.assertEqual(status, 400)
        self.assertIn("outcome", payload["error"])


if __name__ == "__main__":
    unittest.main()
