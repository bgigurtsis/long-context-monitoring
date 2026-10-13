"""Tests for the canonical event model and its sequence rule."""

from __future__ import annotations

import dataclasses
import unittest

from auditlog.models import (
    AuditEvent,
    SequenceError,
    content_digest,
    validate_sequence,
)


def _event(sequence: int, actor: str = "operator:mina") -> AuditEvent:
    action, outcome, at = "policy.update", "allowed", f"2024-03-02T09:0{sequence}:00Z"
    return AuditEvent(content_digest(actor, action, outcome, at), sequence, actor, action, outcome, at)


class CanonicalEventTests(unittest.TestCase):
    def test_event_is_immutable(self) -> None:
        event = _event(1)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            event.outcome = "denied"  # type: ignore[misc]

    def test_metadata_does_not_affect_identity(self) -> None:
        actor, action, outcome, at = "operator:mina", "policy.update", "allowed", "T1"
        bare = AuditEvent(content_digest(actor, action, outcome, at), 1, actor, action, outcome, at)
        annotated = dataclasses.replace(bare, metadata={"note": "reviewed"})
        self.assertEqual(bare.event_id, annotated.event_id)
        self.assertEqual(annotated.recomputed_id(), annotated.event_id)

    def test_source_version_does_not_affect_identity(self) -> None:
        actor, action, outcome, at = "operator:mina", "policy.update", "allowed", "T1"
        bare = AuditEvent(content_digest(actor, action, outcome, at), 1, actor, action, outcome, at)
        legacy = dataclasses.replace(bare, source_version=1)
        self.assertEqual(bare.event_id, legacy.event_id)


class SequenceValidationTests(unittest.TestCase):
    def test_gapless_sequence_starting_at_one_is_valid(self) -> None:
        events = [_event(1), _event(2), _event(3)]
        validate_sequence(events)  # must not raise

    def test_empty_trail_is_valid(self) -> None:
        validate_sequence([])  # must not raise

    def test_gap_is_rejected(self) -> None:
        events = [_event(1), _event(3)]
        with self.assertRaises(SequenceError):
            validate_sequence(events)

    def test_repeated_sequence_is_rejected(self) -> None:
        events = [_event(1), _event(1)]
        with self.assertRaises(SequenceError):
            validate_sequence(events)

    def test_out_of_order_sequence_is_rejected(self) -> None:
        events = [_event(2), _event(1)]
        with self.assertRaises(SequenceError):
            validate_sequence(events)

    def test_sequence_not_starting_at_one_is_rejected(self) -> None:
        events = [_event(2)]
        with self.assertRaises(SequenceError):
            validate_sequence(events)


if __name__ == "__main__":
    unittest.main()
