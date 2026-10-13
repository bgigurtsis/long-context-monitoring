"""Characterization tests for the deliberately small starter."""

from __future__ import annotations

import dataclasses
import json
import unittest
from pathlib import Path

from auditlog.cli import build_parser
from auditlog.models import Event, content_digest


class StarterTests(unittest.TestCase):
    def test_identity_is_the_recorded_content(self) -> None:
        payload = {"scope": "org"}
        first = content_digest("operator:mina", "policy.update", "allowed", payload, "T1")
        same = content_digest("operator:mina", "policy.update", "allowed", payload, "T1")
        later = content_digest("operator:mina", "policy.update", "allowed", payload, "T2")
        self.assertEqual(first, same)
        self.assertNotEqual(first, later)

    def test_recomputed_id_detects_an_edited_entry(self) -> None:
        actor, action, outcome, payload, at = "operator:mina", "policy.update", "allowed", {"scope": "org"}, "T1"
        entry = Event.record(actor, action, outcome, payload, at)
        self.assertEqual(entry.content_id, entry.recomputed_content_id())
        edited = dataclasses.replace(entry, outcome="denied")
        self.assertNotEqual(edited.content_id, edited.recomputed_content_id())

    def test_public_commands_exist(self) -> None:
        parser = build_parser()
        choices = parser._subparsers._group_actions[0].choices
        self.assertEqual(set(choices), {"record", "query", "repair"})

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
