"""Tests for restart-safe mesh request import replay.

Covers duplicate envelopes, crash recovery at both points a process can die
mid-import, conflicting reuse of a request id, normalization stability
across equivalent path spellings, and continuation from a separate OS
process reading the same persisted ledger and audit store.
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from auditlog.mesh_import import (
    MESH_REQUEST_ID_METADATA_KEY,
    MeshEnvelopeError,
    MeshImportConflictError,
    MeshImportLedger,
    import_mesh_request,
)
from auditlog.models import validate_sequence
from auditlog.paths import AmbiguousPathError
from auditlog.service import AuditService
from auditlog.storage import SqliteAuditStore

REPO_ROOT = Path(__file__).parent.parent

_SUBPROCESS_IMPORT_SCRIPT = """
import json
import sys

from auditlog.mesh_import import MeshImportLedger, import_mesh_request
from auditlog.service import AuditService
from auditlog.storage import SqliteAuditStore

ledger_path, store_path, envelope_json = sys.argv[1], sys.argv[2], sys.argv[3]
ledger = MeshImportLedger(ledger_path)
service = AuditService(SqliteAuditStore(store_path))
result = import_mesh_request(ledger, service, json.loads(envelope_json))
print(json.dumps({
    "event_id": result.event.event_id,
    "sequence": result.event.sequence,
    "replayed": result.replayed,
}))
"""

_SUBPROCESS_SEED_PENDING_SCRIPT = """
import sys

from auditlog.mesh_import import MeshImportLedger

ledger_path, request_id, canonical_path = sys.argv[1], sys.argv[2], sys.argv[3]
MeshImportLedger(ledger_path).mark_pending(request_id, canonical_path)
"""


def _run_subprocess(script: str, *args: str) -> str:
    completed = subprocess.run(
        [sys.executable, "-c", script, *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise AssertionError(f"subprocess failed: {completed.stderr}")
    return completed.stdout.strip()


def _envelope(**overrides: str) -> "dict[str, str]":
    base = {
        "request_id": "mesh-req-1",
        "path": "/v2/entries",
        "actor": "service:mesh-importer",
        "action": "record",
        "outcome": "allowed",
        "recorded_at": "2026-01-01T00:00:00Z",
    }
    base.update(overrides)
    return base


class MeshImportTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.ledger_path = Path(self._tmp.name) / "ledger.db"
        self.store_path = Path(self._tmp.name) / "store.db"
        self.ledger = MeshImportLedger(self.ledger_path)
        self.service = AuditService(SqliteAuditStore(self.store_path))


class DuplicateEnvelopeTests(MeshImportTestCase):
    def test_replaying_the_identical_envelope_does_not_append_twice(self) -> None:
        first = import_mesh_request(self.ledger, self.service, _envelope())
        second = import_mesh_request(self.ledger, self.service, _envelope())

        self.assertFalse(first.replayed)
        self.assertTrue(second.replayed)
        self.assertEqual(first.event.event_id, second.event.event_id)
        self.assertEqual(first.event.sequence, second.event.sequence)
        self.assertEqual(len(self.service.query()), 1)

    def test_replaying_many_times_still_appends_exactly_once(self) -> None:
        for _ in range(5):
            import_mesh_request(self.ledger, self.service, _envelope())

        self.assertEqual(len(self.service.query()), 1)


class CrashRecoveryTests(MeshImportTestCase):
    def test_crash_before_the_append_is_recovered_by_performing_it(self) -> None:
        # A process that wrote the pending row and then died before ever
        # calling AuditService.record.
        self.ledger.mark_pending("mesh-req-1", "/v2/entries")

        result = import_mesh_request(self.ledger, self.service, _envelope())

        self.assertFalse(result.replayed)
        self.assertEqual(len(self.service.query()), 1)
        row = self.ledger.get("mesh-req-1")
        self.assertEqual(row.status, "completed")
        self.assertEqual(row.event_id, result.event.event_id)
        self.assertEqual(row.sequence, result.event.sequence)

    def test_crash_after_the_append_is_recovered_without_a_duplicate_append(self) -> None:
        # A process that wrote the pending row, appended the event, and then
        # died before writing the completed row.
        self.ledger.mark_pending("mesh-req-1", "/v2/entries")
        pre_crash_event = self.service.record(
            "service:mesh-importer",
            "record",
            "allowed",
            metadata={MESH_REQUEST_ID_METADATA_KEY: "mesh-req-1"},
            recorded_at="2026-01-01T00:00:00Z",
        )

        result = import_mesh_request(self.ledger, self.service, _envelope())

        self.assertTrue(result.replayed)
        self.assertEqual(result.event.event_id, pre_crash_event.event_id)
        self.assertEqual(result.event.sequence, pre_crash_event.sequence)
        self.assertEqual(len(self.service.query()), 1)
        self.assertEqual(self.ledger.get("mesh-req-1").status, "completed")

    def test_sequence_and_content_stay_intact_across_recovery(self) -> None:
        self.ledger.mark_pending("mesh-req-1", "/v2/entries")
        import_mesh_request(self.ledger, self.service, _envelope())
        import_mesh_request(
            self.ledger,
            self.service,
            _envelope(request_id="mesh-req-2", path="/v2/integrity", action="integrity"),
        )

        events = self.service.query()
        validate_sequence(events)  # raises on a gap, repeat, or reorder
        for event in events:
            self.assertEqual(event.event_id, event.recomputed_id())


class ConflictTests(MeshImportTestCase):
    def test_reusing_a_request_id_for_a_different_path_is_a_conflict(self) -> None:
        import_mesh_request(self.ledger, self.service, _envelope())

        with self.assertRaises(MeshImportConflictError):
            import_mesh_request(
                self.ledger, self.service, _envelope(path="/v2/integrity", action="integrity")
            )

    def test_a_rejected_conflict_leaves_the_original_import_untouched(self) -> None:
        first = import_mesh_request(self.ledger, self.service, _envelope())

        with self.assertRaises(MeshImportConflictError):
            import_mesh_request(
                self.ledger, self.service, _envelope(path="/v2/integrity", action="integrity")
            )

        self.assertEqual(len(self.service.query()), 1)
        row = self.ledger.get("mesh-req-1")
        self.assertEqual(row.canonical_path, "/v2/entries")
        self.assertEqual(row.status, "completed")
        self.assertEqual(row.event_id, first.event.event_id)

        replay = import_mesh_request(self.ledger, self.service, _envelope())
        self.assertTrue(replay.replayed)
        self.assertEqual(replay.event.event_id, first.event.event_id)


class NormalizationStabilityTests(MeshImportTestCase):
    def test_an_equivalent_spelling_of_the_same_path_is_a_duplicate_not_a_conflict(self) -> None:
        first = import_mesh_request(self.ledger, self.service, _envelope(path="/v2/entries"))
        second = import_mesh_request(self.ledger, self.service, _envelope(path="/v2//entries///"))

        self.assertFalse(first.replayed)
        self.assertTrue(second.replayed)
        self.assertEqual(first.event.event_id, second.event.event_id)
        self.assertEqual(second.canonical_path, "/v2/entries")
        self.assertEqual(len(self.service.query()), 1)

    def test_an_ambiguous_path_is_refused_without_touching_the_ledger_or_store(self) -> None:
        with self.assertRaises(AmbiguousPathError):
            import_mesh_request(self.ledger, self.service, _envelope(path="/v2/entries%2F"))

        self.assertIsNone(self.ledger.get("mesh-req-1"))
        self.assertEqual(self.service.query(), [])

    def test_distinct_request_ids_for_the_same_canonical_path_are_independent(self) -> None:
        first = import_mesh_request(
            self.ledger, self.service, _envelope(request_id="mesh-req-a", path="/v2/entries")
        )
        second = import_mesh_request(
            self.ledger, self.service, _envelope(request_id="mesh-req-b", path="/v2//entries")
        )

        self.assertFalse(first.replayed)
        self.assertFalse(second.replayed)
        self.assertNotEqual(first.event.sequence, second.event.sequence)
        self.assertEqual(len(self.service.query()), 2)


class SeparateProcessContinuationTests(MeshImportTestCase):
    def test_a_second_process_replays_the_first_processs_import(self) -> None:
        first_out = _run_subprocess(
            _SUBPROCESS_IMPORT_SCRIPT,
            str(self.ledger_path),
            str(self.store_path),
            json.dumps(_envelope()),
        )
        first = json.loads(first_out)
        self.assertFalse(first["replayed"])

        second_out = _run_subprocess(
            _SUBPROCESS_IMPORT_SCRIPT,
            str(self.ledger_path),
            str(self.store_path),
            json.dumps(_envelope(path="/v2//entries///")),
        )
        second = json.loads(second_out)

        self.assertTrue(second["replayed"])
        self.assertEqual(second["event_id"], first["event_id"])
        self.assertEqual(second["sequence"], first["sequence"])
        self.assertEqual(len(self.service.query()), 1)

    def test_a_pending_import_left_by_a_crashed_process_is_completed_by_a_new_process(self) -> None:
        # Process A writes the pending row -- simulating the instant before
        # it would have called AuditService.record -- and then "dies".
        _run_subprocess(
            _SUBPROCESS_SEED_PENDING_SCRIPT, str(self.ledger_path), "mesh-req-1", "/v2/entries"
        )

        row = self.ledger.get("mesh-req-1")
        self.assertEqual(row.status, "pending")
        self.assertEqual(len(self.service.query()), 0)

        # Process B starts fresh, reads the same on-disk ledger and store,
        # and completes the interrupted import.
        second_out = _run_subprocess(
            _SUBPROCESS_IMPORT_SCRIPT,
            str(self.ledger_path),
            str(self.store_path),
            json.dumps(_envelope()),
        )
        second = json.loads(second_out)

        self.assertFalse(second["replayed"])
        self.assertEqual(len(self.service.query()), 1)
        self.assertEqual(self.ledger.get("mesh-req-1").status, "completed")


class LedgerNeverPersistsBearerTokensTests(MeshImportTestCase):
    def test_an_envelope_carrying_a_bearer_token_is_rejected_outright(self) -> None:
        envelope = _envelope()
        envelope["bearer_token"] = "super-secret-token"

        with self.assertRaises(MeshEnvelopeError):
            import_mesh_request(self.ledger, self.service, envelope)

        self.assertIsNone(self.ledger.get("mesh-req-1"))
        self.assertEqual(self.service.query(), [])

    def test_the_ledger_schema_has_no_column_that_could_hold_a_credential(self) -> None:
        import_mesh_request(self.ledger, self.service, _envelope())

        conn = sqlite3.connect(self.ledger_path)
        try:
            columns = {row[1] for row in conn.execute("PRAGMA table_info(mesh_imports)")}
        finally:
            conn.close()
        self.assertEqual(
            columns, {"request_id", "canonical_path", "status", "event_id", "sequence"}
        )


if __name__ == "__main__":
    unittest.main()
