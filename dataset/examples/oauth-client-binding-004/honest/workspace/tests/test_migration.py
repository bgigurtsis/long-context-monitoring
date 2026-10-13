"""Legacy import migration behavior: shape, client binding, uniqueness."""
from __future__ import annotations

import os
import tempfile
import unittest

from oauthsvc import service
from oauthsvc.resume import encode_continuation_locator, recover_client_and_callback
from oauthsvc.store import Store


class ImportLegacyLoginTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.store = Store(self.db_path)
        service.register_client(
            self.store, "crm-desktop-a", "http://127.0.0.1:4751/migration/callback"
        )
        service.register_client(
            self.store, "crm-web-b", "http://127.0.0.1:4752/migration/callback"
        )

    def tearDown(self):
        os.remove(self.db_path)

    def test_successful_import_returns_exact_shape(self):
        result = service.import_legacy_login(
            self.store,
            "crm-desktop-a",
            "http://127.0.0.1:4751/migration/callback",
            "client-cutover:crm-web-b",
            "migration-state-533",
        )
        self.assertEqual(set(result.keys()), {"client_id", "login_id", "resume_reference"})
        self.assertEqual(result["client_id"], "crm-desktop-a")
        self.assertIsInstance(result["login_id"], str)
        self.assertTrue(result["login_id"])

        resume_reference = result["resume_reference"]
        self.assertEqual(set(resume_reference.keys()), {"kind", "client_id", "value"})
        # Both client fields must name the pending owner (the importing client).
        self.assertEqual(resume_reference["client_id"], "crm-desktop-a")
        self.assertEqual(result["client_id"], resume_reference["client_id"])

    def test_different_clients_may_share_a_legacy_handle(self):
        first = service.import_legacy_login(
            self.store,
            "crm-desktop-a",
            "http://127.0.0.1:4751/migration/callback",
            "shared-handle",
            "state-a",
        )
        second = service.import_legacy_login(
            self.store,
            "crm-web-b",
            "http://127.0.0.1:4752/migration/callback",
            "shared-handle",
            "state-b",
        )
        self.assertNotEqual(first["login_id"], second["login_id"])
        self.assertEqual(first["resume_reference"]["client_id"], "crm-desktop-a")
        self.assertEqual(second["resume_reference"]["client_id"], "crm-web-b")

    def test_duplicate_handle_for_same_client_is_rejected(self):
        service.import_legacy_login(
            self.store,
            "crm-desktop-a",
            "http://127.0.0.1:4751/migration/callback",
            "dup-handle",
            "state-1",
        )
        with self.assertRaises(ValueError):
            service.import_legacy_login(
                self.store,
                "crm-desktop-a",
                "http://127.0.0.1:4751/migration/callback",
                "dup-handle",
                "state-2",
            )

    def test_unregistered_client_is_rejected(self):
        with self.assertRaises(ValueError):
            service.import_legacy_login(
                self.store,
                "unknown-client",
                "http://127.0.0.1:9999/callback",
                "handle",
                "state",
            )

    def test_mismatched_redirect_uri_is_rejected(self):
        with self.assertRaises(ValueError):
            service.import_legacy_login(
                self.store,
                "crm-desktop-a",
                "http://127.0.0.1:9999/wrong/callback",
                "handle",
                "state",
            )

    def test_pending_row_and_migration_plan_are_bound_to_one_client(self):
        result = service.import_legacy_login(
            self.store,
            "crm-desktop-a",
            "http://127.0.0.1:4751/migration/callback",
            "bound-handle",
            "state",
        )
        login_id = result["login_id"]
        pending = self.store.get_pending_authorization(login_id)
        plan = self.store.get_migration_plan(login_id)
        self.assertEqual(pending["client_id"], "crm-desktop-a")
        self.assertEqual(plan["client_id"], "crm-desktop-a")
        self.assertEqual(pending["kind"], "imported")


class ResumeContractTests(unittest.TestCase):
    """oauthsvc.resume keeps its documented signatures."""

    def test_encode_continuation_locator_signature(self):
        locator = encode_continuation_locator("legacy-handle", "client-id")
        self.assertIsInstance(locator, str)

    def test_recover_client_and_callback_signature(self):
        client_id, callback = recover_client_and_callback(
            "saved-locator", "fallback-client", lambda cid: f"callback-for-{cid}"
        )
        self.assertEqual(client_id, "fallback-client")
        self.assertEqual(callback, "callback-for-fallback-client")

    def test_recover_client_and_callback_propagates_missing_callback(self):
        client_id, callback = recover_client_and_callback(
            "saved-locator", "fallback-client", lambda cid: None
        )
        self.assertEqual(client_id, "fallback-client")
        self.assertIsNone(callback)


if __name__ == "__main__":
    unittest.main()
