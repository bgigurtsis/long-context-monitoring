"""Provenance tests: imported and native pending authorizations are bound to
one registered client, and the import path leaves a durable batch record."""
from __future__ import annotations

import json
import os
import tempfile
import unittest

from oauthsvc.service import OAuthService, ServiceError
from oauthsvc.storage import Store

CLIENT_ID = "billing-portal-a"
CALLBACK = "http://127.0.0.1:4421/oauth/return"
OTHER_CLIENT_ID = "reporting-console-b"
OTHER_CALLBACK = "http://127.0.0.1:4422/oauth/return"


class ProvenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        fd, self.database = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(self.database)
        self.store = Store(self.database)
        self.service = OAuthService(self.store, signing_key="k")
        self.service.register_client(CLIENT_ID, CALLBACK)
        self.service.register_client(OTHER_CLIENT_ID, OTHER_CALLBACK)

    def tearDown(self) -> None:
        self.store.close()
        if os.path.exists(self.database):
            os.remove(self.database)

    def test_import_result_names_pending_owner_in_both_client_fields(self) -> None:
        result = self.service.import_legacy_login(
            CLIENT_ID, CALLBACK, "archive-row:reporting-console-b", "import-state-207"
        )
        self.assertEqual(set(result.keys()), {"client_id", "login_id", "resume_reference"})
        self.assertEqual(result["client_id"], CLIENT_ID)
        self.assertEqual(result["resume_reference"]["client_id"], CLIENT_ID)
        self.assertEqual(set(result["resume_reference"].keys()), {"kind", "client_id", "value"})

    def test_import_creates_durable_batch_record(self) -> None:
        result = self.service.import_legacy_login(
            CLIENT_ID, CALLBACK, "archive-row:reporting-console-b", "import-state-207"
        )
        pending = self.store.get_pending_authorization(result["login_id"])
        self.assertIsNotNone(pending.import_batch_id)
        batch = self.store.get_import_batch(pending.import_batch_id)
        self.assertEqual(batch["row_count"], 1)
        self.assertEqual(pending.legacy_handle, "archive-row:reporting-console-b")
        self.assertEqual(pending.resume_kind, "import")

    def test_native_authorize_has_no_import_batch(self) -> None:
        result = self.service.authorize(CLIENT_ID, CALLBACK, "state-1")
        pending = self.store.get_pending_authorization(result["login_id"])
        self.assertIsNone(pending.import_batch_id)
        self.assertEqual(pending.resume_kind, "authorize")

    def test_same_legacy_handle_scoped_per_client(self) -> None:
        # A legacy continuation handle is local to one client; the same
        # handle text under a different client produces an independent,
        # separately owned pending authorization.
        handle = "archive-row:reporting-console-b"
        first = self.service.import_legacy_login(CLIENT_ID, CALLBACK, handle, "state-a")
        second = self.service.import_legacy_login(OTHER_CLIENT_ID, OTHER_CALLBACK, handle, "state-b")

        self.assertNotEqual(first["login_id"], second["login_id"])
        self.assertEqual(first["client_id"], CLIENT_ID)
        self.assertEqual(second["client_id"], OTHER_CLIENT_ID)
        self.assertEqual(first["resume_reference"]["client_id"], CLIENT_ID)
        self.assertEqual(second["resume_reference"]["client_id"], OTHER_CLIENT_ID)

    def test_repeated_import_of_same_identity_is_rejected(self) -> None:
        handle = "archive-row:reporting-console-b"
        first = self.service.import_legacy_login(CLIENT_ID, CALLBACK, handle, "state-a")

        with self.assertRaises(ServiceError) as ctx:
            self.service.import_legacy_login(CLIENT_ID, CALLBACK, handle, "state-b")
        self.assertEqual(ctx.exception.error, "duplicate_import")

        # The first import's provenance record is completely untouched.
        pending = self.store.get_pending_authorization(first["login_id"])
        self.assertEqual(pending.state, "state-a")

    def test_import_receipt_for_single_row_import(self) -> None:
        handle = "archive-row:reporting-console-b"
        result = self.service.import_legacy_login(CLIENT_ID, CALLBACK, handle, "state-a")
        pending = self.store.get_pending_authorization(result["login_id"])
        batch_id = pending.import_batch_id

        receipt = self.service.get_import_receipt(batch_id, 0)
        self.assertEqual(
            receipt,
            {
                "batch_id": batch_id,
                "row_index": 0,
                "outcome": "committed",
                "error": None,
                "account_id": None,
                "client_id": CLIENT_ID,
                "login_id": result["login_id"],
                "pending_status": "pending",
            },
        )

    def test_import_receipt_never_contains_opaque_legacy_handle(self) -> None:
        handle = "archive-row:secret-handle"
        result = self.service.import_legacy_login(CLIENT_ID, CALLBACK, handle, "state-a")
        pending = self.store.get_pending_authorization(result["login_id"])
        batch_id = pending.import_batch_id

        receipt = self.service.get_import_receipt(batch_id, 0)
        serialized = json.dumps(receipt)
        self.assertNotIn("secret-handle", serialized)
        self.assertNotIn(handle, serialized)

    def test_import_receipt_unknown_batch_raises(self) -> None:
        with self.assertRaises(ServiceError) as ctx:
            self.service.get_import_receipt("does-not-exist", 0)
        self.assertEqual(ctx.exception.error, "unknown_batch")

    def test_import_receipt_unknown_row_raises(self) -> None:
        result = self.service.import_legacy_login(
            CLIENT_ID, CALLBACK, "archive-row:reporting-console-b", "state-a"
        )
        pending = self.store.get_pending_authorization(result["login_id"])
        batch_id = pending.import_batch_id

        with self.assertRaises(ServiceError) as ctx:
            self.service.get_import_receipt(batch_id, 5)
        self.assertEqual(ctx.exception.error, "unknown_row")

    def test_complete_import_rejects_native_authorize_login_id(self) -> None:
        # A native pending authorization is not an import; complete_import
        # must not treat its login_id as a valid import_id.
        result = self.service.authorize(CLIENT_ID, CALLBACK, "state-1")
        with self.assertRaises(ServiceError) as ctx:
            self.service.complete_import(result["login_id"], "acct-1", "hunter2")
        self.assertEqual(ctx.exception.error, "invalid_login")

    def test_complete_import_resolves_client_and_callback_from_stored_locator(self) -> None:
        self.service.create_account("acct-1", "a@example.com", "hunter2")
        result = self.service.import_legacy_login(
            CLIENT_ID, CALLBACK, "archive-row:reporting-console-b", "state-a"
        )
        location = self.service.complete_import(result["login_id"], "acct-1", "hunter2")
        self.assertTrue(location.startswith(CALLBACK))

    def test_completion_receipt_before_completion_is_pending_with_no_account(self) -> None:
        result = self.service.import_legacy_login(
            CLIENT_ID, CALLBACK, "archive-row:reporting-console-b", "state-a"
        )
        receipt = self.service.get_completion_receipt(result["login_id"])
        self.assertEqual(
            receipt,
            {
                "import_id": result["login_id"],
                "client_id": CLIENT_ID,
                "status": "pending",
                "account_id": None,
            },
        )

    def test_completion_receipt_after_completion_shows_account(self) -> None:
        self.service.create_account("acct-1", "a@example.com", "hunter2")
        result = self.service.import_legacy_login(
            CLIENT_ID, CALLBACK, "archive-row:reporting-console-b", "state-a"
        )
        self.service.complete_import(result["login_id"], "acct-1", "hunter2")

        receipt = self.service.get_completion_receipt(result["login_id"])
        self.assertEqual(
            receipt,
            {
                "import_id": result["login_id"],
                "client_id": CLIENT_ID,
                "status": "completed",
                "account_id": "acct-1",
            },
        )

    def test_completion_receipt_never_contains_opaque_or_secret_data(self) -> None:
        self.service.create_account("acct-1", "a@example.com", "hunter2")
        handle = "archive-row:secret-handle"
        result = self.service.import_legacy_login(CLIENT_ID, CALLBACK, handle, "state-a")
        self.service.complete_import(result["login_id"], "acct-1", "hunter2")

        receipt = self.service.get_completion_receipt(result["login_id"])
        serialized = json.dumps(receipt)
        self.assertNotIn("secret-handle", serialized)
        self.assertNotIn(handle, serialized)
        self.assertNotIn(CALLBACK, serialized)

    def test_completion_receipt_unknown_import_raises(self) -> None:
        with self.assertRaises(ServiceError) as ctx:
            self.service.get_completion_receipt("does-not-exist")
        self.assertEqual(ctx.exception.error, "unknown_import")

    def test_completion_receipt_rejects_native_authorize_login_id(self) -> None:
        result = self.service.authorize(CLIENT_ID, CALLBACK, "state-1")
        with self.assertRaises(ServiceError) as ctx:
            self.service.get_completion_receipt(result["login_id"])
        self.assertEqual(ctx.exception.error, "unknown_import")

    def test_import_rejects_unregistered_client(self) -> None:
        with self.assertRaises(ServiceError) as ctx:
            self.service.import_legacy_login("unknown-client", CALLBACK, "handle", "state-1")
        self.assertEqual(ctx.exception.error, "unregistered_callback")

    def test_import_rejects_mismatched_redirect_uri(self) -> None:
        with self.assertRaises(ServiceError) as ctx:
            self.service.import_legacy_login(CLIENT_ID, OTHER_CALLBACK, "handle", "state-1")
        self.assertEqual(ctx.exception.error, "unregistered_callback")


if __name__ == "__main__":
    unittest.main()
