import unittest

from accountsvc.models import (
    Account,
    AuditEvent,
    EmailHistoryEntry,
    MFAFactor,
    NotificationAttempt,
    NotificationStatus,
    Organization,
    ProviderReceipt,
    RecoveryRequest,
    RecoveryStatus,
    ValidationError,
    normalize_email,
    require_id,
)


class RequireIdTests(unittest.TestCase):
    def test_accepts_typical_ids(self):
        self.assertEqual(require_id("acme-org_1", "org_id"), "acme-org_1")

    def test_rejects_empty(self):
        with self.assertRaises(ValidationError):
            require_id("", "org_id")

    def test_rejects_too_long(self):
        with self.assertRaises(ValidationError):
            require_id("x" * 65, "org_id")

    def test_rejects_bad_characters(self):
        with self.assertRaises(ValidationError):
            require_id("has spaces", "org_id")

    def test_rejects_non_string(self):
        with self.assertRaises(ValidationError):
            require_id(123, "org_id")


class NormalizeEmailTests(unittest.TestCase):
    def test_lowercases_and_strips(self):
        self.assertEqual(normalize_email("  Alice@Example.COM  "), "alice@example.com")

    def test_rejects_missing_at(self):
        with self.assertRaises(ValidationError):
            normalize_email("not-an-email")

    def test_rejects_missing_domain_dot(self):
        with self.assertRaises(ValidationError):
            normalize_email("alice@example")

    def test_rejects_too_long(self):
        with self.assertRaises(ValidationError):
            normalize_email("a" * 250 + "@example.com")


class AccountModelTests(unittest.TestCase):
    def test_normalizes_email_on_construction(self):
        account = Account(account_id="alice", org_id="acme", email="Alice@Example.com", created_at=1.0)
        self.assertEqual(account.email, "alice@example.com")

    def test_rejects_bad_account_id(self):
        with self.assertRaises(ValidationError):
            Account(account_id="bad id", org_id="acme", email="a@b.com", created_at=1.0)

    def test_rejects_negative_created_at(self):
        with self.assertRaises(ValidationError):
            Account(account_id="alice", org_id="acme", email="a@b.com", created_at=-1.0)

    def test_is_frozen(self):
        account = Account(account_id="alice", org_id="acme", email="a@b.com", created_at=1.0)
        with self.assertRaises(Exception):
            account.email = "other@b.com"


class EmailHistoryEntryTests(unittest.TestCase):
    def test_current_entry_has_no_end(self):
        entry = EmailHistoryEntry(
            account_id="alice", org_id="acme", email="a@b.com",
            effective_from=1.0, effective_until=None,
        )
        self.assertIsNone(entry.effective_until)

    def test_rejects_end_before_start(self):
        with self.assertRaises(ValidationError):
            EmailHistoryEntry(
                account_id="alice", org_id="acme", email="a@b.com",
                effective_from=5.0, effective_until=1.0,
            )


class MFAFactorTests(unittest.TestCase):
    def test_rejects_unknown_kind(self):
        with self.assertRaises(ValidationError):
            MFAFactor(factor_id="f1", account_id="alice", kind="carrier-pigeon", created_at=1.0)

    def test_accepts_known_kind(self):
        factor = MFAFactor(factor_id="f1", account_id="alice", kind="totp", created_at=1.0)
        self.assertTrue(factor.enabled)


class RecoveryRequestTests(unittest.TestCase):
    def _make(self, **overrides):
        fields = dict(
            request_id="r1",
            account_id="alice",
            org_id="acme",
            recipient_email="a@b.com",
            token_hash="a" * 64,
            created_at=100.0,
            expires_at=200.0,
        )
        fields.update(overrides)
        return RecoveryRequest(**fields)

    def test_defaults_to_pending(self):
        request = self._make()
        self.assertEqual(request.status, RecoveryStatus.PENDING)

    def test_rejects_bad_token_hash_length(self):
        with self.assertRaises(ValidationError):
            self._make(token_hash="short")

    def test_rejects_expiry_not_after_creation(self):
        with self.assertRaises(ValidationError):
            self._make(expires_at=100.0)

    def test_is_expired(self):
        request = self._make()
        self.assertFalse(request.is_expired(150.0))
        self.assertTrue(request.is_expired(200.0))
        self.assertTrue(request.is_expired(250.0))


class ProviderReceiptTests(unittest.TestCase):
    def test_truncates_overlong_text(self):
        receipt = ProviderReceipt(request_id="r1", raw_text="x" * 9000, received_at=1.0)
        self.assertEqual(len(receipt.raw_text), 8192)

    def test_treats_text_as_opaque(self):
        # Provider text is never parsed; arbitrary non-JSON content is fine.
        receipt = ProviderReceipt(request_id="r1", raw_text="503 upstream said no thanks", received_at=1.0)
        self.assertEqual(receipt.raw_text, "503 upstream said no thanks")


class NotificationAttemptTests(unittest.TestCase):
    def test_accepts_sent_and_failed(self):
        for status in (NotificationStatus.SENT, NotificationStatus.FAILED):
            attempt = NotificationAttempt(
                attempt_id="n1", request_id="r1", account_id="alice",
                attempted_at=1.0, status=status, receipt_text="ok",
            )
            self.assertEqual(attempt.status, status)


class AuditEventTests(unittest.TestCase):
    def test_allows_missing_org_and_account(self):
        event = AuditEvent(event_id="e1", event_type="account_created", created_at=1.0)
        self.assertIsNone(event.org_id)
        self.assertIsNone(event.account_id)


class OrganizationTests(unittest.TestCase):
    def test_defaults_name_to_org_id_when_blank(self):
        org = Organization(org_id="acme", name="", created_at=1.0)
        self.assertEqual(org.name, "acme")


if __name__ == "__main__":
    unittest.main()
