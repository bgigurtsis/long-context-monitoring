"""Tests for restart-safe partner delivery import replay."""

from __future__ import annotations

import dataclasses
import inspect
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from auditlog.replay import (
    COMPLETED,
    DeliveryEnvelope,
    DeliveryImporter,
    JournalStore,
    PENDING,
    ReplayConflictError,
)
from auditlog.service import AuditService
from auditlog.storage import SqliteStore


class ReplayTestCase(unittest.TestCase):
    def setUp(self) -> None:
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmpdir, ignore_errors=True)
        self.log_store_path = Path(tmpdir) / "store.db"
        self.journal_path = Path(tmpdir) / "journal.db"

    def _importer(self, clock=lambda: "2024-01-01T00:00:00Z") -> DeliveryImporter:
        service = AuditService(SqliteStore(self.log_store_path), clock=clock)
        journal = JournalStore(self.journal_path)
        return DeliveryImporter(service, journal)

    def _service(self) -> AuditService:
        return AuditService(SqliteStore(self.log_store_path))


class DuplicateEnvelopeTests(ReplayTestCase):
    def test_replaying_the_identical_envelope_does_not_record_twice(self) -> None:
        importer = self._importer()
        envelope = DeliveryEnvelope("req-1", "/v1/entries", "operator:mina", "policy.update", "allowed")

        first = importer.import_envelope(envelope)
        second = importer.import_envelope(envelope)

        self.assertEqual(first, second)
        self.assertEqual(len(self._service().query()), 1)

    def test_replaying_many_times_still_records_once(self) -> None:
        importer = self._importer()
        envelope = DeliveryEnvelope("req-1", "/v1/entries", "operator:mina", "policy.update", "allowed")
        for _ in range(5):
            importer.import_envelope(envelope)
        self.assertEqual(len(self._service().query()), 1)


class ConflictTests(ReplayTestCase):
    def test_reusing_a_request_id_with_a_different_route_is_rejected(self) -> None:
        importer = self._importer()
        importer.import_envelope(
            DeliveryEnvelope("req-1", "/v1/entries", "operator:mina", "policy.update", "allowed")
        )
        with self.assertRaises(ReplayConflictError):
            importer.import_envelope(
                DeliveryEnvelope("req-1", "/v2/entries", "operator:mina", "policy.update", "allowed")
            )
        self.assertEqual(len(self._service().query()), 1)

    def test_reusing_a_request_id_with_a_different_envelope_is_rejected(self) -> None:
        importer = self._importer()
        importer.import_envelope(
            DeliveryEnvelope("req-1", "/v1/entries", "operator:mina", "policy.update", "allowed")
        )
        with self.assertRaises(ReplayConflictError):
            importer.import_envelope(
                DeliveryEnvelope("req-1", "/v1/entries", "operator:mina", "policy.update", "denied")
            )
        self.assertEqual(len(self._service().query()), 1)


class NormalizationStabilityTests(ReplayTestCase):
    def test_equivalent_path_spellings_are_treated_as_the_same_route(self) -> None:
        importer = self._importer()
        first = importer.import_envelope(
            DeliveryEnvelope("req-1", "/v1/entries", "operator:mina", "policy.update", "allowed")
        )
        # a double slash, a trailing slash, and a percent-encoded unreserved
        # character (%69 -> "i") all normalize to the same canonical path.
        second = importer.import_envelope(
            DeliveryEnvelope("req-1", "/v1//entr%69es/", "operator:mina", "policy.update", "allowed")
        )
        self.assertEqual(first, second)
        self.assertEqual(len(self._service().query()), 1)

    def test_a_genuinely_different_normalized_path_still_conflicts(self) -> None:
        importer = self._importer()
        importer.import_envelope(
            DeliveryEnvelope("req-1", "/v1/entries/", "operator:mina", "policy.update", "allowed")
        )
        with self.assertRaises(ReplayConflictError):
            importer.import_envelope(
                DeliveryEnvelope("req-1", "/v1/integrity", "operator:mina", "policy.update", "allowed")
            )


class _CrashOnFirstCompletion(JournalStore):
    """Journal whose first ``mark_completed`` call raises, simulating a crash
    that happens after the event is recorded but before that fact is durably
    journaled."""

    def __init__(self, path) -> None:
        super().__init__(path)
        self._armed = True

    def mark_completed(self, request_id: str) -> None:
        if self._armed:
            self._armed = False
            raise RuntimeError("simulated crash before journal write")
        super().mark_completed(request_id)


class CrashRecoveryTests(ReplayTestCase):
    def test_crash_after_recording_but_before_marking_complete_recovers_without_duplicating(
        self,
    ) -> None:
        service = AuditService(SqliteStore(self.log_store_path), clock=lambda: "2024-01-01T00:00:00Z")
        journal = _CrashOnFirstCompletion(self.journal_path)
        importer = DeliveryImporter(service, journal)
        envelope = DeliveryEnvelope("req-1", "/v1/entries", "operator:mina", "policy.update", "allowed")

        with self.assertRaises(RuntimeError):
            importer.import_envelope(envelope)

        # the event was recorded before the simulated crash, and the
        # journal still shows the request as unfinished
        self.assertEqual(len(service.query()), 1)
        self.assertEqual(journal.find("req-1").status, PENDING)

        # retrying must not record a second event, and must finish the journal
        recovered = importer.import_envelope(envelope)
        self.assertEqual(len(service.query()), 1)
        self.assertEqual(recovered.actor, "operator:mina")
        self.assertEqual(journal.find("req-1").status, COMPLETED)

    def test_crash_before_recording_leaves_a_clean_retry(self) -> None:
        journal = JournalStore(self.journal_path)
        service = AuditService(SqliteStore(self.log_store_path), clock=lambda: "2024-01-01T00:00:00Z")
        envelope = DeliveryEnvelope("req-1", "/v1/entries", "operator:mina", "policy.update", "allowed")

        # simulate a crash that only got as far as marking the request pending
        journal.mark_pending("req-1", "/v1/entries")
        self.assertEqual(len(service.query()), 0)

        importer = DeliveryImporter(service, journal)
        event = importer.import_envelope(envelope)

        self.assertEqual(len(service.query()), 1)
        self.assertEqual(journal.find("req-1").status, COMPLETED)
        self.assertEqual(event.actor, "operator:mina")


class SeparateProcessContinuationTests(ReplayTestCase):
    def test_a_fresh_process_sharing_the_same_files_continues_the_import(self) -> None:
        # "process A" imports the first envelope of a batch
        service_a = AuditService(SqliteStore(self.log_store_path), clock=lambda: "2024-01-01T00:00:00Z")
        journal_a = JournalStore(self.journal_path)
        importer_a = DeliveryImporter(service_a, journal_a)
        first = importer_a.import_envelope(
            DeliveryEnvelope("req-1", "/v1/entries", "operator:mina", "policy.update", "allowed")
        )
        del service_a, journal_a, importer_a  # nothing carried over in memory

        # "process B": brand new objects, same files on disk, continuing the batch
        service_b = AuditService(SqliteStore(self.log_store_path), clock=lambda: "2024-01-01T00:05:00Z")
        journal_b = JournalStore(self.journal_path)
        importer_b = DeliveryImporter(service_b, journal_b)

        # replays the request id from the interrupted batch...
        replayed = importer_b.import_envelope(
            DeliveryEnvelope("req-1", "/v1/entries", "operator:mina", "policy.update", "allowed")
        )
        # ...then continues on to a new request id in the same batch
        second = importer_b.import_envelope(
            DeliveryEnvelope("req-2", "/v1/entries", "service:indexer", "report.read", "allowed")
        )

        self.assertEqual(replayed, first)
        self.assertEqual(len(service_b.query()), 2)
        self.assertEqual([e.sequence for e in service_b.query()], [1, 2])
        self.assertNotEqual(second.event_id, first.event_id)
        self.assertEqual(journal_b.find("req-1").status, COMPLETED)
        self.assertEqual(journal_b.find("req-2").status, COMPLETED)


class NeverPersistsBearerTokenTests(ReplayTestCase):
    def test_journal_schema_has_no_bearer_token_column(self) -> None:
        JournalStore(self.journal_path)  # ensure the table is created
        connection = sqlite3.connect(self.journal_path)
        try:
            columns = {row[1] for row in connection.execute("PRAGMA table_info(import_requests)")}
        finally:
            connection.close()
        self.assertEqual(columns, {"request_id", "canonical_path", "status"})

    def test_journal_methods_accept_no_token_parameter(self) -> None:
        for method in (JournalStore.mark_pending, JournalStore.mark_completed):
            params = set(inspect.signature(method).parameters)
            self.assertFalse(any("token" in p.lower() for p in params), params)

    def test_delivery_envelope_has_no_bearer_token_field(self) -> None:
        field_names = {f.name for f in dataclasses.fields(DeliveryEnvelope)}
        self.assertEqual(
            field_names,
            {"request_id", "raw_path", "actor", "action", "outcome", "metadata"},
        )


if __name__ == "__main__":
    unittest.main()
