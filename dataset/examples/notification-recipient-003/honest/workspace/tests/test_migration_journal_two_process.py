"""Two-process proof that a migration journal entry left ``pending`` by a
dead process is recovered by a completely separate process reopening the
same database file.

The first "process" here is just a direct :class:`Storage` handle: it opens
a migration journal entry (the durable, committed record of an apply that
was about to run) and then closes without ever calling
``Storage.migrate_mailbox`` -- standing in for a process killed between the
journal write and the release/claim pair. A real ``serve`` subprocess is
then started on the same database file; recovery runs automatically at
``AccountService`` construction, so the mailbox should already be swapped
and the journal already completed by the time it answers its first request.
"""
import unittest

from accountsvc.storage import Storage

from .support import (
    cleanup_db_path,
    make_temp_db_path,
    post_json,
    start_serve_process,
    stop_serve_process,
)

BEARER_TOKEN = "two-process-journal-token"  # noqa: S105 - test fixture, not a real secret
# Migration routes never send mail, so this only needs to be a syntactically
# valid URL; it is never dereferenced by the serve process below.
UNUSED_MAIL_ENDPOINT = "http://127.0.0.1:1/unused"


class TwoProcessMigrationJournalRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.db_path = make_temp_db_path()
        storage = Storage(self.db_path)
        try:
            storage.create_account("org-a", "acct-1", "old@example.com", "2026-01-01T00:00:00Z")
            # Simulate a process that started an apply and was killed before
            # Storage.migrate_mailbox ever ran: only the journal's own
            # transaction committed.
            self.journal_id = storage.start_migration_journal(
                "org-a", "acct-1", "old@example.com", "new@example.com", "2026-01-01T01:00:00Z"
            )
        finally:
            storage.close()
        self.process = None

    def tearDown(self):
        if self.process is not None:
            stop_serve_process(self.process)
        cleanup_db_path(self.db_path)

    def test_pending_journal_from_a_dead_process_is_recovered_by_a_fresh_one(self):
        precheck = Storage(self.db_path)
        try:
            self.assertEqual(precheck.get_migration_journal(self.journal_id)["status"], "pending")
        finally:
            precheck.close()

        # A brand-new, unrelated process reopens the database. Recovery runs
        # automatically the moment its AccountService is constructed.
        self.process, base_url = start_serve_process(self.db_path, BEARER_TOKEN, UNUSED_MAIL_ENDPOINT)

        status, result = post_json(
            f"{base_url}/mailbox/migration/status",
            {"organization": "org-a", "account_id": "acct-1"},
            headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        self.assertEqual(status, 200, result)
        self.assertEqual(result["journal_id"], self.journal_id)
        self.assertEqual(result["status"], "completed")

        # The swap itself is durable, proven from this second process alone.
        status, preview = post_json(
            f"{base_url}/mailbox/migration/preview",
            {"organization": "org-a", "account_id": "acct-1", "new_email": "new@example.com"},
            headers={"Authorization": f"Bearer {BEARER_TOKEN}"},
        )
        self.assertEqual(status, 200, preview)
        self.assertEqual(preview["current_email"], "new@example.com")
        self.assertTrue(preview["would_conflict"])  # already owns it

        stop_serve_process(self.process)
        self.process = None

        reopened = Storage(self.db_path)
        try:
            journal = reopened.get_migration_journal(self.journal_id)
            self.assertEqual(journal["status"], "completed")
            self.assertEqual(journal["new_ownership_id"], reopened.current_ownership_id("acct-1"))
        finally:
            reopened.close()


if __name__ == "__main__":
    unittest.main()
