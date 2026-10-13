"""Tests for the loopback-only HTTP transport in auditlog.serve.

Exercises the real server (bound to 127.0.0.1 on an OS-assigned port) with a
fake AuditLogService, so these tests prove the transport's own contract —
routing, bearer authentication, and body bounding — independent of any
storage backend.
"""

from __future__ import annotations

import http.client
import json
import threading
import unittest

from auditlog.models import new_event
from auditlog.serve import LOOPBACK_HOST, MAX_BODY_BYTES, make_server
from auditlog.service import AuditLogService, ImportReport, RepairReport

BEARER_TOKEN = "s3cret-token"


class FakeAuditLogService(AuditLogService):
    """A minimal in-memory service used only to test the transport.

    Accepts (but does not exercise) the newer keyword-only parameters so it
    keeps satisfying the ``AuditLogService`` contract; the transport tests
    below only ever call this fake the way ``auditlog.serve`` itself does.
    """

    def __init__(self) -> None:
        self.events = []
        self.record_calls = []

    def record(self, actor, action, outcome, *, metadata=None, idempotency_key=None):
        self.record_calls.append((actor, action, outcome, metadata))
        sequence = len(self.events) + 1
        event = new_event(
            actor, action, outcome, "2024-03-02T09:04:00Z", sequence, metadata=metadata,
            idempotency_key=idempotency_key,
        )
        self.events.append(event)
        return event

    def query(self, *, actor=None, action=None, outcome=None, start=None, end=None):
        events = self.events
        if actor is not None:
            events = [e for e in events if e.actor == actor]
        if action is not None:
            events = [e for e in events if e.action == action]
        if outcome is not None:
            events = [e for e in events if e.outcome == outcome]
        return tuple(events)

    def repair(self, *, report_path=None):
        return RepairReport(checked=len(self.events), corrupt=(), indexed_actors=len({e.actor for e in self.events}))

    def import_events(self, events, *, expected_sequence=None):
        return ImportReport(imported=(), skipped_duplicates=(), base_sequence=len(self.events))


class ServeTransportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fake = FakeAuditLogService()
        self.server = make_server(self.fake, BEARER_TOKEN, port=0)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self._stop_server)

    def _stop_server(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def _connect(self) -> http.client.HTTPConnection:
        conn = http.client.HTTPConnection(LOOPBACK_HOST, self.port, timeout=5)
        self.addCleanup(conn.close)
        return conn

    def _auth_headers(self, token: str = BEARER_TOKEN) -> dict:
        return {"Authorization": f"Bearer {token}"}

    # -- documented paths -------------------------------------------------

    def test_health_is_public_and_returns_ok(self) -> None:
        conn = self._connect()
        conn.request("GET", "/health")
        response = conn.getresponse()
        self.assertEqual(response.status, 200)
        self.assertEqual(json.loads(response.read()), {"status": "ok"})

    def test_post_v1_entries_records_with_bearer(self) -> None:
        conn = self._connect()
        payload = json.dumps({"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"})
        conn.request("POST", "/v1/entries", body=payload, headers=self._auth_headers())
        response = conn.getresponse()
        self.assertEqual(response.status, 201)
        body = json.loads(response.read())
        self.assertEqual(body["sequence"], 1)
        self.assertEqual(self.fake.record_calls, [("operator:mina", "policy.update", "allowed", {})])

    def test_get_v1_entries_queries_with_bearer(self) -> None:
        self.fake.record("operator:mina", "policy.update", "allowed")
        self.fake.record("service:indexer", "report.read", "denied")

        conn = self._connect()
        conn.request("GET", "/v1/entries?actor=operator%3Amina", headers=self._auth_headers())
        response = conn.getresponse()
        self.assertEqual(response.status, 200)
        entries = json.loads(response.read())["entries"]
        self.assertEqual([e["actor"] for e in entries], ["operator:mina"])

    def test_get_v1_integrity_reports_with_bearer(self) -> None:
        self.fake.record("operator:mina", "policy.update", "allowed")

        conn = self._connect()
        conn.request("GET", "/v1/integrity", headers=self._auth_headers())
        response = conn.getresponse()
        self.assertEqual(response.status, 200)
        report = json.loads(response.read())
        self.assertEqual(report["checked"], 1)
        self.assertEqual(report["corrupt"], [])

    # -- /v2 aliases: documented paths -------------------------------------

    def test_post_v2_entries_records_with_bearer(self) -> None:
        conn = self._connect()
        payload = json.dumps({"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"})
        conn.request("POST", "/v2/entries", body=payload, headers=self._auth_headers())
        response = conn.getresponse()
        self.assertEqual(response.status, 201)
        body = json.loads(response.read())
        self.assertEqual(body["sequence"], 1)
        self.assertEqual(self.fake.record_calls, [("operator:mina", "policy.update", "allowed", {})])

    def test_get_v2_entries_queries_with_bearer(self) -> None:
        self.fake.record("operator:mina", "policy.update", "allowed")
        self.fake.record("service:indexer", "report.read", "denied")

        conn = self._connect()
        conn.request("GET", "/v2/entries?actor=operator%3Amina", headers=self._auth_headers())
        response = conn.getresponse()
        self.assertEqual(response.status, 200)
        entries = json.loads(response.read())["entries"]
        self.assertEqual([e["actor"] for e in entries], ["operator:mina"])

    def test_get_v2_integrity_reports_with_bearer(self) -> None:
        self.fake.record("operator:mina", "policy.update", "allowed")

        conn = self._connect()
        conn.request("GET", "/v2/integrity", headers=self._auth_headers())
        response = conn.getresponse()
        self.assertEqual(response.status, 200)
        report = json.loads(response.read())
        self.assertEqual(report["checked"], 1)
        self.assertEqual(report["corrupt"], [])

    def test_v1_and_v2_entries_share_the_same_underlying_store(self) -> None:
        # /v1 and /v2 are aliases of the same route, not independent stores.
        conn = self._connect()
        payload = json.dumps({"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"})
        conn.request("POST", "/v1/entries", body=payload, headers=self._auth_headers())
        first = conn.getresponse()
        self.assertEqual(first.status, 201)
        first.read()

        conn = self._connect()
        conn.request("POST", "/v2/entries", body=payload, headers=self._auth_headers())
        second = conn.getresponse()
        self.assertEqual(second.status, 201)
        second_body = json.loads(second.read())
        self.assertEqual(second_body["sequence"], 2)

        conn = self._connect()
        conn.request("GET", "/v2/entries", headers=self._auth_headers())
        listed = conn.getresponse()
        entries = json.loads(listed.read())["entries"]
        self.assertEqual([e["sequence"] for e in entries], [1, 2])

    # -- /v2 aliases: harmless alternate spellings -------------------------

    def test_v2_entries_trailing_slash_is_equivalent_to_canonical(self) -> None:
        conn = self._connect()
        conn.request("GET", "/v2/entries/", headers=self._auth_headers())
        response = conn.getresponse()
        self.assertEqual(response.status, 200)
        response.read()

    def test_v2_entries_doubled_slashes_are_equivalent_to_canonical(self) -> None:
        conn = self._connect()
        conn.request("GET", "//v2//entries", headers=self._auth_headers())
        response = conn.getresponse()
        self.assertEqual(response.status, 200)
        response.read()

    def test_v2_entries_percent_encoded_slash_is_equivalent_to_canonical(self) -> None:
        conn = self._connect()
        conn.request("GET", "/v2%2Fentries", headers=self._auth_headers())
        response = conn.getresponse()
        self.assertEqual(response.status, 200)
        response.read()

    # -- /v2 aliases: authentication equivalence with /v1 ------------------

    def test_v1_and_v2_entries_reach_the_same_auth_decision_without_bearer(self) -> None:
        conn = self._connect()
        conn.request("GET", "/v1/entries")
        v1_response = conn.getresponse()
        v1_response.read()

        conn = self._connect()
        conn.request("GET", "/v2/entries")
        v2_response = conn.getresponse()
        v2_response.read()

        self.assertEqual(v1_response.status, v2_response.status)
        self.assertEqual(v2_response.status, 401)

    def test_v2_entries_without_bearer_is_rejected(self) -> None:
        conn = self._connect()
        conn.request("POST", "/v2/entries", body=b"{}")
        response = conn.getresponse()
        self.assertEqual(response.status, 401)
        response.read()
        self.assertEqual(self.fake.record_calls, [])

    def test_v2_integrity_with_wrong_bearer_is_rejected(self) -> None:
        conn = self._connect()
        conn.request("GET", "/v2/integrity", headers=self._auth_headers("not-the-token"))
        response = conn.getresponse()
        self.assertEqual(response.status, 401)
        response.read()

    # -- /v2 aliases: bounded request handling ------------------------------

    def test_v2_oversized_body_is_rejected_and_never_recorded(self) -> None:
        conn = self._connect()
        oversized = b"x" * (MAX_BODY_BYTES + 1)
        conn.request("POST", "/v2/entries", body=oversized, headers=self._auth_headers())
        response = conn.getresponse()
        self.assertEqual(response.status, 413)
        response.read()
        self.assertEqual(self.fake.record_calls, [])

    def test_v2_body_at_the_limit_is_accepted(self) -> None:
        base = {"actor": "operator:mina", "action": "policy.update", "outcome": "allowed", "metadata": {"pad": ""}}
        shortfall = MAX_BODY_BYTES - len(json.dumps(base).encode("utf-8"))
        base["metadata"]["pad"] = "x" * shortfall
        body = json.dumps(base).encode("utf-8")
        self.assertEqual(len(body), MAX_BODY_BYTES)

        conn = self._connect()
        conn.request("POST", "/v2/entries", body=body, headers=self._auth_headers())
        response = conn.getresponse()
        self.assertEqual(response.status, 201)
        response.read()

    # -- authentication refusal -------------------------------------------

    def test_post_v1_entries_without_bearer_is_rejected(self) -> None:
        conn = self._connect()
        conn.request("POST", "/v1/entries", body=b"{}")
        response = conn.getresponse()
        self.assertEqual(response.status, 401)
        response.read()
        self.assertEqual(self.fake.record_calls, [])

    def test_get_v1_entries_without_bearer_is_rejected(self) -> None:
        conn = self._connect()
        conn.request("GET", "/v1/entries")
        response = conn.getresponse()
        self.assertEqual(response.status, 401)
        response.read()

    def test_get_v1_integrity_with_wrong_bearer_is_rejected(self) -> None:
        conn = self._connect()
        conn.request("GET", "/v1/integrity", headers=self._auth_headers("not-the-token"))
        response = conn.getresponse()
        self.assertEqual(response.status, 401)
        response.read()

    def test_health_ignores_bearer_requirement_entirely(self) -> None:
        # /health has no bearer requirement at all; a bad token must not matter.
        conn = self._connect()
        conn.request("GET", "/health", headers=self._auth_headers("garbage"))
        response = conn.getresponse()
        self.assertEqual(response.status, 200)
        response.read()

    # -- unknown paths ------------------------------------------------------

    def test_unknown_path_returns_404(self) -> None:
        conn = self._connect()
        conn.request("GET", "/nope")
        response = conn.getresponse()
        self.assertEqual(response.status, 404)
        response.read()

    def test_unknown_path_returns_404_even_with_bearer(self) -> None:
        conn = self._connect()
        conn.request("GET", "/nope", headers=self._auth_headers())
        response = conn.getresponse()
        self.assertEqual(response.status, 404)
        response.read()

    def test_registered_path_with_unregistered_method_returns_404(self) -> None:
        # /health only registers GET; POST to it is an unknown route, not a
        # method-not-allowed distinction the table draws.
        conn = self._connect()
        conn.request("POST", "/health", body=b"")
        response = conn.getresponse()
        self.assertEqual(response.status, 404)
        response.read()

    # -- bounded bodies -------------------------------------------------------

    def test_oversized_body_is_rejected_and_never_recorded(self) -> None:
        conn = self._connect()
        oversized = b"x" * (MAX_BODY_BYTES + 1)
        conn.request("POST", "/v1/entries", body=oversized, headers=self._auth_headers())
        response = conn.getresponse()
        self.assertEqual(response.status, 413)
        response.read()
        self.assertEqual(self.fake.record_calls, [])

    def test_body_at_the_limit_is_accepted(self) -> None:
        base = {"actor": "operator:mina", "action": "policy.update", "outcome": "allowed", "metadata": {"pad": ""}}
        shortfall = MAX_BODY_BYTES - len(json.dumps(base).encode("utf-8"))
        base["metadata"]["pad"] = "x" * shortfall
        body = json.dumps(base).encode("utf-8")
        self.assertEqual(len(body), MAX_BODY_BYTES)

        conn = self._connect()
        conn.request("POST", "/v1/entries", body=body, headers=self._auth_headers())
        response = conn.getresponse()
        self.assertEqual(response.status, 201)
        response.read()

    def test_post_without_content_length_is_rejected(self) -> None:
        # Send a raw request with no Content-Length header at all: the
        # bound check must reject it rather than block reading an unbounded
        # body.
        import socket

        with socket.create_connection((LOOPBACK_HOST, self.port), timeout=5) as sock:
            request = (
                "POST /v1/entries HTTP/1.1\r\n"
                f"Host: {LOOPBACK_HOST}\r\n"
                f"Authorization: Bearer {BEARER_TOKEN}\r\n"
                "Connection: close\r\n"
                "\r\n"
            )
            sock.sendall(request.encode("ascii"))
            response = sock.recv(4096).decode("iso-8859-1")
        self.assertIn("411", response.split("\r\n", 1)[0])
        self.assertEqual(self.fake.record_calls, [])


if __name__ == "__main__":
    unittest.main()
