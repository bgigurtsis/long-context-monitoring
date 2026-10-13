"""Proxy rollout event imports: parsing, reconciliation, and safety under
concurrency, repeated calls, and separate processes -- all through
AuditService."""

from __future__ import annotations

import multiprocessing
import shutil
import tempfile
import threading
import unittest
from pathlib import Path

from auditlog.proxy_rollout import (
    PROXY_ROLLOUT_ACTOR,
    PROXY_ROLLOUT_OUTCOME,
    ProxyRolloutImportError,
    ProxyRolloutRecord,
    parse_proxy_rollout_events,
    read_proxy_rollout_events,
    translate_proxy_rollout_record,
)
from auditlog.service import AuditService
from auditlog.store import IntegrityError, JsonLogStore, SqliteLogStore

FIXTURES = Path(__file__).parent.parent / "fixtures"

RECORDS = [
    ProxyRolloutRecord(sequence=1, event="proxy-canary-start", details={"peer": "127.0.0.1"}),
    ProxyRolloutRecord(sequence=2, event="proxy-canary-verified", details={"protected_routes": 3}),
    ProxyRolloutRecord(sequence=3, event="proxy-canary-promoted", details={"peer": "127.0.0.1"}),
]


class ParsingTests(unittest.TestCase):
    def test_parses_the_real_fixture(self) -> None:
        records = read_proxy_rollout_events(FIXTURES / "proxy-rollout-events.jsonl")
        self.assertEqual(
            records,
            [
                ProxyRolloutRecord(sequence=1, event="proxy-canary-start", details={"peer": "127.0.0.1"}),
                ProxyRolloutRecord(sequence=2, event="proxy-canary-verified", details={"protected_routes": 3}),
            ],
        )

    def test_sorts_by_sequence_regardless_of_line_order(self) -> None:
        text = '{"sequence": 2, "event": "b"}\n{"sequence": 1, "event": "a"}\n'
        records = parse_proxy_rollout_events(text)
        self.assertEqual([r.sequence for r in records], [1, 2])

    def test_skips_blank_lines(self) -> None:
        text = '{"sequence": 1, "event": "a"}\n\n   \n{"sequence": 2, "event": "b"}\n'
        records = parse_proxy_rollout_events(text)
        self.assertEqual(len(records), 2)

    def test_duplicate_sequence_in_one_source_is_rejected(self) -> None:
        text = '{"sequence": 1, "event": "a"}\n{"sequence": 1, "event": "b"}\n'
        with self.assertRaises(ProxyRolloutImportError):
            parse_proxy_rollout_events(text)

    def test_missing_sequence_is_rejected(self) -> None:
        with self.assertRaises(ProxyRolloutImportError):
            parse_proxy_rollout_events('{"event": "a"}\n')

    def test_missing_event_is_rejected(self) -> None:
        with self.assertRaises(ProxyRolloutImportError):
            parse_proxy_rollout_events('{"sequence": 1}\n')

    def test_non_integer_sequence_is_rejected(self) -> None:
        with self.assertRaises(ProxyRolloutImportError):
            parse_proxy_rollout_events('{"sequence": "1", "event": "a"}\n')

    def test_zero_sequence_is_rejected(self) -> None:
        with self.assertRaises(ProxyRolloutImportError):
            parse_proxy_rollout_events('{"sequence": 0, "event": "a"}\n')

    def test_malformed_json_is_rejected(self) -> None:
        with self.assertRaises(ProxyRolloutImportError):
            parse_proxy_rollout_events("not json\n")


class TranslationTests(unittest.TestCase):
    def test_identity_fields_are_deterministic_and_reserved(self) -> None:
        record = ProxyRolloutRecord(sequence=7, event="proxy-canary-start", details={"peer": "127.0.0.1"})
        actor, action, outcome, recorded_at, metadata = translate_proxy_rollout_record(record)
        self.assertEqual(actor, PROXY_ROLLOUT_ACTOR)
        self.assertEqual(action, "proxy-canary-start")
        self.assertEqual(outcome, PROXY_ROLLOUT_OUTCOME)
        self.assertIn("000000000007", recorded_at)

    def test_repeated_translation_is_identical(self) -> None:
        record = ProxyRolloutRecord(sequence=1, event="proxy-canary-start")
        self.assertEqual(translate_proxy_rollout_record(record), translate_proxy_rollout_record(record))

    def test_provenance_lands_in_metadata_not_identity(self) -> None:
        record = ProxyRolloutRecord(sequence=1, event="proxy-canary-start", details={"peer": "127.0.0.1"})
        _, _, _, _, metadata = translate_proxy_rollout_record(record)
        self.assertEqual(metadata["proxy_source_sequence"], 1)
        self.assertEqual(metadata["proxy_details"], {"peer": "127.0.0.1"})


class _ReconciliationBehaviorMixin:
    """Shared reconciliation behavior, run against both store backends."""

    def make_store(self):
        raise NotImplementedError

    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self._tmpdir, ignore_errors=True)
        self.service = AuditService(self.make_store())

    def test_first_reconciliation_imports_every_record(self) -> None:
        report = self.service.reconcile_proxy_rollout(RECORDS)
        self.assertEqual(report.source_records, 3)
        self.assertEqual(report.imported, 3)
        self.assertEqual(report.already_present, 0)
        self.assertEqual(report.entries_checked, 3)

        imported = self.service.query(actor=PROXY_ROLLOUT_ACTOR)
        self.assertEqual([e.action for e in imported], [r.event for r in RECORDS])
        self.assertEqual([e.sequence for e in imported], [1, 2, 3])

    def test_repeated_reconciliation_is_idempotent(self) -> None:
        self.service.reconcile_proxy_rollout(RECORDS)
        second = self.service.reconcile_proxy_rollout(RECORDS)
        self.assertEqual(second.imported, 0)
        self.assertEqual(second.already_present, 3)
        self.assertEqual(len(self.service.query()), 3)

    def test_native_events_stay_distinct_from_proxy_imports(self) -> None:
        native = self.service.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        self.service.reconcile_proxy_rollout(RECORDS)
        second_native = self.service.record("operator:mina", "key.revoke", "allowed", recorded_at="T2")

        all_events = self.service.query()
        self.assertEqual(len(all_events), 5)
        self.assertEqual([e.sequence for e in all_events], [1, 2, 3, 4, 5])

        native_events = self.service.query(actor="operator:mina")
        self.assertEqual([e.event_id for e in native_events], [native.event_id, second_native.event_id])

        proxy_events = self.service.query(actor=PROXY_ROLLOUT_ACTOR)
        self.assertEqual(len(proxy_events), 3)
        self.assertTrue(all(e.outcome == PROXY_ROLLOUT_OUTCOME for e in proxy_events))

    def test_record_rejects_the_reserved_proxy_actor(self) -> None:
        with self.assertRaises(ValueError):
            self.service.record(PROXY_ROLLOUT_ACTOR, "policy.update", "allowed", recorded_at="T1")

    def test_interrupted_import_resumes_without_reimporting_or_reordering(self) -> None:
        # Simulate a crash after the first record was durably appended but
        # before the batch finished, using the store's own primitive.
        store = self.service._store  # noqa: SLF001 -- test needs to poke the store directly
        first_actor, first_action, first_outcome, first_recorded_at, first_metadata = translate_proxy_rollout_record(
            RECORDS[0]
        )
        partial_event, created = store.append_if_absent(
            first_actor, first_action, first_outcome, first_recorded_at, first_metadata
        )
        self.assertTrue(created)

        report = self.service.reconcile_proxy_rollout(RECORDS)
        self.assertEqual(report.imported, 2)
        self.assertEqual(report.already_present, 1)

        all_events = self.service.query()
        self.assertEqual(len(all_events), 3)
        # The record written before the "crash" is untouched: same identity,
        # same trail position.
        self.assertEqual(all_events[0], partial_event)

    def test_conflicting_reimport_of_the_same_sequence_is_rejected(self) -> None:
        self.service.reconcile_proxy_rollout([RECORDS[0]])
        conflicting = ProxyRolloutRecord(sequence=1, event="a-different-event-name")
        with self.assertRaises(ProxyRolloutImportError):
            self.service.reconcile_proxy_rollout([conflicting])
        # Nothing was appended by the rejected call.
        self.assertEqual(len(self.service.query()), 1)

    def test_repair_after_reconciliation_does_not_alter_the_trail(self) -> None:
        self.service.reconcile_proxy_rollout(RECORDS)
        before = self.service.query()
        report = self.service.repair()
        self.assertEqual(report.entries_checked, 3)
        self.assertEqual(self.service.query(), before)

    def test_reconciliation_detects_a_tampered_trail(self) -> None:
        self.service.reconcile_proxy_rollout(RECORDS)
        self._tamper_first_entry()
        with self.assertRaises(IntegrityError):
            self.service.reconcile_proxy_rollout(RECORDS)

    def _tamper_first_entry(self) -> None:
        raise NotImplementedError


class JsonStoreReconciliationTests(_ReconciliationBehaviorMixin, unittest.TestCase):
    def make_store(self) -> JsonLogStore:
        self.store_path = Path(self._tmpdir) / "store.db"
        return JsonLogStore(self.store_path)

    def _tamper_first_entry(self) -> None:
        import json

        raw = json.loads(self.store_path.read_text())
        raw["entries"][0]["action"] = "tampered"
        self.store_path.write_text(json.dumps(raw))


class SqliteStoreReconciliationTests(_ReconciliationBehaviorMixin, unittest.TestCase):
    def make_store(self) -> SqliteLogStore:
        self.store_path = Path(self._tmpdir) / "store.sqlite"
        return SqliteLogStore(self.store_path)

    def _tamper_first_entry(self) -> None:
        import sqlite3

        conn = sqlite3.connect(str(self.store_path))
        conn.execute("UPDATE entries SET action = 'tampered' WHERE sequence = 1")
        conn.commit()
        conn.close()


def _reconcile_worker(store_kind: str, store_path: str, records: list[ProxyRolloutRecord]) -> None:
    """Top-level, picklable worker: build a fresh store/service and reconcile.

    Used by both the threading and the multiprocessing tests below so a
    genuinely separate OS process (not just a separate thread sharing this
    interpreter's store object) opens its own store handle against the same
    path and calls the service the same way a real caller would.
    """

    if store_kind == "json":
        store = JsonLogStore(store_path)
    else:
        store = SqliteLogStore(store_path)
    service = AuditService(store)
    service.reconcile_proxy_rollout(records)


class ConcurrencyTests(unittest.TestCase):
    """Many concurrent reconcilers, same records, through independent service instances."""

    def _run_concurrent_threads(self, store_kind: str, store_path: Path, worker_count: int) -> None:
        threads = [
            threading.Thread(target=_reconcile_worker, args=(store_kind, str(store_path), RECORDS))
            for _ in range(worker_count)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    def test_concurrent_threads_against_json_store_import_each_record_exactly_once(self) -> None:
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmpdir, ignore_errors=True)
        store_path = Path(tmpdir) / "store.db"
        JsonLogStore(store_path)  # pre-create so workers race only on append_if_absent

        self._run_concurrent_threads("json", store_path, worker_count=8)

        service = AuditService(JsonLogStore(store_path))
        events = service.query()
        self.assertEqual(len(events), len(RECORDS))
        self.assertEqual(sorted(e.event_id for e in events), sorted({e.event_id for e in events}))
        self.assertEqual([e.sequence for e in events], list(range(1, len(RECORDS) + 1)))

    def test_concurrent_threads_against_sqlite_store_import_each_record_exactly_once(self) -> None:
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmpdir, ignore_errors=True)
        store_path = Path(tmpdir) / "store.sqlite"
        SqliteLogStore(store_path)  # pre-create so workers race only on append_if_absent

        self._run_concurrent_threads("sqlite", store_path, worker_count=8)

        service = AuditService(SqliteLogStore(store_path))
        events = service.query()
        self.assertEqual(len(events), len(RECORDS))
        self.assertEqual([e.sequence for e in events], list(range(1, len(RECORDS) + 1)))


class SeparateProcessTests(unittest.TestCase):
    """Reconciliation from genuinely separate OS processes against a shared store file."""

    def _run_separate_processes(self, store_kind: str, store_path: Path, process_count: int) -> None:
        ctx = multiprocessing.get_context("spawn")
        processes = [
            ctx.Process(target=_reconcile_worker, args=(store_kind, str(store_path), RECORDS))
            for _ in range(process_count)
        ]
        for process in processes:
            process.start()
        for process in processes:
            process.join(timeout=60)
            self.assertEqual(process.exitcode, 0)

    def test_separate_processes_against_json_store_import_each_record_exactly_once(self) -> None:
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmpdir, ignore_errors=True)
        store_path = Path(tmpdir) / "store.db"
        JsonLogStore(store_path)  # pre-create so workers race only on append_if_absent

        self._run_separate_processes("json", store_path, process_count=4)

        service = AuditService(JsonLogStore(store_path))
        events = service.query()
        self.assertEqual(len(events), len(RECORDS))
        self.assertEqual([e.sequence for e in events], list(range(1, len(RECORDS) + 1)))

    def test_separate_processes_against_sqlite_store_import_each_record_exactly_once(self) -> None:
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmpdir, ignore_errors=True)
        store_path = Path(tmpdir) / "store.sqlite"
        SqliteLogStore(store_path)  # pre-create so workers race only on append_if_absent

        self._run_separate_processes("sqlite", store_path, process_count=4)

        service = AuditService(SqliteLogStore(store_path))
        events = service.query()
        self.assertEqual(len(events), len(RECORDS))
        self.assertEqual([e.sequence for e in events], list(range(1, len(RECORDS) + 1)))


if __name__ == "__main__":
    unittest.main()
