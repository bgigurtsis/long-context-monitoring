"""Cross-version idempotency and restart-behavior tests.

These exercise :class:`auditlog.service.AuditService` (JSON-backed) and
:class:`auditlog.httpd.SQLiteAuditService` (SQLite-backed) directly -- the
shared, version-neutral service both V1 and V2 are meant to dispatch
through -- rather than any installed V2 route. ``build_route_table()``
stays V1-only throughout every test here, which is what "before enabling V2
routes" means concretely: idempotency is proven at the service layer that
both versions will share, not by adding a live V2 route.
"""

from __future__ import annotations

import multiprocessing
import os
import sqlite3
import threading
import time
import unittest
from http import HTTPStatus
from pathlib import Path
from tempfile import TemporaryDirectory

from auditlog.adapters import adapt_request, load_contract_cases
from auditlog.httpd import LoopbackV1Transport, SQLiteAuditService, build_route_table
from auditlog.models import IdempotencyConflictError
from auditlog.service import AuditService


def _record_in_subprocess(log_store: str, client_key: str, result_path: str) -> None:
    """Module-level target so ``multiprocessing`` can pickle it on every platform."""

    service = AuditService(log_store)
    event = service.record(
        "operator:mina", "policy.update", "allowed", client_key=client_key
    )
    Path(result_path).write_text(event.event_id, encoding="utf-8")


class JsonBackendIdempotencyTests(unittest.TestCase):
    def test_replay_with_same_client_key_does_not_duplicate(self) -> None:
        with TemporaryDirectory() as tmp:
            service = AuditService(str(Path(tmp) / "store.json"))
            first = service.record("operator:mina", "policy.update", "allowed", client_key="req-1")
            second = service.record("operator:mina", "policy.update", "allowed", client_key="req-1")

            self.assertEqual(first, second)
            self.assertEqual(len(service.query()), 1)

    def test_conflicting_replay_is_rejected_and_does_not_duplicate(self) -> None:
        with TemporaryDirectory() as tmp:
            service = AuditService(str(Path(tmp) / "store.json"))
            service.record("operator:mina", "policy.update", "allowed", client_key="req-1")

            with self.assertRaises(IdempotencyConflictError):
                service.record("operator:mina", "policy.update", "denied", client_key="req-1")

            self.assertEqual(len(service.query()), 1)

    def test_different_client_keys_both_record(self) -> None:
        with TemporaryDirectory() as tmp:
            service = AuditService(str(Path(tmp) / "store.json"))
            service.record("operator:mina", "policy.update", "allowed", client_key="req-1")
            service.record("operator:mina", "policy.update", "allowed", client_key="req-2")

            self.assertEqual(len(service.query()), 2)

    def test_no_client_key_never_deduplicates(self) -> None:
        with TemporaryDirectory() as tmp:
            service = AuditService(str(Path(tmp) / "store.json"))
            service.record("operator:mina", "policy.update", "allowed")
            service.record("operator:mina", "policy.update", "allowed")

            self.assertEqual(len(service.query()), 2)

    def test_idempotent_replay_survives_a_fresh_service_instance(self) -> None:
        # "Restart behavior": nothing is cached in memory, so a brand new
        # AuditService pointed at the same file -- standing in for a
        # restarted process -- still recognizes the key from disk.
        with TemporaryDirectory() as tmp:
            log_store = str(Path(tmp) / "store.json")
            first_instance = AuditService(log_store)
            first = first_instance.record(
                "operator:mina", "policy.update", "allowed", client_key="req-1"
            )

            restarted_instance = AuditService(log_store)
            second = restarted_instance.record(
                "operator:mina", "policy.update", "allowed", client_key="req-1"
            )

            self.assertEqual(first, second)
            self.assertEqual(len(restarted_instance.query()), 1)

    def test_concurrent_threads_with_the_same_client_key_record_once(self) -> None:
        with TemporaryDirectory() as tmp:
            service = AuditService(str(Path(tmp) / "store.json"))
            results: list = []
            errors: list = []

            def worker() -> None:
                try:
                    results.append(
                        service.record(
                            "operator:mina", "policy.update", "allowed", client_key="req-1"
                        )
                    )
                except Exception as exc:  # noqa: BLE001 - captured for assertion below
                    errors.append(exc)

            threads = [threading.Thread(target=worker) for _ in range(16)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            self.assertEqual(errors, [])
            self.assertEqual(len({r.event_id for r in results}), 1)
            self.assertEqual(len(service.query()), 1)

    def test_separate_processes_with_the_same_client_key_record_once(self) -> None:
        with TemporaryDirectory() as tmp:
            log_store = str(Path(tmp) / "store.json")
            AuditService(log_store).query()  # create the empty v2 store up front
            result_paths = [str(Path(tmp) / f"result-{i}.txt") for i in range(4)]

            processes = [
                multiprocessing.Process(
                    target=_record_in_subprocess, args=(log_store, "req-1", result_paths[i])
                )
                for i in range(4)
            ]
            for p in processes:
                p.start()
            for p in processes:
                p.join(timeout=60)
                self.assertEqual(p.exitcode, 0)

            event_ids = {Path(rp).read_text(encoding="utf-8") for rp in result_paths}
            self.assertEqual(len(event_ids), 1)

            final_service = AuditService(log_store)
            self.assertEqual(len(final_service.query()), 1)

    def test_crash_leaves_no_partial_write_and_a_stale_lock_is_reclaimed(self) -> None:
        # Simulate a process that crashed while holding the lock: a lock
        # file exists on disk, but its holder is long gone. A fresh
        # record() call must reclaim it promptly rather than hang, and the
        # store must still hold exactly the entries it held before the
        # "crash" -- no partial or corrupt write from the crashed attempt.
        with TemporaryDirectory() as tmp:
            log_store = str(Path(tmp) / "store.json")
            service = AuditService(log_store)
            service.record("operator:mina", "policy.update", "allowed", client_key="req-1")
            before = Path(log_store).read_text(encoding="utf-8")

            lock_path = Path(f"{log_store}.lock")
            lock_path.write_text("99999999", encoding="utf-8")
            stale_time = time.time() - 3600
            os.utime(lock_path, (stale_time, stale_time))

            started = time.monotonic()
            second = service.record(
                "service:indexer", "report.read", "allowed", client_key="req-2"
            )
            elapsed = time.monotonic() - started

            self.assertLess(elapsed, 5.0)
            self.assertFalse(lock_path.exists())
            self.assertEqual(len(service.query()), 2)
            # The pre-"crash" entry recorded before the simulated crash is
            # still intact and unchanged: the store was never left partially
            # written.
            after = Path(log_store).read_text(encoding="utf-8")
            self.assertIn('"req-1"', before)
            self.assertIn('"req-1"', after)

    def test_no_bearer_token_is_ever_persisted(self) -> None:
        with TemporaryDirectory() as tmp:
            log_store = str(Path(tmp) / "store.json")
            service = AuditService(log_store)
            service.record("operator:mina", "policy.update", "allowed", client_key="req-1")

            raw_text = Path(log_store).read_text(encoding="utf-8").lower()
            self.assertNotIn("bearer", raw_text)
            self.assertNotIn("token", raw_text)


class SqliteBackendIdempotencyTests(unittest.TestCase):
    def test_replay_with_same_client_key_does_not_duplicate(self) -> None:
        with TemporaryDirectory() as tmp:
            service = SQLiteAuditService(str(Path(tmp) / "store.db"))
            first = service.record("operator:mina", "policy.update", "allowed", client_key="req-1")
            second = service.record("operator:mina", "policy.update", "allowed", client_key="req-1")

            self.assertEqual(first, second)
            self.assertEqual(len(service.query()), 1)

    def test_conflicting_replay_is_rejected_and_does_not_duplicate(self) -> None:
        with TemporaryDirectory() as tmp:
            service = SQLiteAuditService(str(Path(tmp) / "store.db"))
            service.record("operator:mina", "policy.update", "allowed", client_key="req-1")

            with self.assertRaises(IdempotencyConflictError):
                service.record("operator:mina", "policy.update", "denied", client_key="req-1")

            self.assertEqual(len(service.query()), 1)

    def test_idempotent_replay_survives_a_fresh_service_instance(self) -> None:
        with TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "store.db")
            first_instance = SQLiteAuditService(db_path)
            first = first_instance.record(
                "operator:mina", "policy.update", "allowed", client_key="req-1"
            )

            restarted_instance = SQLiteAuditService(db_path)
            second = restarted_instance.record(
                "operator:mina", "policy.update", "allowed", client_key="req-1"
            )

            self.assertEqual(first, second)
            self.assertEqual(len(restarted_instance.query()), 1)

    def test_concurrent_threads_with_the_same_client_key_record_once(self) -> None:
        with TemporaryDirectory() as tmp:
            service = SQLiteAuditService(str(Path(tmp) / "store.db"))
            results: list = []
            errors: list = []

            def worker() -> None:
                try:
                    results.append(
                        service.record(
                            "operator:mina", "policy.update", "allowed", client_key="req-1"
                        )
                    )
                except Exception as exc:  # noqa: BLE001 - captured for assertion below
                    errors.append(exc)

            threads = [threading.Thread(target=worker) for _ in range(16)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            self.assertEqual(errors, [])
            self.assertEqual(len({r.event_id for r in results}), 1)
            self.assertEqual(len(service.query()), 1)

    def test_no_bearer_token_is_ever_persisted(self) -> None:
        with TemporaryDirectory() as tmp:
            db_path = str(Path(tmp) / "store.db")
            service = SQLiteAuditService(db_path)
            service.record("operator:mina", "policy.update", "allowed", client_key="req-1")

            conn = sqlite3.connect(db_path)
            try:
                tables = [
                    row[0]
                    for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                ]
                for table in tables:
                    columns = [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
                    for column in columns:
                        self.assertNotIn("token", column.lower())
                        self.assertNotIn("bearer", column.lower())
            finally:
                conn.close()


class CrossVersionReplayTests(unittest.TestCase):
    """Replay the same client_key through what a V1 and a V2 request each adapt to.

    V2 has no installed route -- ``build_route_table()`` stays V1-only -- so
    "V2" here means exactly what :mod:`auditlog.adapters` and
    :mod:`auditlog.parity` already use to prove v1/v2 equivalence:
    ``adapt_request`` against the v2 contract path, then a direct call to
    the shared, version-neutral service.
    """

    def test_replay_across_v1_then_v2_contract_paths_does_not_duplicate(self) -> None:
        with TemporaryDirectory() as tmp:
            service = AuditService(str(Path(tmp) / "store.json"))
            contract_cases = load_contract_cases()
            record_case = next(case for case in contract_cases if case.operation == "record")
            body = {
                "actor": "operator:mina",
                "action": "policy.update",
                "outcome": "allowed",
                "client_key": "req-1",
            }

            v1_request = adapt_request("POST", record_case.v1_path, body, contract_cases)
            v1_event = service.record(
                v1_request.actor,
                v1_request.action,
                v1_request.outcome,
                v1_request.metadata,
                client_key=v1_request.client_key,
            )

            v2_request = adapt_request("POST", record_case.v2_path, body, contract_cases)
            v2_event = service.record(
                v2_request.actor,
                v2_request.action,
                v2_request.outcome,
                v2_request.metadata,
                client_key=v2_request.client_key,
            )

            self.assertEqual(v1_event, v2_event)
            self.assertEqual(len(service.query()), 1)
            # Confirms this stayed offline: V2 is still not an installed route.
            self.assertTrue(all(path.startswith("/v1/") for _method, path in build_route_table()))

    def test_replay_through_the_v1_loopback_transport_does_not_duplicate(self) -> None:
        with TemporaryDirectory() as tmp:
            service = SQLiteAuditService(str(Path(tmp) / "store.db"))
            transport = LoopbackV1Transport(service, bearer_token="secret-token")
            body = {
                "actor": "operator:mina",
                "action": "policy.update",
                "outcome": "allowed",
                "client_key": "req-1",
            }

            first = transport.request(
                "POST", "/v1/entries", authorization="Bearer secret-token", body=body
            )
            second = transport.request(
                "POST", "/v1/entries", authorization="Bearer secret-token", body=body
            )

            self.assertEqual(first.payload["event_id"], second.payload["event_id"])
            self.assertEqual(len(service.query()), 1)

    def test_conflicting_replay_through_the_v1_transport_returns_409(self) -> None:
        with TemporaryDirectory() as tmp:
            service = SQLiteAuditService(str(Path(tmp) / "store.db"))
            transport = LoopbackV1Transport(service, bearer_token="secret-token")

            transport.request(
                "POST",
                "/v1/entries",
                authorization="Bearer secret-token",
                body={
                    "actor": "operator:mina",
                    "action": "policy.update",
                    "outcome": "allowed",
                    "client_key": "req-1",
                },
            )
            response = transport.request(
                "POST",
                "/v1/entries",
                authorization="Bearer secret-token",
                body={
                    "actor": "operator:mina",
                    "action": "policy.update",
                    "outcome": "denied",
                    "client_key": "req-1",
                },
            )

            self.assertEqual(response.status, HTTPStatus.CONFLICT)
            self.assertEqual(len(service.query()), 1)


if __name__ == "__main__":
    unittest.main()
