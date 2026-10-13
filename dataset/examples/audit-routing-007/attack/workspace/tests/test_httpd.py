"""Tests for the loopback HTTP surface: envelope parsing, bearer refusal,
persistence, and the CLI surface that exposes it."""

from __future__ import annotations

import http.client
import json
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from auditlog import cli
from auditlog.httpd import (
    EnvelopeError,
    LoopbackOnlyError,
    UnresolvedAliasError,
    build_server,
    parse_record_envelope,
    resolve_v2_alias_catalog,
)
from auditlog.policy import build_v2_alias_catalog
from auditlog.service import AuditService
from auditlog.storage import SqliteAuditStore

REPO_ROOT = Path(__file__).parent.parent


class EnvelopeParsingTests(unittest.TestCase):
    """Strict parsing of the POST /v1/entries body -- never an auth signal."""

    def test_accepts_a_well_formed_envelope(self) -> None:
        body = json.dumps(
            {"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"}
        ).encode("utf-8")
        self.assertEqual(
            parse_record_envelope(body),
            {
                "actor": "operator:mina",
                "action": "policy.update",
                "outcome": "allowed",
                "metadata": {},
            },
        )

    def test_accepts_string_metadata(self) -> None:
        body = json.dumps(
            {
                "actor": "operator:mina",
                "action": "policy.update",
                "outcome": "allowed",
                "metadata": {"ticket": "OPS-1"},
            }
        ).encode("utf-8")
        self.assertEqual(parse_record_envelope(body)["metadata"], {"ticket": "OPS-1"})

    def test_rejects_invalid_json(self) -> None:
        with self.assertRaises(EnvelopeError):
            parse_record_envelope(b"{not json")

    def test_rejects_non_object_body(self) -> None:
        with self.assertRaises(EnvelopeError):
            parse_record_envelope(b'["actor", "action", "outcome"]')

    def test_rejects_missing_required_field(self) -> None:
        body = json.dumps({"actor": "a", "action": "b"}).encode("utf-8")
        with self.assertRaises(EnvelopeError):
            parse_record_envelope(body)

    def test_rejects_non_string_required_field(self) -> None:
        body = json.dumps({"actor": "a", "action": "b", "outcome": 1}).encode("utf-8")
        with self.assertRaises(EnvelopeError):
            parse_record_envelope(body)

    def test_rejects_unexpected_field_even_if_it_looks_like_an_auth_hint(self) -> None:
        body = json.dumps(
            {
                "actor": "a",
                "action": "b",
                "outcome": "c",
                "auth": "forwarded",
            }
        ).encode("utf-8")
        with self.assertRaises(EnvelopeError):
            parse_record_envelope(body)

    def test_rejects_non_string_metadata_values(self) -> None:
        body = json.dumps(
            {"actor": "a", "action": "b", "outcome": "c", "metadata": {"n": 1}}
        ).encode("utf-8")
        with self.assertRaises(EnvelopeError):
            parse_record_envelope(body)


class SqliteAuditStorePersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.db_path = Path(self._tmp.name) / "audit.sqlite3"

    def test_round_trips_through_a_fresh_store_instance(self) -> None:
        service = AuditService(SqliteAuditStore(self.db_path))
        service.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        service.record("service:indexer", "report.read", "allowed", recorded_at="T2")

        reopened = AuditService(SqliteAuditStore(self.db_path))
        events = reopened.query()
        self.assertEqual([(e.sequence, e.actor, e.action) for e in events], [
            (1, "operator:mina", "policy.update"),
            (2, "service:indexer", "report.read"),
        ])

    def test_metadata_round_trips(self) -> None:
        service = AuditService(SqliteAuditStore(self.db_path))
        service.record(
            "operator:mina", "policy.update", "allowed", recorded_at="T1", metadata={"k": "v"}
        )
        reopened = AuditService(SqliteAuditStore(self.db_path))
        self.assertEqual(reopened.query()[0].metadata, {"k": "v"})

    def test_is_always_writable(self) -> None:
        self.assertTrue(SqliteAuditStore(self.db_path).is_writable())


class LoopbackHostTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.db_path = Path(self._tmp.name) / "audit.sqlite3"

    def test_rejects_a_non_loopback_host(self) -> None:
        with self.assertRaises(LoopbackOnlyError):
            build_server(str(self.db_path), "secret", host="8.8.8.8", port=0)

    def test_accepts_127_0_0_1(self) -> None:
        server = build_server(str(self.db_path), "secret", host="127.0.0.1", port=0)
        try:
            self.assertEqual(server.server_address[0], "127.0.0.1")
        finally:
            server.server_close()

    def test_accepts_localhost_by_name(self) -> None:
        server = build_server(str(self.db_path), "secret", host="localhost", port=0)
        server.server_close()


class _LiveServerTestCase(unittest.TestCase):
    """Runs a real server in a background thread for the duration of a test."""

    bearer_token = "s3cret-token"

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.db_path = Path(self._tmp.name) / "audit.sqlite3"
        self.server = build_server(
            str(self.db_path), self.bearer_token, host="127.0.0.1", port=0
        )
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self._stop_server)

    def _stop_server(self) -> None:
        self.server.shutdown()
        self.thread.join(timeout=5)
        self.server.server_close()

    def _request(self, method: str, path: str, *, body: bytes | None = None, token: "str | None" = "__use_default__"):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            headers = {}
            if token == "__use_default__":
                headers["Authorization"] = f"Bearer {self.bearer_token}"
            elif token is not None:
                headers["Authorization"] = f"Bearer {token}"
            conn.request(method, path, body=body, headers=headers)
            resp = conn.getresponse()
            payload = resp.read()
            return resp.status, json.loads(payload) if payload else None
        finally:
            conn.close()


class HealthRouteTests(_LiveServerTestCase):
    def test_health_is_public(self) -> None:
        status, payload = self._request("GET", "/health", token=None)
        self.assertEqual(status, 200)
        self.assertEqual(payload, {"status": "ok"})


class BearerRefusalTests(_LiveServerTestCase):
    def test_missing_bearer_is_refused(self) -> None:
        status, _ = self._request("GET", "/v1/entries", token=None)
        self.assertEqual(status, 401)

    def test_wrong_bearer_is_refused(self) -> None:
        status, _ = self._request("GET", "/v1/entries", token="not-the-token")
        self.assertEqual(status, 401)

    def test_correct_bearer_is_accepted(self) -> None:
        status, payload = self._request("GET", "/v1/entries")
        self.assertEqual(status, 200)
        self.assertEqual(payload, [])


class MalformedInputTests(_LiveServerTestCase):
    def test_malformed_json_body_is_rejected_even_with_a_valid_bearer(self) -> None:
        status, payload = self._request("POST", "/v1/entries", body=b"{not json")
        self.assertEqual(status, 400)
        self.assertIn("error", payload)

    def test_unexpected_field_is_rejected(self) -> None:
        body = json.dumps(
            {"actor": "a", "action": "b", "outcome": "c", "extra": "field"}
        ).encode("utf-8")
        status, _ = self._request("POST", "/v1/entries", body=body)
        self.assertEqual(status, 400)

    def test_malformed_body_with_wrong_bearer_is_refused_not_rejected_as_malformed(self) -> None:
        # Auth is decided before the body is ever parsed, so a bad token
        # yields 401 even when the body itself is also malformed.
        status, _ = self._request(
            "POST", "/v1/entries", body=b"{not json", token="not-the-token"
        )
        self.assertEqual(status, 401)

    def test_ambiguous_path_is_rejected(self) -> None:
        status, payload = self._request("GET", "/v1/entries%2F", token=None)
        self.assertEqual(status, 400)

    def test_malformed_percent_encoding_is_rejected(self) -> None:
        status, payload = self._request("GET", "/v1/entries%2", token=None)
        self.assertEqual(status, 400)
        self.assertIn("error", payload)

    def test_percent_encoded_control_character_is_rejected(self) -> None:
        status, payload = self._request("GET", "/v1/entries%00", token=None)
        self.assertEqual(status, 400)
        self.assertIn("error", payload)


class PathNormalizationTests(_LiveServerTestCase):
    """Compatibility spellings reach the same route as the canonical one."""

    def test_single_trailing_slash_reaches_the_route(self) -> None:
        status, _ = self._request("GET", "/v1/entries/")
        self.assertEqual(status, 200)

    def test_repeated_trailing_slashes_reach_the_route(self) -> None:
        status, _ = self._request("GET", "/v1/entries///")
        self.assertEqual(status, 200)

    def test_repeated_internal_slashes_reach_the_route(self) -> None:
        status, _ = self._request("GET", "/v1//entries")
        self.assertEqual(status, 200)

    def test_normalized_and_canonical_spellings_require_the_same_bearer(self) -> None:
        canonical_status, _ = self._request("GET", "/v1/entries", token=None)
        normalized_status, _ = self._request("GET", "/v1//entries//", token=None)
        self.assertEqual(canonical_status, 401)
        self.assertEqual(normalized_status, 401)


class RecordQueryIntegrityFlowTests(_LiveServerTestCase):
    def test_record_then_query_then_integrity(self) -> None:
        body = json.dumps(
            {"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"}
        ).encode("utf-8")
        status, created = self._request("POST", "/v1/entries", body=body)
        self.assertEqual(status, 201)
        self.assertEqual(created["sequence"], 1)

        status, events = self._request("GET", "/v1/entries")
        self.assertEqual(status, 200)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["actor"], "operator:mina")

        status, report = self._request("GET", "/v1/integrity")
        self.assertEqual(status, 200)
        self.assertEqual(report["total_events"], 1)
        self.assertEqual(report["integrity_violations"], [])

    def test_persists_across_a_fresh_store_instance(self) -> None:
        body = json.dumps(
            {"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"}
        ).encode("utf-8")
        self._request("POST", "/v1/entries", body=body)

        reopened = AuditService(SqliteAuditStore(self.db_path))
        self.assertEqual(len(reopened.query()), 1)


class ResolveV2AliasCatalogTests(unittest.TestCase):
    """Direct unit tests of the honest None-resolution helper."""

    def test_explicit_bool_values_pass_through_unchanged(self) -> None:
        catalog = (("POST", "/v2/entries", "record", True),)
        self.assertEqual(
            resolve_v2_alias_catalog(catalog, {}),
            (("POST", "/v2/entries", "record", True),),
        )

    def test_none_resolves_from_the_canonical_v1_route(self) -> None:
        catalog = (("GET", "/v2/integrity", "integrity", None),)
        resolved = resolve_v2_alias_catalog(catalog, {("GET", "/v1/integrity"): False})
        self.assertEqual(resolved, (("GET", "/v2/integrity", "integrity", False),))

    def test_missing_canonical_key_raises_rather_than_defaulting(self) -> None:
        catalog = (("GET", "/v2/integrity", "integrity", None),)
        with self.assertRaises(UnresolvedAliasError):
            resolve_v2_alias_catalog(catalog, {})

    def test_a_present_but_unrelated_canonical_key_still_raises(self) -> None:
        # Having *some* entries in canonical_bearer must not satisfy the
        # requirement for a different, missing one.
        catalog = (("GET", "/v2/integrity", "integrity", None),)
        with self.assertRaises(UnresolvedAliasError):
            resolve_v2_alias_catalog(catalog, {("GET", "/v1/entries"): True})

    def test_the_real_catalog_resolves_cleanly_against_the_installed_v1_routes(self) -> None:
        resolved = resolve_v2_alias_catalog(
            build_v2_alias_catalog(),
            {
                ("POST", "/v1/entries"): True,
                ("GET", "/v1/entries"): True,
                ("GET", "/v1/integrity"): True,
            },
        )
        self.assertEqual(resolved, build_v2_alias_catalog())


class V2AliasLoopbackTests(_LiveServerTestCase):
    """Real HTTP requests against the V2 aliases installed at server startup."""

    def test_v2_entries_post_is_protected_like_its_v1_counterpart(self) -> None:
        status, _ = self._request("POST", "/v2/entries", token=None, body=b"{}")
        self.assertEqual(status, 401)

    def test_v2_entries_get_is_protected_like_its_v1_counterpart(self) -> None:
        status, _ = self._request("GET", "/v2/entries", token=None)
        self.assertEqual(status, 401)

    def test_v2_integrity_is_protected_like_its_v1_counterpart(self) -> None:
        status, _ = self._request("GET", "/v2/integrity", token=None)
        self.assertEqual(status, 401)

    def test_recording_through_the_v2_alias_is_visible_through_v1(self) -> None:
        body = json.dumps(
            {"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"}
        ).encode("utf-8")
        status, created = self._request("POST", "/v2/entries", body=body)
        self.assertEqual(status, 201)
        self.assertEqual(created["sequence"], 1)

        status, events = self._request("GET", "/v1/entries")
        self.assertEqual(status, 200)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["actor"], "operator:mina")

    def test_querying_through_the_v2_alias_sees_a_v1_recorded_entry(self) -> None:
        body = json.dumps(
            {"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"}
        ).encode("utf-8")
        self._request("POST", "/v1/entries", body=body)

        status, events = self._request("GET", "/v2/entries")
        self.assertEqual(status, 200)
        self.assertEqual(len(events), 1)

    def test_v2_integrity_reports_against_the_same_store_as_v1(self) -> None:
        body = json.dumps(
            {"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"}
        ).encode("utf-8")
        self._request("POST", "/v1/entries", body=body)

        status, report = self._request("GET", "/v2/integrity")
        self.assertEqual(status, 200)
        self.assertEqual(report["total_events"], 1)

    def test_normalized_v2_alias_spelling_requires_the_same_bearer(self) -> None:
        canonical_status, _ = self._request("GET", "/v2/entries", token=None)
        normalized_status, _ = self._request("GET", "/v2//entries//", token=None)
        self.assertEqual(canonical_status, 401)
        self.assertEqual(normalized_status, 401)

    def test_v1_paths_are_unaffected_by_installed_aliases(self) -> None:
        status, payload = self._request("GET", "/v1/entries")
        self.assertEqual(status, 200)
        self.assertEqual(payload, [])

    def test_unknown_path_is_still_not_found(self) -> None:
        status, _ = self._request("GET", "/v2/unknown")
        self.assertEqual(status, 404)

    def test_health_remains_public_and_unaffected(self) -> None:
        status, payload = self._request("GET", "/health", token=None)
        self.assertEqual(status, 200)
        self.assertEqual(payload, {"status": "ok"})


class CliSharesTheHttpSqliteStoreTests(_LiveServerTestCase):
    """CLI and HTTP read/write the exact same SQLite store format and path,
    verified from a fresh, separate OS process running the real CLI."""

    def _run_cli(self, *args: str) -> "subprocess.CompletedProcess[str]":
        completed = subprocess.run(
            [sys.executable, "-m", "auditlog.cli", *args],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise AssertionError(f"cli invocation failed: {completed.stderr}")
        return completed

    def test_a_fresh_cli_process_queries_what_the_http_server_recorded(self) -> None:
        body = json.dumps(
            {"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"}
        ).encode("utf-8")
        status, created = self._request("POST", "/v1/entries", body=body)
        self.assertEqual(status, 201)

        completed = self._run_cli("query", "--log-store", str(self.db_path))
        lines = [line for line in completed.stdout.splitlines() if line]
        self.assertEqual(len(lines), 1)
        record = json.loads(lines[0])
        self.assertEqual(record["actor"], "operator:mina")
        self.assertEqual(record["sequence"], 1)

    def test_a_fresh_cli_record_is_visible_through_the_v1_http_route(self) -> None:
        self._run_cli(
            "record", "operator:cli", "policy.update", "allowed",
            "--log-store", str(self.db_path),
        )

        status, events = self._request("GET", "/v1/entries")
        self.assertEqual(status, 200)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["actor"], "operator:cli")

    def test_a_fresh_cli_record_is_visible_through_the_v2_alias(self) -> None:
        self._run_cli(
            "record", "operator:cli", "policy.update", "allowed",
            "--log-store", str(self.db_path),
        )

        status, events = self._request("GET", "/v2/entries")
        self.assertEqual(status, 200)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["actor"], "operator:cli")


class CliSurfaceTests(unittest.TestCase):
    def test_serve_subcommand_is_present_with_expected_options(self) -> None:
        parser = cli.build_parser()
        choices = parser._subparsers._group_actions[0].choices
        self.assertIn("serve", choices)

        serve_parser = choices["serve"]
        args = serve_parser.parse_args(
            ["--log-store", "store.sqlite3", "--bearer-token", "tok"]
        )
        self.assertEqual(args.log_store, "store.sqlite3")
        self.assertEqual(args.bearer_token, "tok")
        self.assertEqual(args.host, "127.0.0.1")
        self.assertEqual(args.port, 8080)

    def test_serve_requires_log_store_and_bearer_token(self) -> None:
        parser = cli.build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["serve", "--bearer-token", "tok"])
        with self.assertRaises(SystemExit):
            parser.parse_args(["serve", "--log-store", "store.sqlite3"])

    def test_main_rejects_a_non_loopback_host_without_starting_a_server(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "audit.sqlite3")
            with self.assertRaises(SystemExit):
                cli.main(
                    [
                        "serve",
                        "--log-store",
                        db_path,
                        "--bearer-token",
                        "tok",
                        "--host",
                        "8.8.8.8",
                    ]
                )


if __name__ == "__main__":
    unittest.main()
