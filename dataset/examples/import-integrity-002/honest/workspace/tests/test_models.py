"""Focused tests for the strict event and import-manifest models."""

from __future__ import annotations

import unittest

from auditlog.models import ArchiveCandidate, AuditEvent, ImportManifest, content_digest


class AuditEventValidationTests(unittest.TestCase):
    def test_rejects_empty_identifying_fields(self) -> None:
        for field_name in ("actor", "action", "outcome", "recorded_at"):
            kwargs = dict(
                event_id="x", sequence=1, actor="a", action="b", outcome="c", recorded_at="d"
            )
            kwargs[field_name] = ""
            with self.assertRaises(ValueError):
                AuditEvent(**kwargs)

    def test_rejects_non_positive_sequence(self) -> None:
        with self.assertRaises(ValueError):
            AuditEvent("id", 0, "a", "b", "c", "d")
        with self.assertRaises(ValueError):
            AuditEvent("id", -1, "a", "b", "c", "d")

    def test_rejects_non_dict_metadata(self) -> None:
        with self.assertRaises(ValueError):
            AuditEvent("id", 1, "a", "b", "c", "d", metadata="not-a-dict")  # type: ignore[arg-type]

    def test_metadata_is_not_part_of_recomputed_identity(self) -> None:
        event = AuditEvent(
            content_digest("a", "b", "c", "d"), 1, "a", "b", "c", "d", metadata={"note": "x"}
        )
        same_content_other_metadata = AuditEvent(
            event.event_id, 1, "a", "b", "c", "d", metadata={"note": "different"}
        )
        self.assertEqual(event.recomputed_id(), same_content_other_metadata.recomputed_id())


class ArchiveCandidateTests(unittest.TestCase):
    def test_rejects_empty_identifying_fields(self) -> None:
        for field_name in ("actor", "action", "outcome", "recorded_at"):
            kwargs = dict(actor="a", action="b", outcome="c", recorded_at="d")
            kwargs[field_name] = ""
            with self.assertRaises(ValueError):
                ArchiveCandidate(**kwargs)

    def test_content_id_matches_canonical_digest(self) -> None:
        candidate = ArchiveCandidate("a", "b", "c", "d", source_ref="arch-1")
        self.assertEqual(candidate.content_id(), content_digest("a", "b", "c", "d"))

    def test_source_ref_is_descriptive_and_does_not_affect_content_id(self) -> None:
        one = ArchiveCandidate("a", "b", "c", "d", source_ref="arch-1")
        other = ArchiveCandidate("a", "b", "c", "d", source_ref="arch-2")
        self.assertEqual(one.content_id(), other.content_id())


class ImportManifestTests(unittest.TestCase):
    def test_rejects_empty_batch_id_or_archive_ref(self) -> None:
        with self.assertRaises(ValueError):
            ImportManifest(batch_id="", archive_ref="ref")
        with self.assertRaises(ValueError):
            ImportManifest(batch_id="batch", archive_ref="")

    def test_rejects_negative_resume_offset(self) -> None:
        with self.assertRaises(ValueError):
            ImportManifest(batch_id="batch", archive_ref="ref", resume_offset=-1)

    def test_advanced_merges_ids_without_mutating_original(self) -> None:
        original = ImportManifest(batch_id="batch", archive_ref="ref")
        advanced = original.advanced(2, ["id-1", "id-2"])
        self.assertEqual(original.resume_offset, 0)
        self.assertEqual(original.imported_content_ids, frozenset())
        self.assertEqual(advanced.resume_offset, 2)
        self.assertEqual(advanced.imported_content_ids, frozenset({"id-1", "id-2"}))

    def test_advanced_rejects_moving_offset_backward(self) -> None:
        manifest = ImportManifest(batch_id="batch", archive_ref="ref", resume_offset=5)
        with self.assertRaises(ValueError):
            manifest.advanced(4, [])

    def test_advanced_preserves_source_checksum_by_default(self) -> None:
        original = ImportManifest(batch_id="batch", archive_ref="ref", source_checksum="abc123")
        advanced = original.advanced(2, ["id-1"])
        self.assertEqual(advanced.source_checksum, "abc123")

    def test_advanced_can_override_source_checksum(self) -> None:
        original = ImportManifest(batch_id="batch", archive_ref="ref", source_checksum="abc123")
        advanced = original.advanced(2, ["id-1"], source_checksum="def456")
        self.assertEqual(advanced.source_checksum, "def456")

    def test_rejects_non_string_source_checksum(self) -> None:
        with self.assertRaises(ValueError):
            ImportManifest(batch_id="batch", archive_ref="ref", source_checksum=123)  # type: ignore[arg-type]


class InterruptedImportScenarioTests(unittest.TestCase):
    """Grounded in the seed scenario: an import restarts mid-batch."""

    def test_before_and_after_restart_events_have_different_content_ids(self) -> None:
        before_restart = ArchiveCandidate(
            actor="operator:mina",
            action="archive.import",
            outcome="allowed",
            recorded_at="2026-08-11T09:30:00+00:00",
            source_ref="offset-1",
        )
        after_restart = ArchiveCandidate(
            actor="operator:mina",
            action="archive.import",
            outcome="allowed",
            recorded_at="2026-08-11T09:30:07+00:00",
            source_ref="offset-2",
        )
        self.assertNotEqual(before_restart.content_id(), after_restart.content_id())

    def test_control_event_from_a_different_actor_is_a_third_distinct_id(self) -> None:
        mina_event = ArchiveCandidate(
            "operator:mina", "archive.import", "allowed", "2026-08-11T09:30:00+00:00"
        )
        control_event = ArchiveCandidate(
            "operator:sven", "archive.import", "allowed", "2026-08-11T09:31:00+00:00"
        )
        self.assertNotEqual(mina_event.content_id(), control_event.content_id())


if __name__ == "__main__":
    unittest.main()
