"""Model tests: immutability, canonical identity, and archive collapsing."""

from __future__ import annotations

import dataclasses
import unittest

from auditlog.models import AuditEvent, content_digest


ACTOR, ACTION, OUTCOME, AT = "operator:mina", "policy.update", "allowed", "2024-03-02T09:04:00Z"


class AuditEventIdentityTests(unittest.TestCase):
    def test_identity_is_a_pure_function_of_the_identifying_fields(self) -> None:
        first = content_digest(ACTOR, ACTION, OUTCOME, AT)
        same = content_digest(ACTOR, ACTION, OUTCOME, AT)
        self.assertEqual(first, same)

    def test_identity_changes_when_any_identifying_field_changes(self) -> None:
        base = content_digest(ACTOR, ACTION, OUTCOME, AT)
        self.assertNotEqual(base, content_digest("operator:sven", ACTION, OUTCOME, AT))
        self.assertNotEqual(base, content_digest(ACTOR, "key.revoke", OUTCOME, AT))
        self.assertNotEqual(base, content_digest(ACTOR, ACTION, "denied", AT))
        self.assertNotEqual(base, content_digest(ACTOR, ACTION, OUTCOME, "2024-03-02T09:11:00Z"))

    def test_separator_cannot_be_forged_by_concatenation(self) -> None:
        # "a\x1fb" as one field vs "a" and "b" as two fields must not collide.
        combined = content_digest("a\x1fb", ACTION, OUTCOME, AT)
        split = content_digest("a", ACTION, OUTCOME, AT)
        self.assertNotEqual(combined, split)

    def test_metadata_is_not_an_input_to_identity(self) -> None:
        event_id = content_digest(ACTOR, ACTION, OUTCOME, AT)
        with_meta = AuditEvent(event_id, 1, ACTOR, ACTION, OUTCOME, AT, metadata={"note": "a"})
        without_meta = AuditEvent(event_id, 1, ACTOR, ACTION, OUTCOME, AT, metadata={})
        self.assertEqual(with_meta.recomputed_id(), without_meta.recomputed_id())
        self.assertEqual(with_meta.event_id, without_meta.event_id)


class AuditEventImmutabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.event = AuditEvent(
            content_digest(ACTOR, ACTION, OUTCOME, AT), 1, ACTOR, ACTION, OUTCOME, AT
        )

    def test_fields_cannot_be_reassigned(self) -> None:
        with self.assertRaises(dataclasses.FrozenInstanceError):
            self.event.outcome = "denied"  # type: ignore[misc]

    def test_correction_requires_a_new_entry_not_a_mutation(self) -> None:
        corrected = AuditEvent(
            content_digest(ACTOR, ACTION, "denied", AT), 2, ACTOR, ACTION, "denied", AT
        )
        self.assertNotEqual(self.event.event_id, corrected.event_id)
        self.assertEqual(self.event.outcome, "allowed")

    def test_recomputed_id_detects_a_tampered_entry(self) -> None:
        self.assertEqual(self.event.event_id, self.event.recomputed_id())
        tampered = AuditEvent(self.event.event_id, 1, ACTOR, ACTION, "denied", AT)
        self.assertNotEqual(tampered.event_id, tampered.recomputed_id())


class AuditEventSerializationTests(unittest.TestCase):
    def test_to_record_and_from_current_record_round_trip(self) -> None:
        original = AuditEvent(
            content_digest(ACTOR, ACTION, OUTCOME, AT),
            3,
            ACTOR,
            ACTION,
            OUTCOME,
            AT,
            metadata={"import_batch": "native"},
        )
        rebuilt = AuditEvent.from_current_record(original.to_record())
        self.assertEqual(original, rebuilt)

    def test_to_record_drops_in_memory_source_version(self) -> None:
        event = AuditEvent(
            content_digest(ACTOR, ACTION, OUTCOME, AT), 1, ACTOR, ACTION, OUTCOME, AT, source_version=1
        )
        self.assertNotIn("source_version", event.to_record())


class ArchiveGroupTests(unittest.TestCase):
    def test_archive_group_id_matches_a_native_entry_with_the_same_content(self) -> None:
        representative_at = "2024-03-02T10:15:00Z"
        from_archive = AuditEvent.from_archive_group(
            actor=ACTOR,
            action=ACTION,
            outcome=OUTCOME,
            recorded_at=representative_at,
            sequence=1,
            origin_refs=["arch-1001", "arch-2001"],
        )
        native_equivalent = content_digest(ACTOR, ACTION, OUTCOME, representative_at)
        self.assertEqual(from_archive.event_id, native_equivalent)

    def test_archive_group_records_origin_refs_as_descriptive_metadata(self) -> None:
        event = AuditEvent.from_archive_group(
            actor=ACTOR,
            action=ACTION,
            outcome=OUTCOME,
            recorded_at=AT,
            sequence=1,
            origin_refs=["arch-2001", "arch-1001"],
        )
        self.assertEqual(event.metadata["origin_refs"], ["arch-2001", "arch-1001"])
        # Origin refs are descriptive only: they don't feed the id.
        self.assertEqual(event.event_id, content_digest(ACTOR, ACTION, OUTCOME, AT))


if __name__ == "__main__":
    unittest.main()
