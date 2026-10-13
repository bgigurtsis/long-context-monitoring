"""Tests for the loopback HTTP transport around RecoveryAuditService.

Covers the documented operations (create/list/get an entry, check
integrity) and the refusal cases (missing/wrong bearer token, auth checked
before the body is parsed, unknown paths, method mismatch, oversized
bodies, malformed JSON, missing fields, duplicate content ids, and the
loopback-only constraint on the server itself).
"""

from __future__ import annotations

import http.client
import json
import threading
import unittest

from auditlog.http_transport import DEFAULT_MAX_BODY_BYTES, make_server
from auditlog.integrity import complete_event_identity
from auditlog.memory import InMemoryRecoveryAuditService
from auditlog.models import content_digest

BEARER_TOKEN = "s05-loopback-secret"


class _ServerFixtureMixin:
    """Starts a real loopback server on an ephemeral port for each test."""

    max_body_bytes = DEFAULT_MAX_BODY_BYTES

    def setUp(self) -> None:
        self.service = InMemoryRecoveryAuditService()
        self.server = make_server(
            self.service, BEARER_TOKEN, port=0, max_body_bytes=self.max_body_bytes
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_port

    def tearDown(self) -> None:
        self.server.shutdown()
        self.thread.join(timeout=5)
        self.server.server_close()

    def request(self, method: str, path: str, *, headers=None, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            conn.request(method, path, body=body, headers=headers or {})
            response = conn.getresponse()
            raw = response.read()
            return response.status, response.headers, raw
        finally:
            conn.close()

    def auth_headers(self, token: str = BEARER_TOKEN, **extra):
        headers = {"Authorization": f"Bearer {token}"}
        headers.update(extra)
        return headers

    def post_entry(self, actor, action, outcome, recorded_at, metadata=None, token=BEARER_TOKEN):
        payload = {"actor": actor, "action": action, "outcome": outcome, "recorded_at": recorded_at}
        if metadata is not None:
            payload["metadata"] = metadata
        body = json.dumps(payload).encode("utf-8")
        headers = self.auth_headers(token=token, **{"Content-Type": "application/json", "Content-Length": str(len(body))})
        return self.request("POST", "/v1/entries", headers=headers, body=body)


class DocumentedOperationsTests(_ServerFixtureMixin, unittest.TestCase):
    def test_create_entry_accepts_role_grant_recorded_at_and_metadata(self) -> None:
        status, _, raw = self.post_entry(
            "operator:mina", "role.grant", "allowed", "2026-08-15T22:55:00+00:00",
            metadata={"ticket": "T-1", "shift": "night"},
        )
        self.assertEqual(status, 201)
        payload = json.loads(raw)
        expected_content_id = content_digest(
            "operator:mina", "role.grant", "allowed", "2026-08-15T22:55:00+00:00"
        )
        self.assertEqual(payload["content_id"], expected_content_id)
        self.assertEqual(payload["recorded_at"], "2026-08-15T22:55:00+00:00")
        self.assertEqual(payload["metadata"], {"ticket": "T-1", "shift": "night"})

    def test_metadata_is_optional(self) -> None:
        status, _, raw = self.post_entry(
            "operator:sven", "role.grant", "allowed", "2026-08-15T23:00:00+00:00",
        )
        self.assertEqual(status, 201)
        payload = json.loads(raw)
        self.assertEqual(payload["metadata"], {})

    def test_metadata_does_not_affect_content_id(self) -> None:
        # Same actor/action/outcome/recorded_at, different metadata: the
        # second call must collide on identity (409), which is only
        # possible if metadata was excluded from the content id.
        status1, _, _ = self.post_entry(
            "operator:mina", "role.grant", "allowed", "2026-08-15T22:55:00+00:00",
            metadata={"ticket": "T-1"},
        )
        status2, _, raw2 = self.post_entry(
            "operator:mina", "role.grant", "allowed", "2026-08-15T22:55:00+00:00",
            metadata={"ticket": "T-2", "note": "resubmitted"},
        )
        self.assertEqual(status1, 201)
        self.assertEqual(status2, 409)
        payload2 = json.loads(raw2)
        self.assertEqual(payload2["error"], "duplicate_event")

    def test_list_entries_exposes_recorded_at_and_content_id(self) -> None:
        self.post_entry("operator:mina", "role.grant", "allowed", "2026-08-15T22:55:00+00:00")
        status, _, raw = self.request("GET", "/v1/entries", headers=self.auth_headers())
        self.assertEqual(status, 200)
        payload = json.loads(raw)
        self.assertEqual(len(payload["entries"]), 1)
        entry = payload["entries"][0]
        self.assertIn("recorded_at", entry)
        self.assertIn("content_id", entry)
        self.assertEqual(entry["recorded_at"], "2026-08-15T22:55:00+00:00")
        self.assertEqual(
            entry["content_id"],
            content_digest("operator:mina", "role.grant", "allowed", "2026-08-15T22:55:00+00:00"),
        )

    def test_get_single_entry(self) -> None:
        _, _, raw = self.post_entry("operator:mina", "role.grant", "allowed", "2026-08-15T22:55:00+00:00")
        content_id = json.loads(raw)["content_id"]
        status, _, raw2 = self.request(
            "GET", f"/v1/entries/{content_id}", headers=self.auth_headers()
        )
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw2)["content_id"], content_id)

    def test_get_missing_entry_is_404(self) -> None:
        status, _, _ = self.request("GET", "/v1/entries/does-not-exist", headers=self.auth_headers())
        self.assertEqual(status, 404)

    def test_get_integrity(self) -> None:
        _, _, raw = self.post_entry("operator:mina", "role.grant", "allowed", "2026-08-15T22:55:00+00:00")
        content_id = json.loads(raw)["content_id"]
        status, _, raw2 = self.request(
            "GET", f"/v1/integrity/{content_id}", headers=self.auth_headers()
        )
        self.assertEqual(status, 200)
        payload = json.loads(raw2)
        self.assertTrue(payload["intact"])
        self.assertEqual(
            payload["complete_identity"],
            complete_event_identity("2026-08-15T22:55:00+00:00", content_id),
        )

    def test_get_integrity_for_missing_entry_is_404(self) -> None:
        status, _, _ = self.request(
            "GET", "/v1/integrity/does-not-exist", headers=self.auth_headers()
        )
        self.assertEqual(status, 404)


class RefusalCaseTests(_ServerFixtureMixin, unittest.TestCase):
    def test_missing_auth_header_is_rejected(self) -> None:
        status, _, _ = self.request("GET", "/v1/entries")
        self.assertEqual(status, 401)

    def test_wrong_bearer_token_is_rejected(self) -> None:
        status, _, _ = self.request("GET", "/v1/entries", headers=self.auth_headers(token="wrong-token"))
        self.assertEqual(status, 401)

    def test_non_bearer_scheme_is_rejected(self) -> None:
        status, _, _ = self.request(
            "GET", "/v1/entries", headers={"Authorization": f"Basic {BEARER_TOKEN}"}
        )
        self.assertEqual(status, 401)

    def test_auth_is_checked_before_body_is_parsed(self) -> None:
        # An unparseable body must not surface as a 400: the request should
        # be rejected for authentication before the body is ever read.
        body = b"{not-json"
        headers = {"Content-Type": "application/json", "Content-Length": str(len(body))}
        status, _, raw = self.request("POST", "/v1/entries", headers=headers, body=body)
        self.assertEqual(status, 401)
        self.assertEqual(json.loads(raw)["error"], "unauthorized")

    def test_unknown_path_is_404_even_without_auth(self) -> None:
        status, _, _ = self.request("GET", "/v1/does-not-exist")
        self.assertEqual(status, 404)

    def test_unknown_path_is_404_with_auth(self) -> None:
        status, _, _ = self.request("GET", "/v1/does-not-exist", headers=self.auth_headers())
        self.assertEqual(status, 404)

    def test_method_not_allowed_on_item_route(self) -> None:
        _, _, raw = self.post_entry("operator:mina", "role.grant", "allowed", "2026-08-15T22:55:00+00:00")
        content_id = json.loads(raw)["content_id"]
        status, headers, _ = self.request(
            "POST", f"/v1/entries/{content_id}", headers=self.auth_headers()
        )
        self.assertEqual(status, 405)
        self.assertIn("GET", headers.get("Allow", ""))

    def test_method_not_allowed_requires_auth_first(self) -> None:
        status, _, _ = self.request("POST", "/v1/entries/some-id")
        self.assertEqual(status, 401)

    def test_malformed_json_is_400(self) -> None:
        body = b"{not-json"
        headers = self.auth_headers(**{"Content-Type": "application/json", "Content-Length": str(len(body))})
        status, _, raw = self.request("POST", "/v1/entries", headers=headers, body=body)
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(raw)["error"], "invalid_json")

    def test_missing_required_field_is_400(self) -> None:
        payload = {"actor": "operator:mina", "action": "role.grant", "outcome": "allowed"}
        body = json.dumps(payload).encode("utf-8")
        headers = self.auth_headers(**{"Content-Type": "application/json", "Content-Length": str(len(body))})
        status, _, raw = self.request("POST", "/v1/entries", headers=headers, body=body)
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(raw)["fields"], ["recorded_at"])

    def test_non_object_metadata_is_400(self) -> None:
        payload = {
            "actor": "operator:mina", "action": "role.grant", "outcome": "allowed",
            "recorded_at": "2026-08-15T22:55:00+00:00", "metadata": "not-an-object",
        }
        body = json.dumps(payload).encode("utf-8")
        headers = self.auth_headers(**{"Content-Type": "application/json", "Content-Length": str(len(body))})
        status, _, raw = self.request("POST", "/v1/entries", headers=headers, body=body)
        self.assertEqual(status, 400)
        self.assertEqual(json.loads(raw)["error"], "invalid_metadata")

    def test_duplicate_entry_is_409(self) -> None:
        status1, _, _ = self.post_entry("operator:mina", "role.grant", "allowed", "2026-08-15T22:55:00+00:00")
        status2, _, _ = self.post_entry("operator:mina", "role.grant", "allowed", "2026-08-15T22:55:00+00:00")
        self.assertEqual(status1, 201)
        self.assertEqual(status2, 409)

    def test_make_server_rejects_non_loopback_host(self) -> None:
        with self.assertRaises(ValueError):
            make_server(self.service, BEARER_TOKEN, host="8.8.8.8")


class OversizedBodyTests(_ServerFixtureMixin, unittest.TestCase):
    max_body_bytes = 16  # small cap so the test does not need a huge payload

    def test_body_over_the_cap_is_413(self) -> None:
        payload = {
            "actor": "operator:mina", "action": "role.grant", "outcome": "allowed",
            "recorded_at": "2026-08-15T22:55:00+00:00",
        }
        body = json.dumps(payload).encode("utf-8")
        self.assertGreater(len(body), self.max_body_bytes)
        headers = self.auth_headers(**{"Content-Type": "application/json", "Content-Length": str(len(body))})
        status, _, raw = self.request("POST", "/v1/entries", headers=headers, body=body)
        self.assertEqual(status, 413)
        self.assertEqual(json.loads(raw)["error"], "body_too_large")


if __name__ == "__main__":
    unittest.main()
