"""Tests for AuditService: record/query/repair, independent of storage."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any

from auditlog.archive import read_legacy_archive
from auditlog.models import AuditEvent, content_digest
from auditlog.service import AuditService
from auditlog.store import IntegrityError, JsonLogStore

FIXTURES = Path(__file__).parent.parent / "fixtures"


class _MemoryLog:
    """A minimal in-memory stand-in for the AppendOnlyLog protocol.

    Exists to prove AuditService depends only on the protocol, not on
    JsonLogStore or any file-backed detail.
    """

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def read_all(self) -> list[AuditEvent]:
        return list(self._events)

    def append(self, actor: str, action: str, outcome: str, recorded_at: str, metadata: dict[str, Any] | None = None) -> AuditEvent:
        event = AuditEvent(
            event_id=content_digest(actor, action, outcome, recorded_at),
            sequence=len(self._events) + 1,
            actor=actor,
            action=action,
            outcome=outcome,
            recorded_at=recorded_at,
            metadata=dict(metadata or {}),
        )
        self._events.append(event)
        return event


class ServiceAgainstMemoryStoreTests(unittest.TestCase):
    """AuditService exercised through a storage backend it was never told about."""

    def test_record_assigns_gapless_sequence(self) -> None:
        service = AuditService(_MemoryLog())
        first = service.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        second = service.record("service:indexer", "report.read", "allowed", recorded_at="T2")
        self.assertEqual((first.sequence, second.sequence), (1, 2))

    def test_query_filters_by_actor_and_action(self) -> None:
        service = AuditService(_MemoryLog())
        service.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        service.record("service:indexer", "report.read", "allowed", recorded_at="T2")
        service.record("operator:mina", "key.revoke", "allowed", recorded_at="T3")

        by_actor = service.query(actor="operator:mina")
        self.assertEqual([e.action for e in by_actor], ["policy.update", "key.revoke"])

        by_action = service.query(action="report.read")
        self.assertEqual([e.actor for e in by_action], ["service:indexer"])

    def test_repair_reports_entries_checked_without_an_index(self) -> None:
        service = AuditService(_MemoryLog())
        service.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        report = service.repair()
        self.assertEqual(report.entries_checked, 1)
        self.assertFalse(report.index_rebuilt)  # _MemoryLog has no rebuild_index


class JsonLogStoreServiceTests(unittest.TestCase):
    """AuditService exercised through the real file-backed store."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self._tmpdir, ignore_errors=True)
        self.store_path = Path(self._tmpdir) / "store.db"
        self.service = AuditService(JsonLogStore(self.store_path))

    def test_record_then_query_round_trips(self) -> None:
        recorded = self.service.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        [queried] = self.service.query(actor="operator:mina")
        self.assertEqual(recorded, queried)

    def test_appending_never_alters_a_prior_entry(self) -> None:
        first = self.service.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        self.service.record("service:indexer", "report.read", "allowed", recorded_at="T2")
        [reread_first, _] = self.service.query()
        self.assertEqual(first, reread_first)

    def test_repair_rebuilds_the_actor_index(self) -> None:
        self.service.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        self.service.record("operator:mina", "key.revoke", "allowed", recorded_at="T2")
        report = self.service.repair()
        self.assertEqual(report.entries_checked, 2)
        self.assertTrue(report.index_rebuilt)

        index = json.loads((Path(self._tmpdir) / "store.db.index.json").read_text())
        self.assertEqual(index["by_actor"]["operator:mina"], [1, 2])

    def test_query_loads_the_current_format_fixture(self) -> None:
        shutil.copy(FIXTURES / "current-events.json", self.store_path)
        events = self.service.query(actor="operator:mina")
        self.assertEqual([e.action for e in events], ["policy.update"])

    def test_a_hand_edited_entry_is_detected_on_read(self) -> None:
        self.service.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        raw = json.loads(self.store_path.read_text())
        raw["entries"][0]["outcome"] = "denied"  # tamper without recomputing event_id
        self.store_path.write_text(json.dumps(raw))

        with self.assertRaises(IntegrityError):
            self.service.query()
        with self.assertRaises(IntegrityError):
            self.service.repair()

    def test_a_sequence_gap_is_detected_on_read(self) -> None:
        self.service.record("operator:mina", "policy.update", "allowed", recorded_at="T1")
        self.service.record("service:indexer", "report.read", "allowed", recorded_at="T2")
        raw = json.loads(self.store_path.read_text())
        raw["entries"][1]["sequence"] = 3
        self.store_path.write_text(json.dumps(raw))

        with self.assertRaises(IntegrityError):
            self.service.query()


class ArchiveImportServiceTests(unittest.TestCase):
    """Legacy archive entries can be loaded into a fresh, verified store."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self._tmpdir, ignore_errors=True)
        self.store_path = Path(self._tmpdir) / "imported.db"

    def test_deduplicated_archive_entries_pass_service_verification(self) -> None:
        events = read_legacy_archive(FIXTURES / "legacy-events.json")
        store = JsonLogStore(self.store_path)
        store.replace_all(events)

        service = AuditService(store)
        all_events = service.query()
        # Two archived exports of the same underlying event collapse to one.
        self.assertEqual(len(all_events), 3)
        self.assertEqual([e.sequence for e in all_events], [1, 2, 3])
        report = service.repair()
        self.assertEqual(report.entries_checked, 3)


if __name__ == "__main__":
    unittest.main()
