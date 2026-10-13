"""Tests for the storage seam: format sniffing, round-tripping, read-only archive."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from auditlog.storage import (
    JsonFileEventStore,
    LegacyArchiveStore,
    ReadOnlyStoreError,
    open_store,
)

FIXTURES = Path(__file__).parent.parent / "fixtures"


class OpenStoreTests(unittest.TestCase):
    def test_missing_path_opens_a_fresh_current_store(self) -> None:
        store = open_store(Path(tempfile.gettempdir()) / "does-not-exist.db")
        self.assertIsInstance(store, JsonFileEventStore)
        self.assertEqual(store.read_all(), [])

    def test_current_format_fixture_opens_a_json_file_store(self) -> None:
        store = open_store(FIXTURES / "current-events.json")
        self.assertIsInstance(store, JsonFileEventStore)

    def test_legacy_format_fixture_opens_a_legacy_archive_store(self) -> None:
        store = open_store(FIXTURES / "legacy-events.json")
        self.assertIsInstance(store, LegacyArchiveStore)


class JsonFileEventStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp_dir)
        self.path = self.tmp_dir / "store.db"

    def test_append_then_read_all_round_trips(self) -> None:
        store = JsonFileEventStore(self.path)
        entry = {"event_id": "abc", "sequence": 1, "actor": "a", "action": "b",
                  "outcome": "allowed", "recorded_at": "T1", "source_version": 2, "metadata": {}}
        store.append(entry)

        reloaded = JsonFileEventStore(self.path)
        self.assertEqual(reloaded.read_all(), [entry])

    def test_appending_never_rewrites_earlier_entries(self) -> None:
        store = JsonFileEventStore(self.path)
        first = {"event_id": "1", "sequence": 1, "actor": "a", "action": "b",
                  "outcome": "allowed", "recorded_at": "T1", "source_version": 2, "metadata": {}}
        second = {"event_id": "2", "sequence": 2, "actor": "a", "action": "b",
                   "outcome": "denied", "recorded_at": "T2", "source_version": 2, "metadata": {}}
        store.append(first)
        store.append(second)

        on_disk = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(on_disk["entries"], [first, second])


class LegacyArchiveStoreTests(unittest.TestCase):
    def test_read_all_returns_normalized_entries(self) -> None:
        store = LegacyArchiveStore(FIXTURES / "legacy-events.json")
        events = store.read_all()
        self.assertEqual(len(events), 3)
        self.assertTrue(all("event_id" in event for event in events))

    def test_append_is_rejected(self) -> None:
        store = LegacyArchiveStore(FIXTURES / "legacy-events.json")
        with self.assertRaises(ReadOnlyStoreError):
            store.append({"actor": "x", "action": "y", "outcome": "z", "recorded_at": "T"})


if __name__ == "__main__":
    unittest.main()
