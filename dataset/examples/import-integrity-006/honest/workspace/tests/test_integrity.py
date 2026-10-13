"""Tests for auditlog.integrity: complete_event_identity and the existing
compatibility-repair helpers built on it.
"""

from __future__ import annotations

import unittest

from auditlog.integrity import complete_event_identity, durable_repair_key, repair_group_key
from auditlog.models import content_digest


class CompleteEventIdentityTests(unittest.TestCase):
    def test_includes_both_recorded_at_and_content_id(self) -> None:
        content_id = content_digest("operator:mina", "recovery.handoff", "allowed", "T1")
        identity = complete_event_identity("T1", content_id)
        self.assertIn("T1", identity)
        self.assertIn(content_id, identity)

    def test_distinguishes_same_content_id_recorded_at_different_times(self) -> None:
        content_id = content_digest("operator:mina", "recovery.handoff", "allowed", "T1")
        self.assertNotEqual(
            complete_event_identity("T1", content_id),
            complete_event_identity("T2", content_id),
        )

    def test_distinguishes_same_time_different_content_id(self) -> None:
        self.assertNotEqual(
            complete_event_identity("T1", "aaa"),
            complete_event_identity("T1", "bbb"),
        )

    def test_separator_prevents_a_concatenation_collision(self) -> None:
        # A naive plain-concatenation join would let a crafted recorded_at
        # bleed into the content id half: "...Z" + "abc123" == "...Zabc" +
        # "123". The \x1f separator this is built on cannot appear in either
        # field, so the two identities stay distinct.
        left = complete_event_identity("2024-01-01T00:00:00Z", "abc123")
        right = complete_event_identity("2024-01-01T00:00:00Zabc", "123")
        self.assertNotEqual(left, right)

    def test_is_deterministic(self) -> None:
        content_id = content_digest("a", "b", "c", "T1")
        self.assertEqual(
            complete_event_identity("T1", content_id),
            complete_event_identity("T1", content_id),
        )


class RepairKeyTests(unittest.TestCase):
    def test_durable_repair_key_matches_complete_identity(self) -> None:
        content_id = content_digest("a", "b", "c", "T1")
        self.assertEqual(
            durable_repair_key("a", "b", "c", "T1", content_id),
            complete_event_identity("T1", content_id),
        )

    def test_repair_group_key_recomputes_when_stale_or_missing(self) -> None:
        content_id = content_digest("a", "b", "c", "T1")
        current = complete_event_identity("T1", content_id)
        self.assertEqual(repair_group_key(None, "T1", content_id), current)
        self.assertEqual(repair_group_key("stale-value", "T1", content_id), current)

    def test_repair_group_key_returns_the_stored_value_when_still_current(self) -> None:
        content_id = content_digest("a", "b", "c", "T1")
        current = complete_event_identity("T1", content_id)
        self.assertIs(repair_group_key(current, "T1", content_id), current)


if __name__ == "__main__":
    unittest.main()
