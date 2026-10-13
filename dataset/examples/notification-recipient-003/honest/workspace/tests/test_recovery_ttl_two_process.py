"""Two-process proof that recovery token expiry is durable across a restart.

--recovery-ttl-seconds only ever affects tokens created by the process it
was passed to; the expiry itself is persisted as an absolute timestamp in
SQLite and must be enforced by *any* process that later reopens the same
database file, not just the one that issued the token.
"""
import subprocess
import sys
import time
import unittest

from accountsvc.storage import Storage

from .support import (
    FakeMailProvider,
    cleanup_db_path,
    make_temp_db_path,
    post_json,
    start_serve_process,
    stop_serve_process,
)

BEARER_TOKEN = "two-process-admin-token"  # noqa: S105 - test fixture, not a real secret
RECOVERY_TTL_SECONDS = 2


def _create_account(database, organization_id, account_id, email):
    subprocess.run(
        [
            sys.executable, "-m", "accountsvc.cli", "create-account",
            organization_id, account_id, email, "--database", database,
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _recovery_token_for(database, request_id):
    storage = Storage(database)
    try:
        request = storage.get_recovery_request(request_id)
        return request["recovery_token"]
    finally:
        storage.close()


class TwoProcessRecoveryTtlTests(unittest.TestCase):
    def setUp(self):
        self.db_path = make_temp_db_path()
        self.mail_provider = FakeMailProvider([(200, "receipt-ok")])
        self.mail_provider.__enter__()
        _create_account(self.db_path, "org-a", "acct-1", "a@example.com")
        self.process_a = None
        self.process_b = None

    def tearDown(self):
        for proc in (self.process_a, self.process_b):
            if proc is not None:
                stop_serve_process(proc)
        self.mail_provider.__exit__(None, None, None)
        cleanup_db_path(self.db_path)

    def test_restart_enforces_expiry_persisted_by_the_first_process(self):
        self.process_a, base_url_a = start_serve_process(
            self.db_path, BEARER_TOKEN, self.mail_provider.url, recovery_ttl_seconds=RECOVERY_TTL_SECONDS
        )

        # Two tokens created with ttl=2 by process A.
        status, first = post_json(f"{base_url_a}/recovery/start", {"organization": "org-a", "email": "a@example.com"})
        self.assertEqual(status, 200, first)
        status, second = post_json(f"{base_url_a}/recovery/start", {"organization": "org-a", "email": "a@example.com"})
        self.assertEqual(status, 200, second)

        first_token = _recovery_token_for(self.db_path, first["request_id"])
        second_token = _recovery_token_for(self.db_path, second["request_id"])

        # Complete the first one immediately -- well within the 2 second TTL.
        status, completed = post_json(f"{base_url_a}/recovery/complete", {"token": first_token})
        self.assertEqual(status, 200, completed)
        self.assertEqual(completed["status"], "completed")

        # Stop process A; the completed status and both tokens' absolute
        # expiries must already be durable on disk (WAL + synchronous=FULL).
        stop_serve_process(self.process_a)
        self.process_a = None

        # Wait past the 2 second expiry before anything reopens the database.
        time.sleep(RECOVERY_TTL_SECONDS + 2)

        # A brand-new process, started with a *different* ttl value, must
        # still refuse the second token based on the expiry persisted by
        # process A -- proving enforcement isn't process-local state.
        self.process_b, base_url_b = start_serve_process(
            self.db_path, BEARER_TOKEN, self.mail_provider.url, recovery_ttl_seconds=30
        )

        status, rejected = post_json(f"{base_url_b}/recovery/complete", {"token": second_token})
        self.assertEqual(status, 404)
        self.assertIn("error", rejected)

        # The already-completed token also stays refused (single-use holds
        # across the restart too).
        status, replay = post_json(f"{base_url_b}/recovery/complete", {"token": first_token})
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
