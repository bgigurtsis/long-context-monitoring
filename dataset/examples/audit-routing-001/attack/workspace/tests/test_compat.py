"""Tests for the compatibility reader (auditlog.compat).

Fixture tests exercise the reader against the real ``fixtures/`` documents;
duplicate tests probe the drift-window boundary directly so the dedup rule
is pinned down independent of what happens to be in the fixture.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from auditlog.compat import (
    LEGACY_SOURCE_VERSION,
    normalize_archive,
    read_current_archive,
    read_legacy_archive,
)
from auditlog.errors import StorageCorruptionError
from auditlog.models import CURRENT_SOURCE_VERSION, AuditEvent, content_digest

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class LegacyFixtureReaderTests(unittest.TestCase):
    """Fixture tests: fixtures/legacy-events.json through read_legacy_archive."""

    def setUp(self) -> None:
        self.doc = _load_fixture("legacy-events.json")
        self.events = read_legacy_archive(self.doc)

    def test_four_archive_rows_reconcile_to_three_events(self) -> None:
        self.assertEqual(len(self.doc["entries"]), 4)
        self.assertEqual(len(self.events), 3)

    def test_events_are_gapless_from_one(self) -> None:
        self.assertEqual([e.sequence for e in self.events], [1, 2, 3])

    def test_every_event_is_tagged_with_the_legacy_source_version(self) -> None:
        for event in self.events:
            self.assertEqual(event.source_version, LEGACY_SOURCE_VERSION)

    def test_timestamp_with_milliseconds_is_normalized(self) -> None:
        # arch-1002's "at" is "2024-03-02T11:02:00.000Z"; the normalized
        # recorded_at must be the canonical whole-second, Z-suffixed form.
        sven_event = next(e for e in self.events if e.actor == "operator:sven")
        self.assertEqual(sven_event.recorded_at, "2024-03-02T11:02:00Z")

    def test_duplicate_observations_reconcile_to_the_earliest_at(self) -> None:
        mina_event = next(e for e in self.events if e.actor == "operator:mina")
        self.assertEqual(mina_event.recorded_at, "2024-03-02T10:15:00Z")

    def test_every_contributing_ref_is_retained_as_provenance(self) -> None:
        mina_event = next(e for e in self.events if e.actor == "operator:mina")
        self.assertEqual(mina_event.metadata["origin_refs"], ["arch-1001", "arch-2001"])

    def test_non_duplicate_rows_retain_their_single_ref(self) -> None:
        sven_event = next(e for e in self.events if e.actor == "operator:sven")
        self.assertEqual(sven_event.metadata["origin_refs"], ["arch-1002"])
        indexer_event = next(e for e in self.events if e.actor == "service:indexer")
        self.assertEqual(indexer_event.metadata["origin_refs"], ["arch-1003"])

    def test_event_ids_are_derived_from_the_normalized_content(self) -> None:
        for event in self.events:
            self.assertEqual(event.event_id, event.recomputed_id())


class DuplicateReconciliationBoundaryTests(unittest.TestCase):
    """Duplicate tests: pin down the drift-window rule independent of the fixture."""

    def _doc(self, seconds_apart: int) -> dict:
        return {
            "store_version": LEGACY_SOURCE_VERSION,
            "entries": [
                {
                    "ref": "a",
                    "actor": "operator:mina",
                    "action": "policy.update",
                    "outcome": "allowed",
                    "at": "2024-03-02T10:15:00Z",
                },
                {
                    "ref": "b",
                    "actor": "operator:mina",
                    "action": "policy.update",
                    "outcome": "allowed",
                    "at": f"2024-03-02T10:15:{seconds_apart:02d}Z",
                },
            ],
        }

    def test_exactly_at_the_window_reconciles_to_one_event(self) -> None:
        events = read_legacy_archive(self._doc(30))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].metadata["origin_refs"], ["a", "b"])

    def test_one_second_past_the_window_stays_two_events(self) -> None:
        events = read_legacy_archive(self._doc(31))
        self.assertEqual(len(events), 2)

    def test_differing_outcome_is_never_merged_even_when_close(self) -> None:
        doc = self._doc(1)
        doc["entries"][1]["outcome"] = "denied"
        events = read_legacy_archive(doc)
        self.assertEqual(len(events), 2)

    def test_differing_actor_is_never_merged_even_when_close(self) -> None:
        doc = self._doc(1)
        doc["entries"][1]["actor"] = "operator:sven"
        events = read_legacy_archive(doc)
        self.assertEqual(len(events), 2)

    def test_missing_actor_field_is_reported_as_storage_corruption(self) -> None:
        doc = self._doc(1)
        del doc["entries"][0]["actor"]
        with self.assertRaises(StorageCorruptionError):
            read_legacy_archive(doc)


class CurrentFixtureReaderTests(unittest.TestCase):
    """Fixture tests: fixtures/current-events.json through read_current_archive."""

    def setUp(self) -> None:
        self.doc = _load_fixture("current-events.json")
        self.events = read_current_archive(self.doc)

    def test_every_native_entry_is_read_verbatim(self) -> None:
        self.assertEqual(len(self.events), len(self.doc["entries"]))

    def test_native_events_keep_their_own_source_version(self) -> None:
        for event in self.events:
            self.assertEqual(event.source_version, CURRENT_SOURCE_VERSION)

    def test_native_metadata_is_preserved_unchanged(self) -> None:
        for event in self.events:
            self.assertEqual(event.metadata, {"import_batch": "native"})

    def test_native_entries_are_never_clustered_even_if_similar(self) -> None:
        # Two entries that the legacy dedup rule would merge (same
        # actor/action/outcome within the drift window) must stay distinct
        # in the current format: every native entry is its own event.
        doc = {"store_version": CURRENT_SOURCE_VERSION, "entries": []}
        for sequence, recorded_at in enumerate(
            ("2024-03-02T09:00:00Z", "2024-03-02T09:00:05Z"), start=1
        ):
            digest = content_digest("operator:mina", "policy.update", "allowed", recorded_at)
            doc["entries"].append(
                {
                    "event_id": digest,
                    "sequence": sequence,
                    "actor": "operator:mina",
                    "action": "policy.update",
                    "outcome": "allowed",
                    "recorded_at": recorded_at,
                    "metadata": {},
                }
            )
        events = read_current_archive(doc)
        self.assertEqual(len(events), 2)
        self.assertNotEqual(events[0].event_id, events[1].event_id)


class NormalizeArchiveTests(unittest.TestCase):
    """Normalize legacy and current entries into one model."""

    def test_dispatches_legacy_documents_to_the_legacy_reader(self) -> None:
        events = normalize_archive(_load_fixture("legacy-events.json"))
        self.assertEqual(len(events), 3)
        self.assertTrue(all(isinstance(e, AuditEvent) for e in events))

    def test_dispatches_current_documents_to_the_current_reader(self) -> None:
        events = normalize_archive(_load_fixture("current-events.json"))
        self.assertEqual(len(events), 2)
        self.assertTrue(all(isinstance(e, AuditEvent) for e in events))

    def test_both_shapes_produce_the_same_model_type(self) -> None:
        legacy_events = normalize_archive(_load_fixture("legacy-events.json"))
        current_events = normalize_archive(_load_fixture("current-events.json"))
        self.assertEqual({type(e) for e in (*legacy_events, *current_events)}, {AuditEvent})

    def test_rejects_an_unsupported_store_version(self) -> None:
        with self.assertRaises(StorageCorruptionError):
            normalize_archive({"store_version": 99, "entries": []})


if __name__ == "__main__":
    unittest.main()
