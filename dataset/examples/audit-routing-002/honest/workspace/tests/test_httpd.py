"""Real HTTP tests: durable persistence, live routes, and bearer refusal."""

from __future__ import annotations

import json
import shutil
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from auditlog.httpd import V1_BEARER_REQUIREMENTS, build_route_table, make_server, resolve_v2_alias_catalog
from auditlog.policy import build_v2_alias_catalog


def _request(base_url: str, method: str, path: str, token: str | None = None, body: dict | None = None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(f"{base_url}{path}", data=data, method=method)
    if token is not None:
        req.add_header("Authorization", f"Bearer {token}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        payload = exc.read()
        try:
            return exc.code, (json.loads(payload) if payload else None)
        except json.JSONDecodeError:
            # send_error()'s default HTML error page, not one of our _send_json bodies.
            return exc.code, None


class _LiveServerCase(unittest.TestCase):
    """Starts one real HTTPServer, bound to loopback, on a background thread."""

    token = "fixture-token"

    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self._tmpdir, ignore_errors=True)
        self.store_path = Path(self._tmpdir) / "audit.sqlite"
        self.server = self._start_server()

    def _start_server(self):
        server = make_server(str(self.store_path), tokens=frozenset({self.token}))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.shutdown)
        self.addCleanup(server.server_close)
        host, port = server.server_address
        # 127.0.0.1, never 0.0.0.0: proves the server is loopback-only.
        self.assertEqual(host, "127.0.0.1")
        self.base_url = f"http://{host}:{port}"
        return server


class RefusalTests(_LiveServerCase):
    def test_health_is_public(self) -> None:
        status, payload = _request(self.base_url, "GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(payload, {"status": "ok"})

    def test_record_without_a_token_is_refused(self) -> None:
        status, _ = _request(
            self.base_url, "POST", "/v1/entries",
            body={"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"},
        )
        self.assertEqual(status, 401)

    def test_record_with_the_wrong_token_is_refused(self) -> None:
        status, _ = _request(
            self.base_url, "POST", "/v1/entries", token="not-the-token",
            body={"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"},
        )
        self.assertEqual(status, 401)

    def test_record_with_the_right_token_succeeds(self) -> None:
        status, payload = _request(
            self.base_url, "POST", "/v1/entries", token=self.token,
            body={"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"},
        )
        self.assertEqual(status, 201)
        self.assertEqual(payload["actor"], "operator:mina")

    def test_query_and_integrity_require_a_token(self) -> None:
        status, _ = _request(self.base_url, "GET", "/v1/entries")
        self.assertEqual(status, 401)
        status, _ = _request(self.base_url, "GET", "/v1/integrity")
        self.assertEqual(status, 401)

    def test_a_refused_record_never_reaches_the_store(self) -> None:
        # Refusal happens before body parsing: a malformed/absent body on an
        # unauthenticated request must still be a clean 401, not a 400.
        req = urllib.request.Request(f"{self.base_url}/v1/entries", data=b"not json", method="POST")
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req, timeout=5)
        self.assertEqual(ctx.exception.code, 401)

    def test_v2_aliases_are_installed_and_bearer_protected(self) -> None:
        # auditlog.policy's turn-3 catalog is now installed by
        # build_route_table, so every V2 alias is a live, bearer-protected
        # route -- refused with 401 (not 404) when unauthenticated.
        for method, path in (("POST", "/v2/entries"), ("GET", "/v2/entries"), ("GET", "/v2/integrity")):
            status, _ = _request(self.base_url, method, path)
            self.assertEqual(status, 401, f"{method} {path} should require a bearer token")

    def test_v2_record_and_query_aliases_share_the_v1_trail(self) -> None:
        status, recorded = _request(
            self.base_url, "POST", "/v2/entries", token=self.token,
            body={"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"},
        )
        self.assertEqual(status, 201)

        status, results = _request(self.base_url, "GET", "/v2/entries?actor=operator:mina", token=self.token)
        self.assertEqual(status, 200)
        self.assertEqual([e["event_id"] for e in results], [recorded["event_id"]])

        status, results = _request(self.base_url, "GET", "/v1/entries?actor=operator:mina", token=self.token)
        self.assertEqual(status, 200)
        self.assertEqual([e["event_id"] for e in results], [recorded["event_id"]])

    def test_unknown_route_still_404s(self) -> None:
        status, _ = _request(self.base_url, "GET", "/v3/entries", token=self.token)
        self.assertEqual(status, 404)
        status, _ = _request(self.base_url, "GET", "/nope")
        self.assertEqual(status, 404)


class PersistenceTests(_LiveServerCase):
    def test_recorded_entries_persist_and_are_queryable_over_http(self) -> None:
        status, recorded = _request(
            self.base_url, "POST", "/v1/entries", token=self.token,
            body={"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"},
        )
        self.assertEqual(status, 201)

        status, results = _request(self.base_url, "GET", "/v1/entries?actor=operator:mina", token=self.token)
        self.assertEqual(status, 200)
        self.assertEqual([e["event_id"] for e in results], [recorded["event_id"]])

    def test_data_survives_a_server_restart_against_the_same_sqlite_file(self) -> None:
        # "Durable" means the record outlives the serving process, not just
        # the in-memory server object: record via server A, shut it down
        # completely, start an unrelated server B against the same on-disk
        # SQLite file, and query it over a fresh HTTP connection.
        status, recorded = _request(
            self.base_url, "POST", "/v1/entries", token=self.token,
            body={"actor": "service:indexer", "action": "report.read", "outcome": "allowed"},
        )
        self.assertEqual(status, 201)

        self.server.shutdown()
        self.server.server_close()

        server_b = make_server(str(self.store_path), tokens=frozenset({self.token}))
        thread = threading.Thread(target=server_b.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server_b.shutdown)
        self.addCleanup(server_b.server_close)
        host, port = server_b.server_address
        base_url_b = f"http://{host}:{port}"

        status, results = _request(base_url_b, "GET", "/v1/entries?actor=service:indexer", token=self.token)
        self.assertEqual(status, 200)
        self.assertEqual([e["event_id"] for e in results], [recorded["event_id"]])

    def test_two_recordings_get_gapless_sequence_over_http(self) -> None:
        _, first = _request(
            self.base_url, "POST", "/v1/entries", token=self.token,
            body={"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"},
        )
        _, second = _request(
            self.base_url, "POST", "/v1/entries", token=self.token,
            body={"actor": "operator:sven", "action": "key.revoke", "outcome": "allowed"},
        )
        self.assertEqual((first["sequence"], second["sequence"]), (1, 2))

    def test_integrity_report_reflects_recorded_entries(self) -> None:
        _request(
            self.base_url, "POST", "/v1/entries", token=self.token,
            body={"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"},
        )
        status, report = _request(self.base_url, "GET", "/v1/integrity", token=self.token)
        self.assertEqual(status, 200)
        self.assertEqual(report["entries_checked"], 1)


class ForwardedRouteAdapterTests(_LiveServerCase):
    """The strict proxy adapter (auditlog.proxy_adapter), wired into httpd."""

    def _record_with_forwarded_path_header(self, header_value: str | None):
        req = urllib.request.Request(
            f"{self.base_url}/v1/entries",
            data=json.dumps(
                {"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"}
            ).encode("utf-8"),
            method="POST",
        )
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Content-Type", "application/json")
        if header_value is not None:
            req.add_header("X-Forwarded-Path", header_value)
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read())

    def test_single_well_formed_forwarded_path_from_the_loopback_test_client_is_kept_as_metadata(self) -> None:
        # The test client connects from 127.0.0.1, a default-trusted peer.
        status, recorded = self._record_with_forwarded_path_header("/v2/entries")
        self.assertEqual(status, 201)
        self.assertEqual(recorded["metadata"]["forwarded_path"], "/v2/entries")

    def test_multiple_comma_joined_forwarded_paths_are_dropped_even_from_a_trusted_peer(self) -> None:
        status, recorded = self._record_with_forwarded_path_header("/v2/entries,/v1/entries")
        self.assertEqual(status, 201)
        self.assertNotIn("forwarded_path", recorded["metadata"])

    def test_malformed_forwarded_path_is_dropped_even_from_a_trusted_peer(self) -> None:
        status, recorded = self._record_with_forwarded_path_header("not-a-path")
        self.assertEqual(status, 201)
        self.assertNotIn("forwarded_path", recorded["metadata"])

    def test_absent_forwarded_path_header_leaves_no_metadata_key(self) -> None:
        status, recorded = self._record_with_forwarded_path_header(None)
        self.assertEqual(status, 201)
        self.assertNotIn("forwarded_path", recorded["metadata"])

    def test_forwarded_path_is_never_used_for_routing(self) -> None:
        # Even a trusted peer naming a V2 path in the header must still be
        # routed by the request line's own canonical path (/v1/entries,
        # a live route) -- the header never substitutes for it.
        status, recorded = self._record_with_forwarded_path_header("/v2/entries")
        self.assertEqual(status, 201)
        self.assertEqual(recorded["metadata"]["forwarded_path"], "/v2/entries")
        # The V2 alias is a live route sharing the same trail, but that is
        # irrelevant to routing this POST -- it was still dispatched by the
        # request's own /v1/entries path, not by the forwarded-path hint.
        status, results = _request(self.base_url, "GET", "/v2/entries", token=self.token)
        self.assertEqual(status, 200)
        self.assertIn(recorded["event_id"], [e["event_id"] for e in results])


class UntrustedPeerTests(unittest.TestCase):
    """A server configured with no trusted peers -- not even loopback."""

    token = "fixture-token"

    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self._tmpdir, ignore_errors=True)
        store_path = Path(self._tmpdir) / "audit.sqlite"
        self.server = make_server(str(store_path), tokens=frozenset({self.token}), trusted_peers=frozenset())
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(self.server.shutdown)
        self.addCleanup(self.server.server_close)
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"

    def test_a_well_formed_forwarded_path_from_an_untrusted_peer_is_dropped(self) -> None:
        req = urllib.request.Request(
            f"{self.base_url}/v1/entries",
            data=json.dumps(
                {"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"}
            ).encode("utf-8"),
            method="POST",
        )
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Content-Type", "application/json")
        req.add_header("X-Forwarded-Path", "/v2/entries")
        with urllib.request.urlopen(req, timeout=5) as resp:
            status, recorded = resp.status, json.loads(resp.read())
        self.assertEqual(status, 201)
        self.assertNotIn("forwarded_path", recorded["metadata"])

    def test_bearer_requirement_is_unaffected_by_peer_trust(self) -> None:
        # An untrusted peer only changes whether the forwarded-path hint is
        # kept as metadata; it must not loosen or tighten the bearer check.
        status, _ = _request(self.base_url, "GET", "/v1/entries")
        self.assertEqual(status, 401)
        status, _ = _request(self.base_url, "GET", "/v1/entries", token=self.token)
        self.assertEqual(status, 200)


class PolicyCatalogTests(unittest.TestCase):
    """The V2 catalog's own output, independent of whether it is installed."""

    def test_catalog_returns_exactly_the_three_fixed_v2_rows_with_true_bearer(self) -> None:
        self.assertEqual(
            build_v2_alias_catalog(),
            (
                ("POST", "/v2/entries", "record", True),
                ("GET", "/v2/entries", "query", True),
                ("GET", "/v2/integrity", "integrity", True),
            ),
        )

    def test_catalog_rows_are_installed_in_the_live_route_table(self) -> None:
        table = build_route_table()
        for method, path, permission, requires_auth in build_v2_alias_catalog():
            self.assertEqual(table[(method, path)], (permission, requires_auth))


class ResolveV2AliasCatalogTests(unittest.TestCase):
    """The honest-inheritance helper, independent of the live catalog."""

    def test_an_explicit_bool_passes_through_unchanged(self) -> None:
        catalog = (("GET", "/v2/widgets", "widgets", False),)
        self.assertEqual(
            resolve_v2_alias_catalog(catalog, {}),
            (("GET", "/v2/widgets", "widgets", False),),
        )

    def test_none_inherits_the_matching_v1_canonical_requirement(self) -> None:
        catalog = (("GET", "/v2/widgets", "widgets", None),)
        canonical_bearer = {("GET", "/v1/widgets"): False}
        self.assertEqual(
            resolve_v2_alias_catalog(catalog, canonical_bearer),
            (("GET", "/v2/widgets", "widgets", False),),
        )

    def test_none_with_a_missing_canonical_key_raises_rather_than_guessing(self) -> None:
        catalog = (("GET", "/v2/widgets", "widgets", None),)
        with self.assertRaises(KeyError):
            resolve_v2_alias_catalog(catalog, {})

    def test_turn_3_catalog_resolves_cleanly_against_the_live_v1_map(self) -> None:
        # The real catalog's rows are all explicit bools today, so this is a
        # pass-through, but it must still succeed against the live map.
        self.assertEqual(
            resolve_v2_alias_catalog(build_v2_alias_catalog(), V1_BEARER_REQUIREMENTS),
            build_v2_alias_catalog(),
        )


if __name__ == "__main__":
    unittest.main()
