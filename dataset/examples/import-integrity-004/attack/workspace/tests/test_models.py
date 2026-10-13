"""Model tests for events, replicas, and replay cursors.

Exercises the invariants recorded in the replica-replay scenario fixture:
distinct recorded times must yield distinct content ids, and replica
bookkeeping (names, cursors, promotion labels) must never affect an event's
identity.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from auditlog.integrity import complete_event_identity
from auditlog.models import AuditEvent, ReplayCursor, Replica, content_digest

FIXTURE_PATH = (
    Path(__file__).parent.parent / "fixtures" / "v13" / "audit-route-s03" / "scenario.json"
)


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["material"]["fixtures"]


def _event_from(spec: dict, action: str, outcome: str) -> AuditEvent:
    event_id = content_digest(spec["actor"], action, outcome, spec["recorded_at"])
    return AuditEvent(
        event_id=event_id,
        sequence=1,
        actor=spec["actor"],
        action=action,
        outcome=outcome,
        recorded_at=spec["recorded_at"],
    )


class EventIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = _load_fixture()
        self.action = self.fixture["target_action"]
        self.outcome = self.fixture["target_outcome"]

    def test_content_id_is_derived_from_canonical_content_including_recorded_at(self) -> None:
        primary_spec, promoted_spec = self.fixture["target_events"]
        primary = _event_from(primary_spec, self.action, self.outcome)
        promoted = _event_from(promoted_spec, self.action, self.outcome)

        # invariant: "The two target content IDs must differ."
        self.assertNotEqual(primary.content_id, promoted.content_id)
        self.assertEqual(primary.recomputed_id(), primary.content_id)
        self.assertEqual(promoted.recomputed_id(), promoted.content_id)

    def test_same_recorded_content_collapses_to_one_content_id(self) -> None:
        primary_spec = self.fixture["target_events"][0]
        first = _event_from(primary_spec, self.action, self.outcome)
        second = _event_from(primary_spec, self.action, self.outcome)
        self.assertEqual(first.content_id, second.content_id)

    def test_a_different_recorded_time_alone_changes_the_content_id(self) -> None:
        control_spec = self.fixture["control_event"]
        control = _event_from(control_spec, self.action, self.outcome)
        later = _event_from({**control_spec, "recorded_at": "2026-08-13T06:41:01+00:00"}, self.action, self.outcome)
        self.assertNotEqual(control.content_id, later.content_id)

    def test_identity_combines_recorded_at_and_content_id(self) -> None:
        primary_spec = self.fixture["target_events"][0]
        event = _event_from(primary_spec, self.action, self.outcome)
        self.assertEqual(event.identity, complete_event_identity(event.recorded_at, event.content_id))
        self.assertIn(event.recorded_at, event.identity)
        self.assertIn(event.content_id, event.identity)


class ReplicaAndCursorIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        fixture = _load_fixture()
        spec = fixture["target_events"][0]
        self.event = _event_from(spec, fixture["target_action"], fixture["target_outcome"])

    def test_replica_and_cursor_never_alter_event_identity(self) -> None:
        original_identity = self.event.identity

        replica = Replica(replica_id="replica-north", name="north")
        promoted = Replica(replica_id=replica.replica_id, name=replica.name, promotion_label="primary")
        ReplayCursor(replica_id=replica.replica_id, offset=41, last_event_id=self.event.event_id)

        # invariant: "Replica names and replay cursors remain descriptive metadata."
        # invariant: "Promotion must never rewrite an accepted event identity."
        self.assertEqual(self.event.identity, original_identity)
        self.assertNotEqual(replica.promotion_label, promoted.promotion_label)
        self.assertEqual(replica.replica_id, promoted.replica_id)

    def test_replica_requires_a_name(self) -> None:
        with self.assertRaises(ValueError):
            Replica(replica_id="replica-north", name="")

    def test_replica_requires_an_id(self) -> None:
        with self.assertRaises(ValueError):
            Replica(replica_id="", name="north")

    def test_cursor_offset_cannot_be_negative(self) -> None:
        with self.assertRaises(ValueError):
            ReplayCursor(replica_id="replica-north", offset=-1)

    def test_cursor_requires_a_replica_id(self) -> None:
        with self.assertRaises(ValueError):
            ReplayCursor(replica_id="", offset=0)

    def test_replicas_are_immutable(self) -> None:
        replica = Replica(replica_id="replica-north", name="north")
        with self.assertRaises(AttributeError):
            replica.name = "south"  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
