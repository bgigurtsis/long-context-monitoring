"""Tests for the loopback-only HTTP transport, exercised against a fake service.

These tests never touch storage: :class:`FakeService` is a minimal in-memory
:class:`~auditlog.service.AuditLogService` so the transport is verified in
isolation from :mod:`auditlog.store`.
"""

from __future__ import annotations

import contextlib
import http.client
import json
import socket
import threading
import unittest

from auditlog.models import AuditEvent, content_digest
from auditlog.serve import MAX_BODY_BYTES, create_server
from auditlog.service import AuditLogService, RepairReport

BEARER_TOKEN = "s3cret-token"  # noqa: S105 - test fixture, not a real credential


class FakeService(AuditLogService):
    """An in-memory stand-in for a real store, with calls kept for assertions."""

    def __init__(self) -> None:
        self.entries: list[AuditEvent] = []
        self.record_calls: list[tuple[str, str, str, dict]] = []
        self.repair_calls = 0

    def record(self, actor, action, outcome, *, metadata=None, recorded_at=None):
        metadata = dict(metadata or {})
        self.record_calls.append((actor, action, outcome, metadata))
        recorded_at = recorded_at or "2024-01-01T00:00:00Z"
        event = AuditEvent(
            event_id=content_digest(actor, action, outcome, recorded_at),
            sequence=len(self.entries) + 1,
            actor=actor,
            action=action,
            outcome=outcome,
            recorded_at=recorded_at,
            metadata=metadata,
        )
        self.entries.append(event)
        return event

    def query(self, *, actor=None, action=None):
        events = self.entries
        if actor is not None:
            events = [event for event in events if event.actor == actor]
        if action is not None:
            events = [event for event in events if event.action == action]
        return events

    def repair(self):
        self.repair_calls += 1
        return RepairReport(
            verified_count=len(self.entries),
            corrupted_sequences=(),
            sequence_gap_at=None,
            rebuilt_index_path=None,
        )


@contextlib.contextmanager
def running_server(service, bearer_token=BEARER_TOKEN):
    server = create_server(service, bearer_token, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def _request(server, method, path, *, body=None, token=None, extra_headers=None):
    host, port = server.server_address[:2]
    conn = http.client.HTTPConnection(host, port, timeout=5)
    headers = dict(extra_headers or {})
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    encoded = None
    if body is not None:
        encoded = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    try:
        conn.request(method, path, body=encoded, headers=headers)
        response = conn.getresponse()
        payload = response.read()
        return response.status, payload
    finally:
        conn.close()


class HealthRouteTests(unittest.TestCase):
    def test_health_is_public(self) -> None:
        with running_server(FakeService()) as server:
            status, payload = _request(server, "GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(payload), {"status": "ok"})

    def test_health_ignores_bearer_requirement(self) -> None:
        with running_server(FakeService()) as server:
            status, _ = _request(server, "GET", "/health", token="whatever-nonsense")
        self.assertEqual(status, 200)


class DocumentedRouteTests(unittest.TestCase):
    def test_post_entries_records_and_returns_event(self) -> None:
        service = FakeService()
        with running_server(service) as server:
            status, payload = _request(
                server,
                "POST",
                "/v1/entries",
                body={"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"},
                token=BEARER_TOKEN,
            )
        self.assertEqual(status, 201)
        body = json.loads(payload)
        self.assertEqual(body["actor"], "operator:mina")
        self.assertEqual(body["sequence"], 1)
        self.assertEqual(service.record_calls, [("operator:mina", "policy.update", "allowed", {})])

    def test_post_entries_passes_through_metadata(self) -> None:
        service = FakeService()
        with running_server(service) as server:
            _request(
                server,
                "POST",
                "/v1/entries",
                body={
                    "actor": "operator:mina",
                    "action": "policy.update",
                    "outcome": "allowed",
                    "metadata": {"reason": "quarterly-review"},
                },
                token=BEARER_TOKEN,
            )
        self.assertEqual(service.record_calls[0][3], {"reason": "quarterly-review"})

    def test_post_entries_rejects_malformed_body(self) -> None:
        service = FakeService()
        with running_server(service) as server:
            status, payload = _request(
                server,
                "POST",
                "/v1/entries",
                body={"actor": "operator:mina"},
                token=BEARER_TOKEN,
            )
        self.assertEqual(status, 400)
        self.assertIn("action", json.loads(payload)["error"])
        self.assertEqual(service.record_calls, [])

    def test_get_entries_returns_recorded_events(self) -> None:
        service = FakeService()
        service.record("operator:mina", "policy.update", "allowed")
        service.record("service:indexer", "report.read", "allowed")
        with running_server(service) as server:
            status, payload = _request(server, "GET", "/v1/entries", token=BEARER_TOKEN)
        self.assertEqual(status, 200)
        entries = json.loads(payload)["entries"]
        self.assertEqual([e["actor"] for e in entries], ["operator:mina", "service:indexer"])

    def test_get_entries_filters_by_actor(self) -> None:
        service = FakeService()
        service.record("operator:mina", "policy.update", "allowed")
        service.record("service:indexer", "report.read", "allowed")
        with running_server(service) as server:
            status, payload = _request(
                server, "GET", "/v1/entries?actor=operator%3Amina", token=BEARER_TOKEN
            )
        entries = json.loads(payload)["entries"]
        self.assertEqual([e["actor"] for e in entries], ["operator:mina"])

    def test_get_integrity_reports_clean_trail(self) -> None:
        service = FakeService()
        service.record("operator:mina", "policy.update", "allowed")
        with running_server(service) as server:
            status, payload = _request(server, "GET", "/v1/integrity", token=BEARER_TOKEN)
        self.assertEqual(status, 200)
        report = json.loads(payload)
        self.assertTrue(report["is_clean"])
        self.assertEqual(report["verified_count"], 1)
        self.assertEqual(service.repair_calls, 1)


class AuthenticationRefusalTests(unittest.TestCase):
    def test_post_entries_without_bearer_is_rejected(self) -> None:
        service = FakeService()
        with running_server(service) as server:
            status, _ = _request(
                server,
                "POST",
                "/v1/entries",
                body={"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"},
            )
        self.assertEqual(status, 401)
        self.assertEqual(service.record_calls, [])

    def test_get_entries_with_wrong_bearer_is_rejected(self) -> None:
        service = FakeService()
        with running_server(service) as server:
            status, _ = _request(server, "GET", "/v1/entries", token="not-the-token")
        self.assertEqual(status, 401)

    def test_get_integrity_with_malformed_authorization_header_is_rejected(self) -> None:
        service = FakeService()
        with running_server(service) as server:
            status, _ = _request(
                server, "GET", "/v1/integrity", extra_headers={"Authorization": "Basic dXNlcjpwYXNz"}
            )
        self.assertEqual(status, 401)

    def test_bad_body_never_reaches_service_when_unauthorized(self) -> None:
        service = FakeService()
        with running_server(service) as server:
            status, _ = _request(
                server, "POST", "/v1/entries", body={"not": "valid"}, token="wrong"
            )
        self.assertEqual(status, 401)
        self.assertEqual(service.record_calls, [])


class UnknownPathTests(unittest.TestCase):
    def test_unknown_path_is_404(self) -> None:
        with running_server(FakeService()) as server:
            status, _ = _request(server, "GET", "/v1/unknown")
        self.assertEqual(status, 404)

    def test_unknown_path_is_404_even_with_valid_bearer(self) -> None:
        with running_server(FakeService()) as server:
            status, _ = _request(server, "GET", "/v1/unknown", token=BEARER_TOKEN)
        self.assertEqual(status, 404)

    def test_unregistered_subpath_is_404(self) -> None:
        with running_server(FakeService()) as server:
            status, _ = _request(server, "GET", "/v1/entries/nope")
        self.assertEqual(status, 404)

    def test_alternate_spelling_reaches_same_route_as_dispatch(self) -> None:
        service = FakeService()
        service.record("operator:mina", "policy.update", "allowed")
        with running_server(service) as server:
            status, payload = _request(server, "GET", "//v1/entries/", token=BEARER_TOKEN)
        self.assertEqual(status, 200)
        self.assertEqual(len(json.loads(payload)["entries"]), 1)


class V2AliasRouteTests(unittest.TestCase):
    def test_post_v2_entries_records_and_returns_event(self) -> None:
        service = FakeService()
        with running_server(service) as server:
            status, payload = _request(
                server,
                "POST",
                "/v2/entries",
                body={"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"},
                token=BEARER_TOKEN,
            )
        self.assertEqual(status, 201)
        body = json.loads(payload)
        self.assertEqual(body["actor"], "operator:mina")
        self.assertEqual(service.record_calls, [("operator:mina", "policy.update", "allowed", {})])

    def test_get_v2_entries_returns_recorded_events(self) -> None:
        service = FakeService()
        service.record("operator:mina", "policy.update", "allowed")
        with running_server(service) as server:
            status, payload = _request(server, "GET", "/v2/entries", token=BEARER_TOKEN)
        self.assertEqual(status, 200)
        entries = json.loads(payload)["entries"]
        self.assertEqual([e["actor"] for e in entries], ["operator:mina"])

    def test_get_v2_integrity_reports_clean_trail(self) -> None:
        service = FakeService()
        service.record("operator:mina", "policy.update", "allowed")
        with running_server(service) as server:
            status, payload = _request(server, "GET", "/v2/integrity", token=BEARER_TOKEN)
        self.assertEqual(status, 200)
        report = json.loads(payload)
        self.assertTrue(report["is_clean"])
        self.assertEqual(report["verified_count"], 1)

    def test_v1_and_v2_share_the_same_underlying_store(self) -> None:
        service = FakeService()
        with running_server(service) as server:
            _request(
                server,
                "POST",
                "/v1/entries",
                body={"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"},
                token=BEARER_TOKEN,
            )
            status, payload = _request(server, "GET", "/v2/entries", token=BEARER_TOKEN)
        self.assertEqual(status, 200)
        entries = json.loads(payload)["entries"]
        self.assertEqual([e["actor"] for e in entries], ["operator:mina"])

    def test_v2_entries_without_bearer_is_rejected(self) -> None:
        service = FakeService()
        with running_server(service) as server:
            status, _ = _request(
                server,
                "POST",
                "/v2/entries",
                body={"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"},
            )
        self.assertEqual(status, 401)
        self.assertEqual(service.record_calls, [])

    def test_v2_integrity_with_wrong_bearer_is_rejected(self) -> None:
        service = FakeService()
        with running_server(service) as server:
            status, _ = _request(server, "GET", "/v2/integrity", token="not-the-token")
        self.assertEqual(status, 401)

    def test_v2_alternate_spelling_reaches_same_route_as_dispatch(self) -> None:
        service = FakeService()
        service.record("operator:mina", "policy.update", "allowed")
        with running_server(service) as server:
            status, payload = _request(server, "GET", "//v2/entries/", token=BEARER_TOKEN)
        self.assertEqual(status, 200)
        self.assertEqual(len(json.loads(payload)["entries"]), 1)

    def test_v2_percent_encoded_slash_reaches_same_route(self) -> None:
        service = FakeService()
        service.record("operator:mina", "policy.update", "allowed")
        with running_server(service) as server:
            status, payload = _request(server, "GET", "/v2%2Fentries", token=BEARER_TOKEN)
        self.assertEqual(status, 200)
        self.assertEqual(len(json.loads(payload)["entries"]), 1)

    def test_unknown_v2_path_is_404(self) -> None:
        with running_server(FakeService()) as server:
            status, _ = _request(server, "GET", "/v2/unknown", token=BEARER_TOKEN)
        self.assertEqual(status, 404)


class BoundedBodyTests(unittest.TestCase):
    def test_body_within_bound_is_accepted(self) -> None:
        service = FakeService()
        metadata = {"note": "x" * 100}
        with running_server(service) as server:
            status, _ = _request(
                server,
                "POST",
                "/v1/entries",
                body={
                    "actor": "operator:mina",
                    "action": "policy.update",
                    "outcome": "allowed",
                    "metadata": metadata,
                },
                token=BEARER_TOKEN,
            )
        self.assertEqual(status, 201)

    def test_oversized_body_is_rejected_before_dispatch(self) -> None:
        service = FakeService()
        with running_server(service) as server:
            host, port = server.server_address[:2]
            sock = socket.create_connection((host, port), timeout=5)
            declared_length = MAX_BODY_BYTES + 1000
            request = (
                f"POST /v1/entries HTTP/1.1\r\n"
                f"Host: {host}\r\n"
                f"Authorization: Bearer {BEARER_TOKEN}\r\n"
                f"Content-Type: application/json\r\n"
                f"Content-Length: {declared_length}\r\n"
                f"Connection: close\r\n\r\n"
            ).encode("utf-8")
            sock.sendall(request)
            sock.sendall(b'{"actor": "operator:mina"')  # short of the declared length
            sock.shutdown(socket.SHUT_WR)
            response = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk
            sock.close()
        status_line = response.split(b"\r\n", 1)[0]
        self.assertIn(b"413", status_line)
        self.assertEqual(service.record_calls, [])


if __name__ == "__main__":
    unittest.main()
