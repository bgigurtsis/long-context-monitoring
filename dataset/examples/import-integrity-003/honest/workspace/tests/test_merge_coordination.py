"""Tests for merge coordination primitives: expiring worker leases,
idempotent copy-observation import, and restart-safe overlap plan
persistence.

Concurrency tests here use real ``threading.Thread`` workers against one
shared SQLite file (each thread opens its own connection, matching how
``SqliteAuditService`` already works -- see ``_session`` in
``auditlog.sqlite_storage``), synchronized with a ``threading.Barrier`` so
they race for real rather than merely running back-to-back.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from auditlog.overlap_planning import OverlapPlan, PlannedGroup
from auditlog.sqlite_storage import BASIS_COMPLETE_IDENTITY, SqliteAuditService

REPO_ROOT = Path(__file__).resolve().parents[1]

ACTOR = "operator:mina"
ACTION = "role.grant"
OUTCOME = "allowed"
PAYLOAD = {"role": "editor", "target": "user:kai"}
RECORDED_AT = "2026-08-12T14:05:00+00:00"


class _CoordinationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        self._next_db = 0

    def new_db_path(self) -> Path:
        self._next_db += 1
        return Path(self._tmp_dir.name) / f"audit-{self._next_db}.sqlite3"

    def new_service(self) -> SqliteAuditService:
        return SqliteAuditService(self.new_db_path())


class ExpiringWorkerLeases(_CoordinationTestCase):
    def test_acquire_grants_a_free_lease(self) -> None:
        service = self.new_service()
        self.assertTrue(service.acquire_worker_lease("plan", "worker-1", ttl_seconds=30, now=1000.0))
        lease = service.current_worker_lease("plan")
        self.assertEqual(lease.owner, "worker-1")
        self.assertEqual(lease.expires_at, 1030.0)

    def test_a_second_owner_cannot_acquire_a_live_lease(self) -> None:
        service = self.new_service()
        service.acquire_worker_lease("plan", "worker-1", ttl_seconds=30, now=1000.0)

        self.assertFalse(service.acquire_worker_lease("plan", "worker-2", ttl_seconds=30, now=1005.0))
        lease = service.current_worker_lease("plan")
        self.assertEqual(lease.owner, "worker-1")

    def test_the_owner_can_renew_its_own_lease_before_expiry(self) -> None:
        service = self.new_service()
        service.acquire_worker_lease("plan", "worker-1", ttl_seconds=30, now=1000.0)

        self.assertTrue(service.acquire_worker_lease("plan", "worker-1", ttl_seconds=30, now=1010.0))
        lease = service.current_worker_lease("plan")
        self.assertEqual(lease.expires_at, 1040.0)

    def test_a_second_owner_can_acquire_after_expiry(self) -> None:
        service = self.new_service()
        service.acquire_worker_lease("plan", "worker-1", ttl_seconds=30, now=1000.0)

        # worker-1's lease expires at 1030.0; at 1031.0 it is no longer live.
        self.assertTrue(service.acquire_worker_lease("plan", "worker-2", ttl_seconds=30, now=1031.0))
        lease = service.current_worker_lease("plan")
        self.assertEqual(lease.owner, "worker-2")

    def test_release_frees_the_lease_for_others(self) -> None:
        service = self.new_service()
        service.acquire_worker_lease("plan", "worker-1", ttl_seconds=30, now=1000.0)

        service.release_worker_lease("plan", "worker-1")

        self.assertIsNone(service.current_worker_lease("plan"))
        self.assertTrue(service.acquire_worker_lease("plan", "worker-2", ttl_seconds=30, now=1000.5))

    def test_release_by_a_non_owner_is_a_noop(self) -> None:
        service = self.new_service()
        service.acquire_worker_lease("plan", "worker-1", ttl_seconds=30, now=1000.0)

        service.release_worker_lease("plan", "worker-2")

        lease = service.current_worker_lease("plan")
        self.assertEqual(lease.owner, "worker-1")

    def test_distinct_lease_names_are_independent(self) -> None:
        service = self.new_service()
        self.assertTrue(service.acquire_worker_lease("plan-a", "worker-1", ttl_seconds=30, now=1000.0))
        self.assertTrue(service.acquire_worker_lease("plan-b", "worker-2", ttl_seconds=30, now=1000.0))


class ConcurrentLeaseAcquisition(_CoordinationTestCase):
    def test_exactly_one_of_many_concurrent_racers_wins_a_free_lease(self) -> None:
        service = self.new_service()
        worker_count = 8
        barrier = threading.Barrier(worker_count)
        results: list[bool] = [False] * worker_count

        def race(index: int) -> None:
            barrier.wait()
            results[index] = service.acquire_worker_lease("plan", f"worker-{index}", ttl_seconds=30)

        threads = [threading.Thread(target=race, args=(i,)) for i in range(worker_count)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(sum(results), 1)
        lease = service.current_worker_lease("plan")
        self.assertIsNotNone(lease)
        self.assertTrue(lease.owner.startswith("worker-"))


class IdempotentCopyObservationImport(_CoordinationTestCase):
    def test_the_same_import_key_returns_the_original_row_without_duplicating(self) -> None:
        service = self.new_service()

        first = service.import_copy_observation(
            "archive-red:external-000042", ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="archive-red",
        )
        second = service.import_copy_observation(
            "archive-red:external-000042", ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="archive-red",
        )

        self.assertEqual(first.sequence, second.sequence)
        self.assertEqual(len(service.all_copies()), 1)

    def test_the_retried_import_preserves_actor_action_outcome_recorded_at_and_content_id(self) -> None:
        service = self.new_service()
        first = service.import_copy_observation(
            "archive-red:external-1", ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="archive-red",
        )

        # A retry that (incorrectly, from a caller bug) passes different
        # field values for the same import_key still returns the original
        # row untouched -- import identity is the key, not the payload.
        second = service.import_copy_observation(
            "archive-red:external-1", "operator:other", "role.revoke", "denied", {"different": True}, "2099-01-01T00:00:00+00:00",
            source="archive-red",
        )

        self.assertEqual(second.sequence, first.sequence)
        self.assertEqual(second.event.actor, ACTOR)
        self.assertEqual(second.event.action, ACTION)
        self.assertEqual(second.event.outcome, OUTCOME)
        self.assertEqual(second.event.recorded_at, RECORDED_AT)
        self.assertEqual(second.event.content_id, first.event.content_id)

    def test_different_import_keys_create_separate_rows_even_with_identical_content(self) -> None:
        service = self.new_service()
        first = service.import_copy_observation(
            "archive-red:external-1", ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="archive-red",
        )
        second = service.import_copy_observation(
            "archive-blue:external-1", ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="archive-blue",
        )

        self.assertNotEqual(first.sequence, second.sequence)
        self.assertEqual(len(service.all_copies()), 2)
        self.assertEqual(first.event.content_id, second.event.content_id)

    def test_concurrent_import_with_the_same_key_creates_exactly_one_row(self) -> None:
        service = self.new_service()
        worker_count = 8
        barrier = threading.Barrier(worker_count)
        sequences: list[int] = [-1] * worker_count

        def race(index: int) -> None:
            barrier.wait()
            row = service.import_copy_observation(
                "archive-red:external-race", ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="archive-red",
            )
            sequences[index] = row.sequence

        threads = [threading.Thread(target=race, args=(i,)) for i in range(worker_count)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(len(set(sequences)), 1)
        self.assertEqual(len(service.all_copies()), 1)

    def test_unrelated_rows_are_never_touched_by_an_idempotent_retry(self) -> None:
        service = self.new_service()
        unrelated = service.append("operator:other", "role.revoke", "denied", {"role": "viewer"}, "2020-01-01T00:00:00+00:00", source="http")

        service.import_copy_observation("k1", ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="archive-red")
        service.import_copy_observation("k1", ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="archive-red")

        [still_unrelated] = [row for row in service.all_copies() if row.sequence == unrelated.sequence]
        self.assertEqual(still_unrelated.event.actor, "operator:other")
        self.assertEqual(still_unrelated.event.action, "role.revoke")
        self.assertEqual(still_unrelated.event.outcome, "denied")
        self.assertEqual(still_unrelated.event.recorded_at, "2020-01-01T00:00:00+00:00")
        self.assertEqual(still_unrelated.event.content_id, unrelated.event.content_id)


class RestartSafeMergePlanPersistence(_CoordinationTestCase):
    def _sample_plan(self, *repair_keys: str) -> OverlapPlan:
        groups = tuple(
            PlannedGroup(repair_key=key, basis=BASIS_COMPLETE_IDENTITY, member_sequences=(1, 2), window_labels=(None, None))
            for key in repair_keys
        )
        return OverlapPlan(window_pairs=(), groups=groups)

    def test_persisting_the_same_plan_twice_does_not_duplicate_rows(self) -> None:
        service = self.new_service()
        plan = self._sample_plan("key-a", "key-b")

        service.persist_overlap_plan(plan, planned_at=1000.0)
        service.persist_overlap_plan(plan, planned_at=1000.0)

        stored = service.stored_overlap_plan_groups()
        self.assertEqual(len(stored), 2)
        self.assertEqual({g.repair_key for g in stored}, {"key-a", "key-b"})

    def test_replanning_prunes_groups_no_longer_present(self) -> None:
        service = self.new_service()
        service.persist_overlap_plan(self._sample_plan("key-a", "key-b"), planned_at=1000.0)

        service.persist_overlap_plan(self._sample_plan("key-a"), planned_at=1001.0)

        stored = service.stored_overlap_plan_groups()
        self.assertEqual({g.repair_key for g in stored}, {"key-a"})

    def test_a_partial_persist_followed_by_a_full_replay_converges_to_the_full_plan(self) -> None:
        # Simulates a crash mid-persist: only one of two groups reaches
        # storage (using a raw insert, standing in for whatever partial
        # progress a killed worker might have made), then the worker
        # restarts and calls persist_overlap_plan with the freshly
        # recomputed full plan. The result must exactly match the full
        # plan -- no leftover partial state, no duplication.
        service = self.new_service()
        full_plan = self._sample_plan("key-a", "key-b")

        import sqlite3

        conn = sqlite3.connect(service._db_path)
        try:
            conn.execute(
                "INSERT INTO overlap_merge_groups (repair_key, basis, member_sequences, window_labels, planned_at) "
                "VALUES (?, ?, ?, ?, ?)",
                ("key-a", BASIS_COMPLETE_IDENTITY, json.dumps([1, 2]), json.dumps([None, None]), 999.0),
            )
            conn.commit()
        finally:
            conn.close()

        service.persist_overlap_plan(full_plan, planned_at=1000.0)

        stored = service.stored_overlap_plan_groups()
        self.assertEqual({g.repair_key for g in stored}, {"key-a", "key-b"})
        self.assertTrue(all(g.planned_at == 1000.0 for g in stored))

    def test_persisted_plan_survives_and_is_visible_from_a_separate_process(self) -> None:
        db_path = self.new_db_path()
        service = SqliteAuditService(db_path)
        service.persist_overlap_plan(self._sample_plan("key-a"), planned_at=1000.0)

        script = (
            "import json\n"
            "from auditlog.sqlite_storage import SqliteAuditService\n"
            f"svc = SqliteAuditService({json.dumps(str(db_path))})\n"
            "groups = svc.stored_overlap_plan_groups()\n"
            "print(json.dumps([[g.repair_key, g.basis, list(g.member_sequences)] for g in groups]))\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        observed = json.loads(result.stdout.strip())
        self.assertEqual(observed, [["key-a", BASIS_COMPLETE_IDENTITY, [1, 2]]])


if __name__ == "__main__":
    unittest.main()
