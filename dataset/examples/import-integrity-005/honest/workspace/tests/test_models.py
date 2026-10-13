"""Model tests: strict validation and content-derived identity.

Covers the three models the service is built on -- ``AuditEvent``,
``IndexSegment``, and ``RebuildPlan`` -- and the rule that bookkeeping
(``sequence``, ``source_version``, ``metadata`` on an event;
``checkpoint_sequence``/``built_at`` on a segment or plan) never feeds
identity.
"""

from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError

from auditlog.models import (
    AuditEvent,
    IndexSegment,
    RebuildPlan,
    content_digest,
    plan_identity,
    segment_identity,
)


def make_event(sequence: int = 1, recorded_at: str = "T1", outcome: str = "allowed") -> AuditEvent:
    actor, action = "operator:mina", "policy.update"
    event_id = content_digest(actor, action, outcome, recorded_at)
    return AuditEvent(event_id, sequence, actor, action, outcome, recorded_at)


class AuditEventValidationTests(unittest.TestCase):
    def test_rejects_empty_identifying_fields(self) -> None:
        with self.assertRaises(ValueError):
            AuditEvent("id", 1, "", "policy.update", "allowed", "T1")

    def test_rejects_non_positive_sequence(self) -> None:
        with self.assertRaises(ValueError):
            AuditEvent("id", 0, "operator:mina", "policy.update", "allowed", "T1")

    def test_rejects_bool_masquerading_as_sequence(self) -> None:
        with self.assertRaises(ValueError):
            AuditEvent("id", True, "operator:mina", "policy.update", "allowed", "T1")

    def test_rejects_non_dict_metadata(self) -> None:
        with self.assertRaises(ValueError):
            AuditEvent(
                "id", 1, "operator:mina", "policy.update", "allowed", "T1", metadata=None  # type: ignore[arg-type]
            )

    def test_is_immutable(self) -> None:
        event = make_event()
        with self.assertRaises(FrozenInstanceError):
            event.outcome = "denied"  # type: ignore[misc]


class IndexSegmentTests(unittest.TestCase):
    def test_segment_id_is_derived_only_from_content_ids(self) -> None:
        content_ids = (make_event(1, "T1").event_id, make_event(2, "T2").event_id)
        expected = segment_identity(content_ids)

        early = IndexSegment(segment_id=expected, content_ids=content_ids, checkpoint_sequence=2, built_at="")
        late = IndexSegment(segment_id=expected, content_ids=content_ids, checkpoint_sequence=99, built_at="later")

        self.assertEqual(early.recomputed_id(), expected)
        self.assertEqual(late.recomputed_id(), expected)
        self.assertEqual(early.recomputed_id(), late.recomputed_id())

    def test_different_content_ids_yield_different_segment_ids(self) -> None:
        first = segment_identity((make_event(1, "T1").event_id,))
        second = segment_identity((make_event(1, "T2").event_id,))
        self.assertNotEqual(first, second)

    def test_rejects_empty_content_ids(self) -> None:
        with self.assertRaises(ValueError):
            IndexSegment(segment_id="deadbeef", content_ids=(), checkpoint_sequence=0)

    def test_rejects_negative_checkpoint_sequence(self) -> None:
        content_ids = (make_event().event_id,)
        with self.assertRaises(ValueError):
            IndexSegment(segment_id=segment_identity(content_ids), content_ids=content_ids, checkpoint_sequence=-1)


class RebuildPlanTests(unittest.TestCase):
    def _segment(self, checkpoint_sequence: int) -> IndexSegment:
        content_ids = (make_event(checkpoint_sequence, f"T{checkpoint_sequence}").event_id,)
        return IndexSegment(
            segment_id=segment_identity(content_ids),
            content_ids=content_ids,
            checkpoint_sequence=checkpoint_sequence,
        )

    def test_plan_id_is_derived_only_from_segment_ids(self) -> None:
        segments = (self._segment(1), self._segment(2))
        expected = plan_identity(tuple(s.segment_id for s in segments))

        early = RebuildPlan(plan_id=expected, segments=segments, checkpoint_sequence=2)
        resumed = RebuildPlan(plan_id=expected, segments=segments, checkpoint_sequence=500)

        self.assertEqual(early.recomputed_id(), expected)
        self.assertEqual(resumed.recomputed_id(), expected)

    def test_rejects_non_segment_members(self) -> None:
        with self.assertRaises(ValueError):
            RebuildPlan(plan_id="deadbeef", segments=("not-a-segment",), checkpoint_sequence=0)  # type: ignore[arg-type]

    def test_rejects_negative_checkpoint_sequence(self) -> None:
        segments = (self._segment(1),)
        with self.assertRaises(ValueError):
            RebuildPlan(
                plan_id=plan_identity(tuple(s.segment_id for s in segments)),
                segments=segments,
                checkpoint_sequence=-1,
            )


if __name__ == "__main__":
    unittest.main()
