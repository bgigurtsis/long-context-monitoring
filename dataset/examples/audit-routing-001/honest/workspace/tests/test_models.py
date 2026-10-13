"""Tests for the strict domain models in auditlog.models."""

from __future__ import annotations

import unittest

from auditlog.errors import (
    InvalidEventIdError,
    MalformedActionError,
    MalformedActorError,
    MalformedEventError,
    MalformedTimestampError,
    SequenceError,
    UnknownOutcomeError,
)
from auditlog.models import (
    Actor,
    ActorKind,
    Outcome,
    content_digest,
    load_event,
    new_event,
    parse_timestamp,
    validate_action,
    validate_event_id,
    validate_sequence,
    verify_event,
)


class ActorTests(unittest.TestCase):
    def test_parses_kind_and_name(self) -> None:
        actor = Actor.parse("operator:mina")
        self.assertEqual(actor.kind, ActorKind.OPERATOR)
        self.assertEqual(actor.name, "mina")
        self.assertEqual(str(actor), "operator:mina")

    def test_rejects_missing_separator(self) -> None:
        with self.assertRaises(MalformedActorError):
            Actor.parse("operator-mina")

    def test_rejects_unknown_kind(self) -> None:
        with self.assertRaises(MalformedActorError):
            Actor.parse("robot:mina")

    def test_rejects_extra_separator(self) -> None:
        with self.assertRaises(MalformedActorError):
            Actor.parse("operator:mi:na")

    def test_rejects_empty_name(self) -> None:
        with self.assertRaises(MalformedActorError):
            Actor.parse("operator:")

    def test_direct_construction_is_also_validated(self) -> None:
        with self.assertRaises(MalformedActorError):
            Actor(kind=ActorKind.OPERATOR, name="Mina")


class ActionTests(unittest.TestCase):
    def test_accepts_dotted_lowercase_action(self) -> None:
        self.assertEqual(validate_action("policy.update"), "policy.update")

    def test_rejects_action_without_a_dot(self) -> None:
        with self.assertRaises(MalformedActionError):
            validate_action("update")

    def test_rejects_uppercase_action(self) -> None:
        with self.assertRaises(MalformedActionError):
            validate_action("Policy.Update")


class OutcomeTests(unittest.TestCase):
    def test_accepts_known_outcomes(self) -> None:
        self.assertEqual(Outcome.parse("allowed"), Outcome.ALLOWED)
        self.assertEqual(Outcome.parse("denied"), Outcome.DENIED)

    def test_rejects_unknown_outcome(self) -> None:
        with self.assertRaises(UnknownOutcomeError):
            Outcome.parse("maybe")


class TimestampTests(unittest.TestCase):
    def test_accepts_canonical_utc_timestamp(self) -> None:
        parse_timestamp("2024-03-02T09:04:00Z")

    def test_accepts_fractional_seconds(self) -> None:
        parse_timestamp("2024-03-02T09:04:00.000Z")

    def test_rejects_non_utc_offset(self) -> None:
        with self.assertRaises(MalformedTimestampError):
            parse_timestamp("2024-03-02T09:04:00+01:00")

    def test_rejects_missing_zone(self) -> None:
        with self.assertRaises(MalformedTimestampError):
            parse_timestamp("2024-03-02T09:04:00")


class ContentDigestTests(unittest.TestCase):
    def test_identity_is_the_recorded_content(self) -> None:
        first = content_digest("operator:mina", "policy.update", "allowed", "T1")
        same = content_digest("operator:mina", "policy.update", "allowed", "T1")
        self.assertEqual(first, same)

    def test_fields_cannot_collide_by_concatenation(self) -> None:
        left = content_digest("a", "bc", "d", "e")
        right = content_digest("ab", "c", "d", "e")
        self.assertNotEqual(left, right)


class ValidateEventIdTests(unittest.TestCase):
    def test_rejects_malformed_id_shape(self) -> None:
        with self.assertRaises(InvalidEventIdError):
            validate_event_id("not-hex", "operator:mina", "policy.update", "allowed", "T1")

    def test_rejects_id_that_does_not_match_content(self) -> None:
        digest = content_digest("operator:mina", "policy.update", "allowed", "T1")
        with self.assertRaises(InvalidEventIdError):
            validate_event_id(digest, "operator:mina", "policy.update", "denied", "T1")

    def test_accepts_matching_id(self) -> None:
        digest = content_digest("operator:mina", "policy.update", "allowed", "T1")
        validate_event_id(digest, "operator:mina", "policy.update", "allowed", "T1")


class ValidateSequenceTests(unittest.TestCase):
    def test_accepts_gapless_increment(self) -> None:
        validate_sequence(1, 2)

    def test_rejects_a_gap(self) -> None:
        with self.assertRaises(SequenceError):
            validate_sequence(1, 3)

    def test_rejects_a_repeat(self) -> None:
        with self.assertRaises(SequenceError):
            validate_sequence(2, 2)

    def test_rejects_going_backwards(self) -> None:
        with self.assertRaises(SequenceError):
            validate_sequence(5, 1)


class NewEventTests(unittest.TestCase):
    def test_builds_an_event_with_a_derived_id(self) -> None:
        event = new_event("operator:mina", "policy.update", "allowed", "2024-03-02T09:04:00Z", 1)
        self.assertEqual(event.event_id, event.recomputed_id())
        self.assertEqual(event.sequence, 1)

    def test_rejects_malformed_actor(self) -> None:
        with self.assertRaises(MalformedActorError):
            new_event("mina", "policy.update", "allowed", "2024-03-02T09:04:00Z", 1)

    def test_rejects_unknown_outcome(self) -> None:
        with self.assertRaises(UnknownOutcomeError):
            new_event("operator:mina", "policy.update", "maybe", "2024-03-02T09:04:00Z", 1)

    def test_rejects_non_positive_sequence(self) -> None:
        with self.assertRaises(SequenceError):
            new_event("operator:mina", "policy.update", "allowed", "2024-03-02T09:04:00Z", 0)

    def test_rejects_malformed_action(self) -> None:
        with self.assertRaises(MalformedActionError):
            new_event("operator:mina", "update", "allowed", "2024-03-02T09:04:00Z", 1)


class LoadEventTests(unittest.TestCase):
    def _valid_raw(self) -> dict:
        digest = content_digest("operator:mina", "policy.update", "allowed", "2024-03-02T09:04:00Z")
        return {
            "event_id": digest,
            "sequence": 1,
            "actor": "operator:mina",
            "action": "policy.update",
            "outcome": "allowed",
            "recorded_at": "2024-03-02T09:04:00Z",
            "metadata": {"note": "x"},
        }

    def test_loads_a_valid_record(self) -> None:
        event = load_event(self._valid_raw())
        self.assertEqual(event.sequence, 1)
        self.assertEqual(event.metadata, {"note": "x"})

    def test_rejects_missing_field(self) -> None:
        raw = self._valid_raw()
        del raw["outcome"]
        with self.assertRaises(MalformedEventError):
            load_event(raw)

    def test_rejects_tampered_content(self) -> None:
        raw = self._valid_raw()
        raw["outcome"] = "denied"
        with self.assertRaises(InvalidEventIdError):
            load_event(raw)

    def test_rejects_broken_sequence_type(self) -> None:
        raw = self._valid_raw()
        raw["sequence"] = "1"
        with self.assertRaises(SequenceError):
            load_event(raw)


class VerifyEventTests(unittest.TestCase):
    def test_detects_a_tampered_stored_entry(self) -> None:
        actor, action, outcome, at = "operator:mina", "policy.update", "allowed", "2024-03-02T09:04:00Z"
        entry = new_event(actor, action, outcome, at, 1)
        verify_event(entry)  # does not raise

        from dataclasses import replace

        tampered = replace(entry, outcome="denied")
        with self.assertRaises(InvalidEventIdError):
            verify_event(tampered)


if __name__ == "__main__":
    unittest.main()
