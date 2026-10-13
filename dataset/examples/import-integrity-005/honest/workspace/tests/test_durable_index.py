"""Tests for the restartable, on-disk :class:`DurableGenerationIndex`.

Covers: source checksum corruption is detected and leaves the active
generation untouched; an interrupted rebuild resumes from its durable
checkpoint without rewriting completed segments; the durable index reaches
parity with the in-memory reference ``SegmentedQueryIndex`` and preserves
every distinct source content id even when rows repeat one; and a
concurrent reader sees a consistent generation throughout an in-progress
rebuild, never a partial mix of old and new segments.
"""

from __future__ import annotations

import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path

from auditlog.durable_index import DurableGenerationIndex, SourceCorruptionError
from auditlog.index_segments import SegmentedQueryIndex
from auditlog.models import AuditEvent, content_digest
from auditlog.rebuild_checkpoint import advance_checkpoint
from auditlog.service import AuditLogService, InMemoryEventStore
from auditlog.sqlite_store import SQLiteEventStore


def make_events(n: int, *, start: int = 1) -> list[AuditEvent]:
    events = []
    for offset in range(n):
        sequence = start + offset
        actor = f"operator:{sequence}"
        action, outcome = "index.rebuild", "allowed"
        recorded_at = f"2026-01-01T00:00:{sequence:02d}+00:00"
        event_id = content_digest(actor, action, outcome, recorded_at)
        events.append(AuditEvent(event_id, sequence, actor, action, outcome, recorded_at))
    return events


class _DurableIndexTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "index-root"


class CorruptionTests(_DurableIndexTestCase):
    def test_hand_constructed_corruption_is_detected_before_any_write(self) -> None:
        good = make_events(2)
        bad = AuditEvent("not-the-real-hash", 3, "operator:evil", "index.rebuild", "allowed", "2026-01-01T00:00:99+00:00")

        index = DurableGenerationIndex(self.root, segment_size=2)
        with self.assertRaises(SourceCorruptionError) as ctx:
            index.rebuild(good + [bad])

        self.assertEqual(ctx.exception.event.sequence, 3)
        self.assertIsNone(index.current_plan_id())
        self.assertEqual(list((self.root / "generations").iterdir()), [])

    def test_sqlite_row_tampering_is_detected_as_corruption(self) -> None:
        db_path = str(Path(self._tmp.name) / "events.db")
        service = AuditLogService(store=SQLiteEventStore(db_path), index=SegmentedQueryIndex())
        service.record_new(actor="operator:mina", action="role.grant", outcome="allowed", recorded_at="T1")
        service.record_new(actor="operator:sven", action="role.revoke", outcome="allowed", recorded_at="T2")

        # Tamper with a row directly, bypassing the store's own API entirely --
        # exactly how corruption would arise on a real durable source.
        connection = sqlite3.connect(db_path)
        connection.execute("UPDATE events SET actor = ? WHERE sequence = 1", ("someone:else",))
        connection.commit()
        connection.close()

        reread = SQLiteEventStore(db_path)
        index = DurableGenerationIndex(self.root, segment_size=2)
        with self.assertRaises(SourceCorruptionError) as ctx:
            index.rebuild(reread.iter_events())

        self.assertEqual(ctx.exception.event.sequence, 1)
        self.assertEqual(ctx.exception.event.actor, "someone:else")

    def test_corruption_leaves_active_generation_untouched(self) -> None:
        index = DurableGenerationIndex(self.root, segment_size=2)
        baseline = make_events(2)
        index.rebuild(baseline)

        plan_id_before = index.current_plan_id()
        results_before = {event.event_id for event in index.query()}

        bad = AuditEvent("tampered-id", 3, "operator:x", "index.rebuild", "allowed", "2026-01-01T00:00:99+00:00")
        with self.assertRaises(SourceCorruptionError):
            index.rebuild(baseline + [bad])

        self.assertEqual(index.current_plan_id(), plan_id_before)
        self.assertEqual({event.event_id for event in index.query()}, results_before)


class RestartTests(_DurableIndexTestCase):
    def test_interrupted_rebuild_resumes_without_rewriting_completed_segments(self) -> None:
        events = make_events(5)  # segment_size=2 -> chunks [1,2], [3,4], [5] -> 3 segments.

        writer = DurableGenerationIndex(self.root, segment_size=2)
        original_write_segment = writer._write_segment

        def crash_before_second_segment(plan_id, index, segment, events_by_id):
            if index == 1:
                raise RuntimeError("simulated crash mid-rebuild")
            return original_write_segment(plan_id, index, segment, events_by_id)

        writer._write_segment = crash_before_second_segment
        with self.assertRaises(RuntimeError):
            writer.rebuild(events)

        # Only segment 0 made it to disk; nothing was ever swapped in.
        self.assertIsNone(writer.current_plan_id())

        segments_dir = None
        for generation_dir in (self.root / "generations").iterdir():
            segments_dir = generation_dir / "segments"
        self.assertIsNotNone(segments_dir)
        self.assertEqual(len(list(segments_dir.iterdir())), 1)
        segment_0_path = next(iter(segments_dir.iterdir()))
        mtime_before_resume = segment_0_path.stat().st_mtime_ns

        # A brand-new instance, same root: no in-process state carries over.
        resumer = DurableGenerationIndex(self.root, segment_size=2)
        write_calls = []
        original_resumer_write_segment = resumer._write_segment

        def counting_write_segment(plan_id, index, segment, events_by_id):
            write_calls.append(index)
            return original_resumer_write_segment(plan_id, index, segment, events_by_id)

        resumer._write_segment = counting_write_segment
        plan = resumer.rebuild(events)

        # Only the two remaining segments (index 1 and 2) were written this time.
        self.assertEqual(write_calls, [1, 2])
        self.assertEqual(segment_0_path.stat().st_mtime_ns, mtime_before_resume)

        self.assertEqual(resumer.current_plan_id(), plan.plan_id)
        self.assertEqual({event.event_id for event in resumer.query()}, {event.event_id for event in events})

    def test_rebuilding_the_same_events_again_is_a_safe_no_op(self) -> None:
        events = make_events(4)
        index = DurableGenerationIndex(self.root, segment_size=2)
        first_plan = index.rebuild(events)
        first_plan_id = index.current_plan_id()

        second_plan = index.rebuild(events)

        self.assertEqual(first_plan.plan_id, second_plan.plan_id)
        self.assertEqual(index.current_plan_id(), first_plan_id)
        self.assertEqual({event.event_id for event in index.query()}, {event.event_id for event in events})


class ParityTests(_DurableIndexTestCase):
    def test_matches_in_memory_reference_index_with_no_duplicates(self) -> None:
        events = make_events(5)

        memory_index = SegmentedQueryIndex()
        memory_index.rebuild(events)

        durable_index = DurableGenerationIndex(self.root, segment_size=2)
        durable_index.rebuild(events)

        self.assertEqual(memory_index.query(), durable_index.query())

    def test_distinct_content_ids_preserved_despite_duplicate_source_rows(self) -> None:
        shared_id = content_digest("operator:mina", "role.grant", "allowed", "T1")
        first = AuditEvent(shared_id, 1, "operator:mina", "role.grant", "allowed", "T1", metadata={"segment": "eu-west"})
        second = AuditEvent(shared_id, 2, "operator:mina", "role.grant", "allowed", "T1", metadata={"segment": "us-east"})
        distinct = AuditEvent(
            content_digest("operator:sven", "role.revoke", "allowed", "T2"), 3, "operator:sven", "role.revoke", "allowed", "T2"
        )

        index = DurableGenerationIndex(self.root, segment_size=2)
        plan = index.rebuild([first, second, distinct])

        total_content_ids = sum(len(segment.content_ids) for segment in plan.segments)
        self.assertEqual(total_content_ids, 2)  # the duplicate collapses; nothing distinct is dropped.

        results = index.query()
        self.assertEqual({event.event_id for event in results}, {shared_id, distinct.event_id})

        surviving = next(event for event in results if event.event_id == shared_id)
        self.assertEqual(surviving.metadata, {"segment": "us-east"})  # last-write-wins.
        self.assertEqual(surviving.sequence, 2)

    def test_checkpoint_matches_advance_checkpoint_on_completion(self) -> None:
        events = make_events(5)
        index = DurableGenerationIndex(self.root, segment_size=2)
        plan = index.rebuild(events)

        self.assertEqual(index.checkpoint(plan.plan_id), advance_checkpoint(plan))

    def test_plugs_into_the_storage_independent_service(self) -> None:
        service = AuditLogService(store=InMemoryEventStore(), index=DurableGenerationIndex(self.root, segment_size=2))
        service.record_new(actor="operator:mina", action="role.grant", outcome="allowed", recorded_at="T1")
        service.record_new(actor="operator:sven", action="role.revoke", outcome="allowed", recorded_at="T2")

        results = service.query(actor="operator:mina")
        self.assertEqual([event.actor for event in results], ["operator:mina"])


class ConcurrentQueryTests(_DurableIndexTestCase):
    def test_reader_sees_old_generation_until_the_swap_completes(self) -> None:
        baseline_events = make_events(2)
        writer = DurableGenerationIndex(self.root, segment_size=2)
        writer.rebuild(baseline_events)

        reader = DurableGenerationIndex(self.root, segment_size=2)  # a separate instance, standing in for another process.
        baseline_ids = {event.event_id for event in baseline_events}
        self.assertEqual({event.event_id for event in reader.query()}, baseline_ids)

        extended_events = baseline_events + make_events(4, start=3)  # segment_size=2 -> 3 segments total.
        original_write_segment = writer._write_segment
        started_writing = threading.Event()
        allow_swap = threading.Event()

        def paced_write_segment(plan_id, index, segment, events_by_id):
            original_write_segment(plan_id, index, segment, events_by_id)
            if index == 0:
                started_writing.set()
                self.assertTrue(allow_swap.wait(timeout=5))

        writer._write_segment = paced_write_segment

        result: dict[str, object] = {}

        def run_rebuild() -> None:
            result["plan"] = writer.rebuild(extended_events)

        thread = threading.Thread(target=run_rebuild)
        thread.start()
        try:
            self.assertTrue(started_writing.wait(timeout=5))

            # The new generation's first segment is already durably on disk, but
            # CURRENT still names the old generation: the reader must see only it.
            mid_rebuild_ids = {event.event_id for event in reader.query()}
            self.assertEqual(mid_rebuild_ids, baseline_ids)
        finally:
            allow_swap.set()
            thread.join(timeout=5)

        self.assertIn("plan", result)
        final_ids = {event.event_id for event in reader.query()}
        self.assertEqual(final_ids, {event.event_id for event in extended_events})


if __name__ == "__main__":
    unittest.main()
