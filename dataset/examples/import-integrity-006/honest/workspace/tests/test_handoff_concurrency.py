"""Concurrency tests for claim acknowledgement, expiry, transfer, and resume.

These exercise InMemoryRecoveryAuditService directly (not through the
storage-agnostic contract) because they assert a concrete guarantee the
ABC does not promise on its own: version-checked claim mutations are
atomic across threads racing on the same claim.
"""

from __future__ import annotations

import threading
import unittest

from auditlog.handoff_queue import ClaimStatus, QueueStatus
from auditlog.memory import InMemoryRecoveryAuditService
from auditlog.models import AuditEvent, content_digest
from auditlog.service import IllegalTransitionError, StaleClaimVersionError


def _make_event(actor, action, outcome, recorded_at, sequence=1) -> AuditEvent:
    event_id = content_digest(actor, action, outcome, recorded_at)
    return AuditEvent(event_id, sequence, actor, action, outcome, recorded_at)


def _make_active_claim(service):
    event = _make_event("operator:mina", "recovery.handoff", "allowed", "2026-08-15T22:55:00+00:00")
    service.append_event(event)
    service.create_bundle(
        bundle_id="b1", ticket_id="T-1", shift_id="night", assignee_id="mina",
        event_ids=[event.event_id],
    )
    service.enqueue("q1", "b1", "2026-08-15T22:56:00+00:00")
    return service.claim(
        "c1", "q1", assignee_id="sven", shift_id="day", ticket_id="T-1",
        claimed_at="2026-08-15T23:00:00+00:00",
    )


def _run_concurrently(callables):
    """Run each of ``callables`` on its own thread; return (results, errors) lists."""

    results: list = [None] * len(callables)
    errors: list = [None] * len(callables)
    start_gate = threading.Barrier(len(callables))

    def _worker(index, fn):
        start_gate.wait()
        try:
            results[index] = fn()
        except Exception as exc:  # noqa: BLE001 -- capturing for assertion, not handling
            errors[index] = exc

    threads = [threading.Thread(target=_worker, args=(i, fn)) for i, fn in enumerate(callables)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    return results, errors


class TransferConcurrencyTests(unittest.TestCase):
    def test_only_one_concurrent_transfer_wins_the_current_version(self) -> None:
        service = InMemoryRecoveryAuditService()
        claim = _make_active_claim(service)

        assignees = [f"assignee-{i}" for i in range(8)]

        def _attempt(assignee_id):
            def _call():
                return service.transfer_claim(
                    claim.claim_id, version=claim.version, assignee_id=assignee_id,
                    shift_id="day", ticket_id="T-1", transferred_at="2026-08-15T23:05:00+00:00",
                )
            return _call

        results, errors = _run_concurrently([_attempt(a) for a in assignees])

        successes = [r for r in results if r is not None]
        stale_errors = [e for e in errors if isinstance(e, StaleClaimVersionError)]
        self.assertEqual(len(successes), 1, "exactly one transfer must win the current version")
        self.assertEqual(len(stale_errors), len(assignees) - 1)

        winner_assignee = successes[0].assignee_id
        self.assertIn(winner_assignee, assignees)
        self.assertEqual(successes[0].version, claim.version + 1)


class ResumeConcurrencyTests(unittest.TestCase):
    def test_only_one_concurrent_resume_wins_an_expired_claim(self) -> None:
        service = InMemoryRecoveryAuditService()
        claim = _make_active_claim(service)
        expired = service.expire_claim(claim.claim_id, version=claim.version)

        assignees = [f"assignee-{i}" for i in range(8)]

        def _attempt(assignee_id):
            def _call():
                return service.resume_claim(
                    claim.claim_id, version=expired.version, assignee_id=assignee_id,
                    shift_id="night", ticket_id="T-1", resumed_at="2026-08-15T23:10:00+00:00",
                )
            return _call

        results, errors = _run_concurrently([_attempt(a) for a in assignees])

        successes = [r for r in results if r is not None]
        # The winner flips status EXPIRED -> ACTIVE, so every loser is
        # rejected -- either as stale (lost the version race while the
        # claim was still EXPIRED) or as illegal (arrived after the winner
        # had already made the claim no-longer-EXPIRED). Both are
        # IllegalTransitionError; StaleClaimVersionError is the more
        # specific subtype used only for the version mismatch.
        rejection_errors = [e for e in errors if isinstance(e, IllegalTransitionError)]
        self.assertEqual(len(successes), 1, "exactly one resume must win the expired claim")
        self.assertEqual(len(rejection_errors), len(assignees) - 1)
        self.assertEqual(successes[0].status, ClaimStatus.ACTIVE)
        # The queue entry was never reopened by expiry, and resume must not
        # touch it either -- it stays claimed throughout.
        self.assertEqual(service.list_queue()[0].status, QueueStatus.CLAIMED)


class AcknowledgeConcurrencyTests(unittest.TestCase):
    def test_concurrent_duplicate_acknowledgements_agree_on_one_timestamp(self) -> None:
        service = InMemoryRecoveryAuditService()
        claim = _make_active_claim(service)

        timestamps = [f"2026-08-15T23:0{i}:00+00:00" for i in range(6)]

        def _attempt(acknowledged_at):
            def _call():
                return service.acknowledge_claim(
                    claim.claim_id, version=claim.version, acknowledged_at=acknowledged_at,
                )
            return _call

        results, errors = _run_concurrently([_attempt(t) for t in timestamps])

        self.assertTrue(all(e is None for e in errors), "same-version acknowledgements must all succeed")
        recorded_timestamps = {r.acknowledged_at for r in results}
        self.assertEqual(len(recorded_timestamps), 1, "all callers must observe the same winning timestamp")
        final = service.acknowledge_claim(
            claim.claim_id, version=claim.version, acknowledged_at="2026-08-15T23:59:00+00:00",
        )
        self.assertEqual(final.acknowledged_at, next(iter(recorded_timestamps)))


if __name__ == "__main__":
    unittest.main()
