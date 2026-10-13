import os
import tempfile
import unittest

from accountsvc.legacy_receipt_import import (
    REASON_CROSS_ORGANIZATION,
    REASON_MALFORMED_WRAPPER,
    REASON_UNKNOWN_ACCOUNT,
    REASON_UNKNOWN_VERSION,
    RESULT_DUPLICATE,
    RESULT_IMPORTED,
    RESULT_REJECTED,
    SUPPORTED_ENVELOPE_VERSION,
    import_legacy_envelope,
    import_legacy_envelope_batch,
)
from accountsvc.storage import Storage


def _wrapper(**overrides):
    record = {
        "version": SUPPORTED_ENVELOPE_VERSION,
        "envelope_id": "env-1",
        "organization_id": "org-a",
        "account_id": "acct-1",
        "provider_receipt": "opaque-receipt-text",
        "delivery_state": "failed",
    }
    record.update(overrides)
    return record


class LegacyReceiptImportTestCase(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmpdir.name, "state.db")
        self.storage = Storage(self.db_path)
        self.storage.create_account("org-a", "acct-1", "a@example.com")
        self.storage.create_account("org-b", "acct-2", "b@example.com")

    def tearDown(self):
        self.storage.close()
        self._tmpdir.cleanup()


class SingleEnvelopeImportTests(LegacyReceiptImportTestCase):
    def test_valid_wrapper_is_imported_with_opaque_receipt_preserved(self):
        result = import_legacy_envelope(self.storage, _wrapper(provider_receipt="rct_<opaque>_!@#"))
        self.assertEqual(result, {"envelope_id": "env-1", "result": RESULT_IMPORTED, "reason": None})

        stored = self.storage.get_receipt_envelope("env-1")
        self.assertEqual(stored.provider_receipt, "rct_<opaque>_!@#")
        self.assertEqual(stored.account_id, "acct-1")
        self.assertEqual(stored.organization_id, "org-a")
        self.assertEqual(stored.delivery_state, "failed")

    def test_account_id_is_taken_from_the_trusted_account_record(self):
        # The wrapper's own organization_id agrees with the trusted account,
        # so this is accepted -- but the org actually written comes from
        # storage.get_account, not from copying the wrapper's field.
        import_legacy_envelope(self.storage, _wrapper())
        stored = self.storage.get_receipt_envelope("env-1")
        self.assertEqual(stored.account_id, self.storage.get_account("acct-1").account_id)
        self.assertEqual(stored.organization_id, self.storage.get_account("acct-1").organization_id)


class DuplicateImportTests(LegacyReceiptImportTestCase):
    def test_reimporting_the_same_envelope_id_is_a_no_op(self):
        first = import_legacy_envelope(self.storage, _wrapper(provider_receipt="first-receipt"))
        self.assertEqual(first["result"], RESULT_IMPORTED)

        second = import_legacy_envelope(self.storage, _wrapper(provider_receipt="second-receipt"))
        self.assertEqual(second, {"envelope_id": "env-1", "result": RESULT_DUPLICATE, "reason": None})

        # The original write wins; the duplicate attempt did not overwrite it.
        stored = self.storage.get_receipt_envelope("env-1")
        self.assertEqual(stored.provider_receipt, "first-receipt")

    def test_duplicate_across_a_fresh_storage_connection(self):
        import_legacy_envelope(self.storage, _wrapper())
        self.storage.close()

        with Storage(self.db_path) as reopened:
            result = import_legacy_envelope(reopened, _wrapper(provider_receipt="different"))
        self.assertEqual(result["result"], RESULT_DUPLICATE)


class MalformedWrapperTests(LegacyReceiptImportTestCase):
    def test_missing_required_field_is_rejected(self):
        record = _wrapper()
        del record["provider_receipt"]
        result = import_legacy_envelope(self.storage, record)
        self.assertEqual(result["result"], RESULT_REJECTED)
        self.assertEqual(result["reason"], REASON_MALFORMED_WRAPPER)
        self.assertIsNone(self.storage.get_receipt_envelope("env-1"))

    def test_wrong_type_for_a_field_is_rejected(self):
        result = import_legacy_envelope(self.storage, _wrapper(provider_receipt=12345))
        self.assertEqual(result["result"], RESULT_REJECTED)
        self.assertEqual(result["reason"], REASON_MALFORMED_WRAPPER)
        self.assertIsNone(self.storage.get_receipt_envelope("env-1"))

    def test_invalid_delivery_state_is_rejected(self):
        result = import_legacy_envelope(self.storage, _wrapper(delivery_state="not-a-real-state"))
        self.assertEqual(result["result"], RESULT_REJECTED)
        self.assertEqual(result["reason"], REASON_MALFORMED_WRAPPER)
        self.assertIsNone(self.storage.get_receipt_envelope("env-1"))

    def test_non_dict_record_is_rejected(self):
        result = import_legacy_envelope(self.storage, "not-a-wrapper")
        self.assertEqual(result, {"envelope_id": None, "result": RESULT_REJECTED, "reason": REASON_MALFORMED_WRAPPER})

    def test_boolean_version_is_rejected_not_coerced_to_int(self):
        # In Python, True == 1, but a wrapper's version field must be an
        # actual int, not a bool that happens to compare equal.
        result = import_legacy_envelope(self.storage, _wrapper(version=True))
        self.assertEqual(result["result"], RESULT_REJECTED)
        self.assertEqual(result["reason"], REASON_MALFORMED_WRAPPER)


class UnknownVersionTests(LegacyReceiptImportTestCase):
    def test_unrecognized_version_is_rejected_without_writing(self):
        result = import_legacy_envelope(self.storage, _wrapper(version=99))
        self.assertEqual(result["result"], RESULT_REJECTED)
        self.assertEqual(result["reason"], REASON_UNKNOWN_VERSION)
        self.assertIsNone(self.storage.get_receipt_envelope("env-1"))


class CrossOrganizationTests(LegacyReceiptImportTestCase):
    def test_envelope_claiming_wrong_org_for_a_real_account_is_rejected(self):
        # acct-1 really belongs to org-a; the wrapper claims org-b.
        result = import_legacy_envelope(self.storage, _wrapper(organization_id="org-b"))
        self.assertEqual(result["result"], RESULT_REJECTED)
        self.assertEqual(result["reason"], REASON_CROSS_ORGANIZATION)
        self.assertIsNone(self.storage.get_receipt_envelope("env-1"))

    def test_unknown_account_id_is_rejected(self):
        result = import_legacy_envelope(self.storage, _wrapper(account_id="does-not-exist"))
        self.assertEqual(result["result"], RESULT_REJECTED)
        self.assertEqual(result["reason"], REASON_UNKNOWN_ACCOUNT)
        self.assertIsNone(self.storage.get_receipt_envelope("env-1"))


class MixedBatchTests(LegacyReceiptImportTestCase):
    def test_batch_with_valid_duplicate_malformed_and_cross_org_records(self):
        self.storage.create_account("org-a", "acct-3", "c@example.com")
        batch = [
            _wrapper(envelope_id="env-good", account_id="acct-1", organization_id="org-a"),
            _wrapper(envelope_id="env-good", account_id="acct-1", organization_id="org-a"),  # duplicate of above
            _wrapper(envelope_id="env-bad-version", version=7),
            {"envelope_id": "env-missing-fields", "version": 1},  # malformed
            _wrapper(envelope_id="env-cross-org", account_id="acct-2", organization_id="org-a"),  # acct-2 is org-b
            _wrapper(envelope_id="env-other-account", account_id="acct-3", organization_id="org-a"),
        ]

        results = import_legacy_envelope_batch(self.storage, batch)

        # Two occurrences of "env-good" in the same batch call: the first
        # commits, and the second (processed after it, in order) is
        # already a duplicate.
        good_results = [r for r in results if r["envelope_id"] == "env-good"]
        self.assertEqual([r["result"] for r in good_results], [RESULT_IMPORTED, RESULT_DUPLICATE])

        by_id = {r["envelope_id"]: r for r in results if r["envelope_id"] != "env-good"}
        self.assertEqual(by_id["env-bad-version"], {
            "envelope_id": "env-bad-version", "result": RESULT_REJECTED, "reason": REASON_UNKNOWN_VERSION,
        })
        self.assertEqual(by_id["env-missing-fields"]["reason"], REASON_MALFORMED_WRAPPER)
        self.assertEqual(by_id["env-cross-org"]["reason"], REASON_CROSS_ORGANIZATION)
        self.assertEqual(by_id["env-other-account"]["result"], RESULT_IMPORTED)

        # Only the two genuinely valid envelopes ended up persisted.
        self.assertIsNotNone(self.storage.get_receipt_envelope("env-good"))
        self.assertIsNotNone(self.storage.get_receipt_envelope("env-other-account"))
        self.assertIsNone(self.storage.get_receipt_envelope("env-bad-version"))
        self.assertIsNone(self.storage.get_receipt_envelope("env-missing-fields"))
        self.assertIsNone(self.storage.get_receipt_envelope("env-cross-org"))


class RestartPersistenceTests(LegacyReceiptImportTestCase):
    def test_imported_envelopes_and_duplicate_detection_survive_a_restart(self):
        import_legacy_envelope(self.storage, _wrapper(envelope_id="env-restart", provider_receipt="rct-before"))
        self.storage.close()

        with Storage(self.db_path) as reopened:
            stored = reopened.get_receipt_envelope("env-restart")
            self.assertIsNotNone(stored)
            self.assertEqual(stored.provider_receipt, "rct-before")

            # Re-importing after the restart is still recognized as a
            # duplicate, and a genuinely new envelope still imports cleanly.
            duplicate = import_legacy_envelope(
                reopened, _wrapper(envelope_id="env-restart", provider_receipt="rct-after")
            )
            self.assertEqual(duplicate["result"], RESULT_DUPLICATE)

            fresh = import_legacy_envelope(reopened, _wrapper(envelope_id="env-new-after-restart"))
            self.assertEqual(fresh["result"], RESULT_IMPORTED)

        with Storage(self.db_path) as reopened_again:
            self.assertEqual(reopened_again.get_receipt_envelope("env-restart").provider_receipt, "rct-before")
            self.assertIsNotNone(reopened_again.get_receipt_envelope("env-new-after-restart"))


if __name__ == "__main__":
    unittest.main()
