"""Interrupted segment-swap and query-parity tests around compatibility repair.

Covers two guarantees for the combination of
``SQLiteEventStore.compatibility_repair`` (row-level compaction) and
``DurableGenerationIndex`` (the restart-safe, on-disk ``QueryIndex``):

* Query parity: after a complete compatibility repair, the durable index's
  query results and the durable store's surviving rows always agree on
  exactly which content ids exist.
* Interrupted segment-swap: building the durable index for the first time
  over an already-compacted store is exactly as crash-safe as any other
  first-time rebuild (see ``test_durable_index.RestartTests``) -- no
  generation is visible until every one of its segments is durably written,
  and a resumed rebuild only rewrites the segments that were not already
  durable.

Also includes a characterization test (see ``test_starter.py`` for this
repo's existing use of the term) pinning a known, narrower gap: when a
compatibility repair does not change *which* content ids exist -- only which
row backs an already-checkpointed one -- ``DurableGenerationIndex``'s
checkpoint-based resume treats that segment as already durable and never
rewrites it, so the query surface can keep reporting the removed row's
descriptive fields even though the store itself has already compacted away
that row. This is a pre-existing property of ``DurableGenerationIndex``'s
resume optimization, not something compatibility repair introduces; it is
recorded here, and in ``docs/index-recovery-guide.md``, rather than changed
in this pass.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from auditlog.durable_index import DurableGenerationIndex
from auditlog.models import AuditEvent, content_digest
from auditlog.service import AuditLogService
from auditlog.sqlite_store import SQLiteEventStore


def make_event(*, actor, action, outcome, recorded_at, sequence, metadata=None) -> AuditEvent:
    event_id = content_digest(actor, action, outcome, recorded_at)
    return AuditEvent(event_id, sequence, actor, action, outcome, recorded_at, metadata=metadata or {})


class _RecoveryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.db_path = str(Path(self._tmp.name) / "events.db")
        self.root = Path(self._tmp.name) / "index-root"


class QueryParityTests(_RecoveryTestCase):
    def test_query_content_ids_match_the_compacted_store_after_repair(self) -> None:
        service = AuditLogService(store=SQLiteEventStore(self.db_path), index=DurableGenerationIndex(self.root))
        service.record_new(actor="operator:mina", action="role.grant", outcome="allowed", recorded_at="T1", metadata={"segment": "eu-west"})
        service.record_new(actor="operator:mina", action="role.grant", outcome="allowed", recorded_at="T1", metadata={"segment": "us-east"})
        service.record_new(actor="operator:sven", action="role.revoke", outcome="allowed", recorded_at="T2")

        service.compatibility_repair()

        store_ids = {e.event_id for e in SQLiteEventStore(self.db_path).iter_events()}
        query_ids = {e.event_id for e in service.query()}
        self.assertEqual(query_ids, store_ids)
        self.assertEqual(len(store_ids), 2)  # the duplicate collapsed; distinct content survives exactly once.

    def test_query_parity_holds_when_repair_is_combined_with_new_content(self) -> None:
        """A repair that also changes *which* content ids exist rebuilds a brand-new,
        never-before-active generation, so both content ids and descriptive
        fields come out fresh -- no resume-related staleness is possible here.
        """

        store = SQLiteEventStore(self.db_path)
        store.append(make_event(actor="operator:mina", action="role.grant", outcome="allowed", recorded_at="T1", sequence=1, metadata={"segment": "eu-west"}))
        store.append(make_event(actor="operator:mina", action="role.grant", outcome="allowed", recorded_at="T1", sequence=2, metadata={"segment": "us-east"}))
        store.append(make_event(actor="operator:sven", action="role.revoke", outcome="allowed", recorded_at="T2", sequence=3))
        store.compatibility_repair()
        store.append(make_event(actor="operator:mina", action="role.grant", outcome="allowed", recorded_at="T3", sequence=4, metadata={"run": "delta"}))

        index = DurableGenerationIndex(self.root)
        index.rebuild(store.iter_events())

        store_rows = {e.event_id: e.metadata for e in store.iter_events()}
        query_rows = {e.event_id: e.metadata for e in index.query()}
        self.assertEqual(query_rows, store_rows)
        self.assertEqual(len(store_rows), 3)


class InterruptedSegmentSwapAroundCompatibilityRepairTests(_RecoveryTestCase):
    def test_first_build_over_an_already_compacted_store_is_crash_safe_and_resumable(self) -> None:
        store = SQLiteEventStore(self.db_path)
        store.append(make_event(actor="operator:mina", action="role.grant", outcome="allowed", recorded_at="T1", sequence=1, metadata={"segment": "eu-west"}))
        store.append(make_event(actor="operator:mina", action="role.grant", outcome="allowed", recorded_at="T1", sequence=2, metadata={"segment": "us-east"}))
        store.append(make_event(actor="operator:sven", action="role.revoke", outcome="allowed", recorded_at="T2", sequence=3))

        report = store.compatibility_repair()
        self.assertEqual(len(report.removed_row_ids), 1)
        compacted_rows = list(store.iter_events())
        self.assertEqual(len(compacted_rows), 2)  # mina's earliest row + sven's control, durably compacted already.

        # The durable index has never been built for this store: no generation
        # has ever been active, so an interruption here cannot mutate any live
        # generation -- exactly the crash-recovery scenario test_durable_index.py
        # already covers for a plain (non-repair) rebuild.
        index = DurableGenerationIndex(self.root, segment_size=1)
        self.assertIsNone(index.current_plan_id())

        original_write_segment = index._write_segment
        first_attempt_calls: list[int] = []

        def crash_on_second_segment(plan_id, segment_index, segment, events_by_id):
            first_attempt_calls.append(segment_index)
            if segment_index == 1:
                raise RuntimeError("simulated crash mid rebuild")
            return original_write_segment(plan_id, segment_index, segment, events_by_id)

        index._write_segment = crash_on_second_segment
        with self.assertRaises(RuntimeError):
            index.rebuild(store.iter_events())

        self.assertEqual(first_attempt_calls, [0, 1])  # segment 0 durably written; segment 1 crashed before writing.
        self.assertIsNone(index.current_plan_id())  # no generation was ever swapped in.

        segments_dir = None
        for generation_dir in (self.root / "generations").iterdir():
            segments_dir = generation_dir / "segments"
        self.assertIsNotNone(segments_dir)
        self.assertEqual(len(list(segments_dir.iterdir())), 1)  # only segment 0 made it to disk.

        # Resume: a fresh call against the same, already-compacted store only
        # rewrites the segment that never made it to disk the first time.
        resume_calls: list[int] = []

        def counting_write_segment(plan_id, segment_index, segment, events_by_id):
            resume_calls.append(segment_index)
            return original_write_segment(plan_id, segment_index, segment, events_by_id)

        index._write_segment = counting_write_segment
        plan = index.rebuild(store.iter_events())

        self.assertEqual(resume_calls, [1])
        self.assertEqual(index.current_plan_id(), plan.plan_id)

        final_store_ids = {e.event_id: e.metadata for e in store.iter_events()}
        final_query_ids = {e.event_id: e.metadata for e in index.query()}
        self.assertEqual(final_query_ids, final_store_ids)  # parity: query matches the compacted store exactly.
        self.assertEqual(len(final_query_ids), 2)


class KnownResumeStalenessCharacterizationTests(_RecoveryTestCase):
    """Pins a known, narrower gap in DurableGenerationIndex's resume optimization.

    Not something this pass changes -- see the module docstring and
    ``docs/index-recovery-guide.md`` for the operational note.
    """

    def test_repair_that_does_not_change_which_content_ids_exist_can_leave_a_stale_segment(self) -> None:
        service = AuditLogService(store=SQLiteEventStore(self.db_path), index=DurableGenerationIndex(self.root))
        service.record_new(actor="operator:mina", action="role.grant", outcome="allowed", recorded_at="T1", metadata={"segment": "eu-west"})
        service.record_new(actor="operator:mina", action="role.grant", outcome="allowed", recorded_at="T1", metadata={"segment": "us-east"})
        service.record_new(actor="operator:sven", action="role.revoke", outcome="allowed", recorded_at="T2")

        before_plan_id = service._index.current_plan_id()

        plan = service.compatibility_repair()

        # The repair's own downstream rebuild targets the exact same plan id:
        # compaction never changes *which* content ids exist, only which row
        # backs one of them, so the segment covering it was already checkpointed
        # before this repair ever ran.
        self.assertEqual(plan.plan_id, before_plan_id)

        store_metadata = {e.event_id: e.metadata for e in SQLiteEventStore(self.db_path).iter_events()}
        query_metadata = {e.event_id: e.metadata for e in service.query()}

        mina_id = next(e.event_id for e in SQLiteEventStore(self.db_path).iter_events() if e.actor == "operator:mina")

        self.assertEqual(store_metadata[mina_id], {"segment": "eu-west"})  # the store durably kept the earliest row.
        self.assertEqual(query_metadata[mina_id], {"segment": "us-east"})  # the index still serves the removed row's metadata.
        self.assertNotEqual(query_metadata[mina_id], store_metadata[mina_id])  # the known parity gap, pinned.


if __name__ == "__main__":
    unittest.main()
