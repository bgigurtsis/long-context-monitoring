"""Tests for the canonical event model: identity, immutability, and the
strict-sequence contract the append-only trail depends on."""

from __future__ import annotations

import dataclasses
import unittest

from auditlog.models import AuditEvent, SequenceError, content_digest, validate_sequence


def _event(sequence: int, at: str = "T1", actor: str = "operator:mina", action: str = "policy.update", outcome: str = "allowed") -> AuditEvent:
    return AuditEvent(content_digest(actor, action, outcome, at), sequence, actor, action, outcome, at)


class CanonicalEventTests(unittest.TestCase):
    def test_event_is_immutable(self) -> None:
        event = _event(1)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            event.outcome = "denied"  # type: ignore[misc]

    def test_metadata_is_not_part_of_identity(self) -> None:
        first = AuditEvent(
            content_digest("operator:mina", "policy.update", "allowed", "T1"),
            1,
            "operator:mina",
            "policy.update",
            "allowed",
            "T1",
            metadata={"import_batch": "native"},
        )
        second = dataclasses.replace(first, metadata={"import_batch": "different"})
        self.assertEqual(first.event_id, second.event_id)
        self.assertEqual(first.recomputed_id(), second.recomputed_id())

    def test_separator_prevents_field_concatenation_collisions(self) -> None:
        split_across_actor_action = content_digest("a", "bc", "allowed", "T1")
        split_across_action_outcome = content_digest("ab", "c", "allowed", "T1")
        self.assertNotEqual(split_across_actor_action, split_across_action_outcome)

    def test_validate_sequence_accepts_a_gapless_run(self) -> None:
        validate_sequence([_event(1), _event(2), _event(3)])

    def test_validate_sequence_rejects_a_gap(self) -> None:
        with self.assertRaises(SequenceError):
            validate_sequence([_event(1), _event(3)])

    def test_validate_sequence_rejects_a_duplicate(self) -> None:
        with self.assertRaises(SequenceError):
            validate_sequence([_event(1), _event(1)])

    def test_validate_sequence_rejects_reordering(self) -> None:
        with self.assertRaises(SequenceError):
            validate_sequence([_event(2), _event(1)])

    def test_validate_sequence_accepts_empty_trail(self) -> None:
        validate_sequence([])


if __name__ == "__main__":
    unittest.main()
