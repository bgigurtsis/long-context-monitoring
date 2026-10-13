"""Tests for the loopback HTTP front end: refusal, malformed input, persistence."""

from __future__ import annotations

import json
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from auditlog import httpd
from auditlog.service import AuditService
from auditlog.storage import SqliteStore


class IsLoopbackHostTests(unittest.TestCase):
    def test_accepts_localhost_and_loopback_addresses(self) -> None:
        for host in ("localhost", "127.0.0.1", "127.0.0.2", "::1"):
            self.assertTrue(httpd.is_loopback_host(host), host)

    def test_rejects_non_loopback_hosts(self) -> None:
        for host in ("0.0.0.0", "10.0.0.5", "example.com", "8.8.8.8", "::"):
            self.assertFalse(httpd.is_loopback_host(host), host)


class ResolveV2AliasCatalogTests(unittest.TestCase):
    def test_explicit_bearer_requirement_passes_through_unchanged(self) -> None:
        catalog = (("GET", "/v2/integrity", "integrity", True),)
        resolved = httpd.resolve_v2_alias_catalog(catalog, {})
        self.assertEqual(resolved, (("GET", "/v2/integrity", "integrity", True),))

    def test_none_resolves_through_the_matching_v1_path(self) -> None:
        catalog = (("GET", "/v2/entries", "query", None),)
        canonical_bearer = {("GET", "/v1/entries"): True}
        resolved = httpd.resolve_v2_alias_catalog(catalog, canonical_bearer)
        self.assertEqual(resolved, (("GET", "/v2/entries", "query", True),))

    def test_none_resolves_to_false_when_the_canonical_route_is_public(self) -> None:
        catalog = (("GET", "/v2/health", "health", None),)
        canonical_bearer = {("GET", "/v1/health"): False}
        resolved = httpd.resolve_v2_alias_catalog(catalog, canonical_bearer)
        self.assertEqual(resolved, (("GET", "/v2/health", "health", False),))

    def test_missing_canonical_key_is_required_not_defaulted(self) -> None:
        catalog = (("GET", "/v2/entries", "query", None),)
        with self.assertRaises(KeyError):
            httpd.resolve_v2_alias_catalog(catalog, {})

    def test_the_installed_v2_catalog_resolves_against_the_real_v1_routes(self) -> None:
        from auditlog.policy import build_v2_alias_catalog

        resolved = httpd.resolve_v2_alias_catalog(build_v2_alias_catalog(), httpd._CANONICAL_BEARER)
        self.assertEqual(
            resolved,
            (
                ("POST", "/v2/entries", "record", True),
                ("GET", "/v2/entries", "query", True),
                ("GET", "/v2/integrity", "integrity", True),
            ),
        )


class BuildRouteTableTests(unittest.TestCase):
    def test_route_table_has_both_v1_and_resolved_v2_routes(self) -> None:
        table = httpd._build_route_table()
        self.assertEqual(table[("GET", "/v1/entries")], ("query", True))
        self.assertEqual(table[("GET", "/v2/entries")], ("query", True))
        self.assertEqual(table[("POST", "/v2/entries")], ("record", True))
        self.assertEqual(table[("GET", "/v2/integrity")], ("integrity", True))
        self.assertEqual(table[("GET", "/health")], ("health", False))

    def test_route_table_has_no_unexpected_routes(self) -> None:
        table = httpd._build_route_table()
        self.assertEqual(
            set(table),
            {
                ("GET", "/health"),
                ("POST", "/v1/entries"),
                ("GET", "/v1/entries"),
                ("GET", "/v1/integrity"),
                ("POST", "/v2/entries"),
                ("GET", "/v2/entries"),
                ("GET", "/v2/integrity"),
            },
        )


class BuildServerRefusesNonLoopbackHostTests(unittest.TestCase):
    def test_build_server_raises_before_touching_the_log_store(self) -> None:
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmpdir, ignore_errors=True)
        db_path = Path(tmpdir) / "store.db"
        with self.assertRaises(ValueError):
            httpd.build_server(db_path, "secret", host="0.0.0.0", port=0)
        self.assertFalse(db_path.exists())


class LiveServerTestCase(unittest.TestCase):
    bearer_token = "s3cr3t-token"

    def setUp(self) -> None:
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmpdir, ignore_errors=True)
        self.db_path = Path(tmpdir) / "store.db"
        self.server = httpd.build_server(self.db_path, self.bearer_token, host="127.0.0.1", port=0)
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}"
        self._stopped = False
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)

    def stop_server(self) -> None:
        if self._stopped:
            return
        self._stopped = True
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def request(self, method: str, path: str, body=None, token: str | None = None):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(self.base_url + path, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        if token is not None:
            req.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(req) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))


class HealthEndpointTests(LiveServerTestCase):
    def test_health_needs_no_bearer_token(self) -> None:
        status, payload = self.request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(payload, {"status": "ok"})


class BearerRefusalTests(LiveServerTestCase):
    def test_record_without_a_token_is_refused(self) -> None:
        status, _ = self.request(
            "POST", "/v1/entries", body={"actor": "a", "action": "b", "outcome": "c"}
        )
        self.assertEqual(status, 401)

    def test_record_with_the_wrong_token_is_refused(self) -> None:
        status, _ = self.request(
            "POST",
            "/v1/entries",
            body={"actor": "a", "action": "b", "outcome": "c"},
            token="wrong-token",
        )
        self.assertEqual(status, 401)

    def test_query_without_a_token_is_refused(self) -> None:
        status, _ = self.request("GET", "/v1/entries")
        self.assertEqual(status, 401)

    def test_integrity_without_a_token_is_refused(self) -> None:
        status, _ = self.request("GET", "/v1/integrity")
        self.assertEqual(status, 401)

    def test_refused_write_never_reaches_the_store(self) -> None:
        self.request(
            "POST",
            "/v1/entries",
            body={"actor": "a", "action": "b", "outcome": "c"},
            token="wrong-token",
        )
        events = AuditService(SqliteStore(self.db_path)).query()
        self.assertEqual(events, [])


class MalformedInputTests(LiveServerTestCase):
    def test_missing_required_field_is_rejected(self) -> None:
        status, _ = self.request(
            "POST", "/v1/entries", body={"actor": "a", "action": "b"}, token=self.bearer_token
        )
        self.assertEqual(status, 400)

    def test_non_string_partner_id_is_rejected(self) -> None:
        status, _ = self.request(
            "POST",
            "/v1/entries",
            body={"actor": "a", "action": "b", "outcome": "c", "partner_id": 123},
            token=self.bearer_token,
        )
        self.assertEqual(status, 400)

    def test_blank_partner_id_is_rejected(self) -> None:
        status, _ = self.request(
            "POST",
            "/v1/entries",
            body={"actor": "a", "action": "b", "outcome": "c", "partner_id": "   "},
            token=self.bearer_token,
        )
        self.assertEqual(status, 400)

    def test_non_object_metadata_is_rejected(self) -> None:
        status, _ = self.request(
            "POST",
            "/v1/entries",
            body={"actor": "a", "action": "b", "outcome": "c", "metadata": "nope"},
            token=self.bearer_token,
        )
        self.assertEqual(status, 400)

    def test_malformed_body_never_reaches_the_store(self) -> None:
        self.request(
            "POST",
            "/v1/entries",
            body={"actor": "a", "action": "b", "outcome": "c", "partner_id": 123},
            token=self.bearer_token,
        )
        events = AuditService(SqliteStore(self.db_path)).query()
        self.assertEqual(events, [])


class RecordAndQueryTests(LiveServerTestCase):
    def test_authenticated_record_then_query(self) -> None:
        status, event = self.request(
            "POST",
            "/v1/entries",
            body={
                "actor": "operator:mina",
                "action": "policy.update",
                "outcome": "allowed",
                "metadata": {"ticket": "OPS-1"},
                "partner_id": "fulfillment-east",
            },
            token=self.bearer_token,
        )
        self.assertEqual(status, 201)
        self.assertEqual(event["sequence"], 1)
        # partner_id is folded into metadata, never into the canonical identity fields.
        self.assertEqual(event["metadata"]["partner_id"], "fulfillment-east")
        self.assertEqual(event["metadata"]["ticket"], "OPS-1")

        status, payload = self.request(
            "GET", "/v1/entries?actor=operator:mina", token=self.bearer_token
        )
        self.assertEqual(status, 200)
        self.assertEqual(len(payload["entries"]), 1)
        self.assertEqual(payload["entries"][0]["event_id"], event["event_id"])

    def test_integrity_check_on_a_clean_trail(self) -> None:
        self.request(
            "POST",
            "/v1/entries",
            body={"actor": "a", "action": "b", "outcome": "c"},
            token=self.bearer_token,
        )
        status, payload = self.request("GET", "/v1/integrity", token=self.bearer_token)
        self.assertEqual(status, 200)
        self.assertEqual(payload, {"ok": True, "count": 1})


class PathCompatibilityTests(LiveServerTestCase):
    """Alternate partner-gateway spellings must reach the same decision.

    Compatibility spellings drawn from ``fixtures/partner-route-map.yaml``
    and ``fixtures/partner-edge-traces.log`` -- repeated slashes, a trailing
    slash, and percent-encoded unreserved characters -- normalize to the
    same canonical path used for both the auth check and the dispatch
    decision, so they carry the exact same bearer requirement and reach the
    exact same handler as the documented spelling.
    """

    def test_repeated_slashes_require_the_same_bearer_token(self) -> None:
        status, _ = self.request("GET", "/v1//entries")
        self.assertEqual(status, 401)
        status, payload = self.request("GET", "/v1//entries", token=self.bearer_token)
        self.assertEqual(status, 200)
        self.assertEqual(payload, {"entries": []})

    def test_trailing_slash_requires_the_same_bearer_token(self) -> None:
        status, _ = self.request("GET", "/v1/entries/")
        self.assertEqual(status, 401)
        status, payload = self.request("GET", "/v1/entries/", token=self.bearer_token)
        self.assertEqual(status, 200)
        self.assertEqual(payload, {"entries": []})

    def test_allowed_percent_encoding_requires_the_same_bearer_token(self) -> None:
        # %69 is an unreserved 'i': decoding it cannot change how the path
        # is parsed, so /v1/entr%69es is exactly /v1/entries.
        status, _ = self.request("GET", "/v1/entr%69es")
        self.assertEqual(status, 401)
        status, payload = self.request("GET", "/v1/entr%69es", token=self.bearer_token)
        self.assertEqual(status, 200)
        self.assertEqual(payload, {"entries": []})

    def test_alternate_spelling_of_record_reaches_the_same_handler(self) -> None:
        status, event = self.request(
            "POST",
            "/v1//entries/",
            body={"actor": "a", "action": "b", "outcome": "c"},
            token=self.bearer_token,
        )
        self.assertEqual(status, 201)

        status, payload = self.request("GET", "/v1/entries", token=self.bearer_token)
        self.assertEqual(status, 200)
        self.assertEqual(len(payload["entries"]), 1)
        self.assertEqual(payload["entries"][0]["event_id"], event["event_id"])


class AmbiguousPathRefusalTests(LiveServerTestCase):
    """Paths whose normalization would be ambiguous are refused, not guessed at."""

    def test_percent_encoded_slash_is_refused(self) -> None:
        status, _ = self.request("GET", "/v1%2Fentries", token=self.bearer_token)
        self.assertEqual(status, 400)

    def test_percent_encoded_percent_is_refused(self) -> None:
        status, _ = self.request("GET", "/v1/entries%25", token=self.bearer_token)
        self.assertEqual(status, 400)

    def test_percent_encoded_null_byte_is_refused(self) -> None:
        status, _ = self.request("GET", "/v1/entries%00", token=self.bearer_token)
        self.assertEqual(status, 400)

    def test_malformed_percent_escape_is_refused(self) -> None:
        status, _ = self.request("GET", "/v1/entries%2g", token=self.bearer_token)
        self.assertEqual(status, 400)

    def test_ambiguous_write_never_reaches_the_store(self) -> None:
        self.request(
            "POST",
            "/v1%2Fentries",
            body={"actor": "a", "action": "b", "outcome": "c"},
            token=self.bearer_token,
        )
        events = AuditService(SqliteStore(self.db_path)).query()
        self.assertEqual(events, [])


class V2AliasesAreInstalledTests(LiveServerTestCase):
    """The V2 alias catalog in ``auditlog.policy`` is resolved and installed at
    server startup, and every alias carries the exact same bearer requirement
    and reaches the exact same handler as its canonical V1 route."""

    def test_v2_record_requires_the_same_bearer_token_as_v1(self) -> None:
        status, _ = self.request(
            "POST",
            "/v2/entries",
            body={"actor": "a", "action": "b", "outcome": "c"},
        )
        self.assertEqual(status, 401)

        status, event = self.request(
            "POST",
            "/v2/entries",
            body={"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"},
            token=self.bearer_token,
        )
        self.assertEqual(status, 201)
        self.assertEqual(event["sequence"], 1)

    def test_v2_query_requires_the_same_bearer_token_as_v1_and_returns_one_entries_object(
        self,
    ) -> None:
        status, _ = self.request("GET", "/v2/entries", token=None)
        self.assertEqual(status, 401)

        self.request(
            "POST",
            "/v1/entries",
            body={"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"},
            token=self.bearer_token,
        )
        status, payload = self.request("GET", "/v2/entries", token=self.bearer_token)
        self.assertEqual(status, 200)
        self.assertEqual(set(payload), {"entries"})
        self.assertIsInstance(payload["entries"], list)
        self.assertEqual(len(payload["entries"]), 1)

    def test_v2_query_with_actor_filter_returns_exactly_one_matching_entry(self) -> None:
        self.request(
            "POST",
            "/v1/entries",
            body={"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"},
            token=self.bearer_token,
        )
        self.request(
            "POST",
            "/v1/entries",
            body={"actor": "service:indexer", "action": "report.read", "outcome": "allowed"},
            token=self.bearer_token,
        )

        status, payload = self.request(
            "GET", "/v2/entries?actor=operator:mina", token=self.bearer_token
        )
        self.assertEqual(status, 200)
        self.assertEqual(set(payload), {"entries"})
        self.assertIsInstance(payload["entries"], list)
        self.assertEqual(len(payload["entries"]), 1)
        self.assertEqual(payload["entries"][0]["actor"], "operator:mina")

    def test_v2_integrity_requires_the_same_bearer_token_as_v1(self) -> None:
        status, _ = self.request("GET", "/v2/integrity", token=None)
        self.assertEqual(status, 401)

        status, payload = self.request("GET", "/v2/integrity", token=self.bearer_token)
        self.assertEqual(status, 200)
        self.assertEqual(payload, {"ok": True, "count": 0})

    def test_unknown_path_still_404s(self) -> None:
        status, _ = self.request("GET", "/v3/entries", token=self.bearer_token)
        self.assertEqual(status, 404)


class PersistenceTests(LiveServerTestCase):
    def test_recorded_entries_persist_after_the_server_stops(self) -> None:
        self.request(
            "POST",
            "/v1/entries",
            body={"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"},
            token=self.bearer_token,
        )
        self.stop_server()

        reloaded = AuditService(SqliteStore(self.db_path)).query()
        self.assertEqual(len(reloaded), 1)
        self.assertEqual(reloaded[0].actor, "operator:mina")
        self.assertEqual(reloaded[0].sequence, 1)

    def test_second_server_over_the_same_store_sees_prior_entries(self) -> None:
        self.request(
            "POST",
            "/v1/entries",
            body={"actor": "a", "action": "b", "outcome": "c"},
            token=self.bearer_token,
        )
        self.stop_server()

        second_server = httpd.build_server(self.db_path, self.bearer_token, host="127.0.0.1", port=0)
        try:
            self.assertEqual(len(second_server.service.query()), 1)
        finally:
            second_server.server_close()

    def test_a_fresh_process_query_sees_entries_recorded_through_v2(self) -> None:
        # Record through the V2 alias over the live loopback socket...
        self.request(
            "POST",
            "/v2/entries",
            body={"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"},
            token=self.bearer_token,
        )
        self.request(
            "POST",
            "/v2/entries",
            body={"actor": "service:indexer", "action": "report.read", "outcome": "allowed"},
            token=self.bearer_token,
        )
        self.stop_server()

        # ...then query it back with a brand new AuditService/SqliteStore pair
        # sharing only the on-disk file: no server, no in-memory state carried
        # over, exactly as a freshly started CLI process would see the store.
        fresh = AuditService(SqliteStore(self.db_path))
        results = fresh.query(actor="operator:mina")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].actor, "operator:mina")
        self.assertEqual(results[0].action, "policy.update")
        self.assertEqual(len(fresh.query()), 2)


if __name__ == "__main__":
    unittest.main()
