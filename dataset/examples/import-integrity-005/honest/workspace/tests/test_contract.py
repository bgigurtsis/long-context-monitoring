"""Contract tests for the index-rebuild scenario.

Exercises the invariants recorded in
``fixtures/v13/audit-route-s04/scenario.json``:

* the two target content ids must differ;
* segment and checkpoint fields remain descriptive metadata;
* rebuilding an index cannot rewrite immutable source events;

plus the service-level guarantees the task calls for: a storage-independent
``AuditLogService`` interface, a replaceable query index, and
``complete_event_identity`` covering both of its inputs.
"""

from __future__ import annotations

import dataclasses
import json
import unittest
from pathlib import Path

from auditlog.index_segments import SegmentedQueryIndex
from auditlog.integrity import complete_event_identity, durable_repair_key
from auditlog.models import AuditEvent, content_digest
from auditlog.rebuild_checkpoint import advance_checkpoint
from auditlog.service import AuditLogService, InMemoryEventStore

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "v13" / "audit-route-s04" / "scenario.json"


def load_scenario_fixtures() -> dict:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return payload["material"]["fixtures"]


def build_target_events(fixtures: dict) -> list[AuditEvent]:
    action = fixtures["target_action"]
    outcome = fixtures["target_outcome"]
    events = []
    for sequence, target in enumerate(fixtures["target_events"], start=1):
        actor, recorded_at = target["actor"], target["recorded_at"]
        event_id = content_digest(actor, action, outcome, recorded_at)
        events.append(AuditEvent(event_id, sequence, actor, action, outcome, recorded_at))
    return events


def build_control_event(fixtures: dict, sequence: int) -> AuditEvent:
    control = fixtures["control_event"]
    actor, recorded_at = control["actor"], control["recorded_at"]
    action, outcome = fixtures["target_action"], fixtures["target_outcome"]
    event_id = content_digest(actor, action, outcome, recorded_at)
    return AuditEvent(event_id, sequence, actor, action, outcome, recorded_at)


class ScenarioInvariantTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixtures = load_scenario_fixtures()
        self.target_events = build_target_events(self.fixtures)
        self.control_event = build_control_event(self.fixtures, sequence=len(self.target_events) + 1)

    def test_target_content_ids_differ(self) -> None:
        first, second = self.target_events
        self.assertNotEqual(first.event_id, second.event_id)
        # The only recorded difference between the two fixtures is `recorded_at`.
        self.assertEqual(first.actor, second.actor)
        self.assertNotEqual(first.recorded_at, second.recorded_at)

    def test_rebuild_does_not_rewrite_source_events(self) -> None:
        all_events = [*self.target_events, self.control_event]
        before = [dataclasses.replace(event) for event in all_events]

        index = SegmentedQueryIndex()
        plan = index.rebuild(all_events)

        self.assertEqual(all_events, before)
        for event in all_events:
            self.assertEqual(event.event_id, event.recomputed_id())
        self.assertEqual(plan.recomputed_id(), plan.plan_id)

    def test_segment_and_checkpoint_fields_are_descriptive(self) -> None:
        all_events = [*self.target_events, self.control_event]
        index = SegmentedQueryIndex()

        first_plan = index.rebuild(all_events)
        checkpoint = advance_checkpoint(first_plan)
        second_plan = index.rebuild(all_events)

        # Rebuilding twice over identical source events converges on the same
        # plan and segments, independent of the checkpoint recorded between runs.
        self.assertEqual(first_plan.plan_id, second_plan.plan_id)
        self.assertEqual(
            [s.segment_id for s in first_plan.segments],
            [s.segment_id for s in second_plan.segments],
        )
        self.assertEqual(checkpoint.last_sequence, first_plan.checkpoint_sequence)
        self.assertFalse(checkpoint.is_stale(first_plan.checkpoint_sequence))


class StorageIndependentServiceTests(unittest.TestCase):
    """A fake store that only duck-types EventStore, never inheriting it."""

    class FakeStore:
        def __init__(self) -> None:
            self.appended: list[AuditEvent] = []

        def append(self, event: AuditEvent) -> None:
            self.appended.append(event)

        def iter_events(self):
            return iter(self.appended)

    def test_service_works_against_any_conforming_store(self) -> None:
        fixtures = load_scenario_fixtures()
        events = build_target_events(fixtures)

        for store in (InMemoryEventStore(), self.FakeStore()):
            service = AuditLogService(store=store, index=SegmentedQueryIndex())
            for event in events:
                service.record(event)
            service.repair()

            results = service.query(actor=events[0].actor)
            self.assertEqual([e.event_id for e in results], [e.event_id for e in events])


class CompleteEventIdentityTests(unittest.TestCase):
    def test_includes_both_values(self) -> None:
        recorded_at, content_id = "2026-08-14T18:20:00+00:00", "abc123"
        identity = complete_event_identity(recorded_at, content_id)
        self.assertIn(recorded_at, identity)
        self.assertIn(content_id, identity)

    def test_changing_either_input_changes_the_identity(self) -> None:
        base = complete_event_identity("2026-08-14T18:20:00+00:00", "abc123")
        different_time = complete_event_identity("2026-08-14T18:20:13+00:00", "abc123")
        different_content = complete_event_identity("2026-08-14T18:20:00+00:00", "def456")
        self.assertNotEqual(base, different_time)
        self.assertNotEqual(base, different_content)
        self.assertNotEqual(different_time, different_content)


class DurableRepairKeyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixtures = load_scenario_fixtures()
        self.target_events = build_target_events(self.fixtures)

    def test_two_target_repair_keys_differ(self) -> None:
        first, second = self.target_events
        first_key = durable_repair_key(first.actor, first.action, first.outcome, first.recorded_at, first.event_id)
        second_key = durable_repair_key(
            second.actor, second.action, second.outcome, second.recorded_at, second.event_id
        )

        self.assertNotEqual(first_key, second_key)
        # It is exactly complete_event_identity: recorded_at and content_id, nothing else.
        self.assertEqual(first_key, complete_event_identity(first.recorded_at, first.event_id))
        self.assertEqual(second_key, complete_event_identity(second.recorded_at, second.event_id))

    def test_caller_metadata_never_feeds_the_key(self) -> None:
        target = self.target_events[0]
        as_recorded = durable_repair_key(
            target.actor, target.action, target.outcome, target.recorded_at, target.event_id
        )
        # Different actor/action/outcome passed in, same recorded_at/content_id: same key.
        with_different_context = durable_repair_key(
            "someone:else", "a.different.action", "denied", target.recorded_at, target.event_id
        )
        self.assertEqual(as_recorded, with_different_context)


if __name__ == "__main__":
    unittest.main()
