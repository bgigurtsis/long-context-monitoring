"""Tests for the loopback HTTP transport, driven against a fake service.

These start a real server on 127.0.0.1 (an OS-assigned port) and speak real
HTTP to it with ``http.client``, so the tests exercise the same code path a
real caller would: routing, authentication, body bounds, and serialization.
"""

from __future__ import annotations

import http.client
import json
import threading
import unittest
from typing import Any, Iterator, Optional

from auditlog.http_transport import MAX_BODY_BYTES, create_server
from auditlog.models import AuditEvent, ReplayCursor, Replica, content_digest
from auditlog.service import AuditLogService

TOKEN = "s3cr3t-loopback-token"


class FakeAuditLogService(AuditLogService):
    """A minimal in-memory stand-in for the transport tests only."""

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []
        self._replicas: dict[str, Replica] = {}

    def record(
        self,
        actor: str,
        action: str,
        outcome: str,
        recorded_at: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AuditEvent:
        event = AuditEvent(
            event_id=content_digest(actor, action, outcome, recorded_at),
            sequence=len(self._events) + 1,
            actor=actor,
            action=action,
            outcome=outcome,
            recorded_at=recorded_at,
            metadata=metadata or {},
        )
        self._events.append(event)
        return event

    def events(self, since_sequence: int = 0) -> Iterator[AuditEvent]:
        return iter(e for e in self._events if e.sequence > since_sequence)

    def register_replica(self, name: str) -> Replica:
        replica_id = f"replica-{len(self._replicas) + 1}"
        replica = Replica(replica_id=replica_id, name=name)
        self._replicas[replica_id] = replica
        return replica

    def get_cursor(self, replica_id: str) -> Optional[ReplayCursor]:
        return None

    def advance_cursor(self, replica_id: str, offset: int, last_event_id: Optional[str] = None) -> ReplayCursor:
        return ReplayCursor(replica_id=replica_id, offset=offset, last_event_id=last_event_id)

    def promote_replica(self, replica_id: str, promotion_label: str) -> Replica:
        existing = self._replicas[replica_id]
        return Replica(replica_id=existing.replica_id, name=existing.name, promotion_label=promotion_label)

    def replay_since_cursor(self, replica_id: str, source_records):
        if replica_id not in self._replicas:
            raise KeyError(replica_id)
        applied = 0
        last_event_id = None
        for record in source_records:
            event = self.record(
                record["actor"],
                record["action"],
                record["outcome"],
                record["recorded_at"],
                metadata=record.get("metadata"),
            )
            last_event_id = event.event_id
            applied += 1
        return ReplayCursor(replica_id=replica_id, offset=applied, last_event_id=last_event_id), applied


class HTTPTransportTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.service = FakeAuditLogService()
        self.server = create_server(self.service, TOKEN, host="127.0.0.1", port=0)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self._shutdown)

    def _shutdown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def _connection(self) -> http.client.HTTPConnection:
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        self.addCleanup(conn.close)
        return conn

    def _request(self, method, path, body=None, token=TOKEN, extra_headers=None, raw_body=None):
        conn = self._connection()
        headers = {}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        if extra_headers:
            headers.update(extra_headers)
        if raw_body is not None:
            payload = raw_body
            headers.setdefault("Content-Type", "application/json")
        elif body is not None:
            payload = json.dumps(body).encode("utf-8")
            headers.setdefault("Content-Type", "application/json")
        else:
            payload = None
        conn.request(method, path, body=payload, headers=headers)
        response = conn.getresponse()
        raw = response.read()
        parsed = json.loads(raw) if raw else None
        return response.status, parsed


class AuthenticationTests(HTTPTransportTestCase):
    def test_post_entries_without_authorization_header_is_rejected(self) -> None:
        status, payload = self._request(
            "POST", "/v1/entries", body={"actor": "a", "action": "b", "outcome": "c", "recorded_at": "t"}, token=None
        )
        self.assertEqual(status, 401)
        self.assertEqual(self.service._events, [])

    def test_get_entries_with_wrong_token_is_rejected(self) -> None:
        status, _ = self._request("GET", "/v1/entries", token="wrong-token")
        self.assertEqual(status, 401)

    def test_get_integrity_without_token_is_rejected(self) -> None:
        status, _ = self._request("GET", "/v1/integrity", token=None)
        self.assertEqual(status, 401)

    def test_malformed_body_with_wrong_token_still_reports_unauthorized(self) -> None:
        # Proves auth happens before the body is parsed: an invalid JSON
        # body would normally be a 400, but the wrong token must win.
        status, _ = self._request(
            "POST", "/v1/entries", token="wrong-token", raw_body=b"{not valid json", extra_headers={}
        )
        self.assertEqual(status, 401)
        self.assertEqual(self.service._events, [])

    def test_correct_token_is_accepted(self) -> None:
        status, _ = self._request("GET", "/v1/entries")
        self.assertEqual(status, 200)


class RecordEntryTests(HTTPTransportTestCase):
    def test_role_grant_action_with_explicit_recorded_at_and_metadata(self) -> None:
        status, payload = self._request(
            "POST",
            "/v1/entries",
            body={
                "actor": "operator:mina",
                "action": "role.grant",
                "outcome": "allowed",
                "recorded_at": "2026-08-13T06:40:00+00:00",
                "metadata": {"granted_role": "admin"},
            },
        )
        self.assertEqual(status, 201)
        self.assertEqual(payload["action"], "role.grant")
        self.assertEqual(payload["recorded_at"], "2026-08-13T06:40:00+00:00")
        self.assertEqual(payload["metadata"], {"granted_role": "admin"})
        self.assertEqual(
            payload["content_id"],
            content_digest("operator:mina", "role.grant", "allowed", "2026-08-13T06:40:00+00:00"),
        )

    def test_metadata_is_optional(self) -> None:
        status, payload = self._request(
            "POST",
            "/v1/entries",
            body={"actor": "a", "action": "role.grant", "outcome": "allowed", "recorded_at": "T1"},
        )
        self.assertEqual(status, 201)
        self.assertEqual(payload["metadata"], {})

    def test_metadata_never_changes_content_id(self) -> None:
        _, first = self._request(
            "POST",
            "/v1/entries",
            body={"actor": "a", "action": "role.grant", "outcome": "allowed", "recorded_at": "T1", "metadata": {"x": 1}},
        )
        status, second = self._request(
            "POST",
            "/v1/entries",
            body={"actor": "a", "action": "role.grant", "outcome": "allowed", "recorded_at": "T1", "metadata": {"x": 2}},
        )
        self.assertEqual(status, 201)
        self.assertEqual(first["content_id"], second["content_id"])
        self.assertNotEqual(first["metadata"], second["metadata"])

    def test_missing_recorded_at_is_rejected(self) -> None:
        status, payload = self._request(
            "POST", "/v1/entries", body={"actor": "a", "action": "role.grant", "outcome": "allowed"}
        )
        self.assertEqual(status, 400)
        self.assertIn("error", payload)

    def test_non_object_metadata_is_rejected(self) -> None:
        status, _ = self._request(
            "POST",
            "/v1/entries",
            body={"actor": "a", "action": "role.grant", "outcome": "allowed", "recorded_at": "T1", "metadata": "nope"},
        )
        self.assertEqual(status, 400)


class QueryEntriesTests(HTTPTransportTestCase):
    def test_entries_expose_recorded_at_and_content_id_explicitly(self) -> None:
        self.service.record("a", "role.grant", "allowed", "T1", metadata={"note": "x"})
        status, payload = self._request("GET", "/v1/entries")
        self.assertEqual(status, 200)
        self.assertEqual(len(payload["entries"]), 1)
        entry = payload["entries"][0]
        self.assertIn("recorded_at", entry)
        self.assertIn("content_id", entry)
        self.assertEqual(entry["recorded_at"], "T1")
        self.assertEqual(entry["content_id"], content_digest("a", "role.grant", "allowed", "T1"))

    def test_since_sequence_filters_results(self) -> None:
        self.service.record("a", "role.grant", "allowed", "T1")
        self.service.record("a", "role.grant", "allowed", "T2")
        status, payload = self._request("GET", "/v1/entries?since_sequence=1")
        self.assertEqual(status, 200)
        self.assertEqual(len(payload["entries"]), 1)
        self.assertEqual(payload["entries"][0]["recorded_at"], "T2")


class IntegrityRouteTests(HTTPTransportTestCase):
    def test_untampered_events_all_verify(self) -> None:
        self.service.record("a", "role.grant", "allowed", "T1")
        self.service.record("b", "role.grant", "allowed", "T2")
        status, payload = self._request("GET", "/v1/integrity")
        self.assertEqual(status, 200)
        self.assertTrue(payload["all_verified"])
        self.assertEqual(len(payload["entries"]), 2)
        for entry in payload["entries"]:
            self.assertTrue(entry["verified"])
            self.assertIn("recorded_at", entry)
            self.assertIn("content_id", entry)

    def test_tampered_event_id_is_detected(self) -> None:
        event = self.service.record("a", "role.grant", "allowed", "T1")
        self.service._events[0] = AuditEvent(
            event_id="tampered",
            sequence=event.sequence,
            actor=event.actor,
            action=event.action,
            outcome=event.outcome,
            recorded_at=event.recorded_at,
        )
        status, payload = self._request("GET", "/v1/integrity")
        self.assertEqual(status, 200)
        self.assertFalse(payload["all_verified"])
        self.assertFalse(payload["entries"][0]["verified"])


class RoutingTests(HTTPTransportTestCase):
    def test_unknown_path_is_404(self) -> None:
        status, _ = self._request("GET", "/v1/does-not-exist")
        self.assertEqual(status, 404)

    def test_unknown_path_is_404_even_without_auth(self) -> None:
        status, _ = self._request("GET", "/v1/does-not-exist", token=None)
        self.assertEqual(status, 404)

    def test_alternate_spelling_reaches_the_same_route(self) -> None:
        self.service.record("a", "role.grant", "allowed", "T1")
        status, payload = self._request("GET", "//v1/entries/")
        self.assertEqual(status, 200)
        self.assertEqual(len(payload["entries"]), 1)


class BodyBoundTests(HTTPTransportTestCase):
    def test_oversized_body_is_rejected(self) -> None:
        oversized = json.dumps({"actor": "a" * (MAX_BODY_BYTES + 1)}).encode("utf-8")
        status, _ = self._request("POST", "/v1/entries", raw_body=oversized)
        self.assertEqual(status, 413)
        self.assertEqual(self.service._events, [])

    def test_missing_content_length_is_rejected(self) -> None:
        conn = self._connection()
        conn.putrequest("POST", "/v1/entries")
        conn.putheader("Authorization", f"Bearer {TOKEN}")
        conn.endheaders()
        response = conn.getresponse()
        response.read()
        self.assertEqual(response.status, 411)


class LoopbackHostTests(unittest.TestCase):
    def test_non_loopback_host_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            create_server(FakeAuditLogService(), TOKEN, host="0.0.0.0", port=0)


if __name__ == "__main__":
    unittest.main()
