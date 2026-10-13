"""Tests for canonical events and archive reconciliation."""

from __future__ import annotations

import dataclasses
import json
import unittest
from pathlib import Path

from auditlog.models import AuditEvent, LegacyRecord, content_digest, reconcile_legacy_records

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "legacy-events.json"


def _legacy_records() -> list[LegacyRecord]:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return [LegacyRecord(**entry) for entry in fixture["entries"]]


class AuditEventTests(unittest.TestCase):
    def test_event_is_immutable(self) -> None:
        event = AuditEvent(
            content_digest("operator:mina", "policy.update", "allowed", "T1"),
            1,
            "operator:mina",
            "policy.update",
            "allowed",
            "T1",
        )
        with self.assertRaises(dataclasses.FrozenInstanceError):
            event.outcome = "denied"  # type: ignore[misc]

    def test_rejects_non_positive_sequence(self) -> None:
        with self.assertRaises(ValueError):
            AuditEvent(content_digest("a", "b", "c", "T1"), 0, "a", "b", "c", "T1")

    def test_rejects_empty_identifying_field(self) -> None:
        with self.assertRaises(ValueError):
            AuditEvent(content_digest("", "b", "c", "T1"), 1, "", "b", "c", "T1")

    def test_rejects_malformed_event_id(self) -> None:
        with self.assertRaises(ValueError):
            AuditEvent("not-a-digest", 1, "a", "b", "c", "T1")

    def test_tampered_entry_is_still_constructible_and_detectable(self) -> None:
        actor, action, outcome, at = "operator:mina", "policy.update", "allowed", "T1"
        stale_id = content_digest(actor, action, outcome, at)
        edited = AuditEvent(stale_id, 1, actor, action, "denied", at)
        self.assertNotEqual(edited.event_id, edited.recomputed_id())


class ReconcileLegacyRecordsTests(unittest.TestCase):
    def test_duplicate_archive_entries_collapse_to_one_event(self) -> None:
        events = reconcile_legacy_records(_legacy_records())
        self.assertEqual(len(events), 3)

    def test_sequence_is_gapless_from_one(self) -> None:
        events = reconcile_legacy_records(_legacy_records())
        self.assertEqual([event.sequence for event in events], [1, 2, 3])

    def test_representative_timestamp_is_the_earliest_export(self) -> None:
        events = reconcile_legacy_records(_legacy_records())
        mina_event = next(event for event in events if event.actor == "operator:mina")
        self.assertEqual(mina_event.recorded_at, "2024-03-02T10:15:00Z")

    def test_events_are_ordered_chronologically(self) -> None:
        events = reconcile_legacy_records(_legacy_records())
        self.assertEqual(
            [event.actor for event in events],
            ["operator:mina", "operator:sven", "service:indexer"],
        )

    def test_reconciliation_is_order_independent(self) -> None:
        forward = reconcile_legacy_records(_legacy_records())
        backward = reconcile_legacy_records(list(reversed(_legacy_records())))
        self.assertEqual(
            [(e.event_id, e.sequence) for e in forward],
            [(e.event_id, e.sequence) for e in backward],
        )

    def test_reconciled_events_pass_their_own_integrity_check(self) -> None:
        for event in reconcile_legacy_records(_legacy_records()):
            self.assertEqual(event.event_id, event.recomputed_id())


if __name__ == "__main__":
    unittest.main()
