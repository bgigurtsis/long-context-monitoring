"""Tests for the strict event and identity models."""

from __future__ import annotations

import unittest

from auditlog.models import (
    AuditEvent,
    Identity,
    InvalidActorError,
    InvalidEventIdError,
    InvalidOutcomeError,
    InvalidSequenceError,
    Outcome,
    content_digest,
    is_valid_event_id,
)

VALID_ID = content_digest("operator:mina", "policy.update", "allowed", "T1")


def make_event(**overrides):
    fields = dict(
        event_id=VALID_ID,
        sequence=1,
        actor="operator:mina",
        action="policy.update",
        outcome="allowed",
        recorded_at="T1",
    )
    fields.update(overrides)
    return AuditEvent(**fields)


class IdentityTests(unittest.TestCase):
    def test_parses_kind_and_name(self) -> None:
        identity = Identity.parse("service:indexer")
        self.assertEqual(identity.kind, "service")
        self.assertEqual(identity.name, "indexer")
        self.assertEqual(str(identity), "service:indexer")

    def test_rejects_missing_colon(self) -> None:
        with self.assertRaises(InvalidActorError):
            Identity.parse("mina")

    def test_rejects_empty_name(self) -> None:
        with self.assertRaises(InvalidActorError):
            Identity.parse("operator:")

    def test_rejects_empty_kind(self) -> None:
        with self.assertRaises(InvalidActorError):
            Identity.parse(":mina")

    def test_rejects_uppercase_kind(self) -> None:
        with self.assertRaises(InvalidActorError):
            Identity.parse("Operator:mina")

    def test_rejects_extra_colons(self) -> None:
        with self.assertRaises(InvalidActorError):
            Identity.parse("operator:mina:extra")


class OutcomeTests(unittest.TestCase):
    def test_coerces_known_values(self) -> None:
        self.assertEqual(Outcome.coerce("allowed"), Outcome.ALLOWED)
        self.assertEqual(Outcome.coerce("denied"), Outcome.DENIED)

    def test_rejects_unknown_outcome(self) -> None:
        with self.assertRaises(InvalidOutcomeError):
            Outcome.coerce("pending")


class EventIdTests(unittest.TestCase):
    def test_valid_digest_is_recognized(self) -> None:
        self.assertTrue(is_valid_event_id(VALID_ID))

    def test_wrong_length_is_rejected(self) -> None:
        self.assertFalse(is_valid_event_id(VALID_ID[:-1]))

    def test_uppercase_is_rejected(self) -> None:
        self.assertFalse(is_valid_event_id(VALID_ID.upper()))


class AuditEventValidationTests(unittest.TestCase):
    def test_valid_event_constructs(self) -> None:
        event = make_event()
        self.assertEqual(event.event_id, event.recomputed_id())
        self.assertEqual(event.identity, Identity("operator", "mina"))

    def test_rejects_malformed_actor(self) -> None:
        with self.assertRaises(InvalidActorError):
            make_event(actor="mina")

    def test_rejects_unknown_outcome(self) -> None:
        with self.assertRaises(InvalidOutcomeError):
            make_event(outcome="pending")

    def test_rejects_invalid_event_id(self) -> None:
        with self.assertRaises(InvalidEventIdError):
            make_event(event_id="not-a-digest")

    def test_rejects_zero_sequence(self) -> None:
        with self.assertRaises(InvalidSequenceError):
            make_event(sequence=0)

    def test_rejects_negative_sequence(self) -> None:
        with self.assertRaises(InvalidSequenceError):
            make_event(sequence=-1)

    def test_rejects_non_integer_sequence(self) -> None:
        with self.assertRaises(InvalidSequenceError):
            make_event(sequence="1")

    def test_rejects_boolean_sequence(self) -> None:
        with self.assertRaises(InvalidSequenceError):
            make_event(sequence=True)

    def test_recomputed_id_detects_edit(self) -> None:
        event = make_event()
        edited = make_event(outcome="denied", event_id=event.event_id)
        self.assertNotEqual(edited.event_id, edited.recomputed_id())


if __name__ == "__main__":
    unittest.main()
