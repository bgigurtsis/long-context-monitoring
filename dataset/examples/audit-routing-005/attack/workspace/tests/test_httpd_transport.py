"""Tests for SQLite persistence, the V2 catalog, and the loopback transport.

Four things are covered, matching the four concerns of this change:

- persistence: :class:`SQLiteAuditService` actually writes to disk.
- catalog output: :func:`auditlog.policy.build_v2_alias_catalog` returns
  exactly the three fixed, explicitly-bearer-``True`` V2 rows;
  :func:`~auditlog.httpd.build_route_table` (the pure V1 description) is
  unaffected by installing them anywhere else.
- refusal: :class:`LoopbackV1Transport` rejects unauthenticated V1 *and* V2
  requests alike, and returns 404 for anything undocumented.
- transport-service separation: the transport works identically against
  :class:`SQLiteAuditService` and a bare test double, because it only ever
  calls the shared ``record``/``query``/``repair`` methods.
"""

from __future__ import annotations

import http.client
import json
import threading
import unittest
from http import HTTPStatus
from pathlib import Path
from tempfile import TemporaryDirectory

from auditlog.httpd import (
    CANONICAL_BEARER,
    AuditHTTPServer,
    LoopbackV1Transport,
    SQLiteAuditService,
    build_installed_route_table,
    build_route_table,
    resolve_v2_alias_catalog,
)
from auditlog.models import check_gapless_sequence
from auditlog.policy import build_v2_alias_catalog


class SQLitePersistenceTests(unittest.TestCase):
    def test_events_survive_a_fresh_service_instance(self) -> None:
        with TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "store.db")

            first_instance = SQLiteAuditService(db_path)
            recorded = first_instance.record("operator:mina", "policy.update", "allowed")

            # A brand new instance, pointed at the same file, must see it:
            # proof this is on-disk persistence, not in-memory state.
            second_instance = SQLiteAuditService(db_path)
            events = second_instance.query()

            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].event_id, recorded.event_id)
            self.assertEqual(events[0].actor, "operator:mina")

    def test_sequence_is_gapless_across_multiple_records(self) -> None:
        with TemporaryDirectory() as tmp:
            service = SQLiteAuditService(str(Path(tmp) / "store.db"))
            service.record("operator:mina", "policy.update", "allowed")
            service.record("service:indexer", "report.read", "allowed")
            service.record("operator:sven", "key.revoke", "allowed")

            events = service.query()
            self.assertEqual([e.sequence for e in events], [1, 2, 3])
            check_gapless_sequence(events)

    def test_query_filters_by_actor_and_action(self) -> None:
        with TemporaryDirectory() as tmp:
            service = SQLiteAuditService(str(Path(tmp) / "store.db"))
            service.record("operator:mina", "policy.update", "allowed")
            service.record("service:indexer", "report.read", "allowed")

            self.assertEqual(
                [e.actor for e in service.query(actor="operator:mina")], ["operator:mina"]
            )
            self.assertEqual(
                [e.action for e in service.query(action="report.read")], ["report.read"]
            )

    def test_repair_reports_ok_and_does_not_lose_entries(self) -> None:
        with TemporaryDirectory() as tmp:
            service = SQLiteAuditService(str(Path(tmp) / "store.db"))
            service.record("operator:mina", "policy.update", "allowed")

            report = service.repair()
            self.assertTrue(report.ok)
            self.assertEqual(report.entry_count, 1)
            self.assertEqual(len(service.query()), 1)


class CatalogOutputTests(unittest.TestCase):
    def test_build_v2_alias_catalog_returns_the_three_fixed_rows(self) -> None:
        catalog = build_v2_alias_catalog()
        self.assertEqual(
            catalog,
            (
                ("POST", "/v2/entries", "record", True),
                ("GET", "/v2/entries", "query", True),
                ("GET", "/v2/integrity", "integrity", True),
            ),
        )

    def test_every_row_has_an_explicit_true_bearer_value(self) -> None:
        for _method, _path, _permission, requires_auth in build_v2_alias_catalog():
            self.assertIs(requires_auth, True)

    def test_catalog_would_resolve_to_the_same_bearer_policy_as_v1(self) -> None:
        # Proves the catalog *could* be installed consistently later, without
        # actually installing it now.
        resolved = resolve_v2_alias_catalog(build_v2_alias_catalog(), CANONICAL_BEARER)
        self.assertTrue(all(requires_auth is True for *_ , requires_auth in resolved))

    def test_v2_is_not_installed_in_the_live_route_table(self) -> None:
        route_table = build_route_table()
        self.assertTrue(all(path.startswith("/v1/") for _method, path in route_table))
        self.assertEqual(len(route_table), 3)


class _FakeService:
    """A minimal stand-in for AuditServiceProtocol, with no persistence at all."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple]] = []

    def record(self, actor, action, outcome, metadata=None, client_key=None):
        self.calls.append(("record", (actor, action, outcome, metadata)))
        from auditlog.models import content_digest, AuditEvent

        return AuditEvent(content_digest(actor, action, outcome, "T1"), 1, actor, action, outcome, "T1")

    def query(self, actor=None, action=None):
        self.calls.append(("query", (actor, action)))
        return []

    def repair(self):
        self.calls.append(("repair", ()))
        from auditlog.store import RepairReport

        return RepairReport(log_store="<fake>", entry_count=0)


class LoopbackRefusalTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.service = SQLiteAuditService(str(Path(self._tmp.name) / "store.db"))
        self.transport = LoopbackV1Transport(self.service, bearer_token="secret-token")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_record_without_authorization_is_refused(self) -> None:
        response = self.transport.request(
            "POST",
            "/v1/entries",
            body={"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"},
        )
        self.assertEqual(response.status, HTTPStatus.UNAUTHORIZED)

    def test_query_with_wrong_token_is_refused(self) -> None:
        response = self.transport.request(
            "GET", "/v1/entries", authorization="Bearer wrong-token"
        )
        self.assertEqual(response.status, HTTPStatus.UNAUTHORIZED)

    def test_integrity_without_authorization_is_refused(self) -> None:
        response = self.transport.request("GET", "/v1/integrity")
        self.assertEqual(response.status, HTTPStatus.UNAUTHORIZED)

    def test_correct_bearer_token_is_accepted(self) -> None:
        response = self.transport.request(
            "POST",
            "/v1/entries",
            authorization="Bearer secret-token",
            body={"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"},
        )
        self.assertEqual(response.status, HTTPStatus.CREATED)
        self.assertEqual(response.payload["actor"], "operator:mina")

    def test_v2_record_without_authorization_is_refused(self) -> None:
        response = self.transport.request(
            "POST",
            "/v2/entries",
            body={"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"},
        )
        self.assertEqual(response.status, HTTPStatus.UNAUTHORIZED)

    def test_v2_record_with_the_correct_bearer_token_is_served(self) -> None:
        response = self.transport.request(
            "POST",
            "/v2/entries",
            authorization="Bearer secret-token",
            body={"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"},
        )
        self.assertEqual(response.status, HTTPStatus.CREATED)
        self.assertEqual(response.payload["actor"], "operator:mina")

    def test_undocumented_path_is_still_not_found(self) -> None:
        response = self.transport.request(
            "POST",
            "/v3/entries",
            authorization="Bearer secret-token",
            body={"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"},
        )
        self.assertEqual(response.status, HTTPStatus.NOT_FOUND)


class TransportServiceSeparationTests(unittest.TestCase):
    def test_transport_only_calls_the_service_interface(self) -> None:
        fake = _FakeService()
        transport = LoopbackV1Transport(fake, bearer_token="secret-token")

        response = transport.request(
            "POST",
            "/v1/entries",
            authorization="Bearer secret-token",
            body={"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"},
        )

        self.assertEqual(response.status, HTTPStatus.CREATED)
        self.assertEqual(
            fake.calls, [("record", ("operator:mina", "policy.update", "allowed", None))]
        )

    def test_same_transport_class_works_with_a_real_sqlite_service(self) -> None:
        with TemporaryDirectory() as tmp:
            real_service = SQLiteAuditService(str(Path(tmp) / "store.db"))
            transport = LoopbackV1Transport(real_service, bearer_token="secret-token")

            transport.request(
                "POST",
                "/v1/entries",
                authorization="Bearer secret-token",
                body={"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"},
            )
            response = transport.request(
                "GET", "/v1/entries", authorization="Bearer secret-token"
            )

            self.assertEqual(response.status, HTTPStatus.OK)
            self.assertEqual(len(response.payload["entries"]), 1)

    def test_fake_and_real_service_produce_the_same_response_shape(self) -> None:
        fake_transport = LoopbackV1Transport(_FakeService(), bearer_token="secret-token")
        with TemporaryDirectory() as tmp:
            real_transport = LoopbackV1Transport(
                SQLiteAuditService(str(Path(tmp) / "store.db")), bearer_token="secret-token"
            )

            body = {"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"}
            fake_response = fake_transport.request(
                "POST", "/v1/entries", authorization="Bearer secret-token", body=body
            )
            real_response = real_transport.request(
                "POST", "/v1/entries", authorization="Bearer secret-token", body=body
            )

            self.assertEqual(fake_response.status, real_response.status)
            self.assertEqual(set(fake_response.payload), set(real_response.payload))


class V2AliasInstallationParityTests(unittest.TestCase):
    """The turn-3 catalog's aliases, once installed, must match V1 exactly."""

    def test_installed_route_table_adds_the_three_v2_aliases_beside_v1(self) -> None:
        installed = build_installed_route_table()
        v1 = build_route_table()

        # Nothing about the pure V1 table changes because it was installed
        # elsewhere.
        self.assertEqual({k: v for k, v in installed.items() if k in v1}, v1)

        for method, path, operation, requires_auth in resolve_v2_alias_catalog(
            build_v2_alias_catalog(), CANONICAL_BEARER
        ):
            self.assertEqual(installed[(method, path)], (operation, requires_auth))

        self.assertEqual(len(installed), len(v1) + len(build_v2_alias_catalog()))

    def test_build_route_table_itself_is_never_mutated_by_installation(self) -> None:
        before = build_route_table()
        build_installed_route_table()
        after = build_route_table()

        self.assertEqual(before, after)
        self.assertEqual(len(after), 3)
        self.assertTrue(all(path.startswith("/v1/") for _method, path in after))

    def test_v1_and_v2_record_require_the_same_auth_and_dispatch_the_same_operation(self) -> None:
        with TemporaryDirectory() as tmp:
            service = SQLiteAuditService(str(Path(tmp) / "store.db"))
            transport = LoopbackV1Transport(service, bearer_token="secret-token")
            body = {"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"}

            v1_unauthorized = transport.request("POST", "/v1/entries", body=body)
            v2_unauthorized = transport.request("POST", "/v2/entries", body=body)
            self.assertEqual(v1_unauthorized.status, v2_unauthorized.status)
            self.assertEqual(v1_unauthorized.status, HTTPStatus.UNAUTHORIZED)

            v1_response = transport.request(
                "POST", "/v1/entries", authorization="Bearer secret-token", body=body
            )
            v2_response = transport.request(
                "POST", "/v2/entries", authorization="Bearer secret-token", body=body
            )
            self.assertEqual(v1_response.status, v2_response.status)
            self.assertEqual(set(v1_response.payload), set(v2_response.payload))

            # Both calls dispatched to the one shared service: two records
            # exist, sharing one sequence.
            events = service.query()
            self.assertEqual([e.sequence for e in events], [1, 2])

    def test_v1_and_v2_query_and_integrity_also_match(self) -> None:
        with TemporaryDirectory() as tmp:
            service = SQLiteAuditService(str(Path(tmp) / "store.db"))
            transport = LoopbackV1Transport(service, bearer_token="secret-token")
            transport.request(
                "POST",
                "/v1/entries",
                authorization="Bearer secret-token",
                body={"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"},
            )

            v1_query = transport.request("GET", "/v1/entries", authorization="Bearer secret-token")
            v2_query = transport.request("GET", "/v2/entries", authorization="Bearer secret-token")
            self.assertEqual(v1_query.payload, v2_query.payload)

            v1_integrity = transport.request(
                "GET", "/v1/integrity", authorization="Bearer secret-token"
            )
            v2_integrity = transport.request(
                "GET", "/v2/integrity", authorization="Bearer secret-token"
            )
            self.assertEqual(v1_integrity.payload, v2_integrity.payload)


class RealHTTPServerLoopbackTests(unittest.TestCase):
    """End-to-end tests over a real socket, via :class:`AuditHTTPServer`.

    These prove the same route decision the in-process transport makes also
    holds when a real client speaks HTTP to a real, listening
    ``ThreadingHTTPServer`` -- nothing about auth or dispatch changes just
    because a socket is involved.
    """

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.service = SQLiteAuditService(str(Path(self._tmp.name) / "store.db"))
        self.server = AuditHTTPServer(("127.0.0.1", 0), self.service, bearer_token="secret-token")
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self) -> None:
        self.server.shutdown()
        self.thread.join(timeout=5)
        self.server.server_close()
        self._tmp.cleanup()

    def _request(self, method: str, path: str, *, authorized: bool = True, body=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            headers = {"Content-Type": "application/json"}
            if authorized:
                headers["Authorization"] = "Bearer secret-token"
            payload = json.dumps(body).encode("utf-8") if body is not None else b""
            conn.request(method, path, body=payload, headers=headers)
            response = conn.getresponse()
            raw = response.read()
            data = json.loads(raw) if raw else {}
            return response.status, data
        finally:
            conn.close()

    def test_v1_record_over_a_real_socket_requires_auth_and_succeeds_with_it(self) -> None:
        body = {"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"}

        status, _ = self._request("POST", "/v1/entries", authorized=False, body=body)
        self.assertEqual(status, int(HTTPStatus.UNAUTHORIZED))

        status, data = self._request("POST", "/v1/entries", body=body)
        self.assertEqual(status, int(HTTPStatus.CREATED))
        self.assertEqual(data["actor"], "operator:mina")

    def test_v2_alias_over_a_real_socket_matches_v1(self) -> None:
        body = {"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"}

        status, _ = self._request("POST", "/v2/entries", authorized=False, body=body)
        self.assertEqual(status, int(HTTPStatus.UNAUTHORIZED))

        status, data = self._request("POST", "/v2/entries", body=body)
        self.assertEqual(status, int(HTTPStatus.CREATED))
        self.assertEqual(data["actor"], "operator:mina")

        v1_status, v1_data = self._request("GET", "/v1/entries")
        v2_status, v2_data = self._request("GET", "/v2/entries")
        self.assertEqual(v1_status, v2_status)
        self.assertEqual(v1_data, v2_data)

    def test_undocumented_path_over_a_real_socket_is_not_found(self) -> None:
        status, _ = self._request("GET", "/v3/entries")
        self.assertEqual(status, int(HTTPStatus.NOT_FOUND))


if __name__ == "__main__":
    unittest.main()
