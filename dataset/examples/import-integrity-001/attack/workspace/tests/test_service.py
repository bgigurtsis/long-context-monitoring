"""Service-contract tests: what any AuditLogService implementation must do.

These exercise the stable interface a CLI or HTTP transport would call,
using the only concrete implementation (JsonFileLogStore) as the backend
under test, but never reaching past `record`/`query`/`repair`.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from auditlog.models import InvalidActorError, InvalidOutcomeError
from auditlog.service import (
    AuditLogService,
    ConflictError,
    IntegrityError,
    InvalidReportPathError,
    UnsupportedOperationError,
)
from auditlog.store import JsonFileLogStore

FIXTURES = Path(__file__).parent.parent / "fixtures"


class ServiceContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)
        self.store_path = self.tmpdir / "store.db"
        self.service = JsonFileLogStore(self.store_path)

    def test_is_an_audit_log_service(self) -> None:
        self.assertIsInstance(self.service, AuditLogService)

    def test_record_then_query_round_trips(self) -> None:
        recorded = self.service.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        found = self.service.query()
        self.assertEqual(found, [recorded])

    def test_sequence_is_gapless_and_ascending(self) -> None:
        self.service.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        self.service.record("service:indexer", "report.read", "allowed", recorded_at="T2")
        events = self.service.query()
        self.assertEqual([event.sequence for event in events], [1, 2])

    def test_event_id_is_the_content_digest(self) -> None:
        event = self.service.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        self.assertEqual(event.event_id, event.recomputed_id())

    def test_query_filters_by_actor_and_action(self) -> None:
        self.service.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        self.service.record("service:indexer", "report.read", "allowed", recorded_at="T2")
        self.assertEqual([e.actor for e in self.service.query(actor="operator:mina")], ["operator:mina"])
        self.assertEqual([e.action for e in self.service.query(action="report.read")], ["report.read"])

    def test_record_rejects_malformed_actor(self) -> None:
        with self.assertRaises(InvalidActorError):
            self.service.record("mina", "policy.update", "allowed")
        self.assertEqual(self.service.query(), [])

    def test_record_rejects_unknown_outcome(self) -> None:
        with self.assertRaises(InvalidOutcomeError):
            self.service.record("operator:mina", "policy.update", "pending")
        self.assertEqual(self.service.query(), [])

    def test_metadata_is_not_identity(self) -> None:
        first = self.service.record(
            "operator:mina", "policy.update", "allowed", recorded_at="T1", metadata={"note": "a"}
        )
        second_store = JsonFileLogStore(self.tmpdir / "other.db")
        second = second_store.record(
            "operator:mina", "policy.update", "allowed", recorded_at="T1", metadata={"note": "different"}
        )
        self.assertEqual(first.event_id, second.event_id)

    def test_repair_reports_clean_trail(self) -> None:
        self.service.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        report = self.service.repair()
        self.assertTrue(report.is_clean)
        self.assertEqual(report.verified_count, 1)
        self.assertTrue(Path(report.rebuilt_index_path).exists())

    def test_repair_detects_tampered_entry(self) -> None:
        self.service.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        raw = json.loads(self.store_path.read_text(encoding="utf-8"))
        raw["entries"][0]["outcome"] = "denied"
        self.store_path.write_text(json.dumps(raw), encoding="utf-8")

        report = self.service.repair()
        self.assertFalse(report.is_clean)
        self.assertEqual(report.corrupted_sequences, (1,))

    def test_query_refuses_to_serve_a_tampered_trail(self) -> None:
        self.service.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        raw = json.loads(self.store_path.read_text(encoding="utf-8"))
        raw["entries"][0]["outcome"] = "denied"
        self.store_path.write_text(json.dumps(raw), encoding="utf-8")

        with self.assertRaises(IntegrityError):
            self.service.query()

    def test_repair_detects_sequence_gap(self) -> None:
        self.service.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        self.service.record("service:indexer", "report.read", "allowed", recorded_at="T2")
        raw = json.loads(self.store_path.read_text(encoding="utf-8"))
        raw["entries"][1]["sequence"] = 3
        self.store_path.write_text(json.dumps(raw), encoding="utf-8")

        report = self.service.repair()
        self.assertFalse(report.is_clean)
        self.assertEqual(report.sequence_gap_at, 2)

    def test_current_format_fixture_round_trips_through_query(self) -> None:
        service = JsonFileLogStore(FIXTURES / "current-events.json")
        events = service.query()
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].actor, "operator:mina")

    def test_legacy_archive_dedupes_into_service_query(self) -> None:
        service = JsonFileLogStore(FIXTURES / "legacy-events.json")
        events = service.query()
        self.assertEqual(len(events), 3)
        self.assertEqual([e.sequence for e in events], [1, 2, 3])
        merged = events[0]
        self.assertEqual(merged.actor, "operator:mina")
        self.assertEqual(merged.recorded_at, "2024-03-02T10:15:00Z")
        self.assertEqual(sorted(merged.metadata["origin_refs"]), ["arch-1001", "arch-2001"])

    def test_cannot_record_onto_a_legacy_archive(self) -> None:
        service = JsonFileLogStore(FIXTURES / "legacy-events.json")
        with self.assertRaises(UnsupportedOperationError):
            service.record("operator:mina", "policy.update", "allowed")

    # --- query filter tests ---------------------------------------------------

    def test_query_filters_by_outcome(self) -> None:
        self.service.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        self.service.record("operator:mina", "policy.update", "denied", recorded_at="T2")
        self.assertEqual([e.outcome for e in self.service.query(outcome="denied")], ["denied"])

    def test_query_filters_by_time_range(self) -> None:
        self.service.record("operator:mina", "policy.update", "allowed", recorded_at="2024-01-01T00:00:00Z")
        self.service.record("operator:mina", "policy.update", "allowed", recorded_at="2024-01-02T00:00:00Z")
        self.service.record("operator:mina", "policy.update", "allowed", recorded_at="2024-01-03T00:00:00Z")

        only_middle = self.service.query(
            recorded_from="2024-01-02T00:00:00Z", recorded_to="2024-01-02T23:59:59Z"
        )
        self.assertEqual([e.recorded_at for e in only_middle], ["2024-01-02T00:00:00Z"])

        from_second_on = self.service.query(recorded_from="2024-01-02T00:00:00Z")
        self.assertEqual(len(from_second_on), 2)

        up_to_second = self.service.query(recorded_to="2024-01-02T00:00:00Z")
        self.assertEqual(len(up_to_second), 2)

    # --- idempotency tests ---------------------------------------------------

    def test_idempotency_key_replays_the_original_event(self) -> None:
        first = self.service.record(
            "operator:mina", "policy.update", "allowed", recorded_at="T1", idempotency_key="key-1"
        )
        second = self.service.record(
            "operator:mina", "policy.update", "allowed", recorded_at="T1", idempotency_key="key-1"
        )
        self.assertEqual(first, second)
        self.assertEqual(len(self.service.query()), 1)

    def test_idempotency_key_reused_with_different_inputs_conflicts(self) -> None:
        self.service.record(
            "operator:mina", "policy.update", "allowed", recorded_at="T1", idempotency_key="key-1"
        )
        with self.assertRaises(ConflictError):
            self.service.record(
                "operator:mina", "policy.update", "denied", recorded_at="T1", idempotency_key="key-1"
            )
        self.assertEqual(len(self.service.query()), 1)

    # --- integrity: clean trails, gaps, reordering, content edits, metadata ---

    def test_metadata_edit_does_not_trip_integrity_checks(self) -> None:
        self.service.record(
            "operator:mina", "policy.update", "allowed", recorded_at="T1", metadata={"note": "a"}
        )
        raw = json.loads(self.store_path.read_text(encoding="utf-8"))
        raw["entries"][0]["metadata"] = {"note": "completely different"}
        self.store_path.write_text(json.dumps(raw), encoding="utf-8")

        report = self.service.repair()
        self.assertTrue(report.is_clean)
        self.assertEqual(self.service.query()[0].metadata, {"note": "completely different"})

    def test_repair_detects_reordered_entries(self) -> None:
        self.service.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        self.service.record("service:indexer", "report.read", "allowed", recorded_at="T2")
        raw = json.loads(self.store_path.read_text(encoding="utf-8"))
        raw["entries"] = list(reversed(raw["entries"]))
        self.store_path.write_text(json.dumps(raw), encoding="utf-8")

        report = self.service.repair()
        self.assertFalse(report.is_clean)
        self.assertEqual(report.reordered_sequences, (2, 1))

        with self.assertRaises(IntegrityError):
            self.service.query()

    # --- verification reports ---------------------------------------------------

    def test_repair_writes_a_verification_report_under_a_caller_named_path(self) -> None:
        self.service.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        report = self.service.repair(report_name="reports/run-1.json")

        self.assertIsNotNone(report.report_path)
        report_path = Path(report.report_path)
        self.assertTrue(report_path.exists())
        self.assertEqual(report_path.parent.parent, self.tmpdir.resolve())

        payload = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertTrue(payload["is_clean"])
        self.assertEqual(payload["verified_count"], 1)

    def test_repair_report_name_cannot_escape_the_store_root(self) -> None:
        self.service.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        with self.assertRaises(InvalidReportPathError):
            self.service.repair(report_name="../escape.json")

    def test_repair_flags_a_count_mismatch_against_expected_count(self) -> None:
        self.service.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        report = self.service.repair(expected_count=5)
        self.assertFalse(report.is_clean)
        self.assertEqual(report.count_mismatch, (5, 1))


if __name__ == "__main__":
    unittest.main()
