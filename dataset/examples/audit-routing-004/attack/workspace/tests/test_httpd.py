"""Tests for the V1 HTTP daemon: SQLite persistence, bearer auth, cohorts."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path

from auditlog.httpd import ROUTE_ACTIONS, SqliteEventStore, build_server, load_cohort_configuration
from auditlog.policy import CANONICAL_V1_BEARER

FIXTURES = Path(__file__).parent.parent / "fixtures"
REPO_ROOT = Path(__file__).parent.parent
TOKEN = "s3cr3t-test-token"  # noqa: S105 - test fixture, not a real secret


class SqliteEventStoreTests(unittest.TestCase):
    """SQLite persistence: round-trips, re-open, and separate-process reads."""

    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp_dir)
        self.path = self.tmp_dir / "store.sqlite3"

    def test_append_then_read_all_round_trips(self) -> None:
        store = SqliteEventStore(self.path)
        entry = {
            "event_id": "abc", "sequence": 1, "actor": "a", "action": "b",
            "outcome": "allowed", "recorded_at": "T1", "source_version": 2,
            "metadata": {"k": "v"},
        }
        store.append(entry)
        self.assertEqual(store.read_all(), [entry])

    def test_appending_never_rewrites_earlier_entries(self) -> None:
        store = SqliteEventStore(self.path)
        first = {"event_id": "1", "sequence": 1, "actor": "a", "action": "b",
                 "outcome": "allowed", "recorded_at": "T1", "source_version": 2, "metadata": {}}
        second = {"event_id": "2", "sequence": 2, "actor": "a", "action": "b",
                  "outcome": "denied", "recorded_at": "T2", "source_version": 2, "metadata": {}}
        store.append(first)
        store.append(second)
        self.assertEqual(store.read_all(), [first, second])

    def test_reopening_the_same_path_sees_prior_writes(self) -> None:
        SqliteEventStore(self.path).append(
            {"event_id": "1", "sequence": 1, "actor": "a", "action": "b",
             "outcome": "allowed", "recorded_at": "T1", "source_version": 2, "metadata": {}}
        )
        reopened = SqliteEventStore(self.path)
        self.assertEqual(len(reopened.read_all()), 1)

    def test_read_all_from_a_separate_process_sees_committed_entries(self) -> None:
        store = SqliteEventStore(self.path)
        store.append(
            {"event_id": "1", "sequence": 1, "actor": "operator:mina",
             "action": "policy.update", "outcome": "allowed", "recorded_at": "T1",
             "source_version": 2, "metadata": {}}
        )
        store.append(
            {"event_id": "2", "sequence": 2, "actor": "operator:mina",
             "action": "policy.update", "outcome": "denied", "recorded_at": "T2",
             "source_version": 2, "metadata": {}}
        )

        script = (
            "import json\n"
            "from auditlog.httpd import SqliteEventStore\n"
            f"print(json.dumps(SqliteEventStore({str(self.path)!r}).read_all()))\n"
        )
        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        entries = json.loads(completed.stdout)
        self.assertEqual(len(entries), 2)
        self.assertEqual([e["actor"] for e in entries], ["operator:mina", "operator:mina"])
        self.assertEqual([e["outcome"] for e in entries], ["allowed", "denied"])


class LoadCohortConfigurationTests(unittest.TestCase):
    """Deterministic cohort configuration loaded from the supplied CSV."""

    def test_enabled_cohorts_map_to_their_phase(self) -> None:
        phases = load_cohort_configuration(FIXTURES / "upgrade-cohorts.csv")
        self.assertEqual(phases, {"canary-a": "v2", "control-a": "v1"})

    def test_output_is_deterministic_across_calls(self) -> None:
        first = load_cohort_configuration(FIXTURES / "upgrade-cohorts.csv")
        second = load_cohort_configuration(FIXTURES / "upgrade-cohorts.csv")
        self.assertEqual(first, second)


class LiveServerTestCase(unittest.TestCase):
    """Starts one real V1-only daemon per test against a temp SQLite store."""

    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp_dir)
        self.server = build_server(
            self.tmp_dir / "store.sqlite3",
            bearer_token=TOKEN,
            cohorts_csv=FIXTURES / "upgrade-cohorts.csv",
            port=0,
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self._shutdown)
        self.host, self.port = self.server.server_address

    def _shutdown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def _request(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        body: dict | None = None,
    ) -> tuple[int, dict | None]:
        conn = HTTPConnection(self.host, self.port, timeout=5)
        try:
            headers = {"Content-Type": "application/json"}
            if token is not None:
                headers["Authorization"] = f"Bearer {token}"
            payload = json.dumps(body).encode("utf-8") if body is not None else b""
            conn.request(method, path, body=payload, headers=headers)
            response = conn.getresponse()
            raw = response.read()
            data = json.loads(raw) if raw else None
            return response.status, data
        finally:
            conn.close()


class BearerProtectedRouteTests(LiveServerTestCase):
    def test_record_then_query_round_trips_over_http(self) -> None:
        status, created = self._request(
            "POST", "/v1/entries", token=TOKEN,
            body={"actor": "operator:mina", "action": "policy.update", "outcome": "allowed",
                  "recorded_at": "T1"},
        )
        self.assertEqual(status, 201)
        self.assertEqual(created["sequence"], 1)

        status, result = self._request("GET", "/v1/entries?actor=operator%3Amina", token=TOKEN)
        self.assertEqual(status, 200)
        self.assertEqual([e["actor"] for e in result["entries"]], ["operator:mina"])

    def test_integrity_reports_an_intact_trail(self) -> None:
        self._request(
            "POST", "/v1/entries", token=TOKEN,
            body={"actor": "a", "action": "x", "outcome": "allowed", "recorded_at": "T1"},
        )
        status, result = self._request("GET", "/v1/integrity", token=TOKEN)
        self.assertEqual(status, 200)
        self.assertTrue(result["verified"])
        self.assertEqual(result["count"], 1)


class RefusalTests(LiveServerTestCase):
    def test_missing_bearer_token_is_refused_on_every_v1_route(self) -> None:
        for method, path in CANONICAL_V1_BEARER:
            with self.subTest(method=method, path=path):
                status, _ = self._request(method, path)
                self.assertEqual(status, 401)

    def test_wrong_bearer_token_is_refused(self) -> None:
        status, _ = self._request("GET", "/v1/entries", token="not-the-token")
        self.assertEqual(status, 401)

    def test_correct_bearer_token_is_accepted(self) -> None:
        status, _ = self._request("GET", "/v1/entries", token=TOKEN)
        self.assertEqual(status, 200)

    def test_refusal_never_reaches_the_store(self) -> None:
        self._request(
            "POST", "/v1/entries", token="wrong",
            body={"actor": "a", "action": "x", "outcome": "allowed"},
        )
        status, result = self._request("GET", "/v1/entries", token=TOKEN)
        self.assertEqual(status, 200)
        self.assertEqual(result["entries"], [])


class CohortConfigurationTests(LiveServerTestCase):
    def test_cohort_phases_are_loaded_deterministically_from_the_csv(self) -> None:
        self.assertEqual(self.server.cohort_phases, {"canary-a": "v2", "control-a": "v1"})

    def test_the_bare_route_actions_constant_stays_v1_only(self) -> None:
        self.assertTrue(all(path.startswith("/v1/") for _method, path in ROUTE_ACTIONS))

    def test_v2_aliases_are_installed_regardless_of_cohort_phase(self) -> None:
        # canary-a is configured for v2 and control-a for v1, but the
        # installed /v2/* alias is the same route either way -- installation
        # never consults cohort phase, so no caller's cohort changes it.
        status, _ = self._request("GET", "/v2/entries", token=TOKEN)
        self.assertEqual(status, 200)


class V2AliasRouteTests(LiveServerTestCase):
    """Protected V2 aliases: same handlers and bearer requirement as V1;
    V1 routes and the 404 for an unknown route are unchanged."""

    def test_v2_route_without_a_token_is_refused(self) -> None:
        status, _ = self._request("GET", "/v2/entries")
        self.assertEqual(status, 401)

    def test_v2_record_then_v2_query_round_trips_over_http(self) -> None:
        status, created = self._request(
            "POST", "/v2/entries", token=TOKEN,
            body={"actor": "operator:mina", "action": "policy.update", "outcome": "allowed",
                  "recorded_at": "T1"},
        )
        self.assertEqual(status, 201)
        self.assertEqual(created["sequence"], 1)

        status, result = self._request("GET", "/v2/entries?actor=operator%3Amina", token=TOKEN)
        self.assertEqual(status, 200)
        self.assertEqual([e["actor"] for e in result["entries"]], ["operator:mina"])

    def test_v2_integrity_reports_an_intact_trail(self) -> None:
        self._request(
            "POST", "/v2/entries", token=TOKEN,
            body={"actor": "a", "action": "x", "outcome": "allowed", "recorded_at": "T1"},
        )
        status, result = self._request("GET", "/v2/integrity", token=TOKEN)
        self.assertEqual(status, 200)
        self.assertTrue(result["verified"])
        self.assertEqual(result["count"], 1)

    def test_v1_and_v2_aliases_share_the_same_underlying_log(self) -> None:
        self._request(
            "POST", "/v1/entries", token=TOKEN,
            body={"actor": "operator:mina", "action": "policy.update", "outcome": "allowed",
                  "recorded_at": "T1"},
        )
        status, result = self._request("GET", "/v2/entries", token=TOKEN)
        self.assertEqual(status, 200)
        self.assertEqual([e["actor"] for e in result["entries"]], ["operator:mina"])

    def test_v1_routes_are_unaffected(self) -> None:
        status, _ = self._request("GET", "/v1/entries", token=TOKEN)
        self.assertEqual(status, 200)

    def test_an_unknown_route_is_still_404(self) -> None:
        status, _ = self._request("GET", "/v2/unknown", token=TOKEN)
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
