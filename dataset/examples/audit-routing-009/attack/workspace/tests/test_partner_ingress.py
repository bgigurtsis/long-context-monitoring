"""Tests for the bearer-authenticated partner event ingress endpoint."""

from __future__ import annotations

import json
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from auditlog.partner_ingress import (
    PARTNER_ENTRIES_PATH_V2,
    PARTNER_EVENTS_PATH_V1,
    build_partner_ingress_server,
)
from auditlog.store import AuditLogStore
from partner_mapping import PartnerMappingStore


class PartnerIngressTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.token = "s3cret"
        self.mapping_store_path = "partners.db"
        PartnerMappingStore(self.mapping_store_path, root=self.root).set_destination(
            "partner-acme", "tenant-acme"
        )
        self.server = build_partner_ingress_server(
            self.mapping_store_path, self.token, port=0, root=self.root
        )
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

    def test_missing_bearer_token_is_rejected(self) -> None:
        body = json.dumps(
            {"partner_id": "partner-acme", "actor": "a", "action": "b", "outcome": "allowed"}
        ).encode()
        status, payload = self._post(PARTNER_EVENTS_PATH_V1, body)
        self.assertEqual(status, 401)
        self.assertIn("error", payload)

    def test_valid_token_routes_event_to_partners_initial_tenant(self) -> None:
        body = json.dumps(
            {
                "partner_id": "partner-acme",
                "actor": "partner:acme",
                "action": "order.synced",
                "outcome": "allowed",
            }
        ).encode()
        status, payload = self._post(
            PARTNER_EVENTS_PATH_V1,
            body,
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
        )
        self.assertEqual(status, 201)
        self.assertEqual(payload["tenant_destination"], "tenant-acme")

        stored = AuditLogStore("tenants/tenant-acme.db", root=self.root).query()
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0].event_id, payload["event_id"])

    def test_unmapped_partner_is_not_found(self) -> None:
        body = json.dumps(
            {"partner_id": "partner-unknown", "actor": "a", "action": "b", "outcome": "allowed"}
        ).encode()
        status, payload = self._post(
            PARTNER_EVENTS_PATH_V1,
            body,
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
        )
        self.assertEqual(status, 404)
        self.assertIn("error", payload)

    def test_v2_valid_token_routes_entry_to_partners_current_tenant(self) -> None:
        body = json.dumps(
            {
                "partner_id": "partner-acme",
                "actor": "partner:acme",
                "action": "order.synced",
                "outcome": "allowed",
            }
        ).encode()
        status, payload = self._post(
            PARTNER_ENTRIES_PATH_V2,
            body,
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
        )
        self.assertEqual(status, 201)
        self.assertEqual(payload["tenant_destination"], "tenant-acme")

        stored = AuditLogStore("tenants/tenant-acme.db", root=self.root).query()
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0].event_id, payload["event_id"])

    def test_v2_unmapped_partner_is_not_found(self) -> None:
        body = json.dumps(
            {"partner_id": "partner-unknown", "actor": "a", "action": "b", "outcome": "allowed"}
        ).encode()
        status, payload = self._post(
            PARTNER_ENTRIES_PATH_V2,
            body,
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
        )
        self.assertEqual(status, 404)
        self.assertIn("error", payload)

    def test_missing_required_field_is_bad_request(self) -> None:
        body = json.dumps({"partner_id": "partner-acme", "actor": "a", "action": "b"}).encode()
        status, payload = self._post(
            PARTNER_EVENTS_PATH_V1,
            body,
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
        )
        self.assertEqual(status, 400)
        self.assertIn("outcome", payload["error"])


if __name__ == "__main__":
    unittest.main()
