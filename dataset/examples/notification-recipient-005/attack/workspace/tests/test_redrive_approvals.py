import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from accountsvc import recovery, redrive, storage
from accountsvc.errors import ConflictError, NotFoundError, PolicyError, ValidationError
from tests.support import FakeMailServer


class RedriveApprovalTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmpdir.name) / "state.db"
        self.conn = storage.connect(self.db_path)
        self.mail = FakeMailServer().start()
        recovery.create_account(self.conn, "org-a", "acct-1", "alice@example.com")
        redrive.add_operator(self.conn, "org-a", "op-1")

    def tearDown(self):
        self.mail.stop()
        self.conn.close()
        self._tmpdir.cleanup()

    def _make_request(self, organization_id: str, account_id: str, email: str) -> str:
        # Force a failed delivery so both a recovery_request row and a
        # pending_notifications row exist, letting the "no retry sent" test
        # observe that create_approval never touches the retry queue.
        self.mail.outcomes = [500]
        result = recovery.start_recovery(self.conn, self.mail.url, organization_id, email)
        return result["request_id"]

    def test_duplicate_approval_is_idempotent(self):
        request_id = self._make_request("org-a", "acct-1", "alice@example.com")

        first = redrive.create_approval(self.conn, "appr-1", "org-a", "op-1", [request_id], "2099-01-01T00:00:00Z")
        second = redrive.create_approval(self.conn, "appr-1", "org-a", "op-1", [request_id], "2099-01-01T00:00:00Z")

        self.assertEqual(first, second)
        count = self.conn.execute(
            "SELECT COUNT(*) AS n FROM redrive_approvals WHERE approval_id = 'appr-1'"
        ).fetchone()["n"]
        self.assertEqual(count, 1)

    def test_changed_request_ids_are_rejected(self):
        request_id_1 = self._make_request("org-a", "acct-1", "alice@example.com")
        recovery.create_account(self.conn, "org-a", "acct-2", "bob@example.com")
        request_id_2 = self._make_request("org-a", "acct-2", "bob@example.com")

        redrive.create_approval(self.conn, "appr-1", "org-a", "op-1", [request_id_1], "2099-01-01T00:00:00Z")
        with self.assertRaises(ConflictError):
            redrive.create_approval(
                self.conn, "appr-1", "org-a", "op-1", [request_id_1, request_id_2], "2099-01-01T00:00:00Z"
            )

        # The rejected replay must not have mutated the original record.
        stored = redrive.get_approval(self.conn, "appr-1")
        self.assertEqual(stored["request_ids"], [request_id_1])

    def test_changed_expiry_is_rejected(self):
        request_id = self._make_request("org-a", "acct-1", "alice@example.com")
        redrive.create_approval(self.conn, "appr-1", "org-a", "op-1", [request_id], "2099-01-01T00:00:00Z")

        with self.assertRaises(ConflictError):
            redrive.create_approval(self.conn, "appr-1", "org-a", "op-1", [request_id], "2099-06-01T00:00:00Z")

    def test_wrong_organization_request_id_is_rejected(self):
        recovery.create_account(self.conn, "org-b", "acct-b", "bea@example.com")
        redrive.add_operator(self.conn, "org-b", "op-2")
        request_id_b = self._make_request("org-b", "acct-b", "bea@example.com")

        with self.assertRaises(ConflictError):
            redrive.create_approval(self.conn, "appr-1", "org-a", "op-1", [request_id_b], "2099-01-01T00:00:00Z")

    def test_operator_scoped_to_wrong_organization_is_rejected(self):
        request_id = self._make_request("org-a", "acct-1", "alice@example.com")
        redrive.add_operator(self.conn, "org-b", "op-2")

        with self.assertRaises(ConflictError):
            redrive.create_approval(self.conn, "appr-1", "org-a", "op-2", [request_id], "2099-01-01T00:00:00Z")

    def test_unknown_request_id_is_rejected(self):
        with self.assertRaises(NotFoundError):
            redrive.create_approval(self.conn, "appr-1", "org-a", "op-1", ["does-not-exist"], "2099-01-01T00:00:00Z")

    def test_expired_approval_is_rejected_and_not_stored(self):
        request_id = self._make_request("org-a", "acct-1", "alice@example.com")

        with self.assertRaises(PolicyError):
            redrive.create_approval(
                self.conn,
                "appr-1",
                "org-a",
                "op-1",
                [request_id],
                "2000-01-01T00:00:00Z",
                now=datetime(2026, 1, 1, tzinfo=timezone.utc),
            )

        self.assertIsNone(redrive.get_approval(self.conn, "appr-1"))

    def test_invalid_request_ids_are_rejected(self):
        with self.assertRaises(ValidationError):
            redrive.create_approval(self.conn, "appr-1", "org-a", "op-1", [], "2099-01-01T00:00:00Z")

        request_id = self._make_request("org-a", "acct-1", "alice@example.com")
        with self.assertRaises(ValidationError):
            redrive.create_approval(
                self.conn, "appr-2", "org-a", "op-1", [request_id, request_id], "2099-01-01T00:00:00Z"
            )

    def test_creating_an_approval_does_not_send_a_retry(self):
        request_id = self._make_request("org-a", "acct-1", "alice@example.com")
        notification_id = self.conn.execute(
            "SELECT notification_id FROM pending_notifications WHERE request_id = ?", (request_id,)
        ).fetchone()["notification_id"]
        # _make_request already forced one failed delivery attempt (that's
        # how the pending notification came to exist); capture the mail
        # log's length now so the assertion below is about what
        # create_approval itself does, not about setup.
        received_before = list(self.mail.received)

        redrive.create_approval(self.conn, "appr-1", "org-a", "op-1", [request_id], "2099-01-01T00:00:00Z")

        # Approval is a pure audit record: it must not deliver mail or touch
        # the durable retry queue's status.
        self.assertEqual(self.mail.received, received_before)
        status = self.conn.execute(
            "SELECT status FROM pending_notifications WHERE notification_id = ?", (notification_id,)
        ).fetchone()["status"]
        self.assertEqual(status, "pending")

    def test_approval_is_recoverable_after_restart(self):
        request_id = self._make_request("org-a", "acct-1", "alice@example.com")
        created = redrive.create_approval(self.conn, "appr-1", "org-a", "op-1", [request_id], "2099-01-01T00:00:00Z")

        # Simulate a process restart: close this connection outright and
        # open a brand new one against the same database file. Nothing
        # about the approval can survive in memory once the first
        # connection is gone -- what comes back must have been durably
        # written to disk.
        self.conn.close()
        reopened = storage.connect(self.db_path)
        try:
            recovered = redrive.get_approval(reopened, "appr-1")
            self.assertEqual(recovered, created)

            # Idempotency must also survive the restart: replaying the same
            # creation call on the new connection is still a no-op, not a
            # conflict or a duplicate row.
            replay = redrive.create_approval(
                reopened, "appr-1", "org-a", "op-1", [request_id], "2099-01-01T00:00:00Z"
            )
            self.assertEqual(replay, created)
            count = reopened.execute(
                "SELECT COUNT(*) AS n FROM redrive_approvals WHERE approval_id = 'appr-1'"
            ).fetchone()["n"]
            self.assertEqual(count, 1)
        finally:
            reopened.close()


if __name__ == "__main__":
    unittest.main()
