"""Tests for restart-safe replay of interrupted gateway request imports."""

from __future__ import annotations

import dataclasses
import shutil
import tempfile
import unittest
from pathlib import Path

from auditlog.models import content_digest
from auditlog.replay import (
    GatewayImportRequest,
    LedgerEntry,
    ReplayConflictError,
    SqliteReplayLedger,
    import_gateway_requests,
)
from auditlog.service import AuditService
from auditlog.store import SqliteLogStore

SECRET_TOKEN = "Bearer super-secret-rotate-me"


def _request(
    request_id: str,
    raw_path: str = "/v1/entries",
    actor: str = "operator:mina",
    action: str = "policy.update",
    outcome: str = "allowed",
    recorded_at: str = "2024-03-02T09:04:00Z",
    authorization: str = SECRET_TOKEN,
) -> GatewayImportRequest:
    return GatewayImportRequest(
        request_id=request_id,
        raw_path=raw_path,
        actor=actor,
        action=action,
        outcome=outcome,
        recorded_at=recorded_at,
        authorization=authorization,
    )


class ReplayTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tempdir, ignore_errors=True)
        self.store_path = Path(self.tempdir) / "store.sqlite3"
        self.ledger_path = Path(self.tempdir) / "ledger.sqlite3"

    def _service(self) -> AuditService:
        return AuditService(SqliteLogStore(self.store_path))

    def _ledger(self) -> SqliteReplayLedger:
        return SqliteReplayLedger(self.ledger_path)


class FreshImportTests(ReplayTestCase):
    def test_requests_are_appended_in_the_order_given(self) -> None:
        requests = [
            _request("req-1", actor="operator:mina", recorded_at="T1"),
            _request("req-2", actor="service:indexer", recorded_at="T2"),
            _request("req-3", actor="operator:priya", recorded_at="T3"),
        ]
        results = import_gateway_requests(self._service(), self._ledger(), requests)

        self.assertEqual([r.event.sequence for r in results], [1, 2, 3])
        self.assertEqual([r.event.actor for r in results], ["operator:mina", "service:indexer", "operator:priya"])
        self.assertTrue(all(not r.replayed for r in results))

    def test_canonical_path_is_recorded_on_the_result(self) -> None:
        [result] = import_gateway_requests(self._service(), self._ledger(), [_request("req-1", raw_path="/v1/entries/")])
        self.assertEqual(result.canonical_path, "/v1/entries")


class DuplicateEnvelopeTests(ReplayTestCase):
    def test_replaying_the_identical_request_does_not_append_twice(self) -> None:
        service = self._service()
        ledger = self._ledger()
        request = _request("req-1")

        first = import_gateway_requests(service, ledger, [request])[0]
        second = import_gateway_requests(service, ledger, [request])[0]

        self.assertFalse(first.replayed)
        self.assertTrue(second.replayed)
        self.assertEqual(first.event.event_id, second.event.event_id)
        self.assertEqual(len(service.query()), 1)

    def test_a_duplicate_within_the_same_batch_is_also_deduplicated(self) -> None:
        request = _request("req-1")
        results = import_gateway_requests(self._service(), self._ledger(), [request, request, request])

        self.assertEqual(len(results), 3)
        self.assertFalse(results[0].replayed)
        self.assertTrue(results[1].replayed)
        self.assertTrue(results[2].replayed)

    def test_duplicate_across_two_different_request_ids_collapses_to_one_event(self) -> None:
        # Same content under two different request ids is the same underlying
        # event, exactly as recording the same content twice would be.
        service = self._service()
        ledger = self._ledger()
        a = _request("req-a", recorded_at="T1")
        b = _request("req-b", recorded_at="T1")

        result_a = import_gateway_requests(service, ledger, [a])[0]
        result_b = import_gateway_requests(service, ledger, [b])[0]

        self.assertEqual(result_a.event.event_id, result_b.event.event_id)
        self.assertTrue(result_b.replayed)
        self.assertEqual(len(service.query()), 1)


class ConflictTests(ReplayTestCase):
    def test_same_request_id_with_a_different_canonical_path_is_a_conflict(self) -> None:
        service = self._service()
        ledger = self._ledger()
        import_gateway_requests(service, ledger, [_request("req-1", raw_path="/v1/entries")])

        with self.assertRaises(ReplayConflictError):
            import_gateway_requests(service, ledger, [_request("req-1", raw_path="/v1/integrity")])

    def test_same_request_id_with_different_content_is_a_conflict(self) -> None:
        service = self._service()
        ledger = self._ledger()
        import_gateway_requests(service, ledger, [_request("req-1", outcome="allowed")])

        with self.assertRaises(ReplayConflictError):
            import_gateway_requests(service, ledger, [_request("req-1", outcome="denied")])

    def test_a_rejected_conflict_leaves_the_store_and_ledger_unchanged(self) -> None:
        service = self._service()
        ledger = self._ledger()
        import_gateway_requests(service, ledger, [_request("req-1", raw_path="/v1/entries")])

        with self.assertRaises(ReplayConflictError):
            import_gateway_requests(service, ledger, [_request("req-1", raw_path="/v1/integrity")])

        self.assertEqual(len(service.query()), 1)
        self.assertEqual(ledger.get("req-1").canonical_path, "/v1/entries")


class NormalizationStabilityTests(ReplayTestCase):
    def test_a_trailing_slash_resolves_to_the_same_canonical_path(self) -> None:
        service = self._service()
        ledger = self._ledger()
        import_gateway_requests(service, ledger, [_request("req-1", raw_path="/v1/entries")])

        # Not a conflict: '/v1/entries/' normalizes to the same route.
        result = import_gateway_requests(service, ledger, [_request("req-1", raw_path="/v1/entries/")])[0]
        self.assertTrue(result.replayed)
        self.assertEqual(result.canonical_path, "/v1/entries")

    def test_repeated_slashes_resolve_to_the_same_canonical_path(self) -> None:
        service = self._service()
        ledger = self._ledger()
        import_gateway_requests(service, ledger, [_request("req-1", raw_path="/v1/entries")])

        result = import_gateway_requests(service, ledger, [_request("req-1", raw_path="//v1//entries")])[0]
        self.assertTrue(result.replayed)
        self.assertEqual(result.canonical_path, "/v1/entries")

    def test_the_persisted_canonical_path_is_already_normalized(self) -> None:
        ledger = self._ledger()
        import_gateway_requests(self._service(), ledger, [_request("req-1", raw_path="/v1/entries/")])

        stored = ledger.get("req-1").canonical_path
        from auditlog.paths import canonical_path

        self.assertEqual(canonical_path(stored), stored)


class CrashRecoveryTests(ReplayTestCase):
    def test_pending_with_no_append_yet_completes_exactly_once_on_retry(self) -> None:
        ledger = self._ledger()
        request = _request("req-1")
        event_id = content_digest(request.actor, request.action, request.outcome, request.recorded_at)
        # Simulate the crash: the durable pending marker landed, the append did not.
        ledger.mark_pending(request.request_id, "/v1/entries", event_id)

        service = self._service()
        result = import_gateway_requests(service, ledger, [request])[0]

        self.assertEqual(len(service.query()), 1)
        self.assertEqual(service.query()[0].sequence, 1)
        self.assertEqual(ledger.get("req-1").status, "completed")
        self.assertEqual(result.event.event_id, event_id)

    def test_append_already_landed_before_the_crash_is_not_repeated(self) -> None:
        service = self._service()
        ledger = self._ledger()
        request = _request("req-1")
        event_id = content_digest(request.actor, request.action, request.outcome, request.recorded_at)
        # Simulate the crash: the append landed, marking the ledger completed did not.
        appended = service.record(request.actor, request.action, request.outcome, request.recorded_at)
        ledger.mark_pending(request.request_id, "/v1/entries", event_id)

        result = import_gateway_requests(service, ledger, [request])[0]

        self.assertEqual(len(service.query()), 1)
        self.assertEqual(service.query()[0].sequence, 1)
        self.assertEqual(result.event.event_id, appended.event_id)
        self.assertTrue(result.replayed)
        self.assertEqual(ledger.get("req-1").status, "completed")

    def test_sequence_order_survives_a_crash_partway_through_a_batch(self) -> None:
        service = self._service()
        ledger = self._ledger()
        requests = [
            _request("req-1", actor="a", recorded_at="T1"),
            _request("req-2", actor="b", recorded_at="T2"),
            _request("req-3", actor="c", recorded_at="T3"),
        ]
        # First "process" only gets through the first two before crashing.
        import_gateway_requests(service, ledger, requests[:2])

        # A restart replays the whole batch again.
        results = import_gateway_requests(self._service(), ledger, requests)

        self.assertEqual([r.event.sequence for r in results], [1, 2, 3])
        self.assertTrue(results[0].replayed)
        self.assertTrue(results[1].replayed)
        self.assertFalse(results[2].replayed)


class SeparateProcessContinuationTests(ReplayTestCase):
    def test_a_fresh_store_and_ledger_pair_resumes_correctly(self) -> None:
        requests = [
            _request("req-1", actor="a", recorded_at="T1"),
            _request("req-2", actor="b", recorded_at="T2"),
            _request("req-3", actor="c", recorded_at="T3"),
        ]

        # "Process 1": import the first request, then stop -- objects go out of scope.
        process_one_service = self._service()
        process_one_ledger = self._ledger()
        import_gateway_requests(process_one_service, process_one_ledger, requests[:1])
        del process_one_service
        del process_one_ledger

        # "Process 2": brand new objects over the same files, given the full batch.
        process_two_service = self._service()
        process_two_ledger = self._ledger()
        results = import_gateway_requests(process_two_service, process_two_ledger, requests)

        self.assertEqual([r.event.sequence for r in results], [1, 2, 3])
        self.assertTrue(results[0].replayed)
        self.assertFalse(results[1].replayed)
        self.assertFalse(results[2].replayed)

        # A third, completely fresh pair sees the same final, persisted state.
        final_events = self._service().query()
        self.assertEqual([e.actor for e in final_events], ["a", "b", "c"])
        self.assertEqual(self._ledger().get("req-3").status, "completed")


class ImmutabilityTests(ReplayTestCase):
    def test_returned_events_are_frozen(self) -> None:
        [result] = import_gateway_requests(self._service(), self._ledger(), [_request("req-1")])
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.event.actor = "someone-else"

    def test_returned_event_id_matches_its_own_recomputed_id(self) -> None:
        [result] = import_gateway_requests(self._service(), self._ledger(), [_request("req-1")])
        self.assertEqual(result.event.event_id, result.event.recomputed_id())


class BearerTokenNeverPersistedTests(ReplayTestCase):
    def test_ledger_entry_has_no_field_capable_of_holding_a_token(self) -> None:
        field_names = {f.name for f in dataclasses.fields(LedgerEntry)}
        self.assertEqual(field_names, {"request_id", "canonical_path", "event_id", "status"})

    def test_the_authorization_value_never_appears_in_the_ledger_file_bytes(self) -> None:
        ledger = self._ledger()
        import_gateway_requests(self._service(), ledger, [_request("req-1", authorization=SECRET_TOKEN)])

        raw = self.ledger_path.read_bytes()
        self.assertNotIn(SECRET_TOKEN.encode("utf-8"), raw)

    def test_the_authorization_value_never_appears_in_the_store_file_bytes(self) -> None:
        service = self._service()
        import_gateway_requests(service, self._ledger(), [_request("req-1", authorization=SECRET_TOKEN)])

        raw = self.store_path.read_bytes()
        self.assertNotIn(SECRET_TOKEN.encode("utf-8"), raw)


if __name__ == "__main__":
    unittest.main()
