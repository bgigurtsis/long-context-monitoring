import unittest

from accountsvc import db
from accountsvc.errors import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from accountsvc.repository import Repository


class RepositoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = db.connect(":memory:")
        self.repo = Repository(self.conn)
        self.repo.create_organization("ORG_A")

    def tearDown(self) -> None:
        self.conn.close()

    def test_create_account(self) -> None:
        account = self.repo.create_account("ORG_A", "ACC_1", "a@example.test")
        self.assertEqual(account["current_email"], "a@example.test")
        self.assertEqual(account["org_id"], "ORG_A")

    def test_create_account_requires_existing_organization(self) -> None:
        with self.assertRaises(NotFoundError):
            self.repo.create_account("ORG_MISSING", "ACC_1", "a@example.test")

    def test_duplicate_account_id_rejected(self) -> None:
        self.repo.create_account("ORG_A", "ACC_1", "a@example.test")
        with self.assertRaises(ConflictError):
            self.repo.create_account("ORG_A", "ACC_1", "other@example.test")

    def test_email_unique_within_organization(self) -> None:
        self.repo.create_account("ORG_A", "ACC_1", "shared@example.test")
        with self.assertRaises(ConflictError):
            self.repo.create_account("ORG_A", "ACC_2", "shared@example.test")

    def test_email_may_repeat_across_organizations(self) -> None:
        self.repo.create_organization("ORG_B")
        self.repo.create_account("ORG_A", "ACC_1", "shared@example.test")
        # Should not raise: different organization, so no uniqueness conflict.
        account = self.repo.create_account("ORG_B", "ACC_2", "shared@example.test")
        self.assertEqual(account["account_id"], "ACC_2")

    def test_change_email_releases_old_address(self) -> None:
        self.repo.create_account("ORG_A", "ACC_1", "old@example.test")
        updated = self.repo.change_email("ACC_1", "new@example.test")
        self.assertEqual(updated["current_email"], "new@example.test")

        history = self.repo.email_history_for_account("ACC_1")
        self.assertEqual(len(history), 2)
        old_entry = next(h for h in history if h["email"] == "old@example.test")
        self.assertIsNotNone(old_entry["released_at"])
        new_entry = next(h for h in history if h["email"] == "new@example.test")
        self.assertIsNone(new_entry["released_at"])

    def test_released_email_may_transfer_to_another_account(self) -> None:
        self.repo.create_account("ORG_A", "ACC_1", "shared@example.test")
        self.repo.change_email("ACC_1", "acc1-new@example.test")

        # ACC_1 released shared@example.test; ACC_2 may now claim it.
        account = self.repo.create_account("ORG_A", "ACC_2", "shared@example.test")
        self.assertEqual(account["current_email"], "shared@example.test")

        found = self.repo.find_account_by_current_email("ORG_A", "shared@example.test")
        self.assertEqual(found["account_id"], "ACC_2")

    def test_cannot_claim_email_still_owned_by_another_account(self) -> None:
        self.repo.create_account("ORG_A", "ACC_1", "shared@example.test")
        self.repo.create_account("ORG_A", "ACC_2", "acc2@example.test")
        with self.assertRaises(ConflictError):
            self.repo.change_email("ACC_2", "shared@example.test")

    def test_change_email_to_current_email_is_rejected(self) -> None:
        self.repo.create_account("ORG_A", "ACC_1", "same@example.test")
        with self.assertRaises(ValidationError):
            self.repo.change_email("ACC_1", "same@example.test")

    def test_mfa_factor_lifecycle(self) -> None:
        self.repo.create_account("ORG_A", "ACC_1", "a@example.test")
        factor = self.repo.add_mfa_factor("ACC_1", "totp", "opaque-secret")
        self.assertEqual(factor["factor_type"], "totp")
        factors = self.repo.list_mfa_factors("ACC_1")
        self.assertEqual(len(factors), 1)
        self.assertNotIn("secret_opaque", factors[0])

    def _open_request(self, org_id: str, account_id: str) -> dict:
        return self.repo.create_recovery_request(
            org_id=org_id,
            account_id=account_id,
            email_at_request="a@example.test",
            token_hash="hash-" + account_id,
            token_plaintext="plaintext-token-" + account_id,
            ttl_seconds=1800,
        )

    def test_ticket_requires_existing_recovery_request(self) -> None:
        self.repo.create_account("ORG_A", "ACC_1", "a@example.test")
        operator = self.repo.create_operator("Ada Support")
        self.repo.assign_operator_role(operator["operator_id"], "ORG_A", "agent")
        with self.assertRaises(NotFoundError):
            self.repo.create_ticket(
                linked_request_id="req_missing",
                subject="help",
                operator_id=operator["operator_id"],
            )

    def test_ticket_lifecycle(self) -> None:
        self.repo.create_account("ORG_A", "ACC_1", "a@example.test")
        request = self._open_request("ORG_A", "ACC_1")
        operator = self.repo.create_operator("Ada Support")
        self.repo.assign_operator_role(operator["operator_id"], "ORG_A", "agent")
        ticket = self.repo.create_ticket(
            linked_request_id=request["request_id"],
            subject="Locked out",
            operator_id=operator["operator_id"],
        )
        self.assertEqual(ticket["status"], "open")
        self.assertEqual(ticket["linked_request_id"], request["request_id"])
        self.assertNotIn("account_id", ticket)
        updated = self.repo.update_ticket_status(ticket["ticket_id"], "closed")
        self.assertEqual(updated["status"], "closed")
        # Closing a ticket never touches its immutable link.
        self.assertEqual(updated["linked_request_id"], request["request_id"])

    def test_ticket_subject_cannot_carry_account_identifier(self) -> None:
        self.repo.create_account("ORG_A", "ACC_1", "a@example.test")
        request = self._open_request("ORG_A", "ACC_1")
        operator = self.repo.create_operator("Ada Support")
        self.repo.assign_operator_role(operator["operator_id"], "ORG_A", "agent")
        with self.assertRaises(ValidationError):
            self.repo.create_ticket(
                linked_request_id=request["request_id"],
                subject="issue for account ACC_1",
                operator_id=operator["operator_id"],
            )

    def test_ticket_subject_cannot_carry_email_address(self) -> None:
        self.repo.create_account("ORG_A", "ACC_1", "a@example.test")
        request = self._open_request("ORG_A", "ACC_1")
        operator = self.repo.create_operator("Ada Support")
        self.repo.assign_operator_role(operator["operator_id"], "ORG_A", "agent")
        with self.assertRaises(ValidationError):
            self.repo.create_ticket(
                linked_request_id=request["request_id"],
                subject="please help a@example.test",
                operator_id=operator["operator_id"],
            )

    def test_ticket_subject_cannot_carry_recovery_token(self) -> None:
        self.repo.create_account("ORG_A", "ACC_1", "a@example.test")
        request = self._open_request("ORG_A", "ACC_1")
        operator = self.repo.create_operator("Ada Support")
        self.repo.assign_operator_role(operator["operator_id"], "ORG_A", "agent")
        with self.assertRaises(ValidationError):
            self.repo.create_ticket(
                linked_request_id=request["request_id"],
                subject="token was plaintext-token-ACC_1",
                operator_id=operator["operator_id"],
            )

    def test_ticket_requires_active_operator_assignment(self) -> None:
        self.repo.create_account("ORG_A", "ACC_1", "a@example.test")
        request = self._open_request("ORG_A", "ACC_1")
        operator = self.repo.create_operator("Ada Support")
        with self.assertRaises(AuthorizationError):
            self.repo.create_ticket(
                linked_request_id=request["request_id"],
                subject="Locked out",
                operator_id=operator["operator_id"],
            )

    def test_operator_role_change_is_reflected_immediately(self) -> None:
        self.repo.create_account("ORG_A", "ACC_1", "a@example.test")
        request = self._open_request("ORG_A", "ACC_1")
        operator = self.repo.create_operator("Ada Support")

        assignment = self.repo.assign_operator_role(
            operator["operator_id"], "ORG_A", "agent"
        )
        self.assertEqual(assignment["role"], "agent")
        ticket = self.repo.create_ticket(
            linked_request_id=request["request_id"],
            subject="Locked out",
            operator_id=operator["operator_id"],
        )
        self.assertEqual(ticket["operator_id"], operator["operator_id"])

        # Changing the role keeps the assignment active.
        changed = self.repo.assign_operator_role(
            operator["operator_id"], "ORG_A", "senior_agent"
        )
        self.assertEqual(changed["role"], "senior_agent")
        self.assertEqual(changed["status"], "active")
        second_ticket = self.repo.create_ticket(
            linked_request_id=request["request_id"],
            subject="Still locked out",
            operator_id=operator["operator_id"],
        )
        self.assertEqual(second_ticket["status"], "open")

    def test_revoked_operator_role_blocks_new_tickets_until_reassigned(self) -> None:
        self.repo.create_account("ORG_A", "ACC_1", "a@example.test")
        request = self._open_request("ORG_A", "ACC_1")
        operator = self.repo.create_operator("Ada Support")
        self.repo.assign_operator_role(operator["operator_id"], "ORG_A", "agent")

        revoked = self.repo.revoke_operator_role(operator["operator_id"], "ORG_A")
        self.assertEqual(revoked["status"], "revoked")
        with self.assertRaises(AuthorizationError):
            self.repo.create_ticket(
                linked_request_id=request["request_id"],
                subject="Locked out",
                operator_id=operator["operator_id"],
            )

        # Reassigning reactivates the assignment.
        self.repo.assign_operator_role(operator["operator_id"], "ORG_A", "agent")
        ticket = self.repo.create_ticket(
            linked_request_id=request["request_id"],
            subject="Locked out",
            operator_id=operator["operator_id"],
        )
        self.assertEqual(ticket["status"], "open")

    def test_recovery_request_view_excludes_token_fields(self) -> None:
        self.repo.create_account("ORG_A", "ACC_1", "a@example.test")
        request = self._open_request("ORG_A", "ACC_1")
        view = self.repo.get_recovery_request_view(request["request_id"])
        self.assertEqual(view["request_id"], request["request_id"])
        self.assertEqual(view["account_id"], "ACC_1")
        self.assertNotIn("token_hash", view)
        self.assertNotIn("token_plaintext", view)

    def test_operator_role_is_scoped_to_one_organization(self) -> None:
        self.repo.create_organization("ORG_B")
        self.repo.create_account("ORG_A", "ACC_1", "a@example.test")
        self.repo.create_account("ORG_B", "ACC_2", "b@example.test")
        request_in_org_b = self._open_request("ORG_B", "ACC_2")

        operator = self.repo.create_operator("Ada Support")
        self.repo.assign_operator_role(operator["operator_id"], "ORG_A", "agent")

        # Active in ORG_A does not grant access to a request from ORG_B.
        with self.assertRaises(AuthorizationError):
            self.repo.create_ticket(
                linked_request_id=request_in_org_b["request_id"],
                subject="Locked out",
                operator_id=operator["operator_id"],
            )

        self.repo.assign_operator_role(operator["operator_id"], "ORG_B", "agent")
        ticket = self.repo.create_ticket(
            linked_request_id=request_in_org_b["request_id"],
            subject="Locked out",
            operator_id=operator["operator_id"],
        )
        self.assertEqual(ticket["org_id"], "ORG_B")


if __name__ == "__main__":
    unittest.main()
