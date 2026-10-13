"""Tests for normalizing the legacy archive format."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from auditlog.archive import normalize_legacy_entries
from auditlog.models import content_digest


class NormalizeLegacyEntriesTests(unittest.TestCase):
    def setUp(self) -> None:
        fixture_path = Path(__file__).parent.parent / "fixtures" / "legacy-events.json"
        self.raw_entries = json.loads(fixture_path.read_text(encoding="utf-8"))["entries"]

    def test_export_duplicates_collapse_to_one_event(self) -> None:
        events = normalize_legacy_entries(self.raw_entries)

        # Four archive rows, but the first two are the same policy.update
        # event re-exported two seconds apart, so three events remain.
        self.assertEqual(len(events), 3)

        merged = next(e for e in events if e["action"] == "policy.update")
        self.assertEqual(merged["recorded_at"], "2024-03-02T10:15:00Z")
        self.assertEqual(sorted(merged["metadata"]["origin_refs"]), ["arch-1001", "arch-2001"])

    def test_representative_timestamp_is_deterministic_regardless_of_order(self) -> None:
        forward = normalize_legacy_entries(self.raw_entries)
        backward = normalize_legacy_entries(list(reversed(self.raw_entries)))

        by_action = lambda events: {e["action"]: e["recorded_at"] for e in events}
        self.assertEqual(by_action(forward), by_action(backward))

    def test_event_id_is_derived_from_the_chosen_content(self) -> None:
        events = normalize_legacy_entries(self.raw_entries)
        merged = next(e for e in events if e["action"] == "policy.update")

        expected_id = content_digest(
            merged["actor"], merged["action"], merged["outcome"], merged["recorded_at"]
        )
        self.assertEqual(merged["event_id"], expected_id)

    def test_far_apart_repeats_of_the_same_content_stay_distinct(self) -> None:
        raw = [
            {"ref": "a", "actor": "operator:mina", "action": "login", "outcome": "allowed",
             "at": "2024-01-01T00:00:00Z"},
            {"ref": "b", "actor": "operator:mina", "action": "login", "outcome": "allowed",
             "at": "2024-01-02T00:00:00Z"},
        ]
        events = normalize_legacy_entries(raw)
        self.assertEqual(len(events), 2)


if __name__ == "__main__":
    unittest.main()
