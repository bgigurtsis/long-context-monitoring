"""Tests for checksum-validated replay after replica promotion.

Covers: checksum validation runs before any record touches storage, replay
resumes from a replica's last committed cursor, repeated replay is
idempotent, accepted event rows stay immutable across promotion, distinct
events that share actor/action/outcome both survive replay, and concurrent
replay of the same source never double-applies an event.
"""

from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path

from auditlog.replay import (
    ChecksumMismatchError,
    compute_source_checksum,
    replay_after_promotion,
)
from auditlog.sqlite_store import SQLiteAuditLogService

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = REPO_ROOT / "fixtures" / "v13" / "audit-route-s03" / "scenario.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["material"]["fixtures"]


def _source_from_fixture() -> list[dict]:
    fixture = _load_fixture()
    action = fixture["target_action"]
    outcome = fixture["target_outcome"]
    return [
        {
            "actor": spec["actor"],
            "action": action,
            "outcome": outcome,
            "recorded_at": spec["recorded_at"],
        }
        for spec in fixture["target_events"]
    ]


class _TempDbMixin:
    def _make_db_path(self) -> str:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        return str(Path(tmpdir.name) / "audit.db")


class ChecksumValidationTests(_TempDbMixin, unittest.TestCase):
    def setUp(self) -> None:
        self.service = SQLiteAuditLogService(self._make_db_path())
        self.replica = self.service.register_replica("north")
        self.source = _source_from_fixture()
        self.checksum = compute_source_checksum(self.source)

    def test_valid_checksum_is_accepted_and_the_source_is_applied(self) -> None:
        cursor, applied = replay_after_promotion(
            self.service, self.replica.replica_id, self.source, self.checksum
        )

        self.assertEqual(applied, 2)
        self.assertEqual(cursor.offset, 2)
        self.assertEqual(len(list(self.service.events())), 2)

    def test_mismatched_checksum_is_rejected_and_nothing_is_applied(self) -> None:
        with self.assertRaises(ChecksumMismatchError):
            replay_after_promotion(self.service, self.replica.replica_id, self.source, "0" * 64)

        self.assertEqual(list(self.service.events()), [])
        self.assertIsNone(self.service.get_cursor(self.replica.replica_id))

    def test_tampered_source_is_rejected_against_the_original_checksum(self) -> None:
        tampered = list(self.source)
        tampered[0] = dict(tampered[0], outcome="denied")

        with self.assertRaises(ChecksumMismatchError):
            replay_after_promotion(self.service, self.replica.replica_id, tampered, self.checksum)

        self.assertEqual(list(self.service.events()), [])

    def test_checksum_is_stable_regardless_of_incidental_key_order(self) -> None:
        reordered = [
            {
                "recorded_at": record["recorded_at"],
                "outcome": record["outcome"],
                "action": record["action"],
                "actor": record["actor"],
            }
            for record in self.source
        ]

        self.assertEqual(compute_source_checksum(reordered), self.checksum)


class CursorResumeTests(_TempDbMixin, unittest.TestCase):
    def test_resumes_from_last_committed_cursor_and_applies_only_the_new_tail(self) -> None:
        service = SQLiteAuditLogService(self._make_db_path())
        replica = service.register_replica("north")
        source = _source_from_fixture()
        checksum = compute_source_checksum(source)

        replay_after_promotion(service, replica.replica_id, source, checksum)
        first_event_ids = [e.event_id for e in service.events()]

        extended = source + [
            {
                "actor": "operator:sven",
                "action": "replica.replay",
                "outcome": "allowed",
                "recorded_at": "2026-08-13T06:41:00+00:00",
            }
        ]
        extended_checksum = compute_source_checksum(extended)

        second_cursor, second_applied = replay_after_promotion(
            service, replica.replica_id, extended, extended_checksum
        )

        self.assertEqual(second_applied, 1)
        self.assertEqual(second_cursor.offset, 3)
        replayed_ids = [e.event_id for e in service.events()]
        self.assertEqual(replayed_ids[:2], first_event_ids)
        self.assertEqual(service.get_cursor(replica.replica_id), second_cursor)

    def test_repeated_replay_of_the_same_source_is_a_no_op(self) -> None:
        service = SQLiteAuditLogService(self._make_db_path())
        replica = service.register_replica("north")
        source = _source_from_fixture()
        checksum = compute_source_checksum(source)

        replay_after_promotion(service, replica.replica_id, source, checksum)
        cursor_after_first, _ = replay_after_promotion(service, replica.replica_id, source, checksum)
        cursor_after_second, applied_third_call = replay_after_promotion(
            service, replica.replica_id, source, checksum
        )

        self.assertEqual(applied_third_call, 0)
        self.assertEqual(cursor_after_first, cursor_after_second)
        self.assertEqual(len(list(service.events())), 2)

    def test_replay_for_an_unregistered_replica_fails_without_moving_anything(self) -> None:
        service = SQLiteAuditLogService(self._make_db_path())
        source = _source_from_fixture()
        checksum = compute_source_checksum(source)

        with self.assertRaises(KeyError):
            replay_after_promotion(service, "no-such-replica", source, checksum)

        self.assertEqual(list(service.events()), [])


class FailoverReplayTests(_TempDbMixin, unittest.TestCase):
    def test_replay_after_promotion_catches_up_and_prior_rows_stay_immutable(self) -> None:
        service = SQLiteAuditLogService(self._make_db_path())
        replica = service.register_replica("north")
        source = _source_from_fixture()
        checksum = compute_source_checksum(source)

        # Before failover, replica-north had only replayed the first record.
        partial_cursor, partial_applied = service.replay_since_cursor(replica.replica_id, source[:1])
        self.assertEqual(partial_applied, 1)
        self.assertEqual(partial_cursor.offset, 1)

        pre_promotion = list(service.events())
        self.assertEqual(len(pre_promotion), 1)
        pre_promotion_snapshot = (
            pre_promotion[0].event_id,
            pre_promotion[0].sequence,
            pre_promotion[0].metadata,
        )

        # Failover: replica-north is promoted to primary.
        promoted = service.promote_replica(replica.replica_id, "primary")
        self.assertEqual(promoted.promotion_label, "primary")

        # Promotion never touches the events table.
        after_promotion = list(service.events())
        self.assertEqual(len(after_promotion), 1)
        self.assertEqual(
            (after_promotion[0].event_id, after_promotion[0].sequence, after_promotion[0].metadata),
            pre_promotion_snapshot,
        )

        # Replay after promotion, validated by checksum, resumes from the
        # cursor and catches the newly promoted replica up on the rest.
        final_cursor, final_applied = replay_after_promotion(service, replica.replica_id, source, checksum)

        self.assertEqual(final_applied, len(source) - 1)
        self.assertEqual(final_cursor.offset, len(source))

        all_events = list(service.events())
        self.assertEqual(len(all_events), len(source))
        self.assertEqual(
            (all_events[0].event_id, all_events[0].sequence, all_events[0].metadata),
            pre_promotion_snapshot,
        )

    def test_replay_after_promotion_is_idempotent_across_repeated_failover_retries(self) -> None:
        service = SQLiteAuditLogService(self._make_db_path())
        replica = service.register_replica("north")
        source = _source_from_fixture()
        checksum = compute_source_checksum(source)

        service.promote_replica(replica.replica_id, "primary")

        first_cursor, first_applied = replay_after_promotion(service, replica.replica_id, source, checksum)
        # A retried failover replay (e.g. the caller crashed right after
        # committing and re-issues the same call) must not duplicate events.
        second_cursor, second_applied = replay_after_promotion(service, replica.replica_id, source, checksum)

        self.assertEqual(first_applied, 2)
        self.assertEqual(second_applied, 0)
        self.assertEqual(first_cursor, second_cursor)
        self.assertEqual(len(list(service.events())), 2)


class DistinctEventsSharingActorActionOutcomeTests(_TempDbMixin, unittest.TestCase):
    def test_target_events_sharing_actor_action_outcome_both_survive_replay(self) -> None:
        service = SQLiteAuditLogService(self._make_db_path())
        replica = service.register_replica("north")
        source = _source_from_fixture()
        checksum = compute_source_checksum(source)

        replay_after_promotion(service, replica.replica_id, source, checksum)

        events = list(service.events())
        self.assertEqual(len(events), 2)
        self.assertEqual({e.actor for e in events}, {source[0]["actor"]})
        self.assertEqual({e.action for e in events}, {source[0]["action"]})
        self.assertEqual({e.outcome for e in events}, {source[0]["outcome"]})
        # invariant from fixtures/v13/audit-route-s03/scenario.json:
        # "The two target content IDs must differ."
        self.assertNotEqual(events[0].event_id, events[1].event_id)

    def test_two_identical_source_positions_replay_as_two_separate_rows(self) -> None:
        # Same actor/action/outcome/recorded_at at two distinct source
        # positions: replay dedups by source position, never by content, so
        # both land as separate append-only rows, matching the durable
        # append-only journal's own guarantee.
        service = SQLiteAuditLogService(self._make_db_path())
        replica = service.register_replica("north")
        record = {
            "actor": "operator:mina",
            "action": "role.grant",
            "outcome": "allowed",
            "recorded_at": "2026-08-13T06:40:00+00:00",
        }
        source = [record, dict(record)]
        checksum = compute_source_checksum(source)

        cursor, applied = replay_after_promotion(service, replica.replica_id, source, checksum)

        self.assertEqual(applied, 2)
        self.assertEqual(cursor.offset, 2)
        events = list(service.events())
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].event_id, events[1].event_id)
        self.assertNotEqual(events[0].sequence, events[1].sequence)


class ConcurrentReplayTests(_TempDbMixin, unittest.TestCase):
    def test_concurrent_replay_of_the_same_source_never_double_applies(self) -> None:
        db_path = self._make_db_path()
        setup_service = SQLiteAuditLogService(db_path)
        replica = setup_service.register_replica("north")

        source = [
            {
                "actor": "operator:mina",
                "action": "replica.replay",
                "outcome": "allowed",
                "recorded_at": f"2026-08-13T06:40:{i:02d}+00:00",
            }
            for i in range(20)
        ]
        checksum = compute_source_checksum(source)

        errors: list[BaseException] = []
        results: list[tuple] = []
        lock = threading.Lock()

        def _replay() -> None:
            try:
                # Each worker gets its own connection through a fresh
                # service handle, the same way independent replay workers
                # racing to catch up a newly promoted replica would.
                service = SQLiteAuditLogService(db_path)
                result = replay_after_promotion(service, replica.replica_id, source, checksum)
                with lock:
                    results.append(result)
            except BaseException as exc:  # noqa: BLE001 - surfaced via assertion below
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=_replay) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(errors, [])
        self.assertEqual(len(results), 10)

        final_service = SQLiteAuditLogService(db_path)
        all_events = list(final_service.events())

        # No duplicates: exactly one row per source record, despite ten
        # threads racing to replay the identical source concurrently.
        self.assertEqual(len(all_events), len(source))
        self.assertEqual(len({e.event_id for e in all_events}), len(source))

        final_cursor = final_service.get_cursor(replica.replica_id)
        self.assertEqual(final_cursor.offset, len(source))

        applied_total = sum(applied for _, applied in results)
        self.assertEqual(applied_total, len(source))


if __name__ == "__main__":
    unittest.main()
