import unittest

from accountsvc.errors import ValidationError
from accountsvc.models import (
    Account,
    MAX_ID_LENGTH,
    MAX_OPAQUE_TEXT_LENGTH,
    MfaEnrollment,
    NotificationAttempt,
    Organization,
    ProviderDeliveryReceipt,
    RecoveryRequest,
    validate_email,
    validate_id,
)


class ValidateIdTests(unittest.TestCase):
    def test_accepts_reasonable_ids(self):
        self.assertEqual(validate_id("org-1_A.b", "org_id"), "org-1_A.b")

    def test_rejects_empty(self):
        with self.assertRaises(ValidationError):
            validate_id("", "org_id")

    def test_rejects_too_long(self):
        with self.assertRaises(ValidationError):
            validate_id("a" * (MAX_ID_LENGTH + 1), "org_id")

    def test_rejects_disallowed_characters(self):
        for bad in ("org id", "org/id", "org;drop table", "org@id"):
            with self.assertRaises(ValidationError):
                validate_id(bad, "org_id")


class ValidateEmailTests(unittest.TestCase):
    def test_accepts_simple_email(self):
        self.assertEqual(validate_email("a@b.com"), "a@b.com")

    def test_rejects_missing_at(self):
        with self.assertRaises(ValidationError):
            validate_email("a-b.com")

    def test_rejects_multiple_at(self):
        with self.assertRaises(ValidationError):
            validate_email("a@b@c.com")

    def test_rejects_missing_dot_in_domain(self):
        with self.assertRaises(ValidationError):
            validate_email("a@bcom")

    def test_rejects_whitespace(self):
        with self.assertRaises(ValidationError):
            validate_email("a b@c.com")

    def test_rejects_too_long(self):
        local = "a" * 250
        with self.assertRaises(ValidationError):
            validate_email(f"{local}@b.com")


class OrganizationModelTests(unittest.TestCase):
    def test_valid(self):
        org = Organization(org_id="org1", created_at="2026-01-01T00:00:00+00:00")
        self.assertEqual(org.org_id, "org1")

    def test_invalid_org_id(self):
        with self.assertRaises(ValidationError):
            Organization(org_id="bad id", created_at="2026-01-01T00:00:00+00:00")


class AccountModelTests(unittest.TestCase):
    def test_valid(self):
        account = Account(
            account_id="acct1",
            org_id="org1",
            current_email="a@b.com",
            created_at="2026-01-01T00:00:00+00:00",
        )
        self.assertEqual(account.current_email, "a@b.com")

    def test_invalid_email(self):
        with self.assertRaises(ValidationError):
            Account(
                account_id="acct1",
                org_id="org1",
                current_email="not-an-email",
                created_at="2026-01-01T00:00:00+00:00",
            )


class MfaEnrollmentModelTests(unittest.TestCase):
    def test_valid_methods(self):
        for method in ("none", "totp"):
            MfaEnrollment(
                account_id="acct1", method=method, enrolled=False, updated_at="t"
            )

    def test_invalid_method(self):
        with self.assertRaises(ValidationError):
            MfaEnrollment(account_id="acct1", method="sms", enrolled=False, updated_at="t")


class RecoveryRequestModelTests(unittest.TestCase):
    def test_valid(self):
        req = RecoveryRequest(
            request_id="r1",
            account_id="acct1",
            org_id="org1",
            token_hash="a" * 64,
            created_at="t1",
            expires_at="t2",
        )
        self.assertFalse(req.used)

    def test_invalid_token_hash_length(self):
        with self.assertRaises(ValidationError):
            RecoveryRequest(
                request_id="r1",
                account_id="acct1",
                org_id="org1",
                token_hash="short",
                created_at="t1",
                expires_at="t2",
            )

    def test_used_property(self):
        req = RecoveryRequest(
            request_id="r1",
            account_id="acct1",
            org_id="org1",
            token_hash="a" * 64,
            created_at="t1",
            expires_at="t2",
            used_at="t3",
        )
        self.assertTrue(req.used)

    def test_token_plain_too_short_rejected(self):
        with self.assertRaises(ValidationError):
            RecoveryRequest(
                request_id="r1",
                account_id="acct1",
                org_id="org1",
                token_hash="a" * 64,
                created_at="t1",
                expires_at="t2",
                token_plain="short",
            )


class ProviderDeliveryReceiptTests(unittest.TestCase):
    def test_opaque_text_is_preserved_verbatim(self):
        weird = '{"not": "parsed", <<not even valid json'
        receipt = ProviderDeliveryReceipt(weird)
        self.assertEqual(receipt.raw_text, weird)

    def test_bounded_length_truncates_rather_than_raises(self):
        huge = "x" * (MAX_OPAQUE_TEXT_LENGTH + 500)
        receipt = ProviderDeliveryReceipt(huge)
        self.assertEqual(len(receipt.raw_text), MAX_OPAQUE_TEXT_LENGTH)


class NotificationAttemptModelTests(unittest.TestCase):
    def test_invalid_attempt_number(self):
        with self.assertRaises(ValidationError):
            NotificationAttempt(
                request_id="r1",
                account_id="acct1",
                attempt_number=0,
                sent_at="t",
                endpoint="http://x",
                success=True,
                receipt=ProviderDeliveryReceipt("ok"),
            )


if __name__ == "__main__":
    unittest.main()
