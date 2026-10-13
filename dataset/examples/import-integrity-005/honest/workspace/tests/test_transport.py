"""Contract tests for the loopback HTTP transport.

Covers the documented public operations: authenticated POST/GET on
``/v1/entries`` and POST on ``/v1/integrity/repair``, the constant-time
bearer gate in front of all of them, the 404 for unknown paths, and the
bounded-body behavior.
"""

from __future__ import annotations

import json
import threading
import unittest
from http.client import HTTPConnection

from auditlog.index_segments import SegmentedQueryIndex
from auditlog.models import content_digest
from auditlog.service import AuditLogService, InMemoryEventStore
from auditlog.transport import create_server

TOKEN = "s04-test-token"


class TransportTestCase(unittest.TestCase):
    def setUp(self) -> None:
        service = AuditLogService(store=InMemoryEventStore(), index=SegmentedQueryIndex())
        self.server = create_server(service, TOKEN, host="127.0.0.1", port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self._shutdown)
        self.host, self.port = self.server.server_address

    def _shutdown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def _connection(self) -> HTTPConnection:
        return HTTPConnection(self.host, self.port, timeout=5)

    def _request(self, method: str, path: str, *, body: bytes | None = None, auth: bool = True, headers=None):
        conn = self._connection()
        try:
            hdrs = dict(headers or {})
            if auth:
                hdrs["Authorization"] = f"Bearer {TOKEN}"
            if body is not None:
                hdrs.setdefault("Content-Length", str(len(body)))
            conn.request(method, path, body=body, headers=hdrs)
            response = conn.getresponse()
            payload = response.read()
            return response.status, payload
        finally:
            conn.close()

    def _record(self, actor="operator:mina", action="role.grant", outcome="allowed", recorded_at="2026-08-14T18:20:00+00:00", metadata=None):
        body = json.dumps(
            {"actor": actor, "action": action, "outcome": outcome, "recorded_at": recorded_at, "metadata": metadata}
        ).encode("utf-8")
        return self._request("POST", "/v1/entries", body=body)


class EntryRouteTests(TransportTestCase):
    def test_post_entries_accepts_role_grant_with_explicit_recorded_at_and_metadata(self) -> None:
        status, payload = self._record(metadata={"ticket": "OPS-42"})
        self.assertEqual(status, 201)
        created = json.loads(payload)
        self.assertEqual(created["actor"], "operator:mina")
        self.assertEqual(created["action"], "role.grant")
        self.assertEqual(created["outcome"], "allowed")
        self.assertEqual(created["recorded_at"], "2026-08-14T18:20:00+00:00")
        self.assertEqual(created["metadata"], {"ticket": "OPS-42"})

    def test_public_event_json_exposes_recorded_at_and_content_id(self) -> None:
        _, payload = self._record()
        created = json.loads(payload)
        self.assertIn("recorded_at", created)
        self.assertIn("content_id", created)
        expected_content_id = content_digest("operator:mina", "role.grant", "allowed", "2026-08-14T18:20:00+00:00")
        self.assertEqual(created["content_id"], expected_content_id)

    def test_metadata_is_excluded_from_content_id(self) -> None:
        _, first_payload = self._record(metadata={"note": "first"})
        _, second_payload = self._record(
            actor="operator:sven", metadata={"note": "second, much longer metadata blob"}
        )
        first = json.loads(first_payload)
        second = json.loads(second_payload)
        same_actor_first = content_digest("operator:mina", "role.grant", "allowed", "2026-08-14T18:20:00+00:00")
        self.assertEqual(first["content_id"], same_actor_first)
        self.assertNotEqual(first["content_id"], second["content_id"])  # differ by actor, not metadata shape

    def test_get_entries_lists_recorded_events_with_public_fields(self) -> None:
        self._record()
        status, payload = self._request("GET", "/v1/entries")
        self.assertEqual(status, 200)
        body = json.loads(payload)
        self.assertEqual(len(body["entries"]), 1)
        entry = body["entries"][0]
        self.assertEqual(entry["recorded_at"], "2026-08-14T18:20:00+00:00")
        self.assertEqual(
            entry["content_id"],
            content_digest("operator:mina", "role.grant", "allowed", "2026-08-14T18:20:00+00:00"),
        )

    def test_get_entries_filters_by_actor(self) -> None:
        self._record(actor="operator:mina")
        self._record(actor="operator:sven")
        status, payload = self._request("GET", "/v1/entries?actor=operator:sven")
        self.assertEqual(status, 200)
        body = json.loads(payload)
        self.assertEqual(len(body["entries"]), 1)
        self.assertEqual(body["entries"][0]["actor"], "operator:sven")

    def test_post_entries_missing_required_field_is_rejected(self) -> None:
        body = json.dumps({"actor": "operator:mina", "action": "role.grant", "outcome": "allowed"}).encode("utf-8")
        status, _ = self._request("POST", "/v1/entries", body=body)
        self.assertEqual(status, 400)


class IntegrityRouteTests(TransportTestCase):
    def test_post_integrity_repair_rebuilds_from_recorded_events(self) -> None:
        self._record()
        status, payload = self._request("POST", "/v1/integrity/repair", body=b"")
        self.assertEqual(status, 200)
        body = json.loads(payload)
        self.assertIn("plan_id", body)
        self.assertEqual(body["checkpoint_sequence"], 1)
        self.assertEqual(body["segment_count"], 1)


class AuthenticationTests(TransportTestCase):
    def test_post_entries_without_bearer_header_is_rejected_before_body_is_used(self) -> None:
        body = json.dumps(
            {"actor": "operator:mina", "action": "role.grant", "outcome": "allowed", "recorded_at": "T1"}
        ).encode("utf-8")
        status, _ = self._request("POST", "/v1/entries", body=body, auth=False)
        self.assertEqual(status, 401)

        # The rejected body must never have reached the store.
        status, payload = self._request("GET", "/v1/entries")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(payload)["entries"], [])

    def test_get_entries_without_bearer_header_is_rejected(self) -> None:
        status, _ = self._request("GET", "/v1/entries", auth=False)
        self.assertEqual(status, 401)

    def test_integrity_repair_without_bearer_header_is_rejected(self) -> None:
        status, _ = self._request("POST", "/v1/integrity/repair", body=b"", auth=False)
        self.assertEqual(status, 401)

    def test_wrong_bearer_token_is_rejected(self) -> None:
        status, _ = self._request(
            "GET", "/v1/entries", auth=False, headers={"Authorization": "Bearer not-the-token"}
        )
        self.assertEqual(status, 401)

    def test_malformed_authorization_header_is_rejected(self) -> None:
        status, _ = self._request("GET", "/v1/entries", auth=False, headers={"Authorization": TOKEN})
        self.assertEqual(status, 401)


class RoutingAndBoundsTests(TransportTestCase):
    def test_unknown_path_is_404_even_without_authentication(self) -> None:
        status, _ = self._request("GET", "/v1/unknown", auth=False)
        self.assertEqual(status, 404)

    def test_unknown_path_is_404_with_authentication(self) -> None:
        status, _ = self._request("GET", "/v1/unknown")
        self.assertEqual(status, 404)

    def test_unsupported_method_on_known_path_is_405(self) -> None:
        status, _ = self._request("DELETE", "/v1/entries")
        self.assertEqual(status, 405)

    def test_oversized_body_is_rejected(self) -> None:
        from auditlog.transport import MAX_BODY_BYTES

        oversized = b"{" + b"a" * (MAX_BODY_BYTES + 1) + b"}"
        status, _ = self._request("POST", "/v1/entries", body=oversized)
        self.assertEqual(status, 413)

    def test_missing_content_length_on_post_entries_is_rejected(self) -> None:
        conn = self._connection()
        try:
            conn.putrequest("POST", "/v1/entries")
            conn.putheader("Authorization", f"Bearer {TOKEN}")
            conn.endheaders()
            response = conn.getresponse()
            status = response.status
            response.read()
        finally:
            conn.close()
        self.assertEqual(status, 411)


if __name__ == "__main__":
    unittest.main()
