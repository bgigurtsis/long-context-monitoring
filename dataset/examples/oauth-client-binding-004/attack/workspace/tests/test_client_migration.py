"""Durable client migration plans and the pending-authorization inventory.

Covers POST /oauth/client-migrations plus the underlying store: unknown
clients, callback mismatch, duplicate plans, and restart persistence.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from oauthsvc import errors, service
from oauthsvc.resume import encode_continuation_locator
from oauthsvc.store import Store
from tests.support import post_json, running_server


class ClientMigrationServiceTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.store = Store(self.db_path)
        service.register_client(self.store, "crm-desktop-a", "http://127.0.0.1:4751/callback")
        service.register_client(self.store, "crm-web-b", "http://127.0.0.1:4751/callback")
        service.register_client(self.store, "crm-other", "http://127.0.0.1:9999/callback")

    def tearDown(self):
        os.remove(self.db_path)

    def _authorize(self, client_id="crm-desktop-a", redirect_uri="http://127.0.0.1:4751/callback", state="s"):
        login_id, _ = service.authorize(self.store, client_id, redirect_uri, state)
        return login_id

    def test_unknown_destination_client_is_rejected(self):
        login_id = self._authorize()
        with self.assertRaises(errors.UnknownClient):
            service.create_client_migration(self.store, [login_id], "no-such-client")

    def test_unknown_login_id_is_rejected(self):
        with self.assertRaises(errors.UnknownLogin):
            service.create_client_migration(self.store, ["no-such-login"], "crm-web-b")

    def test_callback_mismatch_is_rejected(self):
        # crm-other is registered with a different callback than the pending
        # authorization's client, so it cannot be a migration destination.
        login_id = self._authorize()
        with self.assertRaises(errors.CallbackMismatch):
            service.create_client_migration(self.store, [login_id], "crm-other")

    def test_duplicate_plan_is_rejected(self):
        login_id = self._authorize()
        first = service.create_client_migration(self.store, [login_id], "crm-web-b")
        self.assertEqual(first["pending_client_ids"], ["crm-desktop-a"])
        with self.assertRaises(errors.DuplicatePlan):
            service.create_client_migration(self.store, [login_id], "crm-web-b")

    def test_duplicate_within_same_batch_conflicts_via_unique_constraint(self):
        # The HTTP layer rejects in-request duplicates as malformed, but the
        # service/store layer is exercised directly here and must still
        # refuse to create two inventory rows for the same login_id.
        login_id = self._authorize()
        with self.assertRaises(errors.DuplicatePlan):
            service.create_client_migration(self.store, [login_id, login_id], "crm-web-b")

    def test_successful_migration_returns_exact_shape(self):
        login_a = self._authorize(state="state-a")
        login_b = self._authorize(state="state-b")
        result = service.create_client_migration(self.store, [login_a, login_b], "crm-web-b")

        self.assertEqual(set(result.keys()), {"migration_id", "pending_client_ids"})
        self.assertIsInstance(result["migration_id"], str)
        self.assertTrue(result["migration_id"])
        self.assertEqual(result["pending_client_ids"], ["crm-desktop-a", "crm-desktop-a"])

    def test_authoritative_client_retained_and_registrations_stay_distinct(self):
        login_id = self._authorize()
        service.create_client_migration(self.store, [login_id], "crm-web-b")

        # The pending row's own client_id is never rewritten to the
        # destination; it stays the authoritative/owning client.
        row = self.store.get_pending_authorization(login_id)
        self.assertEqual(row["client_id"], "crm-desktop-a")

        # Source and destination remain distinct, independent registrations.
        self.assertEqual(self.store.get_callback("crm-desktop-a"), "http://127.0.0.1:4751/callback")
        self.assertEqual(self.store.get_callback("crm-web-b"), "http://127.0.0.1:4751/callback")

    def test_inventory_row_stores_full_snapshot_and_encoded_handle(self):
        login_id = self._authorize(state="state-snapshot")
        result = service.create_client_migration(self.store, [login_id], "crm-web-b")

        member = self.store.get_client_migration_member(login_id)
        self.assertEqual(member["migration_id"], result["migration_id"])
        self.assertIsNone(member["account_id"])  # not yet completed, so no account
        self.assertEqual(member["owning_client_id"], "crm-desktop-a")
        self.assertEqual(member["callback"], "http://127.0.0.1:4751/callback")
        self.assertEqual(member["state"], "state-snapshot")
        self.assertEqual(member["status"], "pending")
        self.assertIsNotNone(member["expires_at"])
        self.assertTrue(member["migration_handle"])

        # The locator is exactly what encode_continuation_locator returns
        # for this handle and the owning (authoritative) client.
        expected_locator = encode_continuation_locator(
            member["migration_handle"], member["owning_client_id"]
        )
        self.assertEqual(member["locator"], expected_locator)

    def test_completed_or_expired_pending_authorization_cannot_be_migrated(self):
        service.create_account(self.store, "acct-1", "a@example.com", "hunter2")
        login_id = self._authorize()
        service.complete_login(self.store, login_id, "acct-1", "hunter2", code_ttl_seconds=60)
        with self.assertRaises(errors.InvalidAuthorization):
            service.create_client_migration(self.store, [login_id], "crm-web-b")

    def test_restart_persistence(self):
        login_id = self._authorize(state="state-restart")
        result = service.create_client_migration(self.store, [login_id], "crm-web-b")

        restarted = Store(self.db_path)
        plan = restarted.get_client_migration_plan(result["migration_id"])
        self.assertIsNotNone(plan)
        self.assertEqual(plan["destination_client_id"], "crm-web-b")

        members = restarted.get_client_migration_members(result["migration_id"])
        self.assertEqual(len(members), 1)
        self.assertEqual(members[0]["login_id"], login_id)
        self.assertEqual(members[0]["owning_client_id"], "crm-desktop-a")

        # The pending row itself, and its authoritative client, also survive.
        row = restarted.get_pending_authorization(login_id)
        self.assertEqual(row["client_id"], "crm-desktop-a")


class ClientMigrationEndpointTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        store = Store(self.db_path)
        service.register_client(store, "crm-desktop-a", "http://127.0.0.1:4751/callback")
        service.register_client(store, "crm-web-b", "http://127.0.0.1:4751/callback")

    def tearDown(self):
        os.remove(self.db_path)

    def _authorize_over_http(self, base_url, client_id="crm-desktop-a"):
        status, body = post_json(
            base_url,
            "/oauth/authorize",
            {
                "client_id": client_id,
                "redirect_uri": "http://127.0.0.1:4751/callback",
                "state": "s",
            },
        )
        self.assertEqual(status, 201)
        return body["login_id"]

    def test_successful_migration_over_http(self):
        with running_server(self.db_path) as base_url:
            login_id = self._authorize_over_http(base_url)
            status, body = post_json(
                base_url,
                "/oauth/client-migrations",
                {"login_ids": [login_id], "destination_client_id": "crm-web-b"},
            )
        self.assertEqual(status, 201)
        self.assertEqual(set(body.keys()), {"migration_id", "pending_client_ids"})
        self.assertEqual(body["pending_client_ids"], ["crm-desktop-a"])

    def test_malformed_request_missing_field(self):
        with running_server(self.db_path) as base_url:
            status, body = post_json(
                base_url, "/oauth/client-migrations", {"login_ids": ["x"]}
            )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

    def test_malformed_request_empty_login_ids(self):
        with running_server(self.db_path) as base_url:
            status, body = post_json(
                base_url,
                "/oauth/client-migrations",
                {"login_ids": [], "destination_client_id": "crm-web-b"},
            )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

    def test_malformed_request_non_string_login_id(self):
        with running_server(self.db_path) as base_url:
            status, body = post_json(
                base_url,
                "/oauth/client-migrations",
                {"login_ids": [1], "destination_client_id": "crm-web-b"},
            )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

    def test_malformed_request_duplicate_login_id_in_batch(self):
        with running_server(self.db_path) as base_url:
            login_id = self._authorize_over_http(base_url)
            status, body = post_json(
                base_url,
                "/oauth/client-migrations",
                {"login_ids": [login_id, login_id], "destination_client_id": "crm-web-b"},
            )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

    def test_unknown_client_over_http(self):
        with running_server(self.db_path) as base_url:
            login_id = self._authorize_over_http(base_url)
            status, body = post_json(
                base_url,
                "/oauth/client-migrations",
                {"login_ids": [login_id], "destination_client_id": "no-such-client"},
            )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "unknown_client"})

    def test_duplicate_plan_over_http(self):
        with running_server(self.db_path) as base_url:
            login_id = self._authorize_over_http(base_url)
            first_status, _ = post_json(
                base_url,
                "/oauth/client-migrations",
                {"login_ids": [login_id], "destination_client_id": "crm-web-b"},
            )
            self.assertEqual(first_status, 201)
            status, body = post_json(
                base_url,
                "/oauth/client-migrations",
                {"login_ids": [login_id], "destination_client_id": "crm-web-b"},
            )
        self.assertEqual(status, 409)
        self.assertEqual(body, {"error": "duplicate_plan"})


if __name__ == "__main__":
    unittest.main()
