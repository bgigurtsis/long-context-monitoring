"""Tests for the canonical event model, sequence checks, and archive dedup."""

from __future__ import annotations

import dataclasses
import json
import unittest
from pathlib import Path

from auditlog.archive import to_canonical_events
from auditlog.models import (
    AuditEvent,
    SequenceError,
    check_gapless_sequence,
    content_digest,
)

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _event(sequence: int, actor: str = "operator:mina") -> AuditEvent:
    at = f"2024-03-02T09:0{sequence}:00Z"
    return AuditEvent(content_digest(actor, "policy.update", "allowed", at), sequence, actor, "policy.update", "allowed", at)


class AuditEventTests(unittest.TestCase):
    def test_event_is_immutable(self) -> None:
        event = _event(1)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            event.outcome = "denied"  # type: ignore[misc]

    def test_identity_ignores_metadata(self) -> None:
        at = "2024-03-02T09:00:00Z"
        base = content_digest("operator:mina", "policy.update", "allowed", at)
        with_metadata = AuditEvent(base, 1, "operator:mina", "policy.update", "allowed", at, metadata={"note": "x"})
        self.assertEqual(base, with_metadata.recomputed_id())

    def test_recomputed_id_detects_edit(self) -> None:
        event = _event(1)
        edited = dataclasses.replace(event, outcome="denied")
        self.assertNotEqual(edited.event_id, edited.recomputed_id())


class GaplessSequenceTests(unittest.TestCase):
    def test_gapless_run_passes(self) -> None:
        events = [_event(1), _event(2), _event(3)]
        check_gapless_sequence(events)  # must not raise

    def test_empty_trail_passes(self) -> None:
        check_gapless_sequence([])  # must not raise

    def test_gap_is_detected(self) -> None:
        events = [_event(1), _event(3)]
        with self.assertRaises(SequenceError):
            check_gapless_sequence(events)

    def test_duplicate_sequence_is_detected(self) -> None:
        events = [_event(1), _event(1)]
        with self.assertRaises(SequenceError):
            check_gapless_sequence(events)

    def test_must_start_at_one(self) -> None:
        events = [_event(2)]
        with self.assertRaises(SequenceError):
            check_gapless_sequence(events)


class ArchiveDedupTests(unittest.TestCase):
    def setUp(self) -> None:
        fixture = json.loads((FIXTURES / "legacy-events.json").read_text(encoding="utf-8"))
        self.events = to_canonical_events(fixture["entries"])

    def test_export_duplicate_collapses_to_one_event(self) -> None:
        # legacy-events.json has 4 raw rows but only 3 distinct events: the
        # first two rows are the same event re-exported with a 2s time drift.
        self.assertEqual(len(self.events), 3)

    def test_representative_timestamp_is_the_earliest_export(self) -> None:
        merged = next(e for e in self.events if e.action == "policy.update")
        self.assertEqual(merged.recorded_at, "2024-03-02T10:15:00Z")
        self.assertEqual(merged.metadata["origin_ref"], "arch-1001")

    def test_sequence_is_gapless_and_stable(self) -> None:
        check_gapless_sequence(self.events)  # must not raise

    def test_distinct_events_are_preserved(self) -> None:
        actions = sorted(e.action for e in self.events)
        self.assertEqual(actions, ["key.revoke", "policy.update", "report.read"])

    def test_archive_events_are_marked_source_version_one(self) -> None:
        self.assertTrue(all(e.source_version == 1 for e in self.events))


if __name__ == "__main__":
    unittest.main()
