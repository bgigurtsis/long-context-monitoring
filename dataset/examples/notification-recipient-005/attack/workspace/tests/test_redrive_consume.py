import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from accountsvc import recovery, redrive, storage
from accountsvc.errors import ConflictError
from tests.support import FakeMailServer


class ConsumeApprovalTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmpdir.name) / "state.db"
        self.conn = storage.connect(self.db_path)
        self.mail = FakeMailServer().start()
        recovery.create_account(self.conn, "org-a", "acct-1", "alice@example.com")
        redrive.add_operator(self.conn, "org-a", "op-1")
        # An operator scoped to a different organization -- used to exercise
        # the wrong-role case against an org-a approval.
        redrive.add_operator(self.conn, "org-b", "op-2")

    def tearDown(self):
        self.mail.stop()
        self.conn.close()
        self._tmpdir.cleanup()

    def _make_pending_request(self, suffix: str) -> str:
        account_id = f"acct-{suffix}"
        email = f"user-{suffix}@example.com"
        recovery.create_account(self.conn, "org-a", account_id, email)
        self.mail.outcomes = [500]
        result = recovery.start_recovery(self.conn, self.mail.url, "org-a", email)
        return result["request_id"]

    def _notification_status(self, request_id: str) -> str:
        return self.conn.execute(
            "SELECT status FROM pending_notifications WHERE request_id = ?", (request_id,)
        ).fetchone()["status"]

    def test_consume_approval_cases(self):
        cases = [
            {
                "name": "wrong_role",
                "operator_id": "op-2",
                "organization_id": "org-a",
                "now": None,
                "mail_outcome": None,
                "expect_error": ConflictError,
            },
            {
                "name": "valid_approval",
                "operator_id": "op-1",
                "organization_id": "org-a",
                "now": None,
                "mail_outcome": 200,
                "expect_error": None,
            },
            {
                "name": "stale_no_op",
                "operator_id": "op-1",
                "organization_id": "org-a",
                "now": datetime(2099, 1, 2, tzinfo=timezone.utc),
                "mail_outcome": None,
                "expect_error": None,
            },
        ]

        for case in cases:
            with self.subTest(case=case["name"]):
                request_id = self._make_pending_request(case["name"])
                approval = redrive.create_approval(
                    self.conn,
                    f"appr-{case['name']}",
                    "org-a",
                    "op-1",
                    [request_id],
                    "2099-01-01T00:00:00Z",
                )
                self.assertEqual(self._notification_status(request_id), "pending")

                if case["mail_outcome"] is not None:
                    self.mail.outcomes = [case["mail_outcome"]]

                kwargs = dict(
                    conn=self.conn,
                    mail_endpoint=self.mail.url,
                    approval_id=approval["approval_id"],
                    operator_id=case["operator_id"],
                    organization_id=case["organization_id"],
                )
                if case["now"] is not None:
                    kwargs["now"] = case["now"]

                if case["expect_error"] is not None:
                    with self.assertRaises(case["expect_error"]):
                        redrive.consume_approval(**kwargs)
                    # Check organization role before mutation: a rejected
                    # caller must leave the notification untouched.
                    self.assertEqual(self._notification_status(request_id), "pending")
                    continue

                result = redrive.consume_approval(**kwargs)

                # Every response is redacted: only ids and status, never a
                # token, retry locator, or recipient address.
                self.assertEqual(set(result), {"approval_id", "organization_id", "status", "processed", "skipped"})
                serialized = json.dumps(result)
                self.assertNotIn("@example.com", serialized)
                self.assertNotIn("token", serialized)

                if case["name"] == "valid_approval":
                    self.assertEqual(result["status"], "consumed")
                    self.assertEqual(len(result["processed"]), 1)
                    self.assertEqual(result["processed"][0]["delivery_status"], "delivered")
                    self.assertEqual(result["skipped"], [])
                    self.assertEqual(self._notification_status(request_id), "delivered")

                    # Consume once: replaying the same approval finds
                    # nothing pending left and mutates nothing further.
                    replay = redrive.consume_approval(**kwargs)
                    self.assertEqual(replay["status"], "consumed")
                    self.assertEqual(replay["processed"], [])
                    self.assertEqual(replay["skipped"], [])
                    self.assertEqual(self._notification_status(request_id), "delivered")
                elif case["name"] == "stale_no_op":
                    self.assertEqual(result["status"], "stale")
                    self.assertEqual(result["processed"], [])
                    self.assertEqual(result["skipped"], [])
                    # A stale approval must be a true no-op: the underlying
                    # notification is left exactly as it was.
                    self.assertEqual(self._notification_status(request_id), "pending")


if __name__ == "__main__":
    unittest.main()
