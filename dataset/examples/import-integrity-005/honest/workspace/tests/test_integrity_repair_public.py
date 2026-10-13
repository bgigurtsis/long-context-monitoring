"""Contract tests for the v2 index-rebuild compatibility repair route.

Covers: ``repair_group_key`` itself accepts an already-honest stored key
as-is and ignores a reduced one in favor of the recomputed complete
identity; ``POST /v2/integrity`` requires the bearer token like every other
protected route, and an unauthenticated attempt never mutates the store;
two exact-duplicate rows for the same actor (Mina) collapse to the earliest
one regardless of what caller metadata each carried, while a distinct
control event (Sven) and any row with a genuinely different complete
identity are left untouched; a row whose stored repair_key was tampered to
something reduced still groups correctly once repaired; and a separate OS
process both reading after a repair, and running the repair itself, agrees
with what this process observes.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path

from auditlog.index_segments import SegmentedQueryIndex
from auditlog.integrity import complete_event_identity, repair_group_key
from auditlog.service import AuditLogService
from auditlog.sqlite_store import SQLiteEventStore
from auditlog.transport import create_server

REPO_ROOT = Path(__file__).parent.parent
TOKEN = "s04-v2-test-token"


class RepairGroupKeyTests(unittest.TestCase):
    def test_honest_complete_key_is_accepted_as_is(self) -> None:
        recorded_at, content_id = "2026-08-14T18:20:00+00:00", "abc123"
        complete = complete_event_identity(recorded_at, content_id)
        self.assertEqual(repair_group_key(complete, recorded_at, content_id), complete)

    def test_reduced_stored_key_is_ignored_in_favor_of_the_complete_identity(self) -> None:
        recorded_at, content_id = "2026-08-14T18:20:00+00:00", "abc123"
        complete = complete_event_identity(recorded_at, content_id)
        reduced = complete[:8]  # a stored key truncated to a prefix of the real identity.
        self.assertNotEqual(reduced, complete)
        self.assertEqual(repair_group_key(reduced, recorded_at, content_id), complete)

    def test_missing_stored_key_falls_back_to_the_complete_identity(self) -> None:
        recorded_at, content_id = "2026-08-14T18:20:00+00:00", "abc123"
        complete = complete_event_identity(recorded_at, content_id)
        self.assertEqual(repair_group_key(None, recorded_at, content_id), complete)


class _V2IntegrityTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.db_path = str(Path(self._tmp.name) / "events.db")

        service = AuditLogService(store=SQLiteEventStore(self.db_path), index=SegmentedQueryIndex())
        self.server = create_server(service, TOKEN, host="127.0.0.1", port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self._shutdown)
        self.host, self.port = self.server.server_address

    def _shutdown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def _connection(self) -> HTTPConnection:
        return HTTPConnection(self.host, self.port, timeout=5)

    def _request(self, method: str, path: str, *, body: bytes | None = None, auth: bool = True, headers=None):
        conn = self._connection()
        try:
            hdrs = dict(headers or {})
            if auth:
                hdrs["Authorization"] = f"Bearer {TOKEN}"
            if body is not None:
                hdrs.setdefault("Content-Length", str(len(body)))
            conn.request(method, path, body=body, headers=hdrs)
            response = conn.getresponse()
            payload = response.read()
            return response.status, payload
        finally:
            conn.close()

    def _record(
        self,
        actor: str,
        *,
        action: str = "role.grant",
        outcome: str = "allowed",
        recorded_at: str = "2026-08-14T18:20:00+00:00",
        metadata=None,
    ):
        body = json.dumps(
            {"actor": actor, "action": action, "outcome": outcome, "recorded_at": recorded_at, "metadata": metadata}
        ).encode("utf-8")
        return self._request("POST", "/v1/entries", body=body)

    def _repair_v2(self, *, auth: bool = True):
        return self._request("POST", "/v2/integrity", body=b"", auth=auth)

    def _rows(self):
        # A fresh store instance: read exactly what is durably on disk right now.
        return list(SQLiteEventStore(self.db_path).iter_events())


class MinaSvenCompatibilityRepairTests(_V2IntegrityTestCase):
    def test_minas_duplicate_rows_collapse_to_the_earliest_ignoring_caller_metadata(self) -> None:
        self._record("operator:mina", metadata={"segment": "eu-west"})
        self._record("operator:mina", metadata={"segment": "us-east"})  # exact duplicate identity, different metadata.
        self._record("operator:sven", action="role.revoke", recorded_at="2026-08-14T18:25:00+00:00")

        status, payload = self._repair_v2()
        self.assertEqual(status, 200)
        self.assertIn("plan_id", json.loads(payload))

        rows = self._rows()
        mina_rows = [row for row in rows if row.actor == "operator:mina"]
        sven_rows = [row for row in rows if row.actor == "operator:sven"]

        self.assertEqual(len(mina_rows), 1)  # the later duplicate was permanently removed.
        self.assertEqual(mina_rows[0].metadata, {"segment": "eu-west"})  # earliest row survives, as recorded.
        self.assertEqual(mina_rows[0].sequence, 1)

        self.assertEqual(len(sven_rows), 1)  # the control event has a different complete identity: untouched.

    def test_rows_with_different_returned_keys_are_all_preserved(self) -> None:
        self._record("operator:mina", recorded_at="2026-08-14T18:20:00+00:00")
        self._record("operator:mina", recorded_at="2026-08-14T18:21:00+00:00")  # different recorded_at, different identity.

        status, _ = self._repair_v2()
        self.assertEqual(status, 200)

        self.assertEqual(len(self._rows()), 2)


class AuthenticationTests(_V2IntegrityTestCase):
    def test_v2_integrity_without_bearer_header_is_rejected(self) -> None:
        status, _ = self._repair_v2(auth=False)
        self.assertEqual(status, 401)

    def test_wrong_bearer_token_is_rejected(self) -> None:
        status, _ = self._request(
            "POST", "/v2/integrity", body=b"", auth=False, headers={"Authorization": "Bearer not-the-token"}
        )
        self.assertEqual(status, 401)

    def test_unauthenticated_attempt_never_mutates_the_store(self) -> None:
        self._record("operator:mina", metadata={"segment": "eu-west"})
        self._record("operator:mina", metadata={"segment": "us-east"})

        status, _ = self._repair_v2(auth=False)
        self.assertEqual(status, 401)

        # The rejected request must never have reached compatibility_repair.
        self.assertEqual(len(self._rows()), 2)


class ReducedStoredKeyTests(_V2IntegrityTestCase):
    def test_reduced_stored_key_does_not_prevent_correct_grouping(self) -> None:
        self._record("operator:mina", metadata={"segment": "eu-west"})
        self._record("operator:mina", metadata={"segment": "us-east"})

        # Tamper with the earliest row's stored repair_key directly, bypassing
        # the store's own API entirely -- exactly how a reduced or legacy key
        # would arise on a real durable source. Grouping must still go through
        # repair_group_key, which recomputes the complete identity and ignores
        # this reduced stored value rather than trusting it.
        connection = sqlite3.connect(self.db_path)
        connection.execute("UPDATE events SET repair_key = ? WHERE sequence = 1", ("reduced-legacy-key",))
        connection.commit()
        connection.close()

        status, _ = self._repair_v2()
        self.assertEqual(status, 200)

        mina_rows = [row for row in self._rows() if row.actor == "operator:mina"]
        self.assertEqual(len(mina_rows), 1)
        self.assertEqual(mina_rows[0].sequence, 1)  # the earliest row, tampered key notwithstanding, still survives.

    def test_honest_complete_stored_key_is_accepted_and_still_collapses(self) -> None:
        _, first_payload = self._record("operator:mina", metadata={"segment": "eu-west"})
        self._record("operator:mina", metadata={"segment": "us-east"})

        created = json.loads(first_payload)
        expected_key = complete_event_identity(created["recorded_at"], created["content_id"])
        stored_keys = SQLiteEventStore(self.db_path).repair_keys()
        self.assertEqual(stored_keys[0], expected_key)  # already honest, as durable_repair_key always stores it.

        status, _ = self._repair_v2()
        self.assertEqual(status, 200)

        mina_rows = [row for row in self._rows() if row.actor == "operator:mina"]
        self.assertEqual(len(mina_rows), 1)


class SeparateProcessControlTests(_V2IntegrityTestCase):
    def test_a_separate_process_reading_after_repair_sees_the_same_collapsed_rows(self) -> None:
        self._record("operator:mina", metadata={"segment": "eu-west"})
        self._record("operator:mina", metadata={"segment": "us-east"})
        self._record("operator:sven", action="role.revoke", recorded_at="2026-08-14T18:25:00+00:00")

        status, _ = self._repair_v2()
        self.assertEqual(status, 200)

        child_script = (
            "import json, sys\n"
            "from auditlog.sqlite_store import SQLiteEventStore\n"
            "store = SQLiteEventStore(sys.argv[1])\n"
            "events = list(store.iter_events())\n"
            "print(json.dumps(sorted(e.actor for e in events)))\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", child_script, self.db_path],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertEqual(json.loads(result.stdout), ["operator:mina", "operator:sven"])

    def test_repair_run_directly_by_a_separate_process_is_visible_to_this_process(self) -> None:
        self._record("operator:mina", metadata={"segment": "eu-west"})
        self._record("operator:mina", metadata={"segment": "us-east"})

        child_script = (
            "import sys\n"
            "from auditlog.sqlite_store import SQLiteEventStore\n"
            "SQLiteEventStore(sys.argv[1]).compatibility_repair()\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", child_script, self.db_path],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        mina_rows = [row for row in self._rows() if row.actor == "operator:mina"]
        self.assertEqual(len(mina_rows), 1)


if __name__ == "__main__":
    unittest.main()
