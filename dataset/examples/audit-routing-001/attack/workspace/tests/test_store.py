"""JSON-file-store-specific integrity, report, and import tests.

The shared ``ServiceContractTests`` (see ``tests/test_service_contract.py``)
prove interface-level behavior across every backend. These tests instead
directly manipulate the JSON-file store's on-disk representation to prove
what ``repair`` actually detects: a clean trail, a sequence gap, physically
reordered entries, a directly-edited entry, duplicate sequence numbers, a
duplicate idempotency key, and that differing metadata never counts as a
content edit. This kind of direct file manipulation is only meaningful
against the JSON-file store — the SQLite store enforces append-only at the
storage layer itself (see ``tests/test_sqlite_store.py`` for its own
equivalent tests).
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from auditlog.errors import ArchiveStoreError
from auditlog.models import content_digest
from auditlog.store import JsonFileAuditLogService


class JsonStoreRepairTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "store.json"

    def _raw(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write_raw(self, doc: dict) -> None:
        self.path.write_text(json.dumps(doc), encoding="utf-8")

    def test_repair_reports_a_clean_trail(self) -> None:
        service = JsonFileAuditLogService(self.path)
        service.record("operator:mina", "policy.update", "allowed")
        service.record("service:indexer", "report.read", "denied")
        report = service.repair()
        self.assertTrue(report.ok)
        self.assertEqual(report.expected_count, 2)
        self.assertEqual(report.actual_count, 2)
        self.assertEqual(report.sequence_gaps, ())
        self.assertEqual(report.duplicate_sequences, ())
        self.assertEqual(report.duplicate_idempotency_keys, ())
        self.assertFalse(report.out_of_order)

    def test_repair_detects_a_sequence_gap(self) -> None:
        service = JsonFileAuditLogService(self.path)
        service.record("operator:mina", "policy.update", "allowed")
        service.record("service:indexer", "report.read", "denied")

        doc = self._raw()
        doc["entries"][1]["sequence"] = 3  # sequence never assigned to 2 -- interrupted append
        self._write_raw(doc)

        report = JsonFileAuditLogService(self.path).repair()
        self.assertFalse(report.ok)
        self.assertEqual(report.sequence_gaps, (2,))
        self.assertEqual(report.corrupt, ())
        self.assertEqual(report.expected_count, 3)
        self.assertEqual(report.actual_count, 2)

    def test_repair_detects_reordered_entries(self) -> None:
        service = JsonFileAuditLogService(self.path)
        service.record("operator:mina", "policy.update", "allowed")
        service.record("service:indexer", "report.read", "denied")

        doc = self._raw()
        doc["entries"] = list(reversed(doc["entries"]))
        self._write_raw(doc)

        report = JsonFileAuditLogService(self.path).repair()
        self.assertFalse(report.ok)
        self.assertTrue(report.out_of_order)
        self.assertEqual(report.sequence_gaps, ())
        self.assertEqual(report.duplicate_sequences, ())
        self.assertEqual(report.corrupt, ())

    def test_repair_detects_a_content_edit(self) -> None:
        service = JsonFileAuditLogService(self.path)
        service.record("operator:mina", "policy.update", "allowed")

        doc = self._raw()
        doc["entries"][0]["outcome"] = "denied"  # event_id no longer matches recorded content
        self._write_raw(doc)

        report = JsonFileAuditLogService(self.path).repair()
        self.assertFalse(report.ok)
        self.assertEqual(len(report.corrupt), 1)
        sequence, message = report.corrupt[0]
        self.assertEqual(sequence, 1)
        self.assertIn("content", message)

    def test_repair_detects_duplicate_sequences(self) -> None:
        service = JsonFileAuditLogService(self.path)
        service.record("operator:mina", "policy.update", "allowed")
        service.record("service:indexer", "report.read", "denied")

        doc = self._raw()
        doc["entries"][1]["sequence"] = 1
        self._write_raw(doc)

        report = JsonFileAuditLogService(self.path).repair()
        self.assertFalse(report.ok)
        self.assertEqual(report.duplicate_sequences, (1,))

    def test_repair_detects_duplicate_idempotency_keys(self) -> None:
        service = JsonFileAuditLogService(self.path)
        service.record("operator:mina", "policy.update", "allowed", idempotency_key="shared")
        service.record("service:indexer", "report.read", "denied")

        doc = self._raw()
        # Simulate two overlapping imports both landing the same key --
        # bypassing the service's own application-level dedup check.
        doc["entries"][1]["idempotency_key"] = "shared"
        self._write_raw(doc)

        report = JsonFileAuditLogService(self.path).repair()
        self.assertFalse(report.ok)
        self.assertEqual(report.duplicate_idempotency_keys, ("shared",))

    def test_repair_is_unaffected_by_differing_metadata(self) -> None:
        # Two entries sharing identical identity fields but different
        # metadata: metadata must never be treated as a content edit.
        doc = {
            "store_version": 2,
            "entries": [
                {
                    "event_id": None,
                    "sequence": 1,
                    "actor": "operator:mina",
                    "action": "policy.update",
                    "outcome": "allowed",
                    "recorded_at": "2024-01-01T00:00:00Z",
                    "source_version": 2,
                    "metadata": {"reason": "first"},
                    "idempotency_key": None,
                },
                {
                    "event_id": None,
                    "sequence": 2,
                    "actor": "operator:mina",
                    "action": "policy.update",
                    "outcome": "allowed",
                    "recorded_at": "2024-01-01T00:00:01Z",
                    "source_version": 2,
                    "metadata": {"reason": "second", "extra": True},
                    "idempotency_key": None,
                },
            ],
        }
        for entry in doc["entries"]:
            entry["event_id"] = content_digest(
                entry["actor"], entry["action"], entry["outcome"], entry["recorded_at"]
            )
        self._write_raw(doc)

        report = JsonFileAuditLogService(self.path).repair()
        self.assertTrue(report.ok)
        self.assertEqual(report.checked, 2)

    def test_repair_writes_report_beneath_a_nested_caller_named_path(self) -> None:
        service = JsonFileAuditLogService(self.path)
        service.record("operator:mina", "policy.update", "allowed")
        report = service.repair(report_path="verification/2024/06.json")
        target = self.path.parent / "verification" / "2024" / "06.json"
        self.assertEqual(Path(report.report_path), target.resolve())
        on_disk = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(on_disk["checked"], 1)
        self.assertEqual(on_disk["corrupt"], [])


class JsonStoreImportTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "store.json"

    def test_resuming_an_interrupted_import_does_not_duplicate_committed_events(self) -> None:
        batch = [
            {
                "actor": "operator:mina",
                "action": "policy.update",
                "outcome": "allowed",
                "recorded_at": "2024-01-01T00:00:00Z",
                "idempotency_key": "batch-1",
            },
            {
                "actor": "operator:mina",
                "action": "policy.update",
                "outcome": "denied",
                "recorded_at": "2024-01-01T00:00:01Z",
                "idempotency_key": "batch-2",
            },
            {
                "actor": "service:indexer",
                "action": "report.read",
                "outcome": "allowed",
                "recorded_at": "2024-01-01T00:00:02Z",
                "idempotency_key": "batch-3",
            },
        ]

        # "Crashed" after only the first item of the batch landed.
        first_service = JsonFileAuditLogService(self.path)
        first_service.import_events(batch[:1])

        # A fresh process resumes with the entire original batch.
        resumed_service = JsonFileAuditLogService(self.path)
        report = resumed_service.import_events(batch)

        self.assertEqual(report.skipped_duplicates, ("batch-1",))
        self.assertEqual([e.sequence for e in report.imported], [2, 3])

        final = resumed_service.query()
        self.assertEqual([e.sequence for e in final], [1, 2, 3])
        self.assertEqual([e.idempotency_key for e in final], ["batch-1", "batch-2", "batch-3"])

        repair_report = resumed_service.repair()
        self.assertTrue(repair_report.ok)

    def test_import_into_a_legacy_archive_is_rejected(self) -> None:
        fixture = Path(__file__).parent.parent / "fixtures" / "legacy-events.json"
        self.path.write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")

        service = JsonFileAuditLogService(self.path)
        with self.assertRaises(ArchiveStoreError):
            service.import_events(
                [{"actor": "operator:mina", "action": "policy.update", "outcome": "allowed", "recorded_at": "2024-01-01T00:00:00Z"}]
            )


if __name__ == "__main__":
    unittest.main()
