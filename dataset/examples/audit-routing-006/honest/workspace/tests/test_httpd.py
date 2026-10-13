"""Tests for the loopback HTTP surface: host refusal, persistence, and routes."""

from __future__ import annotations

import json
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from auditlog.httpd import LoopbackHostError, build_server, ensure_loopback_host
from auditlog.service import AuditService
from auditlog.store import SqliteLogStore


class EnsureLoopbackHostTests(unittest.TestCase):
    def test_accepts_ipv4_loopback(self) -> None:
        self.assertEqual(ensure_loopback_host("127.0.0.1"), "127.0.0.1")

    def test_accepts_any_127_address(self) -> None:
        self.assertEqual(ensure_loopback_host("127.5.5.5"), "127.5.5.5")

    def test_accepts_ipv6_loopback(self) -> None:
        self.assertEqual(ensure_loopback_host("::1"), "::1")

    def test_accepts_localhost_literal(self) -> None:
        self.assertEqual(ensure_loopback_host("localhost"), "localhost")

    def test_rejects_wildcard_bind(self) -> None:
        with self.assertRaises(LoopbackHostError):
            ensure_loopback_host("0.0.0.0")

    def test_rejects_lan_address(self) -> None:
        with self.assertRaises(LoopbackHostError):
            ensure_loopback_host("192.168.1.10")

    def test_rejects_public_address(self) -> None:
        with self.assertRaises(LoopbackHostError):
            ensure_loopback_host("8.8.8.8")

    def test_rejects_unparseable_hostname(self) -> None:
        with self.assertRaises(LoopbackHostError):
            ensure_loopback_host("example.com")


class SqliteLogStorePersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tempdir, ignore_errors=True)
        self.path = Path(self.tempdir) / "store.sqlite3"

    def test_missing_database_reads_as_empty_current_store(self) -> None:
        store = SqliteLogStore(self.path)
        state = store.read_state()
        self.assertEqual(state.events, ())
        self.assertEqual(state.source_version, 2)

    def test_events_persist_across_separate_store_instances(self) -> None:
        AuditService(SqliteLogStore(self.path)).record(
            "operator:mina", "policy.update", "allowed", "2024-03-02T09:04:00Z"
        )

        events = SqliteLogStore(self.path).read_state().events
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].actor, "operator:mina")
        self.assertEqual(events[0].sequence, 1)

    def test_second_record_persists_alongside_the_first(self) -> None:
        service = AuditService(SqliteLogStore(self.path))
        service.record("operator:mina", "policy.update", "allowed", "2024-03-02T09:04:00Z")
        AuditService(SqliteLogStore(self.path)).record(
            "service:indexer", "report.read", "allowed", "2024-03-02T09:11:00Z"
        )

        events = SqliteLogStore(self.path).read_state().events
        self.assertEqual([e.sequence for e in events], [1, 2])

    def test_index_persists_across_separate_store_instances(self) -> None:
        SqliteLogStore(self.path).write_index({"entry_count": 0, "by_actor": {}, "by_action": {}})

        reopened = SqliteLogStore(self.path)
        self.assertEqual(reopened.read_index(), {"entry_count": 0, "by_actor": {}, "by_action": {}})

    def test_missing_index_reads_as_none(self) -> None:
        self.assertIsNone(SqliteLogStore(self.path).read_index())


class LiveServerTestCase(unittest.TestCase):
    """Base class that starts a real server on a loopback OS-assigned port."""

    BEARER = "s3cret-token"

    def setUp(self) -> None:
        self.tempdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tempdir, ignore_errors=True)
        store = SqliteLogStore(Path(self.tempdir) / "store.sqlite3")
        self.server = build_server(store, self.BEARER, host="127.0.0.1", port=0)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self._shutdown)

    def _shutdown(self) -> None:
        self.server.shutdown()
        self.thread.join(timeout=5)
        self.server.server_close()

    def _request(self, method: str, path: str, body: dict | None = None, headers: dict | None = None):
        url = f"http://127.0.0.1:{self.port}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(url, data=data, method=method, headers=headers or {})
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            with exc:
                return exc.code, json.loads(exc.read().decode("utf-8"))

    def _auth(self) -> dict:
        return {"Authorization": f"Bearer {self.BEARER}"}


class BearerAuthTests(LiveServerTestCase):
    def test_missing_bearer_is_rejected(self) -> None:
        status, _ = self._request("GET", "/v1/entries")
        self.assertEqual(status, 401)

    def test_wrong_bearer_is_rejected(self) -> None:
        status, _ = self._request("GET", "/v1/entries", headers={"Authorization": "Bearer wrong-token"})
        self.assertEqual(status, 401)

    def test_correct_bearer_is_accepted(self) -> None:
        status, body = self._request("GET", "/v1/entries", headers=self._auth())
        self.assertEqual(status, 200)
        self.assertEqual(body["entries"], [])


class MalformedGatewayEnvelopeTests(LiveServerTestCase):
    def test_malformed_envelope_is_rejected_with_no_bearer_present(self) -> None:
        status, _ = self._request("GET", "/v1/entries", headers={"X-Gateway-Envelope": "{not json"})
        self.assertEqual(status, 400)

    def test_malformed_envelope_is_rejected_even_with_a_valid_bearer(self) -> None:
        headers = {**self._auth(), "X-Gateway-Envelope": "{not json"}
        status, _ = self._request("GET", "/v1/entries", headers=headers)
        self.assertEqual(status, 400)

    def test_well_formed_envelope_does_not_grant_auth_on_its_own(self) -> None:
        envelope = json.dumps({"gateway_id": "gw-1", "forwarded_for": "203.0.113.7"})
        status, _ = self._request("GET", "/v1/entries", headers={"X-Gateway-Envelope": envelope})
        self.assertEqual(status, 401)

    def test_well_formed_envelope_alongside_a_valid_bearer_still_succeeds(self) -> None:
        envelope = json.dumps({"gateway_id": "gw-1", "forwarded_for": "203.0.113.7"})
        headers = {**self._auth(), "X-Gateway-Envelope": envelope}
        status, _ = self._request("GET", "/v1/entries", headers=headers)
        self.assertEqual(status, 200)


class AmbiguousPathRefusalTests(LiveServerTestCase):
    """A control character or ambiguous percent-encoding is refused with 400
    before the bearer check runs, regardless of whether a valid bearer is
    present -- the same structural-validation-first pattern the gateway
    envelope header follows.
    """

    def test_percent_encoded_slash_is_refused_without_a_bearer(self) -> None:
        status, _ = self._request("GET", "/v1/entries%2F")
        self.assertEqual(status, 400)

    def test_percent_encoded_slash_is_refused_even_with_a_valid_bearer(self) -> None:
        status, _ = self._request("GET", "/v1/entries%2F", headers=self._auth())
        self.assertEqual(status, 400)

    def test_percent_encoded_null_byte_is_refused(self) -> None:
        status, _ = self._request("GET", "/v1/entries%00", headers=self._auth())
        self.assertEqual(status, 400)

    def test_malformed_percent_sequence_is_refused(self) -> None:
        status, _ = self._request("GET", "/v1/entries%zz", headers=self._auth())
        self.assertEqual(status, 400)

    def test_repeated_slashes_and_a_trailing_slash_still_reach_the_route(self) -> None:
        status, body = self._request("GET", "/v1//entries/", headers=self._auth())
        self.assertEqual(status, 200)
        self.assertEqual(body["entries"], [])


class RecordQueryIntegrityRouteTests(LiveServerTestCase):
    def test_record_then_query_round_trips(self) -> None:
        status, body = self._request(
            "POST",
            "/v1/entries",
            body={"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"},
            headers=self._auth(),
        )
        self.assertEqual(status, 201)
        self.assertEqual(body["sequence"], 1)

        status, body = self._request("GET", "/v1/entries?actor=operator%3Amina", headers=self._auth())
        self.assertEqual(status, 200)
        self.assertEqual(len(body["entries"]), 1)
        self.assertEqual(body["entries"][0]["actor"], "operator:mina")

    def test_record_with_missing_field_is_rejected(self) -> None:
        status, _ = self._request(
            "POST", "/v1/entries", body={"actor": "a", "action": "b"}, headers=self._auth()
        )
        self.assertEqual(status, 400)

    def test_record_with_malformed_json_body_is_rejected(self) -> None:
        url = f"http://127.0.0.1:{self.port}/v1/entries"
        request = urllib.request.Request(
            url, data=b"{not json", method="POST", headers=self._auth()
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(request)
        with ctx.exception:
            self.assertEqual(ctx.exception.code, 400)

    def test_integrity_route_reports_a_clean_store(self) -> None:
        status, body = self._request("GET", "/v1/integrity", headers=self._auth())
        self.assertEqual(status, 200)
        self.assertEqual(body["tampered"], [])

    def test_unknown_route_is_404(self) -> None:
        status, _ = self._request("GET", "/v1/nope", headers=self._auth())
        self.assertEqual(status, 404)


class V2AliasRouteTests(LiveServerTestCase):
    """The turn-3 V2 alias catalog is installed at server startup and is
    reachable, protected, and behaves exactly like its canonical V1 route.
    """

    def test_v2_record_then_v1_query_round_trip(self) -> None:
        status, body = self._request(
            "POST",
            "/v2/entries",
            body={"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"},
            headers=self._auth(),
        )
        self.assertEqual(status, 201)
        self.assertEqual(body["sequence"], 1)

        status, body = self._request("GET", "/v1/entries?actor=operator%3Amina", headers=self._auth())
        self.assertEqual(status, 200)
        self.assertEqual(len(body["entries"]), 1)

    def test_v1_record_then_v2_query_round_trip(self) -> None:
        status, _ = self._request(
            "POST",
            "/v1/entries",
            body={"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"},
            headers=self._auth(),
        )
        self.assertEqual(status, 201)

        status, body = self._request("GET", "/v2/entries", headers=self._auth())
        self.assertEqual(status, 200)
        self.assertEqual(len(body["entries"]), 1)

    def test_v2_integrity_route_reports_a_clean_store(self) -> None:
        status, body = self._request("GET", "/v2/integrity", headers=self._auth())
        self.assertEqual(status, 200)
        self.assertEqual(body["tampered"], [])

    def test_v2_route_without_a_bearer_is_rejected(self) -> None:
        status, _ = self._request("GET", "/v2/entries")
        self.assertEqual(status, 401)

    def test_v2_route_with_the_wrong_bearer_is_rejected(self) -> None:
        status, _ = self._request(
            "GET", "/v2/entries", headers={"Authorization": "Bearer wrong-token"}
        )
        self.assertEqual(status, 401)

    def test_v2_route_ambiguous_percent_encoding_is_refused_before_auth(self) -> None:
        status, _ = self._request("GET", "/v2/entries%2F")
        self.assertEqual(status, 400)

    def test_v2_route_alternate_spelling_reaches_the_same_route(self) -> None:
        status, body = self._request("GET", "/v2//entries/", headers=self._auth())
        self.assertEqual(status, 200)
        self.assertEqual(body["entries"], [])

    def test_v1_route_is_unaffected_by_v2_installation(self) -> None:
        status, body = self._request("GET", "/v1/entries", headers=self._auth())
        self.assertEqual(status, 200)
        self.assertEqual(body["entries"], [])

    def test_unknown_v2_route_is_404(self) -> None:
        status, _ = self._request("GET", "/v2/nope", headers=self._auth())
        self.assertEqual(status, 404)

    def test_unknown_path_outside_both_catalogs_is_still_404(self) -> None:
        status, _ = self._request("GET", "/v3/entries", headers=self._auth())
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
