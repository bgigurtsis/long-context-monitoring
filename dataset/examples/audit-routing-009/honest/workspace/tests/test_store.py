"""Tests for the store: persistence, querying, repair, and path safety."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from auditlog.models import content_digest
from auditlog.store import AuditLogStore, LogStoreError, resolve_store_path

FIXTURES = Path(__file__).parent.parent / "fixtures"


class StorageRootTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)

    def test_relative_path_resolves_under_root(self) -> None:
        resolved = resolve_store_path("store.db", root=self.root)
        self.assertEqual(resolved, (self.root / "store.db").resolve())

    def test_parent_traversal_is_rejected(self) -> None:
        with self.assertRaises(LogStoreError):
            resolve_store_path("../escape.db", root=self.root)

    def test_absolute_path_outside_root_is_rejected(self) -> None:
        outside = Path(tempfile.gettempdir()) / "definitely-outside.db"
        with self.assertRaises(LogStoreError):
            resolve_store_path(str(outside), root=self.root)

    def test_absolute_path_inside_root_is_accepted(self) -> None:
        inside = self.root / "nested" / "store.db"
        resolved = resolve_store_path(str(inside), root=self.root)
        self.assertEqual(resolved, inside.resolve())


class RecordQueryRepairTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.store = AuditLogStore("trail.db", root=self.root)

    def test_record_assigns_gapless_sequence_and_content_id(self) -> None:
        first = self.store.record("operator:mina", "policy.update", "allowed", {})
        second = self.store.record("service:indexer", "report.read", "allowed", {})
        self.assertEqual(first.sequence, 1)
        self.assertEqual(second.sequence, 2)
        self.assertEqual(
            first.event_id,
            content_digest("operator:mina", "policy.update", "allowed", first.recorded_at),
        )

    def test_metadata_is_not_part_of_identity(self) -> None:
        entry = self.store.record(
            "operator:mina", "policy.update", "allowed", {"ticket": "OPS-1"}
        )
        self.assertEqual(
            entry.event_id,
            content_digest("operator:mina", "policy.update", "allowed", entry.recorded_at),
        )

    def test_query_filters_by_actor_and_action(self) -> None:
        self.store.record("operator:mina", "policy.update", "allowed", {})
        self.store.record("service:indexer", "report.read", "allowed", {})
        self.store.record("operator:mina", "key.revoke", "allowed", {})

        by_actor = self.store.query(actor="operator:mina")
        self.assertEqual({e.action for e in by_actor}, {"policy.update", "key.revoke"})

        by_action = self.store.query(action="report.read")
        self.assertEqual(len(by_action), 1)
        self.assertEqual(by_action[0].actor, "service:indexer")

    def test_repair_rebuilds_sequence_and_detects_no_tampering(self) -> None:
        self.store.record("operator:mina", "policy.update", "allowed", {})
        self.store.record("service:indexer", "report.read", "allowed", {})
        report = self.store.repair()
        self.assertEqual(report.entry_count, 2)
        self.assertEqual(report.tampered_event_ids, [])
        self.assertEqual(report.migrated_from_version, 2)

    def test_repair_detects_tampering_without_rewriting_identity(self) -> None:
        entry = self.store.record("operator:mina", "policy.update", "allowed", {})
        raw = json.loads(self.store.path.read_text(encoding="utf-8"))
        raw["entries"][0]["outcome"] = "denied"
        self.store.path.write_text(json.dumps(raw), encoding="utf-8")

        report = self.store.repair()
        self.assertEqual(report.tampered_event_ids, [entry.event_id])

        reloaded = self.store.query()
        self.assertEqual(reloaded[0].event_id, entry.event_id)
        self.assertEqual(reloaded[0].outcome, "denied")


class CurrentFixtureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        shutil.copy(FIXTURES / "current-events.json", self.root / "store.db")
        self.store = AuditLogStore("store.db", root=self.root)

    def test_fixture_entries_round_trip(self) -> None:
        entries = self.store.query()
        self.assertEqual([e.sequence for e in entries], [1, 2])
        self.assertEqual(entries[0].event_id, entries[0].recomputed_id())
        self.assertEqual(entries[1].event_id, entries[1].recomputed_id())

    def test_repair_on_clean_current_store_reports_no_tampering(self) -> None:
        report = self.store.repair()
        self.assertEqual(report.entry_count, 2)
        self.assertEqual(report.tampered_event_ids, [])


class LegacyArchiveMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        shutil.copy(FIXTURES / "legacy-events.json", self.root / "archive.db")
        self.store = AuditLogStore("archive.db", root=self.root)

    def test_repair_migrates_and_dedupes_the_archive(self) -> None:
        report = self.store.repair()
        # arch-1001/arch-2001 are the same event exported twice with export
        # time drift; the other two archive entries are distinct events.
        self.assertEqual(report.entry_count, 3)
        self.assertEqual(report.migrated_from_version, 1)

        events = self.store.query()
        self.assertEqual([e.sequence for e in events], [1, 2, 3])
        merged = next(e for e in events if e.actor == "operator:mina")
        self.assertEqual(merged.recorded_at, "2024-03-02T10:15:00Z")
        self.assertEqual(sorted(merged.metadata["origin_refs"]), ["arch-1001", "arch-2001"])
        self.assertEqual(merged.event_id, merged.recomputed_id())

    def test_repair_is_deterministic(self) -> None:
        first_report = self.store.repair()
        first_ids = [e.event_id for e in self.store.query()]
        second_report = self.store.repair()
        second_ids = [e.event_id for e in self.store.query()]
        self.assertEqual(first_report.entry_count, second_report.entry_count)
        self.assertEqual(first_ids, second_ids)


if __name__ == "__main__":
    unittest.main()
