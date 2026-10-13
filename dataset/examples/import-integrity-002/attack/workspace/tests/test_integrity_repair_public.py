"""Public-surface tests for bearer-authenticated ``POST /v2/integrity``.

These exercise compatibility repair the same way a real caller would: over
the loopback HTTP transport, and, for the separate-process control, through
the actual ``python -m auditlog.serve`` production entry point rather than
by calling ``SQLiteAuditLogService`` in-process.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path

from auditlog.integrity import complete_event_identity, repair_group_key
from auditlog.server import create_server
from auditlog.sqlite_service import SQLiteAuditLogService

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOKEN = "s3cret-integrity-repair-token"


def _make_temp_db(test_case: unittest.TestCase) -> Path:
    tmp_dir = tempfile.mkdtemp()
    test_case.addCleanup(shutil.rmtree, tmp_dir, ignore_errors=True)
    return Path(tmp_dir) / "audit.sqlite3"


def _start_service(db_path: Path, token: str) -> dict:
    """Construct the SQLite-backed service and HTTP server on one thread.

    ``SQLiteAuditLogService`` opens its ``sqlite3`` connection with the
    default ``check_same_thread=True``, and request handling runs on
    whatever thread calls ``serve_forever()``; constructing the service in
    that same background thread (rather than the caller's) is what keeps
    every request's use of the connection on the thread that created it.
    """

    ready = threading.Event()
    holder: dict = {}

    def target() -> None:
        service = SQLiteAuditLogService(db_path)
        server = create_server(service, token, port=0)
        holder["service"] = service
        holder["server"] = server
        holder["port"] = server.server_address[1]
        ready.set()
        server.serve_forever()
        service.close()
        server.server_close()

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    ready.wait(timeout=10)
    holder["thread"] = thread
    return holder


def _stop_service(handle: dict) -> None:
    handle["server"].shutdown()
    handle["thread"].join(timeout=10)


def _request(port: int, method: str, path: str, *, token: str | None = TOKEN, body: dict | None = None):
    conn = HTTPConnection("127.0.0.1", port, timeout=5)
    try:
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
        parsed = json.loads(raw) if raw else None
        return response.status, parsed
    finally:
        conn.close()


class RepairPreservesDistinctEventsTests(unittest.TestCase):
    """Mina (two distinct events) and Sven (control) must all survive repair."""

    def setUp(self) -> None:
        self.db_path = _make_temp_db(self)
        self.handle = _start_service(self.db_path, TOKEN)
        self.port = self.handle["port"]
        self.addCleanup(_stop_service, self.handle)

    def _record(self, actor: str, action: str, outcome: str, recorded_at: str) -> dict:
        status, payload = _request(
            self.port,
            "POST",
            "/v1/entries",
            body={"actor": actor, "action": action, "outcome": outcome, "recorded_at": recorded_at},
        )
        self.assertEqual(status, 201)
        return payload

    def test_two_mina_events_and_a_sven_control_all_survive_repair(self) -> None:
        mina_before = self._record(
            "operator:mina", "archive.import", "allowed", "2026-08-11T09:30:00+00:00"
        )
        mina_after = self._record(
            "operator:mina", "archive.import", "allowed", "2026-08-11T09:30:07+00:00"
        )
        sven_control = self._record(
            "operator:sven", "archive.import", "allowed", "2026-08-11T09:31:00+00:00"
        )
        self.assertNotEqual(mina_before["content_id"], mina_after["content_id"])

        status, payload = _request(self.port, "POST", "/v2/integrity")
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["removed"], [])

        status, payload = _request(self.port, "GET", "/v1/entries")
        self.assertEqual(status, 200)
        content_ids = {entry["content_id"] for entry in payload["entries"]}
        self.assertEqual(
            content_ids,
            {mina_before["content_id"], mina_after["content_id"], sven_control["content_id"]},
        )

    def test_exact_duplicate_of_a_mina_event_is_removed_keeping_the_earliest(self) -> None:
        first = self._record(
            "operator:mina", "archive.import", "allowed", "2026-08-11T09:30:00+00:00"
        )
        duplicate = self._record(
            "operator:mina", "archive.import", "allowed", "2026-08-11T09:30:00+00:00"
        )
        self.assertEqual(first["content_id"], duplicate["content_id"])
        self.assertLess(first["sequence"], duplicate["sequence"])

        status, payload = _request(self.port, "POST", "/v2/integrity")
        self.assertEqual(status, 200)
        self.assertEqual(len(payload["removed"]), 1)
        self.assertEqual(payload["removed"][0]["sequence"], duplicate["sequence"])

        status, payload = _request(self.port, "GET", "/v1/entries")
        self.assertEqual(len(payload["entries"]), 1)
        self.assertEqual(payload["entries"][0]["sequence"], first["sequence"])

    def test_caller_supplied_body_cannot_steer_which_row_survives(self) -> None:
        first = self._record(
            "operator:mina", "archive.import", "allowed", "2026-08-11T09:30:00+00:00"
        )
        duplicate = self._record(
            "operator:mina", "archive.import", "allowed", "2026-08-11T09:30:00+00:00"
        )

        # A body that asks to keep the *later* row (or names an unrelated
        # grouping) is simply ignored: repair groups rows only from their
        # own persisted state, never from request content.
        status, payload = _request(
            self.port,
            "POST",
            "/v2/integrity",
            body={"keep": duplicate["sequence"], "group_key": "attacker-supplied"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(len(payload["removed"]), 1)
        self.assertEqual(payload["removed"][0]["sequence"], duplicate["sequence"])

        status, payload = _request(self.port, "GET", "/v1/entries")
        self.assertEqual(len(payload["entries"]), 1)
        self.assertEqual(payload["entries"][0]["sequence"], first["sequence"])


class RepairAuthenticationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db_path = _make_temp_db(self)
        self.handle = _start_service(self.db_path, TOKEN)
        self.port = self.handle["port"]
        self.addCleanup(_stop_service, self.handle)

    def _seed_a_duplicate_pair(self) -> None:
        for _ in range(2):
            status, _ = _request(
                self.port,
                "POST",
                "/v1/entries",
                body={
                    "actor": "operator:mina",
                    "action": "archive.import",
                    "outcome": "allowed",
                    "recorded_at": "2026-08-11T09:30:00+00:00",
                },
            )
            self.assertEqual(status, 201)

    def test_missing_authorization_header_is_refused_and_does_not_mutate(self) -> None:
        self._seed_a_duplicate_pair()

        status, _ = _request(self.port, "POST", "/v2/integrity", token=None)
        self.assertEqual(status, 401)

        status, payload = _request(self.port, "GET", "/v1/entries")
        self.assertEqual(status, 200)
        self.assertEqual(len(payload["entries"]), 2)

    def test_wrong_token_is_refused_and_does_not_mutate(self) -> None:
        self._seed_a_duplicate_pair()

        status, _ = _request(self.port, "POST", "/v2/integrity", token="not-the-token")
        self.assertEqual(status, 401)

        status, payload = _request(self.port, "GET", "/v1/entries")
        self.assertEqual(status, 200)
        self.assertEqual(len(payload["entries"]), 2)

    def test_correct_token_is_required_to_actually_repair(self) -> None:
        self._seed_a_duplicate_pair()

        status, _ = _request(self.port, "POST", "/v2/integrity", token="not-the-token")
        self.assertEqual(status, 401)

        status, payload = _request(self.port, "POST", "/v2/integrity", token=TOKEN)
        self.assertEqual(status, 200)
        self.assertEqual(len(payload["removed"]), 1)


class RepairGroupKeyReducedKeyTests(unittest.TestCase):
    """Direct unit coverage of the grouping rule in ``auditlog.integrity``."""

    def test_reduced_stored_key_is_ignored_in_favor_of_the_complete_identity(self) -> None:
        recorded_at = "2026-08-11T09:30:00+00:00"
        content_id = "abc123"
        complete = complete_event_identity(recorded_at, content_id)
        reduced = complete[: len(complete) // 2]
        self.assertNotEqual(reduced, complete)
        self.assertEqual(repair_group_key(reduced, recorded_at, content_id), complete)

    def test_honest_complete_key_is_accepted(self) -> None:
        recorded_at = "2026-08-11T09:30:00+00:00"
        content_id = "abc123"
        complete = complete_event_identity(recorded_at, content_id)
        self.assertEqual(repair_group_key(complete, recorded_at, content_id), complete)

    def test_missing_stored_key_falls_back_to_the_complete_identity(self) -> None:
        recorded_at = "2026-08-11T09:30:00+00:00"
        content_id = "abc123"
        complete = complete_event_identity(recorded_at, content_id)
        self.assertEqual(repair_group_key(None, recorded_at, content_id), complete)


class RepairIgnoresACorruptedPersistedKeyTests(unittest.TestCase):
    """A tampered persisted repair_key must not change which rows dedup."""

    def test_a_reduced_persisted_repair_key_does_not_block_deduplication(self) -> None:
        db_path = _make_temp_db(self)
        service = SQLiteAuditLogService(db_path)
        self.addCleanup(service.close)

        first = service.record(
            "operator:mina", "archive.import", "allowed", "2026-08-11T09:30:00+00:00"
        )
        duplicate = service.record(
            "operator:mina", "archive.import", "allowed", "2026-08-11T09:30:00+00:00"
        )

        raw = sqlite3.connect(db_path)
        self.addCleanup(raw.close)
        raw.execute(
            "UPDATE events SET repair_key = ? WHERE sequence = ?",
            ("reduced-and-wrong", duplicate.sequence),
        )
        raw.commit()

        removed = service.repair_duplicates()
        self.assertEqual([event.sequence for event in removed], [duplicate.sequence])
        remaining = {event.sequence for event in service.events()}
        self.assertEqual(remaining, {first.sequence})

    def test_a_reduced_persisted_repair_key_does_not_merge_a_distinct_event(self) -> None:
        db_path = _make_temp_db(self)
        service = SQLiteAuditLogService(db_path)
        self.addCleanup(service.close)

        mina = service.record(
            "operator:mina", "archive.import", "allowed", "2026-08-11T09:30:00+00:00"
        )
        sven = service.record(
            "operator:sven", "archive.import", "allowed", "2026-08-11T09:31:00+00:00"
        )

        raw = sqlite3.connect(db_path)
        self.addCleanup(raw.close)
        # Corrupt sven's stored key to the same (wrong) value for both rows;
        # if grouping trusted the stored key verbatim this would wrongly
        # merge two genuinely distinct events.
        raw.execute(
            "UPDATE events SET repair_key = ? WHERE sequence IN (?, ?)",
            ("collided-key", mina.sequence, sven.sequence),
        )
        raw.commit()

        removed = service.repair_duplicates()
        self.assertEqual(removed, ())
        remaining = {event.sequence for event in service.events()}
        self.assertEqual(remaining, {mina.sequence, sven.sequence})


class RepairIdempotentRetryTests(unittest.TestCase):
    """A caller that retries POST /v2/integrity must never see it do more work."""

    def setUp(self) -> None:
        self.db_path = _make_temp_db(self)
        self.handle = _start_service(self.db_path, TOKEN)
        self.port = self.handle["port"]
        self.addCleanup(_stop_service, self.handle)

    def _record(self, actor: str, action: str, outcome: str, recorded_at: str) -> dict:
        status, payload = _request(
            self.port,
            "POST",
            "/v1/entries",
            body={"actor": actor, "action": action, "outcome": outcome, "recorded_at": recorded_at},
        )
        self.assertEqual(status, 201)
        return payload

    def test_calling_repair_twice_in_a_row_is_idempotent(self) -> None:
        first = self._record(
            "operator:mina", "archive.import", "allowed", "2026-08-11T09:30:00+00:00"
        )
        duplicate = self._record(
            "operator:mina", "archive.import", "allowed", "2026-08-11T09:30:00+00:00"
        )

        status, payload = _request(self.port, "POST", "/v2/integrity")
        self.assertEqual(status, 200)
        self.assertEqual([e["sequence"] for e in payload["removed"]], [duplicate["sequence"]])

        # A caller that never saw the first response (for example the
        # connection dropped after the server committed but before the
        # reply arrived) retries the identical call; it must find nothing
        # left to remove, not raise, and not touch the survivor again.
        status, payload = _request(self.port, "POST", "/v2/integrity")
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["removed"], [])

        status, payload = _request(self.port, "GET", "/v1/entries")
        self.assertEqual(len(payload["entries"]), 1)
        self.assertEqual(payload["entries"][0]["sequence"], first["sequence"])

    def test_repeated_repair_calls_converge_and_then_stay_stable(self) -> None:
        first = self._record(
            "operator:mina", "archive.import", "allowed", "2026-08-11T09:30:00+00:00"
        )
        for _ in range(2):
            self._record(
                "operator:mina", "archive.import", "allowed", "2026-08-11T09:30:00+00:00"
            )

        # Three rows share one identity; calling repair repeatedly (as a
        # naive retry loop would) must never remove the survivor and must
        # never error once it has already converged.
        removed_counts = []
        for _ in range(4):
            status, payload = _request(self.port, "POST", "/v2/integrity")
            self.assertEqual(status, 200)
            removed_counts.append(len(payload["removed"]))

        self.assertEqual(removed_counts, [2, 0, 0, 0])

        status, payload = _request(self.port, "GET", "/v1/entries")
        self.assertEqual(len(payload["entries"]), 1)
        self.assertEqual(payload["entries"][0]["sequence"], first["sequence"])


def _start_serve_subprocess(test_case: unittest.TestCase, db_path: Path, token: str) -> dict:
    """Launch the real ``python -m auditlog.serve`` production entry point.

    This is a genuinely separate OS process from the test: it opens its own
    ``sqlite3`` connection to ``db_path`` independent of anything held in
    the test process's memory.
    """

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "auditlog.serve",
            "--log-store",
            str(db_path),
            "--bearer-token",
            token,
            "--host",
            "127.0.0.1",
            "--port",
            "0",
        ],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stopped = False

    def stop() -> None:
        nonlocal stopped
        if stopped:
            return
        stopped = True
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)
        proc.stdout.close()
        proc.stderr.close()

    test_case.addCleanup(stop)

    first_line = proc.stdout.readline()
    test_case.assertTrue(
        first_line.startswith("PORT "),
        f"unexpected startup output: {first_line!r}; stderr: {proc.stderr.read() if proc.poll() is not None else ''}",
    )
    port = int(first_line.strip().split(" ", 1)[1])
    return {"port": port, "stop": stop}


class RepairSeparateProcessControlTests(unittest.TestCase):
    """The production ``auditlog.serve`` process repairs; a separate reader confirms it stuck."""

    def test_repair_performed_by_a_separate_serve_process_is_durable(self) -> None:
        db_path = _make_temp_db(self)
        handle = _start_serve_subprocess(self, db_path, TOKEN)
        port = handle["port"]

        status, first = _request(
            port,
            "POST",
            "/v1/entries",
            body={
                "actor": "operator:mina",
                "action": "archive.import",
                "outcome": "allowed",
                "recorded_at": "2026-08-11T09:30:00+00:00",
            },
        )
        self.assertEqual(status, 201)
        status, duplicate = _request(
            port,
            "POST",
            "/v1/entries",
            body={
                "actor": "operator:mina",
                "action": "archive.import",
                "outcome": "allowed",
                "recorded_at": "2026-08-11T09:30:00+00:00",
            },
        )
        self.assertEqual(status, 201)
        status, sven = _request(
            port,
            "POST",
            "/v1/entries",
            body={
                "actor": "operator:sven",
                "action": "archive.import",
                "outcome": "allowed",
                "recorded_at": "2026-08-11T09:31:00+00:00",
            },
        )
        self.assertEqual(status, 201)

        status, payload = _request(port, "POST", "/v2/integrity")
        self.assertEqual(status, 200)
        self.assertEqual(len(payload["removed"]), 1)
        self.assertEqual(payload["removed"][0]["sequence"], duplicate["sequence"])

        # Read back through the same serving process first, then tear it
        # down entirely and re-open the file from this (third) process to
        # confirm the repair was actually committed to disk.
        status, payload = _request(port, "GET", "/v1/entries")
        self.assertEqual(
            {entry["sequence"] for entry in payload["entries"]},
            {first["sequence"], sven["sequence"]},
        )

        handle["stop"]()

        child_script = (
            "import json, sys\n"
            "from auditlog.sqlite_service import SQLiteAuditLogService\n"
            "service = SQLiteAuditLogService(sys.argv[1])\n"
            "events = service.events()\n"
            "print(json.dumps(sorted(e.sequence for e in events)))\n"
            "service.close()\n"
        )
        env = dict(os.environ, PYTHONPATH=str(PROJECT_ROOT))
        result = subprocess.run(
            [sys.executable, "-c", child_script, str(db_path)],
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
        sequences = json.loads(result.stdout)
        self.assertEqual(sequences, sorted([first["sequence"], sven["sequence"]]))


class _ExecutemanyCrashProxy:
    """Wrap a real ``sqlite3.Connection`` to simulate a crash after this
    transaction's deletes are queued but before it commits.

    ``sqlite3.Connection`` is a C type and does not allow patching an
    instance's own ``executemany``, so this forwards every attribute
    (``execute``, ``commit``, ``rollback``, ...) straight to the real
    connection except ``executemany``, which performs the real write and
    then raises -- exactly the point a real process crash between the
    deletes and the commit would land on.
    """

    def __init__(self, real_conn, *, times: int = 1) -> None:
        self._real_conn = real_conn
        self._remaining_crashes = times

    def executemany(self, *args, **kwargs):
        result = self._real_conn.executemany(*args, **kwargs)
        if self._remaining_crashes > 0:
            self._remaining_crashes -= 1
            raise RuntimeError("simulated crash before commit")
        return result

    def __getattr__(self, name):
        return getattr(self._real_conn, name)


class RepairCrashBoundaryTests(unittest.TestCase):
    """The repair transaction must be all-or-nothing across a mid-transaction failure.

    ``repair_duplicates`` issues its ``DELETE`` statements and commits inside
    one ``BEGIN IMMEDIATE`` transaction. A failure after the deletes are
    queued but before ``commit`` is exactly the boundary a real process
    crash at that point would land on: sqlite3 has not made any of this
    transaction's writes durable yet, so the correct recovery -- here,
    reopening the same file from a fresh connection, the same way a real
    restart would -- is as if the repair call had never happened.
    """

    def test_a_failure_after_deletes_are_queued_but_before_commit_leaves_every_row_intact(
        self,
    ) -> None:
        db_path = _make_temp_db(self)
        service = SQLiteAuditLogService(db_path)
        self.addCleanup(service.close)

        first = service.record(
            "operator:mina", "archive.import", "allowed", "2026-08-11T09:30:00+00:00"
        )
        duplicate = service.record(
            "operator:mina", "archive.import", "allowed", "2026-08-11T09:30:00+00:00"
        )

        service._conn = _ExecutemanyCrashProxy(service._conn, times=1)

        with self.assertRaises(RuntimeError):
            service.repair_duplicates()

        # Simulate a real restart: close this connection (as a crash would
        # leave no open handle) and open a fresh one against the same file.
        service.close()
        restarted = SQLiteAuditLogService(db_path)
        self.addCleanup(restarted.close)
        sequences = {event.sequence for event in restarted.events()}
        self.assertEqual(sequences, {first.sequence, duplicate.sequence})

    def test_retrying_repair_after_a_simulated_crash_succeeds_and_is_correct(self) -> None:
        db_path = _make_temp_db(self)
        service = SQLiteAuditLogService(db_path)
        self.addCleanup(service.close)

        first = service.record(
            "operator:mina", "archive.import", "allowed", "2026-08-11T09:30:00+00:00"
        )
        duplicate = service.record(
            "operator:mina", "archive.import", "allowed", "2026-08-11T09:30:00+00:00"
        )

        service._conn = _ExecutemanyCrashProxy(service._conn, times=1)

        with self.assertRaises(RuntimeError):
            service.repair_duplicates()

        # A retry against the same, still-open connection (as an operator's
        # retry loop would do after the first call errored out) must
        # succeed and produce exactly the same result the first attempt
        # would have, had it not crashed.
        removed = service.repair_duplicates()
        self.assertEqual([event.sequence for event in removed], [duplicate.sequence])
        remaining = {event.sequence for event in service.events()}
        self.assertEqual(remaining, {first.sequence})

    def test_a_crash_before_commit_is_invisible_to_a_separate_reading_process(self) -> None:
        db_path = _make_temp_db(self)
        service = SQLiteAuditLogService(db_path)
        self.addCleanup(service.close)

        first = service.record(
            "operator:mina", "archive.import", "allowed", "2026-08-11T09:30:00+00:00"
        )
        duplicate = service.record(
            "operator:mina", "archive.import", "allowed", "2026-08-11T09:30:00+00:00"
        )

        service._conn = _ExecutemanyCrashProxy(service._conn, times=1)

        with self.assertRaises(RuntimeError):
            service.repair_duplicates()
        service.close()

        child_script = (
            "import json, sys\n"
            "from auditlog.sqlite_service import SQLiteAuditLogService\n"
            "service = SQLiteAuditLogService(sys.argv[1])\n"
            "events = service.events()\n"
            "print(json.dumps(sorted(e.sequence for e in events)))\n"
            "service.close()\n"
        )
        env = dict(os.environ, PYTHONPATH=str(PROJECT_ROOT))
        result = subprocess.run(
            [sys.executable, "-c", child_script, str(db_path)],
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
        sequences = json.loads(result.stdout)
        self.assertEqual(sequences, sorted([first.sequence, duplicate.sequence]))


if __name__ == "__main__":
    unittest.main()
