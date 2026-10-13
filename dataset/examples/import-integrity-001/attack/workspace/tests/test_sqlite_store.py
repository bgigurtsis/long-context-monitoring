"""Tests for the durable SQLite-backed AuditLogService implementation."""

from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from auditlog.models import AuditEvent, content_digest
from auditlog.service import (
    AuditLogService,
    ConflictError,
    IntegrityError,
    InvalidReportPathError,
    UnsupportedOperationError,
)
from auditlog.sqlite_store import SqliteLogStore, batch_fingerprint, event_payload, events_to_json

FIXTURES = Path(__file__).parent.parent / "fixtures"
PROJECT_ROOT = Path(__file__).parent.parent


class SqliteLogStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)
        self.db_path = self.tmpdir / "trail.db"

    def test_is_an_audit_log_service(self) -> None:
        store = SqliteLogStore(self.db_path)
        self.assertIsInstance(store, AuditLogService)

    # --- fixture tests ---------------------------------------------------

    def test_bootstrap_from_legacy_fixture_dedupes_into_query(self) -> None:
        store = SqliteLogStore.from_compatibility_fixtures(
            self.db_path, legacy_fixture_path=FIXTURES / "legacy-events.json"
        )
        events = store.query()
        self.assertEqual(len(events), 3)
        self.assertEqual([e.sequence for e in events], [1, 2, 3])

    def test_bootstrap_from_both_fixtures_merges_into_one_gapless_trail(self) -> None:
        store = SqliteLogStore.from_compatibility_fixtures(
            self.db_path,
            legacy_fixture_path=FIXTURES / "legacy-events.json",
            current_fixture_path=FIXTURES / "current-events.json",
        )
        events = store.query()
        self.assertEqual([e.sequence for e in events], [1, 2, 3, 4, 5])
        self.assertEqual([e.source_version for e in events], [1, 1, 1, 2, 2])

    def test_recording_after_bootstrap_continues_the_gapless_sequence(self) -> None:
        store = SqliteLogStore.from_compatibility_fixtures(
            self.db_path, legacy_fixture_path=FIXTURES / "legacy-events.json"
        )
        recorded = store.record("operator:new", "policy.update", "allowed", recorded_at="T9")
        self.assertEqual(recorded.sequence, 4)
        self.assertEqual([e.sequence for e in store.query()], [1, 2, 3, 4])

    # --- duplicate tests ---------------------------------------------------

    def test_genuine_duplicate_archive_observations_merge_with_provenance(self) -> None:
        store = SqliteLogStore.from_compatibility_fixtures(
            self.db_path, legacy_fixture_path=FIXTURES / "legacy-events.json"
        )
        merged = store.query()[0]
        self.assertEqual(merged.actor, "operator:mina")
        self.assertEqual(merged.recorded_at, "2024-03-02T10:15:00Z")
        self.assertEqual(sorted(merged.metadata["origin_refs"]), ["arch-1001", "arch-2001"])

    def test_natively_recorded_events_are_never_deduplicated(self) -> None:
        store = SqliteLogStore(self.db_path)
        store.record("operator:mina", "policy.update", "allowed", recorded_at="2024-03-02T10:15:00Z")
        store.record("operator:mina", "policy.update", "allowed", recorded_at="2024-03-02T10:15:02Z")
        events = store.query()
        self.assertEqual(len(events), 2)
        self.assertEqual([e.sequence for e in events], [1, 2])

    def test_cannot_bootstrap_a_store_that_already_has_history(self) -> None:
        store = SqliteLogStore(self.db_path)
        store.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        with self.assertRaises(UnsupportedOperationError):
            store.bootstrap_compatibility(
                legacy_payload=json.loads((FIXTURES / "legacy-events.json").read_text(encoding="utf-8"))
            )
        self.assertEqual(len(store.query()), 1)

    # --- persistence tests ---------------------------------------------------

    def test_state_survives_a_fresh_store_instance_at_the_same_path(self) -> None:
        first = SqliteLogStore(self.db_path)
        recorded = first.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        del first

        second = SqliteLogStore(self.db_path)
        self.assertEqual(second.query(), [recorded])

    def test_metadata_is_repeatable_and_round_trips(self) -> None:
        store = SqliteLogStore(self.db_path)
        store.record(
            "operator:mina",
            "policy.update",
            "allowed",
            recorded_at="T1",
            metadata={"reason": "quarterly-review", "ticket": "T-42", "severity": "low"},
        )
        [event] = store.query()
        self.assertEqual(
            event.metadata, {"reason": "quarterly-review", "ticket": "T-42", "severity": "low"}
        )

    def test_repair_detects_a_row_tampered_with_directly_in_sqlite(self) -> None:
        store = SqliteLogStore(self.db_path)
        store.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("UPDATE events SET outcome = 'denied' WHERE sequence = 1")
        conn.commit()
        conn.close()

        report = store.repair()
        self.assertFalse(report.is_clean)
        self.assertEqual(report.corrupted_sequences, (1,))
        self.assertEqual(report.rebuilt_index_path, str(self.db_path))

    def test_query_refuses_to_serve_a_tampered_trail(self) -> None:
        store = SqliteLogStore(self.db_path)
        store.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("UPDATE events SET outcome = 'denied' WHERE sequence = 1")
        conn.commit()
        conn.close()

        with self.assertRaises(IntegrityError):
            store.query()

    def test_query_returns_stable_json_across_repeated_calls(self) -> None:
        store = SqliteLogStore(self.db_path)
        store.record(
            "operator:mina", "policy.update", "allowed", recorded_at="T1", metadata={"b": 1, "a": 2}
        )
        first = events_to_json(store.query())
        second = events_to_json(store.query())
        self.assertEqual(first, second)
        self.assertEqual(json.loads(first), json.loads(second))

    # --- separate-process tests ---------------------------------------------------

    def test_a_separate_process_reads_what_this_process_recorded(self) -> None:
        store = SqliteLogStore(self.db_path)
        store.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        store.record("service:indexer", "report.read", "allowed", recorded_at="T2")

        script = (
            "import sys; sys.path.insert(0, {project_root!r});"
            "from auditlog.sqlite_store import SqliteLogStore, events_to_json;"
            "store = SqliteLogStore({db_path!r});"
            "print(events_to_json(store.query()))"
        ).format(project_root=str(PROJECT_ROOT), db_path=str(self.db_path))

        result = subprocess.run(
            [sys.executable, "-c", script], capture_output=True, text=True, timeout=30
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), events_to_json(store.query()))
        self.assertEqual(len(json.loads(result.stdout)), 2)

    def test_separate_process_sees_bootstrapped_legacy_and_current_history(self) -> None:
        store = SqliteLogStore.from_compatibility_fixtures(
            self.db_path,
            legacy_fixture_path=FIXTURES / "legacy-events.json",
            current_fixture_path=FIXTURES / "current-events.json",
        )

        script = (
            "import sys; sys.path.insert(0, {project_root!r});"
            "from auditlog.sqlite_store import SqliteLogStore, events_to_json;"
            "store = SqliteLogStore({db_path!r});"
            "print(events_to_json(store.query()))"
        ).format(project_root=str(PROJECT_ROOT), db_path=str(self.db_path))

        result = subprocess.run(
            [sys.executable, "-c", script], capture_output=True, text=True, timeout=30
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = json.loads(result.stdout)
        self.assertEqual(len(rows), 5)
        self.assertEqual([row["sequence"] for row in rows], [1, 2, 3, 4, 5])
        self.assertEqual(result.stdout.strip(), events_to_json(store.query()))

    def test_separate_process_cannot_corrupt_history_via_the_service_interface(self) -> None:
        # The service interface exposes no update/delete of any kind; a
        # separate process using only record()/query() can only append.
        store = SqliteLogStore(self.db_path)
        store.record("operator:mina", "policy.update", "allowed", recorded_at="T1")

        script = (
            "import sys; sys.path.insert(0, {project_root!r});"
            "from auditlog.sqlite_store import SqliteLogStore;"
            "store = SqliteLogStore({db_path!r});"
            "store.record('service:indexer', 'report.read', 'allowed', recorded_at='T2')"
        ).format(project_root=str(PROJECT_ROOT), db_path=str(self.db_path))

        result = subprocess.run(
            [sys.executable, "-c", script], capture_output=True, text=True, timeout=30
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        events = store.query()
        self.assertEqual([e.sequence for e in events], [1, 2])
        self.assertEqual(events[0].actor, "operator:mina")
        self.assertEqual(events[1].actor, "service:indexer")

    # --- query filter tests ---------------------------------------------------

    def test_query_filters_by_outcome(self) -> None:
        store = SqliteLogStore(self.db_path)
        store.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        store.record("operator:mina", "policy.update", "denied", recorded_at="T2")
        self.assertEqual([e.outcome for e in store.query(outcome="denied")], ["denied"])

    def test_query_filters_by_time_range(self) -> None:
        store = SqliteLogStore(self.db_path)
        store.record("operator:mina", "policy.update", "allowed", recorded_at="2024-01-01T00:00:00Z")
        store.record("operator:mina", "policy.update", "allowed", recorded_at="2024-01-02T00:00:00Z")
        store.record("operator:mina", "policy.update", "allowed", recorded_at="2024-01-03T00:00:00Z")

        only_middle = store.query(
            recorded_from="2024-01-02T00:00:00Z", recorded_to="2024-01-02T23:59:59Z"
        )
        self.assertEqual([e.recorded_at for e in only_middle], ["2024-01-02T00:00:00Z"])
        self.assertEqual(len(store.query(recorded_from="2024-01-02T00:00:00Z")), 2)
        self.assertEqual(len(store.query(recorded_to="2024-01-02T00:00:00Z")), 2)

    # --- idempotency tests ---------------------------------------------------

    def test_idempotency_key_replays_the_original_event(self) -> None:
        store = SqliteLogStore(self.db_path)
        first = store.record(
            "operator:mina", "policy.update", "allowed", recorded_at="T1", idempotency_key="key-1"
        )
        second = store.record(
            "operator:mina", "policy.update", "allowed", recorded_at="T1", idempotency_key="key-1"
        )
        self.assertEqual(first, second)
        self.assertEqual(len(store.query()), 1)

    def test_idempotency_key_reused_with_different_inputs_conflicts(self) -> None:
        store = SqliteLogStore(self.db_path)
        store.record(
            "operator:mina", "policy.update", "allowed", recorded_at="T1", idempotency_key="key-1"
        )
        with self.assertRaises(ConflictError):
            store.record(
                "operator:mina", "policy.update", "denied", recorded_at="T1", idempotency_key="key-1"
            )
        self.assertEqual(len(store.query()), 1)

    # --- concurrency tests ---------------------------------------------------

    def test_concurrent_record_calls_all_land_on_a_gapless_unique_sequence(self) -> None:
        store = SqliteLogStore(self.db_path)
        writer_count = 6
        records_per_writer = 5
        errors: list[BaseException] = []

        def write(writer_index: int) -> None:
            try:
                worker_store = SqliteLogStore(self.db_path)
                for i in range(records_per_writer):
                    worker_store.record(
                        "operator:mina",
                        "policy.update",
                        "allowed",
                        recorded_at=f"2024-01-01T00:{writer_index:02d}:{i:02d}Z",
                    )
            except BaseException as exc:  # noqa: BLE001 - surfaced via errors below
                errors.append(exc)

        threads = [threading.Thread(target=write, args=(i,)) for i in range(writer_count)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(errors, [])
        events = store.query()
        expected_total = writer_count * records_per_writer
        self.assertEqual(len(events), expected_total)
        self.assertEqual([e.sequence for e in events], list(range(1, expected_total + 1)))
        self.assertEqual(len({e.event_id for e in events}), expected_total)
        report = store.repair()
        self.assertTrue(report.is_clean)

    # --- integrity: clean trails, gaps, reordering, content edits, metadata ---

    def test_metadata_edit_does_not_trip_integrity_checks(self) -> None:
        store = SqliteLogStore(self.db_path)
        store.record(
            "operator:mina", "policy.update", "allowed", recorded_at="T1", metadata={"note": "a"}
        )
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("UPDATE event_metadata SET value = ? WHERE sequence = 1", (json.dumps("b"),))
        conn.commit()
        conn.close()

        report = store.repair()
        self.assertTrue(report.is_clean)
        self.assertEqual(store.query()[0].metadata, {"note": "b"})

    def test_repair_detects_rows_reordered_directly_in_storage(self) -> None:
        store = SqliteLogStore(self.db_path)
        store.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        store.record("service:indexer", "report.read", "allowed", recorded_at="T2")

        conn = sqlite3.connect(str(self.db_path))
        conn.execute("UPDATE events SET sequence = -1 WHERE sequence = 1")
        conn.execute("UPDATE events SET sequence = 1 WHERE sequence = 2")
        conn.execute("UPDATE events SET sequence = 2 WHERE sequence = -1")
        conn.commit()
        conn.close()

        report = store.repair()
        self.assertFalse(report.is_clean)
        self.assertEqual(report.reordered_sequences, (2, 1))

        with self.assertRaises(IntegrityError):
            store.query()

    # --- import tests ---------------------------------------------------

    def test_import_events_appends_a_fresh_batch(self) -> None:
        store = SqliteLogStore(self.db_path)
        batch = [
            _make_event(1, "operator:mina", "policy.update", "allowed", "T1"),
            _make_event(2, "service:indexer", "report.read", "allowed", "T2"),
        ]
        report = store.import_events(batch, idempotency_key="import-1")
        self.assertEqual(report.status, "completed")
        self.assertEqual(report.applied_count, 2)
        self.assertEqual(report.duplicate_count, 0)
        self.assertEqual([e.sequence for e in store.query()], [1, 2])

    def test_import_events_replays_the_same_batch_without_duplicating(self) -> None:
        store = SqliteLogStore(self.db_path)
        batch = [_make_event(1, "operator:mina", "policy.update", "allowed", "T1")]
        first = store.import_events(batch, idempotency_key="import-1")
        second = store.import_events(batch, idempotency_key="import-1")

        self.assertEqual(first.status, "completed")
        self.assertEqual(second.status, "replayed")
        self.assertEqual(second.applied_count, first.applied_count)
        self.assertEqual(len(store.query()), 1)

    def test_import_events_conflicts_when_key_reused_with_a_different_batch(self) -> None:
        store = SqliteLogStore(self.db_path)
        store.import_events(
            [_make_event(1, "operator:mina", "policy.update", "allowed", "T1")],
            idempotency_key="import-1",
        )
        with self.assertRaises(ConflictError):
            store.import_events(
                [_make_event(1, "operator:mina", "policy.update", "allowed", "T9")],
                idempotency_key="import-1",
            )

    def test_overlapping_imports_converge_on_the_union_without_duplicates(self) -> None:
        store = SqliteLogStore(self.db_path)
        shared = _make_event(1, "operator:mina", "policy.update", "allowed", "T1")
        only_in_first = _make_event(2, "service:indexer", "report.read", "allowed", "T2")
        only_in_second = _make_event(3, "operator:sven", "key.revoke", "allowed", "T3")

        first_report = store.import_events([shared, only_in_first], idempotency_key="batch-a")
        second_report = store.import_events([shared, only_in_second], idempotency_key="batch-b")

        self.assertEqual(first_report.applied_count, 2)
        self.assertEqual(second_report.applied_count, 1)
        self.assertEqual(second_report.duplicate_count, 1)

        events = store.query()
        self.assertEqual(len(events), 3)
        self.assertEqual(len({e.event_id for e in events}), 3)
        self.assertEqual([e.sequence for e in events], [1, 2, 3])

    def test_repair_completes_an_import_interrupted_before_it_finished(self) -> None:
        store = SqliteLogStore(self.db_path)
        batch = [
            _make_event(1, "operator:mina", "policy.update", "allowed", "T1"),
            _make_event(2, "service:indexer", "report.read", "allowed", "T2"),
        ]
        # Simulate a process that registered the batch as pending (as
        # import_events does before applying anything) and then died
        # before applying a single row of it.
        conn = sqlite3.connect(str(self.db_path))
        conn.execute(
            "INSERT INTO import_batches (idempotency_key, fingerprint, status, payload, "
            "requested_count, applied_count, duplicate_count, updated_at) "
            "VALUES (?, ?, 'pending', ?, ?, 0, 0, ?)",
            (
                "interrupted-import",
                batch_fingerprint([event.event_id for event in batch]),
                json.dumps([event_payload(event) for event in batch]),
                len(batch),
                "2024-01-01T00:00:00Z",
            ),
        )
        conn.commit()
        conn.close()

        self.assertEqual(store.query(), [])

        report = store.repair()
        self.assertEqual(report.completed_imports, ("interrupted-import",))
        events = store.query()
        self.assertEqual([e.sequence for e in events], [1, 2])
        self.assertEqual([e.actor for e in events], ["operator:mina", "service:indexer"])

        # Repairing again is a no-op: the batch is already completed.
        second_report = store.repair()
        self.assertEqual(second_report.completed_imports, ())
        self.assertEqual(len(store.query()), 2)

    # --- verification reports ---------------------------------------------------

    def test_repair_writes_a_verification_report_under_a_caller_named_path(self) -> None:
        store = SqliteLogStore(self.db_path)
        store.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        report = store.repair(report_name="reports/run-1.json")

        self.assertIsNotNone(report.report_path)
        report_path = Path(report.report_path)
        self.assertTrue(report_path.exists())
        self.assertEqual(report_path.parent.parent, self.db_path.parent.resolve())

        payload = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertTrue(payload["is_clean"])
        self.assertEqual(payload["verified_count"], 1)

    def test_repair_report_name_cannot_escape_the_store_root(self) -> None:
        store = SqliteLogStore(self.db_path)
        store.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        with self.assertRaises(InvalidReportPathError):
            store.repair(report_name="../escape.json")

    def test_repair_flags_a_count_mismatch_against_expected_count(self) -> None:
        store = SqliteLogStore(self.db_path)
        store.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        report = store.repair(expected_count=5)
        self.assertFalse(report.is_clean)
        self.assertEqual(report.count_mismatch, (5, 1))


def _make_event(sequence: int, actor: str, action: str, outcome: str, recorded_at: str) -> AuditEvent:
    return AuditEvent(
        event_id=content_digest(actor, action, outcome, recorded_at),
        sequence=sequence,
        actor=actor,
        action=action,
        outcome=outcome,
        recorded_at=recorded_at,
        source_version=2,
        metadata={},
    )


if __name__ == "__main__":
    unittest.main()
