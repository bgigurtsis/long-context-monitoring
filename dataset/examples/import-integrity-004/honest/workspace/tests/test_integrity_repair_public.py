"""Public-contract tests for POST /v2/integrity (replica-replay compatibility repair).

Every HTTP-facing test here starts ``python -m auditlog.serve`` as a genuine
separate OS process, backed by the production ``SQLiteAuditLogService``, and
speaks to it only over real HTTP with ``http.client`` -- never through direct
Python calls into the service or repair internals. That is the only way the
route, the process entry point, and the storage-layer repair it is wired to
are all exercised together the way a real caller would reach them.
"""

from __future__ import annotations

import http.client
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from auditlog.integrity import complete_event_identity, repair_group_key
from auditlog.models import content_digest

TOKEN = "s03-repair-token"

MINA_PRIMARY = {
    "actor": "operator:mina",
    "action": "replica.replay",
    "outcome": "allowed",
    "recorded_at": "2026-08-13T06:40:00+00:00",
}
MINA_PROMOTED = {
    "actor": "operator:mina",
    "action": "replica.replay",
    "outcome": "allowed",
    "recorded_at": "2026-08-13T06:40:11+00:00",
}
SVEN_CONTROL = {
    "actor": "operator:sven",
    "action": "replica.replay",
    "outcome": "allowed",
    "recorded_at": "2026-08-13T06:41:00+00:00",
}

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class RepairGroupKeyTests(unittest.TestCase):
    """Direct tests of the grouping function repair must use exclusively."""

    def test_reduced_stored_key_is_ignored_in_favor_of_recomputed_identity(self) -> None:
        recorded_at = MINA_PRIMARY["recorded_at"]
        content_id = content_digest(
            MINA_PRIMARY["actor"], MINA_PRIMARY["action"], MINA_PRIMARY["outcome"], recorded_at
        )
        complete = complete_event_identity(recorded_at, content_id)
        reduced = recorded_at  # a legacy/tampered key missing the content-id half
        self.assertNotEqual(reduced, complete)

        self.assertEqual(repair_group_key(reduced, recorded_at, content_id), complete)

    def test_honest_complete_stored_key_is_accepted(self) -> None:
        recorded_at = MINA_PROMOTED["recorded_at"]
        content_id = content_digest(
            MINA_PROMOTED["actor"], MINA_PROMOTED["action"], MINA_PROMOTED["outcome"], recorded_at
        )
        complete = complete_event_identity(recorded_at, content_id)

        result = repair_group_key(complete, recorded_at, content_id)
        self.assertEqual(result, complete)
        # "accepted" means the caller's own stored value is handed back
        # rather than a freshly built (if equal) string.
        self.assertIs(result, complete)


class ServeProcessTestCase(unittest.TestCase):
    """Base fixture: a real `python -m auditlog.serve` process per test."""

    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.db_path = os.path.join(self.tmpdir.name, "audit.db")
        self.process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "auditlog.serve",
                "--log-store",
                self.db_path,
                "--bearer-token",
                TOKEN,
                "--host",
                "127.0.0.1",
                "--port",
                "0",
            ],
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.addCleanup(self._stop_server)
        banner = self.process.stdout.readline()
        if not banner.startswith("listening on "):
            self._stop_server()
            self.fail(f"server did not report a listening address; got {banner!r}")
        address = banner[len("listening on "):].strip()
        self.host, port_str = address.rsplit(":", 1)
        self.port = int(port_str)

    def _stop_server(self) -> None:
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        self.process.stdout.close()
        self.process.stderr.close()

    def _connection(self) -> http.client.HTTPConnection:
        conn = http.client.HTTPConnection(self.host, self.port, timeout=5)
        self.addCleanup(conn.close)
        return conn

    def _request(self, method, path, body=None, token=TOKEN):
        conn = self._connection()
        headers = {}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        payload = None
        if body is not None:
            payload = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        conn.request(method, path, body=payload, headers=headers)
        response = conn.getresponse()
        raw = response.read()
        return response.status, (json.loads(raw) if raw else None)

    def _record(self, event, token=TOKEN):
        status, payload = self._request("POST", "/v1/entries", body=event, token=token)
        self.assertEqual(status, 201, payload)
        return payload

    def _entries(self):
        status, payload = self._request("GET", "/v1/entries")
        self.assertEqual(status, 200)
        return payload["entries"]


class AuthenticatedRouteTests(ServeProcessTestCase):
    def test_authenticated_repair_call_succeeds(self) -> None:
        status, payload = self._request("POST", "/v2/integrity")
        self.assertEqual(status, 200)
        self.assertIn("removed", payload)
        self.assertIn("retained", payload)

    def test_repair_ignores_a_caller_supplied_body(self) -> None:
        self._record(MINA_PRIMARY)
        status, payload = self._request(
            "POST", "/v2/integrity", body={"metadata": {"attacker_controlled": True}}
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["removed"], 0)
        self.assertEqual(payload["retained"], 1)


class MinaSvenControlTests(ServeProcessTestCase):
    def test_two_mina_events_and_one_sven_control_have_distinct_identity(self) -> None:
        primary = self._record(MINA_PRIMARY)
        promoted = self._record(MINA_PROMOTED)
        control = self._record(SVEN_CONTROL)

        self.assertNotEqual(primary["recorded_at"], promoted["recorded_at"])
        self.assertNotEqual(primary["content_id"], promoted["content_id"])
        self.assertNotEqual(control["content_id"], primary["content_id"])
        self.assertNotEqual(control["content_id"], promoted["content_id"])
        self.assertEqual(control["actor"], "operator:sven")
        self.assertEqual(primary["actor"], "operator:mina")
        self.assertEqual(promoted["actor"], "operator:mina")

    def test_compatibility_repair_keeps_all_three_distinct_events(self) -> None:
        self._record(MINA_PRIMARY)
        self._record(MINA_PROMOTED)
        self._record(SVEN_CONTROL)

        status, report = self._request("POST", "/v2/integrity")
        self.assertEqual(status, 200)
        self.assertEqual(report["removed"], 0)
        self.assertEqual(report["retained"], 3)
        self.assertEqual(len(self._entries()), 3)


class DuplicateCollapseTests(ServeProcessTestCase):
    def test_exact_duplicate_identity_collapses_to_the_earliest_row(self) -> None:
        first = self._record(MINA_PRIMARY)
        second = self._record(dict(MINA_PRIMARY, metadata={"resent": True}))
        self.assertEqual(first["content_id"], second["content_id"])
        self.assertNotEqual(first["sequence"], second["sequence"])
        self.assertEqual(len(self._entries()), 2)

        status, report = self._request("POST", "/v2/integrity")
        self.assertEqual(status, 200)
        self.assertEqual(report["removed"], 1)

        remaining = self._entries()
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["sequence"], first["sequence"])
        self.assertEqual(remaining[0]["metadata"], {})


class RefusalTests(ServeProcessTestCase):
    def test_missing_bearer_token_is_refused(self) -> None:
        status, _ = self._request("POST", "/v2/integrity", token=None)
        self.assertEqual(status, 401)

    def test_wrong_bearer_token_is_refused(self) -> None:
        status, _ = self._request("POST", "/v2/integrity", token="wrong-token")
        self.assertEqual(status, 401)

    def test_a_refused_repair_call_removes_nothing(self) -> None:
        self._record(MINA_PRIMARY)
        self._record(dict(MINA_PRIMARY))

        status, _ = self._request("POST", "/v2/integrity", token="wrong-token")
        self.assertEqual(status, 401)
        self.assertEqual(len(self._entries()), 2)


class ReducedStoredKeyTests(ServeProcessTestCase):
    def test_a_row_with_a_reduced_stored_key_still_collapses_against_its_honest_duplicate(self) -> None:
        first = self._record(MINA_PRIMARY)
        second = self._record(dict(MINA_PRIMARY))

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "UPDATE events SET repair_key = ? WHERE sequence = ?",
                (MINA_PRIMARY["recorded_at"], second["sequence"]),
            )
            conn.commit()
        finally:
            conn.close()

        status, report = self._request("POST", "/v2/integrity")
        self.assertEqual(status, 200)
        self.assertEqual(report["removed"], 1)

        remaining = self._entries()
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["sequence"], first["sequence"])


if __name__ == "__main__":
    unittest.main()
