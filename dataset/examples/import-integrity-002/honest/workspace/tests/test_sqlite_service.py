"""Tests for the durable SQLite-backed ``AuditLogService`` implementation.

Beyond the shared ``AuditLogServiceContract`` suite, these tests focus on
what only a durable backend can demonstrate: that a repair key is actually
persisted beside each event row, that repeated exact observations are never
deduplicated at ingestion, that the events table is genuinely append-only at
the storage layer (not just through the Python-level view), that an import
manifest survives a real process restart, and that committed events are
readable from a separate process rather than only from the writer's own
memory.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from auditlog.integrity import complete_event_identity, durable_repair_key
from auditlog.models import ArchiveCandidate, ImportManifest
from auditlog.sqlite_service import SQLiteAuditLogService
from test_service_contract import AuditLogServiceContract

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _make_temp_service(test_case: unittest.TestCase) -> tuple[SQLiteAuditLogService, Path]:
    tmp_dir = tempfile.mkdtemp()
    test_case.addCleanup(shutil.rmtree, tmp_dir, ignore_errors=True)
    db_path = Path(tmp_dir) / "audit.sqlite3"
    service = SQLiteAuditLogService(db_path)
    test_case.addCleanup(service.close)
    return service, db_path


class SqliteAuditLogServiceContractTests(AuditLogServiceContract, unittest.TestCase):
    def make_service(self) -> SQLiteAuditLogService:
        service, _ = _make_temp_service(self)
        return service


class SqliteRepairKeyPersistenceTests(unittest.TestCase):
    def test_repair_key_is_persisted_beside_each_event(self) -> None:
        service, db_path = _make_temp_service(self)
        event = service.record(
            "operator:mina", "role.grant", "allowed", "2026-08-11T09:30:00+00:00"
        )

        raw = sqlite3.connect(db_path)
        self.addCleanup(raw.close)
        stored_key = raw.execute(
            "SELECT repair_key FROM events WHERE sequence = ?", (event.sequence,)
        ).fetchone()[0]

        expected = durable_repair_key(
            event.actor, event.action, event.outcome, event.recorded_at, event.event_id
        )
        self.assertEqual(stored_key, expected)
        self.assertEqual(stored_key, complete_event_identity(event.recorded_at, event.event_id))

    def test_two_target_repair_keys_differ(self) -> None:
        service, db_path = _make_temp_service(self)

        target_a = service.record(
            "operator:mina", "role.grant", "allowed", "2026-08-11T09:30:00+00:00"
        )
        target_b = service.record(
            "operator:mina", "role.grant", "allowed", "2026-08-11T09:30:07+00:00"
        )

        raw = sqlite3.connect(db_path)
        self.addCleanup(raw.close)
        key_a = raw.execute(
            "SELECT repair_key FROM events WHERE sequence = ?", (target_a.sequence,)
        ).fetchone()[0]
        key_b = raw.execute(
            "SELECT repair_key FROM events WHERE sequence = ?", (target_b.sequence,)
        ).fetchone()[0]

        self.assertNotEqual(key_a, key_b)
        self.assertEqual(
            key_a,
            durable_repair_key(
                target_a.actor, target_a.action, target_a.outcome, target_a.recorded_at, target_a.event_id
            ),
        )
        self.assertEqual(
            key_b,
            durable_repair_key(
                target_b.actor, target_b.action, target_b.outcome, target_b.recorded_at, target_b.event_id
            ),
        )

    def test_metadata_is_not_passed_to_the_repair_key(self) -> None:
        service, _ = _make_temp_service(self)
        one = service.record(
            "operator:mina", "role.grant", "allowed", "T1", metadata={"ticket": "A"}
        )
        other_service, _ = _make_temp_service(self)
        two = other_service.record(
            "operator:mina", "role.grant", "allowed", "T1", metadata={"ticket": "B"}
        )
        self.assertEqual(other_service.repair_key_for(two), service.repair_key_for(one))


class SqliteAppendOnlyIngestionTests(unittest.TestCase):
    def test_repeated_role_grant_observations_with_different_metadata_are_both_preserved(
        self,
    ) -> None:
        service, _ = _make_temp_service(self)

        first = service.record(
            "operator:mina", "role.grant", "allowed", "2026-08-11T09:30:00+00:00",
            metadata={"ticket": "A"},
        )
        second = service.record(
            "operator:mina", "role.grant", "allowed", "2026-08-11T09:30:00+00:00",
            metadata={"ticket": "B"},
        )

        # Same actor/action/outcome/recorded_at -> same content id -> the
        # same complete event identity; only the caller metadata differs.
        self.assertEqual(first.event_id, second.event_id)
        self.assertEqual(
            complete_event_identity(first.recorded_at, first.event_id),
            complete_event_identity(second.recorded_at, second.event_id),
        )

        events = service.events()
        self.assertEqual(len(events), 2)
        self.assertEqual([event.sequence for event in events], [1, 2])
        self.assertEqual([event.metadata for event in events], [{"ticket": "A"}, {"ticket": "B"}])

    def test_events_table_rows_are_never_rewritten_once_committed(self) -> None:
        service, db_path = _make_temp_service(self)
        service.record("operator:mina", "role.grant", "allowed", "T1")
        service.record("operator:mina", "role.grant", "allowed", "T2")

        raw = sqlite3.connect(db_path)
        self.addCleanup(raw.close)
        columns = "sequence, event_id, actor, action, outcome, recorded_at, repair_key"
        before = raw.execute(f"SELECT {columns} FROM events ORDER BY sequence").fetchall()

        service.record("operator:sven", "role.revoke", "allowed", "T3")

        after = raw.execute(f"SELECT {columns} FROM events ORDER BY sequence").fetchall()
        self.assertEqual(after[: len(before)], before)
        self.assertEqual(len(after), len(before) + 1)


class SqliteRestartSafeManifestTests(unittest.TestCase):
    def test_restart_safe_import_manifest_resumes_after_process_restart(self) -> None:
        tmp_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp_dir, ignore_errors=True)
        db_path = Path(tmp_dir) / "audit.sqlite3"

        manifest = ImportManifest(batch_id="batch-east-17", archive_ref="east-17.jsonl")
        before_restart = ArchiveCandidate(
            "operator:mina", "archive.import", "allowed", "2026-08-11T09:30:00+00:00", "offset-1"
        )
        after_restart = ArchiveCandidate(
            "operator:mina", "archive.import", "allowed", "2026-08-11T09:30:07+00:00", "offset-2"
        )

        service = SQLiteAuditLogService(db_path)
        manifest, first_batch = service.import_archive(manifest, [before_restart])
        self.assertEqual(len(first_batch), 1)
        service.close()

        # A real restart loses the in-memory `manifest` object above; the
        # restarted service below never receives it. It only ever reads the
        # resume point back from db_path, which is the property under test.
        restarted_service = SQLiteAuditLogService(db_path)
        self.addCleanup(restarted_service.close)

        reloaded_manifest = restarted_service.load_manifest("batch-east-17")
        self.assertIsNotNone(reloaded_manifest)
        self.assertEqual(reloaded_manifest.batch_id, "batch-east-17")
        self.assertEqual(reloaded_manifest.resume_offset, 1)
        self.assertEqual(
            reloaded_manifest.imported_content_ids, frozenset({before_restart.content_id()})
        )
        self.assertFalse(reloaded_manifest.completed)

        # Resume re-reads the archive from the start, as an interrupted
        # import would after a restart: the already-imported candidate is
        # present again alongside the one that was never imported.
        reloaded_manifest, second_batch = restarted_service.import_archive(
            reloaded_manifest, [before_restart, after_restart]
        )

        self.assertEqual(len(second_batch), 1)
        self.assertEqual(second_batch[0].event_id, after_restart.content_id())
        all_content_ids = {event.event_id for event in restarted_service.events()}
        self.assertEqual(
            all_content_ids, {before_restart.content_id(), after_restart.content_id()}
        )
        self.assertEqual(
            reloaded_manifest.imported_content_ids,
            frozenset({before_restart.content_id(), after_restart.content_id()}),
        )

    def test_load_manifest_returns_none_for_an_unknown_batch(self) -> None:
        service, _ = _make_temp_service(self)
        self.assertIsNone(service.load_manifest("batch-east-17"))


class SqliteSeparateProcessReadTests(unittest.TestCase):
    def test_events_are_durable_and_readable_from_a_separate_process(self) -> None:
        service, db_path = _make_temp_service(self)

        recorded = [
            service.record(
                "operator:mina", "role.grant", "allowed", "2026-08-11T09:30:00+00:00",
                metadata={"ticket": "A"},
            ),
            service.record(
                "operator:mina", "role.grant", "allowed", "2026-08-11T09:30:00+00:00",
                metadata={"ticket": "B"},
            ),
        ]
        # Close the writer's own connection before handing the file to a
        # separate process, so the read below cannot be seeing anything
        # still held only in this process's memory or an open transaction.
        service.close()

        child_script = (
            "import json, sys\n"
            "from auditlog.sqlite_service import SQLiteAuditLogService\n"
            "service = SQLiteAuditLogService(sys.argv[1])\n"
            "events = service.events()\n"
            "print(json.dumps([[e.sequence, e.event_id, e.actor, e.action, e.metadata] for e in events]))\n"
            "service.close()\n"
        )
        env = dict(os.environ, PYTHONPATH=str(PROJECT_ROOT))
        result = subprocess.run(
            [sys.executable, "-c", child_script, str(db_path)],
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )

        rows = json.loads(result.stdout)
        self.assertEqual(len(rows), 2)
        self.assertEqual([row[0] for row in rows], [event.sequence for event in recorded])
        self.assertEqual([row[1] for row in rows], [event.event_id for event in recorded])
        self.assertEqual([row[4] for row in rows], [{"ticket": "A"}, {"ticket": "B"}])


if __name__ == "__main__":
    unittest.main()
