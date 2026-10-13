"""Crash-recovery tests for compatibility repair: the lease that guards
atomic removal, and what happens to a plan whose worker "crashes" between
candidate validation (planning) and the atomic removal step itself.

Each test simulates a crashed worker by acquiring the compatibility-repair
lease directly -- standing in for a worker that read the store, validated
candidates, and then died before ever calling ``remove_copies`` or
releasing the lease -- and proves three things: a second worker cannot
acquire the lease (and therefore cannot remove anything) while the first
worker's lease is still live; once that lease naturally expires, a second
worker safely resumes and completes exactly the same repair an
uninterrupted run would have produced, for every basis compatibility repair
can ever act on (``complete_identity``, ``verified_http_compatibility``,
and the always-untouched ``verified_lineage``); and the lease is released
again immediately after an ordinary, successful repair, rather than making
the next repair wait out the full TTL.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from auditlog.compatibility_repair import (
    COMPATIBILITY_REPAIR_LEASE_NAME,
    execute_compatibility_repair,
)
from auditlog.integrity import identity_bound_http_receipt
from auditlog.models import ArchiveWindow, Event
from auditlog.overlap_planning import LeaseNotHeldError
from auditlog.sqlite_storage import (
    BASIS_COMPLETE_IDENTITY,
    BASIS_VERIFIED_HTTP_COMPATIBILITY,
    SqliteAuditService,
)

ACTOR = "operator:mina"
ACTION = "role.grant"
OUTCOME = "allowed"
PAYLOAD = {"role": "editor", "target": "user:kai"}
RECORDED_AT = "2026-08-12T14:05:00+00:00"
NEXT_SECOND = "2026-08-12T14:05:01+00:00"


class _CrashRecoveryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp_dir.cleanup)
        self._next_db = 0

    def new_service(self) -> SqliteAuditService:
        self._next_db += 1
        return SqliteAuditService(Path(self._tmp_dir.name) / f"audit-{self._next_db}.sqlite3")

    def genuine_receipt(self, event: Event) -> str:
        return identity_bound_http_receipt(
            event.actor, event.action, event.outcome, event.payload, event.recorded_at, event.content_id,
        )

    def simulate_crashed_worker(self, service: SqliteAuditService, *, now: float) -> None:
        """Stand in for a worker that got as far as validating candidates
        and then died before ever calling remove_copies or releasing the
        lease: acquire the lease and stop there, exactly as a killed
        process would leave it -- no cleanup code runs for a real crash."""

        acquired = service.acquire_worker_lease(COMPATIBILITY_REPAIR_LEASE_NAME, "crashed-worker", ttl_seconds=30, now=now)
        self.assertTrue(acquired)


class InterruptionBetweenCandidateValidationAndRemoval(_CrashRecoveryTestCase):
    def test_a_second_worker_is_locked_out_while_the_crashed_workers_lease_is_still_live(self) -> None:
        service = self.new_service()
        event = Event.record(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT)
        receipt = self.genuine_receipt(event)
        service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=receipt)
        service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=receipt)

        self.simulate_crashed_worker(service, now=1000.0)  # expires at 1030.0

        with self.assertRaises(LeaseNotHeldError):
            execute_compatibility_repair(service, owner="worker-2", ttl_seconds=30, now=1005.0)

        # Nothing was removed: the crashed worker never reached
        # remove_copies, and the second worker never got past the lease.
        self.assertEqual(len(service.all_copies()), 2)

    def test_a_second_worker_resumes_and_completes_the_same_repair_after_the_lease_expires(self) -> None:
        service = self.new_service()
        event = Event.record(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT)
        receipt = self.genuine_receipt(event)
        first = service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=receipt)
        second = service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=receipt)

        self.simulate_crashed_worker(service, now=1000.0)  # expires at 1030.0

        result = execute_compatibility_repair(service, owner="worker-2", ttl_seconds=30, now=1031.0)

        [group] = result.removed_groups
        self.assertEqual(group.basis, BASIS_COMPLETE_IDENTITY)
        self.assertEqual(group.retained_sequence, first.sequence)
        self.assertEqual(group.removed_sequences, (second.sequence,))
        self.assertEqual({row.sequence for row in service.all_copies()}, {first.sequence})

    def test_the_lease_is_released_immediately_after_an_ordinary_successful_repair(self) -> None:
        service = self.new_service()
        event = Event.record(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT)
        receipt = self.genuine_receipt(event)
        service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=receipt)
        service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt=receipt)

        execute_compatibility_repair(service, owner="worker-1", ttl_seconds=30, now=1000.0)

        # Free again well before the TTL would have expired -- ordinary,
        # uninterrupted work releases the lease explicitly rather than
        # making the next repair wait out the full TTL.
        self.assertIsNone(service.current_worker_lease(COMPATIBILITY_REPAIR_LEASE_NAME))
        self.assertTrue(service.acquire_worker_lease(COMPATIBILITY_REPAIR_LEASE_NAME, "worker-2", ttl_seconds=30, now=1000.5))


class ActionableValidatedTransportGroupsSurviveACrash(_CrashRecoveryTestCase):
    def test_a_transport_cohort_is_correctly_removed_after_a_crashed_workers_lease_expires(self) -> None:
        # Substitutes a validator that returns a candidate spanning two
        # distinct complete identities, exactly like
        # tests/test_compatibility_repair.py's InjectedTransportCohortRemoval
        # -- today's real validator's own invariants keep this from
        # occurring on real fixtures, which is a property of those fixtures,
        # not a claim that the branch is unreachable in general.
        service = self.new_service()
        first = service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT, source="http", stored_receipt="whatever-1")
        second = service.append(ACTOR, ACTION, OUTCOME, PAYLOAD, NEXT_SECOND, source="http", stored_receipt="whatever-2")

        def always_shared_candidate(stored_receipt, actor, action, outcome, payload, recorded_at, content_id, source, verified_lineage):
            return "shared-transport-candidate"

        self.simulate_crashed_worker(service, now=1000.0)  # expires at 1030.0

        result = execute_compatibility_repair(
            service, owner="worker-2", ttl_seconds=30, now=1031.0,
            http_compatibility_validator=always_shared_candidate,
        )

        [group] = result.removed_groups
        self.assertEqual(group.basis, BASIS_VERIFIED_HTTP_COMPATIBILITY)
        self.assertEqual(group.retained_sequence, first.sequence)
        self.assertEqual(group.removed_sequences, (second.sequence,))
        self.assertEqual({row.sequence for row in service.all_copies()}, {first.sequence})


class NonRemovableVerifiedLineageGroupsSurviveACrash(_CrashRecoveryTestCase):
    def test_a_lineage_cohort_is_still_never_removed_after_a_crashed_workers_lease_expires(self) -> None:
        service = self.new_service()
        red = service.append(
            ACTOR, ACTION, OUTCOME, PAYLOAD, RECORDED_AT,
            source="archive-red", verified_lineage="case-77", window=ArchiveWindow("red"),
        )
        blue = service.append(
            ACTOR, ACTION, OUTCOME, PAYLOAD, NEXT_SECOND,
            source="archive-blue", verified_lineage="case-77", window=ArchiveWindow("blue"),
        )

        self.simulate_crashed_worker(service, now=1000.0)  # expires at 1030.0

        result = execute_compatibility_repair(service, owner="worker-2", ttl_seconds=30, now=1031.0)

        self.assertEqual(result.removed_groups, ())
        [group] = result.retained_lineage_groups
        self.assertEqual(group.member_sequences, (red.sequence, blue.sequence))
        self.assertEqual({row.sequence for row in service.all_copies()}, {red.sequence, blue.sequence})


if __name__ == "__main__":
    unittest.main()
