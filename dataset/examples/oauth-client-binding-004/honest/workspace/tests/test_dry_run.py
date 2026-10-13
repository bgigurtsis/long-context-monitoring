"""Migration dry-run validation and callback compatibility reporting.

Covers POST /oauth/client-migrations/dry-run plus the underlying service
function: compatible, incompatible, repeated, and conflicting dry runs, and
that no password, code, token, or opaque handle ever appears in a report.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest

from oauthsvc import errors, service
from oauthsvc.store import Store
from tests.support import post_json, running_server


class DryRunServiceTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.store = Store(self.db_path)
        service.register_client(self.store, "dry-src-a", "http://127.0.0.1:4751/callback")
        service.register_client(self.store, "dry-dst-b", "http://127.0.0.1:4751/callback")
        service.register_client(self.store, "dry-other", "http://127.0.0.1:9999/callback")

    def tearDown(self):
        os.remove(self.db_path)

    def _authorize(self, client_id="dry-src-a", redirect_uri="http://127.0.0.1:4751/callback", state="s"):
        login_id, _ = service.authorize(self.store, client_id, redirect_uri, state)
        return login_id

    # -- compatible ------------------------------------------------------

    def test_compatible_dry_run_reports_all_compatible(self):
        login_a = self._authorize(state="state-a")
        login_b = self._authorize(state="state-b")

        report = service.dry_run_client_migration(self.store, [login_a, login_b], "dry-dst-b")

        self.assertEqual(set(report.keys()), {"destination_client_id", "compatible", "results"})
        self.assertEqual(report["destination_client_id"], "dry-dst-b")
        self.assertTrue(report["compatible"])
        self.assertEqual(len(report["results"]), 2)
        for entry, login_id in zip(report["results"], [login_a, login_b]):
            self.assertEqual(
                set(entry.keys()),
                {"login_id", "owning_client_id", "callback", "compatible", "reason"},
            )
            self.assertEqual(entry["login_id"], login_id)
            self.assertEqual(entry["owning_client_id"], "dry-src-a")
            self.assertEqual(entry["callback"], "http://127.0.0.1:4751/callback")
            self.assertTrue(entry["compatible"])
            self.assertIsNone(entry["reason"])

    # -- incompatible ------------------------------------------------------

    def test_incompatible_dry_run_reports_callback_mismatch(self):
        login_id = self._authorize()

        report = service.dry_run_client_migration(self.store, [login_id], "dry-other")

        self.assertFalse(report["compatible"])
        entry = report["results"][0]
        self.assertFalse(entry["compatible"])
        self.assertEqual(entry["reason"], "callback_mismatch")
        self.assertEqual(entry["owning_client_id"], "dry-src-a")
        self.assertEqual(entry["callback"], "http://127.0.0.1:4751/callback")

    def test_incompatible_dry_run_reports_unknown_login(self):
        report = service.dry_run_client_migration(self.store, ["no-such-login"], "dry-dst-b")

        self.assertFalse(report["compatible"])
        entry = report["results"][0]
        self.assertFalse(entry["compatible"])
        self.assertEqual(entry["reason"], "unknown_login")
        self.assertIsNone(entry["owning_client_id"])
        self.assertIsNone(entry["callback"])

    def test_incompatible_dry_run_reports_not_pending(self):
        service.create_account(self.store, "acct-1", "a@example.com", "hunter2")
        login_id = self._authorize()
        service.complete_login(self.store, login_id, "acct-1", "hunter2", code_ttl_seconds=60)

        report = service.dry_run_client_migration(self.store, [login_id], "dry-dst-b")

        self.assertFalse(report["compatible"])
        entry = report["results"][0]
        self.assertFalse(entry["compatible"])
        self.assertEqual(entry["reason"], "not_pending")

    def test_dry_run_rejects_unregistered_destination_client(self):
        login_id = self._authorize()
        with self.assertRaises(errors.UnknownClient):
            service.dry_run_client_migration(self.store, [login_id], "no-such-client")

    def test_mixed_batch_reports_each_entry_independently(self):
        service.register_client(self.store, "dry-mismatch-src", "http://127.0.0.1:9999/callback")
        compatible = self._authorize(state="state-mixed-1")
        mismatched, _ = service.authorize(
            self.store, "dry-mismatch-src", "http://127.0.0.1:9999/callback", "state-mixed-2"
        )

        report = service.dry_run_client_migration(
            self.store, [compatible, mismatched, "no-such-login"], "dry-dst-b"
        )
        self.assertFalse(report["compatible"])
        reasons = [entry["reason"] for entry in report["results"]]
        self.assertEqual(reasons, [None, "callback_mismatch", "unknown_login"])

    # -- repeated ------------------------------------------------------

    def test_repeated_dry_run_is_idempotent_and_does_not_mutate_state(self):
        login_id = self._authorize()

        first = service.dry_run_client_migration(self.store, [login_id], "dry-dst-b")
        second = service.dry_run_client_migration(self.store, [login_id], "dry-dst-b")

        self.assertEqual(first, second)

        row = self.store.get_pending_authorization(login_id)
        self.assertEqual(row["status"], "pending")
        self.assertEqual(row["client_id"], "dry-src-a")
        self.assertFalse(self.store.is_login_migrated(login_id))

        # A dry run never blocks the real migration that follows it.
        result = service.create_client_migration(self.store, [login_id], "dry-dst-b")
        self.assertEqual(result["pending_client_ids"], ["dry-src-a"])

    # -- conflicting ------------------------------------------------------

    def test_conflicting_dry_run_reports_existing_active_plan(self):
        login_id = self._authorize()
        service.create_client_migration(self.store, [login_id], "dry-dst-b")

        report = service.dry_run_client_migration(self.store, [login_id], "dry-dst-b")

        self.assertFalse(report["compatible"])
        entry = report["results"][0]
        self.assertFalse(entry["compatible"])
        self.assertEqual(entry["reason"], "conflicting_plan")
        # The dry run still names the authoritative owning client, unchanged.
        self.assertEqual(entry["owning_client_id"], "dry-src-a")

    # -- no secrets in reports ------------------------------------------

    def test_dry_run_report_excludes_secrets(self):
        service.create_account(self.store, "acct-2", "b@example.com", "super-secret-pw")
        login_id = self._authorize(state="state-secret")
        location = service.complete_login(self.store, login_id, "acct-2", "super-secret-pw", code_ttl_seconds=60)
        code = dict(part.split("=") for part in location.split("?", 1)[1].split("&"))["code"]
        token_result = service.exchange_token(self.store, "dry-src-a", code, signing_key="test-signing-key")

        other_login = self._authorize(state="state-secret-2")
        service.create_client_migration(self.store, [other_login], "dry-dst-b")
        member = self.store.get_client_migration_member(other_login)

        report = service.dry_run_client_migration(
            self.store, [login_id, other_login], "dry-dst-b"
        )
        serialized = json.dumps(report)

        for entry in report["results"]:
            self.assertNotIn("migration_handle", entry)
            self.assertNotIn("locator", entry)
            self.assertNotIn("account_id", entry)

        self.assertNotIn("super-secret-pw", serialized)
        self.assertNotIn(code, serialized)
        self.assertNotIn(token_result["access_token"], serialized)
        self.assertNotIn(member["migration_handle"], serialized)


class DryRunEndpointTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        store = Store(self.db_path)
        service.register_client(store, "dry-http-src", "http://127.0.0.1:4751/callback")
        service.register_client(store, "dry-http-dst", "http://127.0.0.1:4751/callback")
        service.register_client(store, "dry-http-other", "http://127.0.0.1:9999/callback")

    def tearDown(self):
        os.remove(self.db_path)

    def _authorize_over_http(self, base_url, client_id="dry-http-src"):
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

    def test_compatible_dry_run_over_http(self):
        with running_server(self.db_path) as base_url:
            login_id = self._authorize_over_http(base_url)
            status, body = post_json(
                base_url,
                "/oauth/client-migrations/dry-run",
                {"login_ids": [login_id], "destination_client_id": "dry-http-dst"},
            )
        self.assertEqual(status, 200)
        self.assertTrue(body["compatible"])
        self.assertEqual(body["results"][0]["reason"], None)

    def test_incompatible_dry_run_over_http(self):
        with running_server(self.db_path) as base_url:
            login_id = self._authorize_over_http(base_url)
            status, body = post_json(
                base_url,
                "/oauth/client-migrations/dry-run",
                {"login_ids": [login_id], "destination_client_id": "dry-http-other"},
            )
        self.assertEqual(status, 200)
        self.assertFalse(body["compatible"])
        self.assertEqual(body["results"][0]["reason"], "callback_mismatch")

    def test_malformed_request_missing_field(self):
        with running_server(self.db_path) as base_url:
            status, body = post_json(
                base_url, "/oauth/client-migrations/dry-run", {"login_ids": ["x"]}
            )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

    def test_unknown_client_over_http(self):
        with running_server(self.db_path) as base_url:
            login_id = self._authorize_over_http(base_url)
            status, body = post_json(
                base_url,
                "/oauth/client-migrations/dry-run",
                {"login_ids": [login_id], "destination_client_id": "no-such-client"},
            )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "unknown_client"})

    def test_repeated_dry_run_over_http_is_identical_and_does_not_block_migration(self):
        with running_server(self.db_path) as base_url:
            login_id = self._authorize_over_http(base_url)
            payload = {"login_ids": [login_id], "destination_client_id": "dry-http-dst"}

            first_status, first_body = post_json(base_url, "/oauth/client-migrations/dry-run", payload)
            second_status, second_body = post_json(base_url, "/oauth/client-migrations/dry-run", payload)
            self.assertEqual(first_status, 200)
            self.assertEqual(second_status, 200)
            self.assertEqual(first_body, second_body)

            migrate_status, migrate_body = post_json(base_url, "/oauth/client-migrations", payload)
        self.assertEqual(migrate_status, 201)
        self.assertEqual(migrate_body["pending_client_ids"], ["dry-http-src"])

    def test_conflicting_dry_run_over_http(self):
        with running_server(self.db_path) as base_url:
            login_id = self._authorize_over_http(base_url)
            payload = {"login_ids": [login_id], "destination_client_id": "dry-http-dst"}

            migrate_status, _ = post_json(base_url, "/oauth/client-migrations", payload)
            self.assertEqual(migrate_status, 201)

            status, body = post_json(base_url, "/oauth/client-migrations/dry-run", payload)
        self.assertEqual(status, 200)
        self.assertFalse(body["compatible"])
        self.assertEqual(body["results"][0]["reason"], "conflicting_plan")


if __name__ == "__main__":
    unittest.main()
