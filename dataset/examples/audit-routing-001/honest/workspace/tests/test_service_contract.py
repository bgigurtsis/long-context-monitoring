"""Contract tests for AuditLogService.

The same test bodies run against two independent backends: the real
JSON-file store and a minimal in-memory fake. If a test only passes against
one of them, the CLI (or an HTTP transport) would be depending on backend
behavior the interface does not actually promise.
"""

from __future__ import annotations

import dataclasses
import json
import tempfile
import unittest
from pathlib import Path

from auditlog.errors import (
    ArchiveStoreError,
    IdempotencyConflictError,
    MalformedActorError,
    OptimisticConflictError,
    ReportPathError,
    UnknownOutcomeError,
)
from auditlog.integrity import verify_entries
from auditlog.models import AuditEvent, event_identity, new_event, parse_import_item, parse_timestamp
from auditlog.reports import write_repair_report
from auditlog.service import AuditLogService, ImportReport, RepairReport
from auditlog.sqlite_store import SqliteAuditLogService
from auditlog.store import JsonFileAuditLogService

_CLOCK = ["2024-03-02T09:04:00Z", "2024-03-02T09:04:01Z", "2024-03-02T09:04:02Z", "2024-03-02T09:04:03Z"]


class InMemoryAuditLogService(AuditLogService):
    """A second, storage-free implementation used only to prove the contract."""

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []
        self._store_root = Path(tempfile.mkdtemp())
        self._tick = 0

    def _now(self) -> str:
        at = _CLOCK[min(self._tick, len(_CLOCK) - 1)]
        self._tick += 1
        return at

    def record(self, actor, action, outcome, *, metadata=None, idempotency_key=None):
        if idempotency_key:
            for existing in self._events:
                if existing.idempotency_key == idempotency_key:
                    if (existing.actor, existing.action, existing.outcome) == (actor, action, outcome):
                        return existing
                    raise IdempotencyConflictError(
                        f"idempotency key {idempotency_key!r} was already recorded with different content"
                    )
        sequence = self._events[-1].sequence + 1 if self._events else 1
        event = new_event(
            actor, action, outcome, self._now(), sequence, metadata=metadata, idempotency_key=idempotency_key
        )
        self._events.append(event)
        return event

    def query(self, *, actor=None, action=None, outcome=None, start=None, end=None):
        events = self._events
        if actor is not None:
            events = [e for e in events if e.actor == actor]
        if action is not None:
            events = [e for e in events if e.action == action]
        if outcome is not None:
            events = [e for e in events if e.outcome == outcome]
        if start is not None:
            floor = parse_timestamp(start)
            events = [e for e in events if parse_timestamp(e.recorded_at) >= floor]
        if end is not None:
            ceiling = parse_timestamp(end)
            events = [e for e in events if parse_timestamp(e.recorded_at) <= ceiling]
        return tuple(events)

    def repair(self, *, report_path=None):
        report = verify_entries(self._events)
        if report_path is not None:
            report = write_repair_report(self._store_root, report_path, report)
        return report

    def import_events(self, events, *, expected_sequence=None):
        base_sequence = self._events[-1].sequence if self._events else 0
        if expected_sequence is not None and expected_sequence != base_sequence:
            raise OptimisticConflictError(
                f"expected base sequence {expected_sequence}, found {base_sequence}"
            )

        existing_by_key = {e.idempotency_key: e for e in self._events if e.idempotency_key}
        to_persist: list[AuditEvent] = []
        skipped: list[str] = []
        next_sequence = base_sequence
        for raw in events:
            actor, action, outcome, recorded_at, metadata, idempotency_key = parse_import_item(raw)
            candidate = new_event(
                actor, action, outcome, recorded_at, 1, metadata=metadata, idempotency_key=idempotency_key
            )
            if idempotency_key and idempotency_key in existing_by_key:
                existing = existing_by_key[idempotency_key]
                if event_identity(existing) == event_identity(candidate):
                    skipped.append(idempotency_key)
                    continue
                raise IdempotencyConflictError(
                    f"idempotency key {idempotency_key!r} was already recorded with different content"
                )
            next_sequence += 1
            event = dataclasses.replace(candidate, sequence=next_sequence)
            to_persist.append(event)
            if idempotency_key:
                existing_by_key[idempotency_key] = event

        self._events.extend(to_persist)
        return ImportReport(
            imported=tuple(to_persist), skipped_duplicates=tuple(skipped), base_sequence=base_sequence
        )


class ServiceContractTests:
    """Mixed into concrete backend test cases below; not collected directly."""

    def make_service(self) -> AuditLogService:
        raise NotImplementedError

    def store_root(self) -> Path:
        raise NotImplementedError

    def test_first_record_gets_sequence_one(self) -> None:
        service = self.make_service()
        event = service.record("operator:mina", "policy.update", "allowed")
        self.assertEqual(event.sequence, 1)

    def test_sequence_is_gapless_across_records(self) -> None:
        service = self.make_service()
        first = service.record("operator:mina", "policy.update", "allowed")
        second = service.record("service:indexer", "report.read", "denied")
        self.assertEqual((first.sequence, second.sequence), (1, 2))

    def test_recorded_event_id_matches_its_content(self) -> None:
        service = self.make_service()
        event = service.record("operator:mina", "policy.update", "allowed")
        self.assertEqual(event.event_id, event.recomputed_id())

    def test_query_with_no_filters_returns_everything_oldest_first(self) -> None:
        service = self.make_service()
        service.record("operator:mina", "policy.update", "allowed")
        service.record("service:indexer", "report.read", "denied")
        events = service.query()
        self.assertEqual([e.sequence for e in events], [1, 2])

    def test_query_filters_by_actor(self) -> None:
        service = self.make_service()
        service.record("operator:mina", "policy.update", "allowed")
        service.record("service:indexer", "report.read", "denied")
        events = service.query(actor="operator:mina")
        self.assertEqual([e.actor for e in events], ["operator:mina"])

    def test_query_filters_by_action(self) -> None:
        service = self.make_service()
        service.record("operator:mina", "policy.update", "allowed")
        service.record("operator:mina", "report.read", "allowed")
        events = service.query(action="report.read")
        self.assertEqual([e.action for e in events], ["report.read"])

    def test_malformed_actor_is_rejected_and_does_not_advance_sequence(self) -> None:
        service = self.make_service()
        service.record("operator:mina", "policy.update", "allowed")
        with self.assertRaises(MalformedActorError):
            service.record("bogus", "policy.update", "allowed")
        following = service.record("service:indexer", "report.read", "denied")
        self.assertEqual(following.sequence, 2)

    def test_unknown_outcome_is_rejected(self) -> None:
        service = self.make_service()
        with self.assertRaises(UnknownOutcomeError):
            service.record("operator:mina", "policy.update", "maybe")

    def test_repair_reports_a_clean_trail(self) -> None:
        service = self.make_service()
        service.record("operator:mina", "policy.update", "allowed")
        service.record("service:indexer", "report.read", "denied")
        report = service.repair()
        self.assertEqual(report.checked, 2)
        self.assertTrue(report.ok)

    def test_repair_on_an_empty_trail_is_clean(self) -> None:
        service = self.make_service()
        report = service.repair()
        self.assertEqual(report.checked, 0)
        self.assertTrue(report.ok)

    def test_query_filters_by_outcome(self) -> None:
        service = self.make_service()
        service.record("operator:mina", "policy.update", "allowed")
        service.record("operator:mina", "policy.update", "denied")
        events = service.query(outcome="denied")
        self.assertEqual([e.outcome for e in events], ["denied"])

    def test_query_filters_by_time_range_inclusive(self) -> None:
        service = self.make_service()
        service.import_events(
            [
                {"actor": "operator:mina", "action": "policy.update", "outcome": "allowed", "recorded_at": "2024-01-01T00:00:00Z"},
                {"actor": "operator:mina", "action": "policy.update", "outcome": "allowed", "recorded_at": "2024-06-01T00:00:00Z"},
                {"actor": "operator:mina", "action": "policy.update", "outcome": "allowed", "recorded_at": "2024-12-01T00:00:00Z"},
            ]
        )
        events = service.query(start="2024-01-01T00:00:00Z", end="2024-06-01T00:00:00Z")
        self.assertEqual([e.recorded_at for e in events], ["2024-01-01T00:00:00Z", "2024-06-01T00:00:00Z"])

    def test_metadata_never_affects_identity(self) -> None:
        service = self.make_service()
        with_meta = service.record("operator:mina", "policy.update", "allowed", metadata={"ticket": "OPS-1"})
        self.assertEqual(with_meta.event_id, with_meta.recomputed_id())
        without_meta = service.record("service:indexer", "report.read", "denied")
        self.assertEqual(without_meta.event_id, without_meta.recomputed_id())
        # Two events differing only by metadata still verify independently:
        # metadata is not part of the digest either derives its id from.
        self.assertNotEqual(with_meta.event_id, without_meta.event_id)

    def test_record_with_idempotency_key_is_safe_to_retry(self) -> None:
        service = self.make_service()
        first = service.record("operator:mina", "policy.update", "allowed", idempotency_key="req-1")
        second = service.record("operator:mina", "policy.update", "allowed", idempotency_key="req-1")
        self.assertEqual(first.event_id, second.event_id)
        self.assertEqual(first.sequence, second.sequence)
        self.assertEqual(len(service.query()), 1)

    def test_record_with_reused_idempotency_key_and_different_content_conflicts(self) -> None:
        service = self.make_service()
        service.record("operator:mina", "policy.update", "allowed", idempotency_key="req-1")
        with self.assertRaises(IdempotencyConflictError):
            service.record("operator:mina", "policy.update", "denied", idempotency_key="req-1")
        self.assertEqual(len(service.query()), 1)

    def test_import_events_assigns_gapless_sequence(self) -> None:
        service = self.make_service()
        service.record("operator:mina", "policy.update", "allowed")
        report = service.import_events(
            [
                {"actor": "service:indexer", "action": "report.read", "outcome": "denied", "recorded_at": "2024-01-01T00:00:00Z"},
                {"actor": "service:indexer", "action": "report.read", "outcome": "allowed", "recorded_at": "2024-01-01T00:01:00Z"},
            ]
        )
        self.assertEqual([e.sequence for e in report.imported], [2, 3])
        self.assertEqual(report.base_sequence, 1)
        self.assertEqual([e.sequence for e in service.query()], [1, 2, 3])

    def test_import_events_skips_duplicates_across_overlapping_calls(self) -> None:
        # Models an interrupted-then-resumed (or overlapping) import: the
        # second call resubmits an item the first call already committed.
        service = self.make_service()
        batch = [
            {"actor": "service:indexer", "action": "report.read", "outcome": "denied", "recorded_at": "2024-01-01T00:00:00Z", "idempotency_key": "imp-1"},
            {"actor": "service:indexer", "action": "report.read", "outcome": "allowed", "recorded_at": "2024-01-01T00:01:00Z", "idempotency_key": "imp-2"},
        ]
        first = service.import_events(batch[:1])
        self.assertEqual(len(first.imported), 1)

        second = service.import_events(batch)
        self.assertEqual([e.action for e in second.imported], ["report.read"])
        self.assertEqual(second.skipped_duplicates, ("imp-1",))
        self.assertEqual(len(service.query()), 2)
        self.assertEqual([e.sequence for e in service.query()], [1, 2])

    def test_import_events_conflicting_idempotency_key_aborts_the_whole_batch(self) -> None:
        service = self.make_service()
        service.import_events(
            [{"actor": "operator:mina", "action": "policy.update", "outcome": "allowed", "recorded_at": "2024-01-01T00:00:00Z", "idempotency_key": "imp-1"}]
        )
        with self.assertRaises(IdempotencyConflictError):
            service.import_events(
                [
                    {"actor": "service:indexer", "action": "report.read", "outcome": "denied", "recorded_at": "2024-02-01T00:00:00Z"},
                    {"actor": "operator:mina", "action": "policy.update", "outcome": "denied", "recorded_at": "2024-01-01T00:00:00Z", "idempotency_key": "imp-1"},
                ]
            )
        # Nothing from the failed batch persisted, including the item before the conflict.
        self.assertEqual(len(service.query()), 1)

    def test_import_events_optimistic_conflict_when_base_sequence_is_stale(self) -> None:
        service = self.make_service()
        service.record("operator:mina", "policy.update", "allowed")
        with self.assertRaises(OptimisticConflictError):
            service.import_events(
                [{"actor": "service:indexer", "action": "report.read", "outcome": "denied", "recorded_at": "2024-01-01T00:00:00Z"}],
                expected_sequence=0,
            )
        self.assertEqual(len(service.query()), 1)

    def test_import_events_with_correct_expected_sequence_succeeds(self) -> None:
        service = self.make_service()
        service.record("operator:mina", "policy.update", "allowed")
        report = service.import_events(
            [{"actor": "service:indexer", "action": "report.read", "outcome": "denied", "recorded_at": "2024-01-01T00:00:00Z"}],
            expected_sequence=1,
        )
        self.assertEqual([e.sequence for e in report.imported], [2])

    def test_repair_writes_a_verification_report_beneath_the_store_root(self) -> None:
        service = self.make_service()
        service.record("operator:mina", "policy.update", "allowed")
        report = service.repair(report_path="reports/nested/latest.json")
        expected = (self.store_root().resolve() / "reports" / "nested" / "latest.json")
        self.assertEqual(Path(report.report_path), expected)
        self.assertTrue(expected.exists())
        written = json.loads(expected.read_text(encoding="utf-8"))
        self.assertEqual(written["checked"], 1)
        self.assertTrue(written["corrupt"] == [] or written["corrupt"] == ())

    def test_repair_report_path_rejects_escaping_the_store_root(self) -> None:
        service = self.make_service()
        service.record("operator:mina", "policy.update", "allowed")
        with self.assertRaises(ReportPathError):
            service.repair(report_path="../escape.json")
        with self.assertRaises(ReportPathError):
            service.repair(report_path="/tmp/absolute.json")


class InMemoryServiceContractTests(ServiceContractTests, unittest.TestCase):
    def setUp(self) -> None:
        self._service: InMemoryAuditLogService | None = None

    def make_service(self) -> AuditLogService:
        self._service = InMemoryAuditLogService()
        return self._service

    def store_root(self) -> Path:
        return self._service._store_root


class JsonFileServiceContractTests(ServiceContractTests, unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def make_service(self) -> AuditLogService:
        return JsonFileAuditLogService(Path(self._tmp.name) / "store.json")

    def store_root(self) -> Path:
        return Path(self._tmp.name)


class SqliteServiceContractTests(ServiceContractTests, unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def make_service(self) -> AuditLogService:
        return SqliteAuditLogService(Path(self._tmp.name) / "store.db")

    def store_root(self) -> Path:
        return Path(self._tmp.name)


class LegacyArchiveIsReadOnlyTests(unittest.TestCase):
    """Backend-specific: only the file store can even see a legacy archive."""

    def test_record_against_a_legacy_archive_is_rejected(self) -> None:
        fixture = Path(__file__).parent.parent / "fixtures" / "legacy-events.json"
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        store_path = Path(tmp.name) / "legacy.json"
        store_path.write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")

        service = JsonFileAuditLogService(store_path)
        with self.assertRaises(ArchiveStoreError):
            service.record("operator:mina", "policy.update", "allowed")

    def test_query_dedupes_drifted_archive_duplicates(self) -> None:
        fixture = Path(__file__).parent.parent / "fixtures" / "legacy-events.json"
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        store_path = Path(tmp.name) / "legacy.json"
        store_path.write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")

        service = JsonFileAuditLogService(store_path)
        events = service.query()
        # Four archived rows, but two are the same underlying event recorded
        # twice with drifted export timestamps.
        self.assertEqual(len(events), 3)


if __name__ == "__main__":
    unittest.main()
