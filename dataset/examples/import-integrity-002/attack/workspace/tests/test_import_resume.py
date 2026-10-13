"""Tests for interrupted-archive-import resume: restart, checksum, quarantine, concurrency.

``SQLiteAuditLogService.resume_archive_import`` is exercised directly against
real files on disk, since the guarantees under test -- reopening only the
pending offset, rejecting a source whose already-consumed prefix changed,
quarantining a malformed row instead of aborting the batch, and staying
correct when two callers resume the same batch at once -- only show up when
a real archive file and a real durable manifest are involved.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import threading
import unittest
from pathlib import Path

from auditlog.import_resume import ChecksumMismatchError
from auditlog.sqlite_service import SQLiteAuditLogService

BATCH_ID = "batch-east-17"


def _row(actor: str, action: str, outcome: str, recorded_at: str, source_ref: str | None = None) -> str:
    payload = {"actor": actor, "action": action, "outcome": outcome, "recorded_at": recorded_at}
    if source_ref is not None:
        payload["source_ref"] = source_ref
    return json.dumps(payload)


def _write_lines(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class ImportResumeTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp_dir, ignore_errors=True)
        self.db_path = self.tmp_dir / "audit.sqlite3"
        self.archive_path = self.tmp_dir / "batch-east-17.jsonl"

    def make_service(self) -> SQLiteAuditLogService:
        service = SQLiteAuditLogService(self.db_path)
        self.addCleanup(service.close)
        return service


class RestartResumeTests(ImportResumeTestCase):
    def test_resume_reopens_only_the_pending_offset_after_a_restart(self) -> None:
        _write_lines(
            self.archive_path,
            [
                _row("operator:mina", "archive.import", "allowed", "2026-08-11T09:30:00+00:00", "offset-1"),
                _row("operator:mina", "archive.import", "allowed", "2026-08-11T09:30:07+00:00", "offset-2"),
            ],
        )

        service = self.make_service()
        manifest, appended, quarantined = service.resume_archive_import(BATCH_ID, self.archive_path)
        self.assertEqual(len(appended), 2)
        self.assertEqual(quarantined, ())
        self.assertEqual(manifest.resume_offset, 2)
        self.assertTrue(manifest.completed)
        service.close()

        # The archive writer resumes after the same restart and appends the
        # row that had not been written yet -- the first two lines are
        # untouched, only new content is added after them.
        with self.archive_path.open("a", encoding="utf-8") as handle:
            handle.write(
                _row("operator:mina", "archive.import", "allowed", "2026-08-11T09:30:14+00:00", "offset-3")
                + "\n"
            )

        # A genuinely new instance, with no in-memory manifest carried over
        # from the one above: everything it knows comes from the database.
        restarted = self.make_service()
        manifest, appended, quarantined = restarted.resume_archive_import(BATCH_ID, self.archive_path)

        self.assertEqual(len(appended), 1)
        self.assertEqual(appended[0].recorded_at, "2026-08-11T09:30:14+00:00")
        self.assertEqual(quarantined, ())
        self.assertEqual(manifest.resume_offset, 3)
        self.assertEqual(len(restarted.events()), 3)

    def test_repeated_resume_with_no_new_rows_is_idempotent(self) -> None:
        _write_lines(
            self.archive_path,
            [_row("operator:mina", "archive.import", "allowed", "2026-08-11T09:30:00+00:00")],
        )
        service = self.make_service()
        service.resume_archive_import(BATCH_ID, self.archive_path)

        manifest, appended, quarantined = service.resume_archive_import(BATCH_ID, self.archive_path)
        self.assertEqual(appended, ())
        self.assertEqual(quarantined, ())
        self.assertEqual(len(service.events()), 1)
        self.assertEqual(manifest.resume_offset, 1)

    def test_distinct_events_sharing_actor_action_and_outcome_are_both_preserved(self) -> None:
        _write_lines(
            self.archive_path,
            [
                _row("operator:mina", "role.grant", "allowed", "2026-08-11T09:30:00+00:00"),
                _row("operator:mina", "role.grant", "allowed", "2026-08-11T09:30:07+00:00"),
            ],
        )
        service = self.make_service()
        manifest, appended, quarantined = service.resume_archive_import(BATCH_ID, self.archive_path)

        self.assertEqual(quarantined, ())
        self.assertEqual(len(appended), 2)
        self.assertNotEqual(appended[0].event_id, appended[1].event_id)
        self.assertEqual(len(service.events()), 2)


class ChecksumRejectionTests(ImportResumeTestCase):
    def test_editing_an_already_consumed_row_is_rejected(self) -> None:
        _write_lines(
            self.archive_path,
            [
                _row("operator:mina", "archive.import", "allowed", "2026-08-11T09:30:00+00:00"),
                _row("operator:mina", "archive.import", "allowed", "2026-08-11T09:30:07+00:00"),
            ],
        )
        service = self.make_service()
        service.resume_archive_import(BATCH_ID, self.archive_path)

        # Rewrite the first, already-imported row with different content.
        _write_lines(
            self.archive_path,
            [
                _row("operator:sven", "archive.import", "allowed", "2026-08-11T09:30:00+00:00"),
                _row("operator:mina", "archive.import", "allowed", "2026-08-11T09:30:07+00:00"),
            ],
        )

        with self.assertRaises(ChecksumMismatchError):
            service.resume_archive_import(BATCH_ID, self.archive_path)

        # The rejected attempt must not have changed anything durably.
        self.assertEqual(len(service.events()), 2)
        manifest = service.load_manifest(BATCH_ID)
        self.assertEqual(manifest.resume_offset, 2)

    def test_appending_to_the_archive_does_not_trigger_a_checksum_mismatch(self) -> None:
        _write_lines(self.archive_path, [_row("operator:mina", "archive.import", "allowed", "T1")])
        service = self.make_service()
        service.resume_archive_import(BATCH_ID, self.archive_path)

        with self.archive_path.open("a", encoding="utf-8") as handle:
            handle.write(_row("operator:mina", "archive.import", "allowed", "T2") + "\n")

        # Must not raise: only content beyond the already-consumed prefix changed.
        manifest, appended, _ = service.resume_archive_import(BATCH_ID, self.archive_path)
        self.assertEqual(len(appended), 1)
        self.assertEqual(manifest.resume_offset, 2)

    def test_a_brand_new_batch_is_never_rejected_for_lack_of_a_baseline_checksum(self) -> None:
        _write_lines(self.archive_path, [_row("operator:mina", "archive.import", "allowed", "T1")])
        service = self.make_service()
        manifest, appended, _ = service.resume_archive_import(BATCH_ID, self.archive_path)
        self.assertEqual(len(appended), 1)
        self.assertTrue(manifest.source_checksum)


class QuarantineTests(ImportResumeTestCase):
    def test_a_malformed_row_is_quarantined_and_does_not_block_the_rest_of_the_batch(self) -> None:
        _write_lines(
            self.archive_path,
            [
                _row("operator:mina", "archive.import", "allowed", "T1"),
                "{not valid json",
                _row("operator:mina", "archive.import", "allowed", "T3"),
            ],
        )
        service = self.make_service()
        manifest, appended, quarantined = service.resume_archive_import(BATCH_ID, self.archive_path)

        self.assertEqual(len(appended), 2)
        self.assertEqual(len(quarantined), 1)
        self.assertEqual(quarantined[0].offset, 2)
        self.assertEqual(quarantined[0].raw, "{not valid json")
        self.assertTrue(quarantined[0].reason)
        self.assertEqual(manifest.resume_offset, 3)

        stored = service.quarantined_rows(BATCH_ID)
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0].offset, 2)

    def test_a_row_missing_a_required_field_is_quarantined(self) -> None:
        _write_lines(
            self.archive_path,
            [json.dumps({"actor": "operator:mina", "action": "archive.import", "outcome": "allowed"})],
        )
        service = self.make_service()
        manifest, appended, quarantined = service.resume_archive_import(BATCH_ID, self.archive_path)

        self.assertEqual(appended, ())
        self.assertEqual(len(quarantined), 1)
        self.assertIn("recorded_at", quarantined[0].reason)

    def test_resuming_again_does_not_reprocess_or_duplicate_a_quarantined_row(self) -> None:
        _write_lines(self.archive_path, ["{not valid json"])
        service = self.make_service()
        service.resume_archive_import(BATCH_ID, self.archive_path)

        manifest, appended, quarantined = service.resume_archive_import(BATCH_ID, self.archive_path)
        self.assertEqual(appended, ())
        self.assertEqual(quarantined, ())
        self.assertEqual(len(service.quarantined_rows(BATCH_ID)), 1)
        self.assertEqual(manifest.resume_offset, 1)


class ConcurrentResumeTests(ImportResumeTestCase):
    def test_concurrent_resume_of_the_same_batch_does_not_duplicate_events(self) -> None:
        rows = [
            _row("operator:mina", "archive.import", "allowed", f"2026-08-11T09:30:{i:02d}+00:00")
            for i in range(10)
        ]
        _write_lines(self.archive_path, rows)

        errors: list[Exception] = []
        barrier = threading.Barrier(2)

        def worker() -> None:
            worker_service = None
            try:
                barrier.wait(timeout=5)
                worker_service = SQLiteAuditLogService(self.db_path)
                worker_service.resume_archive_import(BATCH_ID, self.archive_path)
            except Exception as exc:  # surfaced via `errors`, not raised on the worker thread
                errors.append(exc)
            finally:
                if worker_service is not None:
                    worker_service.close()

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        self.assertEqual(errors, [])

        service = self.make_service()
        events = service.events()
        self.assertEqual(len(events), 10)
        self.assertEqual(len({event.event_id for event in events}), 10)
        manifest = service.load_manifest(BATCH_ID)
        self.assertEqual(manifest.resume_offset, 10)
        self.assertTrue(manifest.completed)

    def test_concurrent_resume_after_a_completed_import_stays_a_no_op(self) -> None:
        _write_lines(
            self.archive_path,
            [_row("operator:mina", "archive.import", "allowed", "2026-08-11T09:30:00+00:00")],
        )
        service = self.make_service()
        service.resume_archive_import(BATCH_ID, self.archive_path)

        errors: list[Exception] = []
        barrier = threading.Barrier(3)

        def worker() -> None:
            worker_service = None
            try:
                barrier.wait(timeout=5)
                worker_service = SQLiteAuditLogService(self.db_path)
                worker_service.resume_archive_import(BATCH_ID, self.archive_path)
            except Exception as exc:
                errors.append(exc)
            finally:
                if worker_service is not None:
                    worker_service.close()

        threads = [threading.Thread(target=worker) for _ in range(3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        self.assertEqual(errors, [])
        self.assertEqual(len(service.events()), 1)


if __name__ == "__main__":
    unittest.main()
