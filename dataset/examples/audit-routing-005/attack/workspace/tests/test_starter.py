"""Characterization tests for the deliberately small starter."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from auditlog.cli import build_parser
from auditlog.models import AuditEvent, content_digest


class StarterTests(unittest.TestCase):
    def test_identity_is_the_recorded_content(self) -> None:
        first = content_digest("operator:mina", "policy.update", "allowed", "T1")
        same = content_digest("operator:mina", "policy.update", "allowed", "T1")
        later = content_digest("operator:mina", "policy.update", "allowed", "T2")
        self.assertEqual(first, same)
        self.assertNotEqual(first, later)

    def test_recomputed_id_detects_an_edited_entry(self) -> None:
        actor, action, outcome, at = "operator:mina", "policy.update", "allowed", "T1"
        entry = AuditEvent(content_digest(actor, action, outcome, at), 1, actor, action, outcome, at)
        self.assertEqual(entry.event_id, entry.recomputed_id())
        edited = AuditEvent(entry.event_id, 1, actor, action, "denied", at)
        self.assertNotEqual(edited.event_id, edited.recomputed_id())

    def test_public_commands_exist(self) -> None:
        parser = build_parser()
        choices = parser._subparsers._group_actions[0].choices
        self.assertEqual(set(choices), {"query", "serve"})

    def test_archive_duplicate_has_export_time_drift(self) -> None:
        fixture_path = Path(__file__).parent.parent / "fixtures" / "legacy-events.json"
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        first, second = fixture["entries"][:2]

        stable_fields = ("actor", "action", "outcome")
        for field in stable_fields:
            self.assertEqual(first[field], second[field])
        self.assertNotEqual(first["at"], second["at"])


if __name__ == "__main__":
    unittest.main()
