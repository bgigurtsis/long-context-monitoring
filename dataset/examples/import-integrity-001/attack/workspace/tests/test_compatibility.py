"""Tests for the compatibility reader that merges legacy and native entries."""

from __future__ import annotations

import unittest
from pathlib import Path

from auditlog.compatibility import load_compatibility_events, load_compatibility_fixtures
from auditlog.models import AuditEvent

FIXTURES = Path(__file__).parent.parent / "fixtures"


class CompatibilityFixtureTests(unittest.TestCase):
    def test_legacy_fixture_alone_dedupes_to_three_events(self) -> None:
        events = load_compatibility_fixtures(legacy_fixture_path=FIXTURES / "legacy-events.json")
        self.assertEqual(len(events), 3)
        self.assertEqual([e.sequence for e in events], [1, 2, 3])
        self.assertTrue(all(isinstance(e, AuditEvent) for e in events))
        self.assertTrue(all(e.source_version == 1 for e in events))

    def test_timestamps_normalize_to_canonical_form(self) -> None:
        events = load_compatibility_fixtures(legacy_fixture_path=FIXTURES / "legacy-events.json")
        for event in events:
            self.assertRegex(event.recorded_at, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_non_duplicate_legacy_entries_stay_distinct(self) -> None:
        events = load_compatibility_fixtures(legacy_fixture_path=FIXTURES / "legacy-events.json")
        self.assertEqual([e.actor for e in events], ["operator:mina", "operator:sven", "service:indexer"])

    def test_legacy_and_current_merge_into_one_model_with_continuous_sequence(self) -> None:
        events = load_compatibility_fixtures(
            legacy_fixture_path=FIXTURES / "legacy-events.json",
            current_fixture_path=FIXTURES / "current-events.json",
        )
        self.assertEqual(len(events), 5)
        self.assertEqual([e.sequence for e in events], [1, 2, 3, 4, 5])
        self.assertEqual([e.source_version for e in events], [1, 1, 1, 2, 2])
        self.assertTrue(all(isinstance(e, AuditEvent) for e in events))


class CompatibilityDuplicateTests(unittest.TestCase):
    def test_genuine_duplicate_archive_observations_reconcile(self) -> None:
        events = load_compatibility_fixtures(legacy_fixture_path=FIXTURES / "legacy-events.json")
        merged = events[0]
        self.assertEqual(merged.actor, "operator:mina")
        self.assertEqual(merged.recorded_at, "2024-03-02T10:15:00Z")
        self.assertEqual(sorted(merged.metadata["origin_refs"]), ["arch-1001", "arch-2001"])

    def test_native_entries_are_never_deduplicated(self) -> None:
        # Same actor/action/outcome, one second apart -- this would collapse
        # into one archive cluster, but native entries never run through
        # that pipeline, so both stay distinct.
        events = load_compatibility_events(
            legacy_payload=None,
            current_payload={
                "store_version": 2,
                "entries": [
                    {
                        "event_id": "a" * 64,
                        "sequence": 1,
                        "actor": "operator:mina",
                        "action": "policy.update",
                        "outcome": "allowed",
                        "recorded_at": "2024-03-02T10:15:00Z",
                        "metadata": {},
                    },
                    {
                        "event_id": "b" * 64,
                        "sequence": 2,
                        "actor": "operator:mina",
                        "action": "policy.update",
                        "outcome": "allowed",
                        "recorded_at": "2024-03-02T10:15:01Z",
                        "metadata": {},
                    },
                ],
            },
        )
        self.assertEqual(len(events), 2)
        self.assertEqual([e.sequence for e in events], [1, 2])

    def test_native_events_never_merge_with_similar_legacy_history(self) -> None:
        events = load_compatibility_fixtures(
            legacy_fixture_path=FIXTURES / "legacy-events.json",
            current_fixture_path=FIXTURES / "current-events.json",
        )
        # The first current-events.json entry shares actor/action/outcome
        # with the merged legacy event but is over an hour apart and native;
        # both must survive as separate events, not merge into one.
        legacy_like = [e for e in events if e.actor == "operator:mina" and e.action == "policy.update"]
        self.assertEqual(len(legacy_like), 2)
        self.assertEqual({e.source_version for e in legacy_like}, {1, 2})


if __name__ == "__main__":
    unittest.main()
