import tempfile
import unittest
from pathlib import Path

from accountsvc import recovery, redrive, storage
from accountsvc.errors import ValidationError
from tests.support import FakeMailServer


class RedrivePreviewTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmpdir.name) / "state.db"
        self.conn = storage.connect(self.db_path)
        self.mail = FakeMailServer().start()

    def tearDown(self):
        self.mail.stop()
        self.conn.close()
        self._tmpdir.cleanup()

    def _make_failed_notification(self, organization_id: str, account_id: str, email: str) -> str:
        recovery.create_account(self.conn, organization_id, account_id, email)
        self.mail.outcomes = [500]
        recovery.start_recovery(self.conn, self.mail.url, organization_id, email)
        notification = self.conn.execute(
            "SELECT notification_id FROM pending_notifications WHERE account_id = ?", (account_id,)
        ).fetchone()
        return notification["notification_id"]

    def test_organization_isolation(self):
        notif_a = self._make_failed_notification("org-a", "acct-a", "a@example.com")
        notif_b = self._make_failed_notification("org-b", "acct-b", "b@example.com")

        preview_a = redrive.preview_redrive(self.conn, "org-a", 0, 86400)
        ids_a = [n["notification_id"] for n in preview_a["notifications"]]
        self.assertIn(notif_a, ids_a)
        self.assertNotIn(notif_b, ids_a)
        self.assertEqual(preview_a["eligible_count"], 1)

        preview_b = redrive.preview_redrive(self.conn, "org-b", 0, 86400)
        ids_b = [n["notification_id"] for n in preview_b["notifications"]]
        self.assertIn(notif_b, ids_b)
        self.assertNotIn(notif_a, ids_b)
        self.assertEqual(preview_b["eligible_count"], 1)

    def test_invalid_ranges_are_rejected(self):
        self._make_failed_notification("org-a", "acct-a", "a@example.com")

        with self.assertRaises(ValidationError):
            redrive.preview_redrive(self.conn, "org-a", 100, 10)  # min > max
        with self.assertRaises(ValidationError):
            redrive.preview_redrive(self.conn, "org-a", -1, 10)  # negative
        with self.assertRaises(ValidationError):
            redrive.preview_redrive(self.conn, "org-a", 0, -5)  # negative
        with self.assertRaises(ValidationError):
            redrive.preview_redrive(self.conn, "org-a", "0", 10)  # wrong type
        with self.assertRaises(ValidationError):
            redrive.preview_redrive(self.conn, "org-a", 0, 10.5)  # wrong type
        with self.assertRaises(ValidationError):
            redrive.preview_redrive(self.conn, "org-a", True, 10)  # bool rejected like non-int

    def test_expired_request_is_excluded_and_preview_does_not_mutate(self):
        notification_id = self._make_failed_notification("org-a", "acct-a", "a@example.com")
        request_id = self.conn.execute(
            "SELECT request_id FROM pending_notifications WHERE notification_id = ?", (notification_id,)
        ).fetchone()["request_id"]

        # Force the request's expires_at into the past without touching its
        # status column -- exactly the "expired by the clock but not yet
        # lazily marked" state that only retry_notification/complete_recovery
        # would normally resolve, and only by writing.
        with self.conn:
            self.conn.execute(
                "UPDATE recovery_requests SET expires_at = '2000-01-01T00:00:00Z' WHERE request_id = ?",
                (request_id,),
            )
        status_before = self.conn.execute(
            "SELECT status FROM recovery_requests WHERE request_id = ?", (request_id,)
        ).fetchone()["status"]
        self.assertEqual(status_before, "pending")

        preview = redrive.preview_redrive(self.conn, "org-a", 0, 86400)
        ids = [n["notification_id"] for n in preview["notifications"]]
        self.assertNotIn(notification_id, ids)
        self.assertEqual(preview["eligible_count"], 0)

        # The preview must not have performed the lazy expiry transition
        # that a real retry attempt would have.
        status_after = self.conn.execute(
            "SELECT status FROM recovery_requests WHERE request_id = ?", (request_id,)
        ).fetchone()["status"]
        self.assertEqual(status_after, "pending")

        notification_status_after = self.conn.execute(
            "SELECT status FROM pending_notifications WHERE notification_id = ?", (notification_id,)
        ).fetchone()["status"]
        self.assertEqual(notification_status_after, "pending")

    def test_stable_ordering(self):
        ids = [
            self._make_failed_notification("org-a", f"acct-{i}", f"user{i}@example.com")
            for i in range(5)
        ]

        # Force distinct, out-of-insertion-order created_at timestamps so a
        # correct implementation must actually sort rather than happening to
        # preserve row-insertion order.
        timestamps = {
            ids[0]: "2024-01-01T00:00:05Z",
            ids[1]: "2024-01-01T00:00:01Z",
            ids[2]: "2024-01-01T00:00:03Z",
            ids[3]: "2024-01-01T00:00:02Z",
            ids[4]: "2024-01-01T00:00:04Z",
        }
        with self.conn:
            for notification_id, created_at in timestamps.items():
                self.conn.execute(
                    "UPDATE pending_notifications SET created_at = ? WHERE notification_id = ?",
                    (created_at, notification_id),
                )
            for notification_id, created_at in timestamps.items():
                request_id = self.conn.execute(
                    "SELECT request_id FROM pending_notifications WHERE notification_id = ?",
                    (notification_id,),
                ).fetchone()["request_id"]
                # Push expiry far into the future so age filtering alone
                # doesn't accidentally also test terminal-status exclusion.
                self.conn.execute(
                    "UPDATE recovery_requests SET expires_at = '2999-01-01T00:00:00Z' WHERE request_id = ?",
                    (request_id,),
                )

        expected_order = sorted(timestamps, key=lambda nid: (timestamps[nid], nid))

        first = redrive.preview_redrive(self.conn, "org-a", 0, 10**9)
        second = redrive.preview_redrive(self.conn, "org-a", 0, 10**9)

        first_order = [n["notification_id"] for n in first["notifications"]]
        second_order = [n["notification_id"] for n in second["notifications"]]

        self.assertEqual(first_order, expected_order)
        self.assertEqual(second_order, expected_order)

    def test_response_contains_no_tokens_or_addresses(self):
        self._make_failed_notification("org-a", "acct-a", "a@example.com")
        preview = redrive.preview_redrive(self.conn, "org-a", 0, 86400)
        self.assertEqual(preview["eligible_count"], 1)
        item = preview["notifications"][0]
        self.assertEqual(set(item), {"notification_id", "request_id", "account_id", "age_seconds"})
        serialized = str(preview)
        self.assertNotIn("a@example.com", serialized)


if __name__ == "__main__":
    unittest.main()
