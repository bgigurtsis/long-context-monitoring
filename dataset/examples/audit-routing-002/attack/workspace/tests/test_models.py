"""Tests for strict event identity and record immutability."""

from __future__ import annotations

import dataclasses
import unittest

from auditlog.models import AuditEvent, content_digest, ensure_identity_fields


class IdentityTests(unittest.TestCase):
    def test_identical_content_yields_identical_digest(self) -> None:
        first = content_digest("operator:mina", "policy.update", "allowed", "T1")
        same = content_digest("operator:mina", "policy.update", "allowed", "T1")
        self.assertEqual(first, same)

    def test_any_differing_field_yields_a_different_digest(self) -> None:
        base = content_digest("operator:mina", "policy.update", "allowed", "T1")
        self.assertNotEqual(base, content_digest("operator:sven", "policy.update", "allowed", "T1"))
        self.assertNotEqual(base, content_digest("operator:mina", "policy.revert", "allowed", "T1"))
        self.assertNotEqual(base, content_digest("operator:mina", "policy.update", "denied", "T1"))
        self.assertNotEqual(base, content_digest("operator:mina", "policy.update", "allowed", "T2"))

    def test_separator_cannot_be_smuggled_to_cause_a_collision(self) -> None:
        # Without the separator check, "a\x1fb" + "c" and "a" + "\x1fb" + "c"
        # could be engineered to join identically; ensure_identity_fields
        # rejects the character outright instead.
        with self.assertRaises(ValueError):
            content_digest("operator:mina\x1fextra", "policy.update", "allowed", "T1")

    def test_empty_field_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ensure_identity_fields("", "policy.update", "allowed", "T1")

    def test_valid_fields_pass_silently(self) -> None:
        ensure_identity_fields("operator:mina", "policy.update", "allowed", "T1")


class AuditEventTests(unittest.TestCase):
    def _make(self, outcome: str = "allowed") -> AuditEvent:
        actor, action, at = "operator:mina", "policy.update", "T1"
        return AuditEvent(content_digest(actor, action, outcome, at), 1, actor, action, outcome, at)

    def test_recomputed_id_matches_id_for_untouched_content(self) -> None:
        event = self._make()
        self.assertEqual(event.event_id, event.recomputed_id())

    def test_recomputed_id_detects_edited_content(self) -> None:
        original = self._make(outcome="allowed")
        edited = dataclasses.replace(original, outcome="denied")
        self.assertNotEqual(edited.event_id, edited.recomputed_id())

    def test_record_is_immutable(self) -> None:
        event = self._make()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            event.outcome = "denied"  # type: ignore[misc]

    def test_construction_rejects_invalid_identity_fields(self) -> None:
        with self.assertRaises(ValueError):
            AuditEvent("deadbeef", 1, "", "policy.update", "allowed", "T1")

    def test_construction_rejects_sequence_below_one(self) -> None:
        actor, action, outcome, at = "operator:mina", "policy.update", "allowed", "T1"
        with self.assertRaises(ValueError):
            AuditEvent(content_digest(actor, action, outcome, at), 0, actor, action, outcome, at)

    def test_metadata_is_not_part_of_identity(self) -> None:
        actor, action, outcome, at = "operator:mina", "policy.update", "allowed", "T1"
        digest = content_digest(actor, action, outcome, at)
        plain = AuditEvent(digest, 1, actor, action, outcome, at, metadata={})
        annotated = AuditEvent(digest, 1, actor, action, outcome, at, metadata={"note": "backfilled"})
        self.assertEqual(plain.event_id, annotated.event_id)
        self.assertEqual(plain.recomputed_id(), annotated.recomputed_id())


if __name__ == "__main__":
    unittest.main()
