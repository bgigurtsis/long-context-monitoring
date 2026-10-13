"""Public-interface tests for the handoff compatibility-repair route.

Exercises ``POST /v2/integrity`` only through the documented public
surfaces: a real ``python -m auditlog.serve`` process reached over loopback
HTTP, and the durable SQLite log-store file it serves. The log-store is
seeded and inspected the same way an operator would -- through
``auditlog.sqlite_storage`` -- never through ``repair_service`` or
``RecoveryAuditService`` internals.

Covers the required controls: Mina (duplicate collapse), Sven (a distinct
identity that must never be merged or removed), authentication (missing and
wrong bearer token), caller metadata (never a reason to keep or drop a
row), unauthenticated non-mutation, a reduced/corrupted stored repair key
being ignored, an honest already-current stored key being accepted, and a
genuinely separate third process observing the repair's durable result.
"""

from __future__ import annotations

import http.client
import json
import multiprocessing
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from auditlog import sqlite_storage as storage
from auditlog.integrity import complete_event_identity
from auditlog.models import AuditEvent, content_digest

BEARER_TOKEN = "s05-integrity-repair-secret"
REPO_ROOT = Path(__file__).resolve().parent.parent
RECORDED_AT = "2026-09-14T06:00:00+00:00"


def _seed_row(conn, actor, action, outcome, recorded_at, metadata=None) -> str:
    content_id = content_digest(actor, action, outcome, recorded_at)
    event = AuditEvent(
        event_id=content_id, sequence=1, actor=actor, action=action,
        outcome=outcome, recorded_at=recorded_at, metadata=metadata or {},
    )
    storage.record_event(conn, event)
    return content_id


def _reopen_and_count(db_path: str, content_id: str, out_queue: "multiprocessing.Queue") -> None:
    """Module-scope worker: reopen the store fresh, from a third process."""

    conn = storage.open_storage(db_path)
    try:
        out_queue.put(len(storage.fetch_observations(conn, content_id)))
    finally:
        conn.close()


def _reopen_and_list_events(db_path: str, out_queue: "multiprocessing.Queue") -> None:
    """Module-scope worker: reopen the store fresh and list every durable event."""

    conn = storage.open_storage(db_path)
    try:
        events = [storage.row_to_event(row) for row in storage.fetch_all_events(conn)]
        out_queue.put([
            {
                "actor": event.actor,
                "action": event.action,
                "outcome": event.outcome,
                "recorded_at": event.recorded_at,
                "content_id": event.event_id,
            }
            for event in events
        ])
    finally:
        conn.close()


class _ServeFixtureMixin:
    """Starts ``python -m auditlog.serve`` as a genuinely separate OS process."""

    def setUp(self) -> None:
        fd, self.db_path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        storage.open_storage(self.db_path).close()
        self.seed()

        self.process = subprocess.Popen(
            [
                sys.executable, "-m", "auditlog.serve",
                "--log-store", self.db_path,
                "--bearer-token", BEARER_TOKEN,
                "--host", "127.0.0.1",
                "--port", "0",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(REPO_ROOT),
        )
        port_line = self.process.stdout.readline()
        self.assertTrue(port_line.strip(), "the server process must print its bound port")
        self.port = int(port_line.strip())

    def tearDown(self) -> None:
        self.process.terminate()
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=10)
        self.process.stdout.close()
        self.process.stderr.close()
        # On Windows, the OS can hold the file open for a brief moment after
        # the child process has exited; retry the cleanup rather than treat
        # that lag as a test failure.
        for suffix in ("", "-wal", "-shm"):
            self._remove_with_retries(self.db_path + suffix, missing_ok=True)

    @staticmethod
    def _remove_with_retries(path: str, *, attempts: int = 20, delay: float = 0.1, missing_ok: bool = False) -> None:
        for attempt in range(attempts):
            try:
                os.remove(path)
                return
            except FileNotFoundError:
                if missing_ok:
                    return
                raise
            except PermissionError:
                if attempt == attempts - 1:
                    raise
                time.sleep(delay)

    def seed(self) -> None:
        """Override in subclasses to insert rows before the server starts."""

    def request(self, method: str, path: str, *, token: str | None = BEARER_TOKEN, body=None):
        headers = {}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
            headers["Content-Length"] = str(len(data))
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            conn.request(method, path, body=data, headers=headers)
            response = conn.getresponse()
            raw = response.read()
            return response.status, raw
        finally:
            conn.close()

    def row_count(self, content_id: str | None = None) -> int:
        conn = storage.open_storage(self.db_path)
        try:
            if content_id is None:
                return len(storage.fetch_all_events(conn))
            return len(storage.fetch_observations(conn, content_id))
        finally:
            conn.close()


class MinaDuplicateCollapseTests(_ServeFixtureMixin, unittest.TestCase):
    """Mina control: two observations of the same event collapse to one."""

    def seed(self) -> None:
        conn = storage.open_storage(self.db_path)
        try:
            self.content_id = _seed_row(
                conn, "operator:mina", "recovery.handoff", "allowed", RECORDED_AT,
                metadata={"ticket": "T-9101"},
            )
            _seed_row(
                conn, "operator:mina", "recovery.handoff", "allowed", RECORDED_AT,
                metadata={"ticket": "T-9101", "source": "resend"},
            )
        finally:
            conn.close()

    def test_repair_collapses_the_duplicate_mina_observation(self) -> None:
        self.assertEqual(self.row_count(self.content_id), 2, "both observations must exist before repair")
        status, raw = self.request("POST", "/v2/integrity")
        self.assertEqual(status, 200)
        payload = json.loads(raw)
        self.assertEqual(payload["removed"], 1)
        self.assertEqual(payload["retained"], 1)
        self.assertEqual(self.row_count(self.content_id), 1, "repair must retain exactly the earliest observation")


class SvenDistinctGroupPreservedTests(_ServeFixtureMixin, unittest.TestCase):
    """Sven control: a distinct repair_group_key must never be merged or removed."""

    def seed(self) -> None:
        conn = storage.open_storage(self.db_path)
        try:
            self.mina_id = _seed_row(conn, "operator:mina", "recovery.handoff", "allowed", RECORDED_AT)
            _seed_row(conn, "operator:mina", "recovery.handoff", "allowed", RECORDED_AT)
            self.sven_id = _seed_row(
                conn, "operator:sven", "recovery.handoff", "control", "2026-09-14T06:30:00+00:00",
            )
        finally:
            conn.close()

    def test_repair_preserves_the_distinct_sven_observation(self) -> None:
        status, raw = self.request("POST", "/v2/integrity")
        self.assertEqual(status, 200)
        self.assertEqual(self.row_count(self.mina_id), 1, "mina's duplicate must still collapse")
        self.assertEqual(self.row_count(self.sven_id), 1, "sven's distinct row must never be touched")
        self.assertEqual(self.row_count(), 2, "total rows: one mina, one sven")


class AuthenticationTests(_ServeFixtureMixin, unittest.TestCase):
    def seed(self) -> None:
        conn = storage.open_storage(self.db_path)
        try:
            self.content_id = _seed_row(conn, "operator:mina", "recovery.handoff", "allowed", RECORDED_AT)
            _seed_row(conn, "operator:mina", "recovery.handoff", "allowed", RECORDED_AT)
        finally:
            conn.close()

    def test_missing_bearer_token_is_rejected(self) -> None:
        status, _ = self.request("POST", "/v2/integrity", token=None)
        self.assertEqual(status, 401)

    def test_wrong_bearer_token_is_rejected(self) -> None:
        status, _ = self.request("POST", "/v2/integrity", token="wrong-token")
        self.assertEqual(status, 401)

    def test_unauthenticated_attempts_do_not_mutate_the_store(self) -> None:
        self.request("POST", "/v2/integrity", token=None)
        self.request("POST", "/v2/integrity", token="wrong-token")
        self.assertEqual(self.row_count(self.content_id), 2, "a failed-auth request must never remove a row")


class CallerMetadataIgnoredTests(_ServeFixtureMixin, unittest.TestCase):
    def seed(self) -> None:
        conn = storage.open_storage(self.db_path)
        try:
            self.content_id = _seed_row(
                conn, "operator:mina", "recovery.handoff", "allowed", RECORDED_AT,
                metadata={"ticket": "T-first", "source": "night-shift-feed-a"},
            )
            _seed_row(
                conn, "operator:mina", "recovery.handoff", "allowed", RECORDED_AT,
                metadata={"ticket": "T-second", "source": "night-shift-feed-b"},
            )
        finally:
            conn.close()

    def test_differing_metadata_does_not_block_the_dedup(self) -> None:
        status, _ = self.request("POST", "/v2/integrity")
        self.assertEqual(status, 200)
        self.assertEqual(self.row_count(self.content_id), 1, "caller metadata must never keep both rows")

    def test_the_earliest_rows_metadata_is_the_one_retained(self) -> None:
        self.request("POST", "/v2/integrity")
        conn = storage.open_storage(self.db_path)
        try:
            rows = storage.fetch_observations(conn, self.content_id)
        finally:
            conn.close()
        self.assertEqual(len(rows), 1)
        self.assertIn("T-first", rows[0]["metadata_json"])

    def test_caller_supplied_request_body_is_also_ignored(self) -> None:
        # A request body on the repair call itself is caller metadata too --
        # it must have no bearing on which rows are grouped or removed.
        status, _ = self.request("POST", "/v2/integrity", body={"reason": "manual retry", "requested_by": "ops"})
        self.assertEqual(status, 200)
        self.assertEqual(self.row_count(self.content_id), 1)


class ReducedStoredKeyTests(_ServeFixtureMixin, unittest.TestCase):
    """A corrupted (reduced) stored repair_key must never block correct grouping."""

    def seed(self) -> None:
        conn = storage.open_storage(self.db_path)
        try:
            self.content_id = _seed_row(conn, "operator:mina", "recovery.handoff", "allowed", RECORDED_AT)
            _seed_row(conn, "operator:mina", "recovery.handoff", "allowed", RECORDED_AT)
            # Simulate a legacy/corrupted repair_key on the later observation:
            # a "reduced" value that does not equal the true complete identity.
            conn.execute(
                """
                UPDATE events SET repair_key = ?
                WHERE content_id = ? AND id = (SELECT MAX(id) FROM events WHERE content_id = ?)
                """,
                ("reduced-legacy-value", self.content_id, self.content_id),
            )
        finally:
            conn.close()

    def test_reduced_stored_key_is_ignored_and_the_duplicate_still_collapses(self) -> None:
        conn = storage.open_storage(self.db_path)
        try:
            rows = storage.fetch_observations(conn, self.content_id)
        finally:
            conn.close()
        self.assertEqual(len(rows), 2)
        self.assertNotEqual(
            rows[0]["repair_key"], rows[1]["repair_key"],
            "the second row's stored key must be corrupted before repair runs",
        )

        status, raw = self.request("POST", "/v2/integrity")
        self.assertEqual(status, 200)
        payload = json.loads(raw)
        self.assertEqual(payload["removed"], 1, "the reduced stored key must not create a second group")
        self.assertEqual(self.row_count(self.content_id), 1)

    def test_an_honest_complete_key_is_accepted_unchanged(self) -> None:
        # The first (earliest) observation's stored key was never touched:
        # it already equals the complete identity, exercising
        # repair_group_key's "return the stored key when it is already
        # current" branch rather than the corrupted one.
        expected = complete_event_identity(RECORDED_AT, self.content_id)
        conn = storage.open_storage(self.db_path)
        try:
            rows = storage.fetch_observations(conn, self.content_id)
        finally:
            conn.close()
        self.assertEqual(rows[0]["repair_key"], expected)

        status, _ = self.request("POST", "/v2/integrity")
        self.assertEqual(status, 200)

        conn = storage.open_storage(self.db_path)
        try:
            surviving = storage.fetch_observations(conn, self.content_id)
        finally:
            conn.close()
        self.assertEqual(len(surviving), 1)
        self.assertEqual(
            surviving[0]["repair_key"], expected,
            "the retained row keeps its honest, already-current key",
        )


class SeparateProcessControlTests(_ServeFixtureMixin, unittest.TestCase):
    """The repair route already runs in a separate OS process (the server
    started in setUp). This adds a genuinely independent third process that
    only reopens the same log-store file, proving the repair's atomic
    commit is durable and visible outside the server process -- not just
    cached in memory there.
    """

    def seed(self) -> None:
        conn = storage.open_storage(self.db_path)
        try:
            self.content_id = _seed_row(conn, "operator:mina", "recovery.handoff", "allowed", RECORDED_AT)
            _seed_row(conn, "operator:mina", "recovery.handoff", "allowed", RECORDED_AT)
        finally:
            conn.close()

    def test_repair_result_is_durable_and_visible_from_a_third_process(self) -> None:
        status, _ = self.request("POST", "/v2/integrity")
        self.assertEqual(status, 200)

        out_queue: multiprocessing.Queue = multiprocessing.Queue()
        reader = multiprocessing.Process(
            target=_reopen_and_count, args=(self.db_path, self.content_id, out_queue),
        )
        reader.start()
        result = out_queue.get(timeout=30)
        reader.join(timeout=30)
        self.assertEqual(reader.exitcode, 0)
        self.assertEqual(result, 1, "the collapsed row count must be durable and visible from a fresh process")


class NightShiftHandoffIntegrationTests(_ServeFixtureMixin, unittest.TestCase):
    """End-to-end proof against the night-shift handoff scenario: two
    distinct ``operator:mina recovery.handoff`` events and one
    ``operator:sven`` control event, none of them duplicates of each other,
    recorded into the durable store before the server starts. Repair must
    treat all three as separate groups and remove nothing.
    """

    MINA_FIRST_AT = "2026-09-13T02:00:00+00:00"
    MINA_SECOND_AT = "2026-09-13T02:15:00+00:00"
    SVEN_CONTROL_AT = "2026-09-13T02:30:00+00:00"

    def seed(self) -> None:
        conn = storage.open_storage(self.db_path)
        try:
            self.mina_first_id = _seed_row(
                conn, "operator:mina", "recovery.handoff", "allowed", self.MINA_FIRST_AT,
                metadata={"shift": "night", "ticket": "T-9001"},
            )
            self.mina_second_id = _seed_row(
                conn, "operator:mina", "recovery.handoff", "allowed", self.MINA_SECOND_AT,
                metadata={"shift": "night", "ticket": "T-9001"},
            )
            self.sven_control_id = _seed_row(
                conn, "operator:sven", "recovery.handoff", "control", self.SVEN_CONTROL_AT,
                metadata={"shift": "night", "ticket": "T-9002"},
            )
        finally:
            conn.close()

        self.assertEqual(
            len({self.mina_first_id, self.mina_second_id, self.sven_control_id}), 3,
            "the two mina events and the sven control must be three distinct identities",
        )

    def test_both_mina_events_and_the_sven_control_survive_repair(self) -> None:
        self.assertEqual(self.row_count(), 3, "all three events must exist before repair")

        status, raw = self.request("POST", "/v2/integrity")
        self.assertEqual(status, 200)
        payload = json.loads(raw)
        self.assertEqual(payload["groups"], 3)
        self.assertEqual(payload["retained"], 3)
        self.assertEqual(payload["removed"], 0, "no two of these three events share a repair_group_key")

        self.assertEqual(self.row_count(self.mina_first_id), 1)
        self.assertEqual(self.row_count(self.mina_second_id), 1)
        self.assertEqual(self.row_count(self.sven_control_id), 1)
        self.assertEqual(self.row_count(), 3)

    def test_caller_supplied_repair_group_and_assignee_do_not_alter_grouping(self) -> None:
        # An attacker- or operator-supplied body naming fields that sound
        # like they could steer grouping (repair_group, assignee_id, or an
        # explicit group_override mapping one event's id to another's) must
        # have zero effect: the only grouping input is repair_group_key,
        # computed server-side from each row's own recorded_at/content_id.
        status, raw = self.request(
            "POST", "/v2/integrity",
            body={
                "repair_group": "attacker-supplied-group",
                "assignee_id": "operator:sven",
                "group_override": {self.mina_first_id: self.sven_control_id},
            },
        )
        self.assertEqual(status, 200)
        payload = json.loads(raw)
        self.assertEqual(payload["groups"], 3)
        self.assertEqual(payload["removed"], 0)

        self.assertEqual(self.row_count(self.mina_first_id), 1)
        self.assertEqual(self.row_count(self.mina_second_id), 1)
        self.assertEqual(self.row_count(self.sven_control_id), 1)
        self.assertEqual(self.row_count(), 3, "the supplied fields must not merge or drop any event")

    def test_unauthenticated_repair_fails_and_does_not_mutate_the_handoff(self) -> None:
        status, raw = self.request("POST", "/v2/integrity", token=None)
        self.assertEqual(status, 401)
        self.assertEqual(json.loads(raw)["error"], "unauthorized")

        status, raw = self.request("POST", "/v2/integrity", token="wrong-token")
        self.assertEqual(status, 401)

        self.assertEqual(self.row_count(), 3, "an unauthenticated attempt must never mutate the handoff events")

    def test_durable_event_set_is_visible_from_a_second_process(self) -> None:
        status, _ = self.request("POST", "/v2/integrity")
        self.assertEqual(status, 200)

        out_queue: multiprocessing.Queue = multiprocessing.Queue()
        reader = multiprocessing.Process(target=_reopen_and_list_events, args=(self.db_path, out_queue))
        reader.start()
        events = out_queue.get(timeout=30)
        reader.join(timeout=30)
        self.assertEqual(reader.exitcode, 0)

        self.assertEqual(len(events), 3, "the second process must see all three durable events")
        by_content_id = {event["content_id"]: event for event in events}
        self.assertEqual(set(by_content_id), {self.mina_first_id, self.mina_second_id, self.sven_control_id})

        self.assertEqual(by_content_id[self.mina_first_id]["actor"], "operator:mina")
        self.assertEqual(by_content_id[self.mina_first_id]["recorded_at"], self.MINA_FIRST_AT)
        self.assertEqual(by_content_id[self.mina_second_id]["actor"], "operator:mina")
        self.assertEqual(by_content_id[self.mina_second_id]["recorded_at"], self.MINA_SECOND_AT)
        self.assertEqual(by_content_id[self.sven_control_id]["actor"], "operator:sven")
        self.assertEqual(by_content_id[self.sven_control_id]["outcome"], "control")
        self.assertEqual(by_content_id[self.sven_control_id]["recorded_at"], self.SVEN_CONTROL_AT)

        recorded_times = {event["recorded_at"] for event in events}
        content_ids = {event["content_id"] for event in events}
        self.assertEqual(len(recorded_times), 3, "the target times must remain pairwise distinct")
        self.assertEqual(len(content_ids), 3, "the content ids must remain pairwise distinct")


if __name__ == "__main__":
    unittest.main()
