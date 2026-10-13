"""Contract tests for the storage-independent ``AuditLogService`` interface.

``AuditLogServiceContract`` is a mixin, not a ``TestCase`` on its own: any
storage backend that implements ``AuditLogService`` runs the same suite by
subclassing the mixin alongside ``unittest.TestCase`` and setting
``SERVICE_FACTORY``. This keeps the append-only and identity guarantees
enforced identically regardless of what backs the service.
"""

from __future__ import annotations

import unittest

from auditlog.integrity import complete_event_identity
from auditlog.models import ArchiveCandidate, ImportManifest
from auditlog.service import InMemoryAuditLogService


class AuditLogServiceContract:
    SERVICE_FACTORY = None

    def make_service(self):
        return self.SERVICE_FACTORY()

    def test_record_assigns_gapless_sequence_from_one(self) -> None:
        service = self.make_service()
        first = service.record("operator:mina", "policy.update", "allowed", "T1")
        second = service.record("service:indexer", "report.read", "allowed", "T2")
        self.assertEqual(first.sequence, 1)
        self.assertEqual(second.sequence, 2)

    def test_events_are_returned_in_append_order(self) -> None:
        service = self.make_service()
        service.record("a", "act1", "allowed", "T1")
        service.record("b", "act2", "allowed", "T2")
        events = service.events()
        self.assertEqual([e.action for e in events], ["act1", "act2"])

    def test_events_view_cannot_be_used_to_mutate_the_trail(self) -> None:
        service = self.make_service()
        service.record("a", "act1", "allowed", "T1")
        first_view = service.events()
        service.record("b", "act2", "allowed", "T2")
        # The tuple already returned is a snapshot; it does not grow, and
        # nothing about the interface lets a caller edit or remove an entry.
        self.assertEqual(len(first_view), 1)
        self.assertFalse(hasattr(service, "delete"))
        self.assertFalse(hasattr(service, "update"))

    def test_find_filters_by_actor_and_action(self) -> None:
        service = self.make_service()
        service.record("operator:mina", "policy.update", "allowed", "T1")
        service.record("operator:mina", "report.read", "allowed", "T2")
        service.record("service:indexer", "report.read", "allowed", "T3")

        self.assertEqual(len(service.find(actor="operator:mina")), 2)
        self.assertEqual(len(service.find(action="report.read")), 2)
        self.assertEqual(
            len(service.find(actor="operator:mina", action="report.read")), 1
        )

    def test_content_id_is_derived_from_recorded_content_including_recorded_at(self) -> None:
        service = self.make_service()
        first = service.record("operator:mina", "policy.update", "allowed", "T1")
        second = service.record("operator:mina", "policy.update", "allowed", "T2")
        self.assertNotEqual(first.event_id, second.event_id)

    def test_caller_metadata_is_not_an_input_to_identity(self) -> None:
        service = self.make_service()
        one = service.record("a", "b", "c", "T1", metadata={"tag": "one"})
        other_service = self.make_service()
        two = other_service.record("a", "b", "c", "T1", metadata={"tag": "two"})
        self.assertEqual(one.event_id, two.event_id)

    def test_verify_reports_nothing_on_an_untampered_trail(self) -> None:
        service = self.make_service()
        service.record("a", "b", "c", "T1")
        service.record("d", "e", "f", "T2")
        self.assertEqual(service.verify(), ())

    def test_import_archive_recomputes_identity_rather_than_trusting_the_archive(self) -> None:
        service = self.make_service()
        manifest = ImportManifest(batch_id="batch-1", archive_ref="archive.jsonl")
        candidates = [
            ArchiveCandidate("operator:mina", "archive.import", "allowed", "T1", source_ref="arch-1"),
        ]
        _, appended = service.import_archive(manifest, candidates)
        self.assertEqual(len(appended), 1)
        self.assertEqual(appended[0].recomputed_id(), appended[0].event_id)

    def test_resuming_an_interrupted_import_does_not_duplicate_the_completed_event(self) -> None:
        service = self.make_service()
        manifest = ImportManifest(batch_id="batch-1", archive_ref="archive.jsonl")

        before_restart = ArchiveCandidate(
            "operator:mina", "archive.import", "allowed", "2026-08-11T09:30:00+00:00", "offset-1"
        )
        after_restart = ArchiveCandidate(
            "operator:mina", "archive.import", "allowed", "2026-08-11T09:30:07+00:00", "offset-2"
        )

        manifest, first_batch = service.import_archive(manifest, [before_restart])
        self.assertEqual(len(first_batch), 1)

        # Resume re-reads from the start of the archive, as an interrupted
        # import would after a restart: the already-imported candidate is
        # present again alongside the one that was never imported.
        manifest, second_batch = service.import_archive(manifest, [before_restart, after_restart])

        self.assertEqual(len(second_batch), 1)
        self.assertEqual(second_batch[0].event_id, after_restart.content_id())
        all_content_ids = {event.event_id for event in service.events()}
        self.assertEqual(
            all_content_ids, {before_restart.content_id(), after_restart.content_id()}
        )
        self.assertEqual(
            manifest.imported_content_ids,
            frozenset({before_restart.content_id(), after_restart.content_id()}),
        )

    def test_import_archive_offsets_and_source_refs_are_descriptive_only(self) -> None:
        service = self.make_service()
        manifest = ImportManifest(batch_id="batch-1", archive_ref="archive.jsonl")
        same_event_different_ref = [
            ArchiveCandidate("operator:mina", "archive.import", "allowed", "T1", "arch-1001"),
            ArchiveCandidate("operator:mina", "archive.import", "allowed", "T1", "arch-2001"),
        ]
        manifest, appended = service.import_archive(manifest, same_event_different_ref)
        self.assertEqual(len(appended), 1)
        self.assertEqual(len(service.events()), 1)


class InMemoryAuditLogServiceContractTests(AuditLogServiceContract, unittest.TestCase):
    SERVICE_FACTORY = InMemoryAuditLogService


class CompleteEventIdentityTests(unittest.TestCase):
    def test_includes_both_recorded_at_and_content_id(self) -> None:
        identity = complete_event_identity("2026-08-11T09:30:00+00:00", "abc123")
        self.assertIn("2026-08-11T09:30:00+00:00", identity)
        self.assertIn("abc123", identity)

    def test_distinguishes_events_that_share_only_one_value(self) -> None:
        same_time_different_content = complete_event_identity("T1", "content-a")
        same_content_different_time = complete_event_identity("T2", "content-a")
        same_time_same_content_other = complete_event_identity("T1", "content-b")
        self.assertNotEqual(same_time_different_content, same_content_different_time)
        self.assertNotEqual(same_time_different_content, same_time_same_content_other)


if __name__ == "__main__":
    unittest.main()
