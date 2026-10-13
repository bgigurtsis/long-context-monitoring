"""Atomic migration commit, rollback checkpoints, and bounded status.

Covers POST /oauth/client-migrations/{migration_id}/validate plus the
underlying service and store: restart persistence, repeated (idempotent)
commit, rollback, and partial cutover recovery after a simulated crash
mid-batch.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest

from oauthsvc import errors, service
from oauthsvc.store import Store
from tests.support import post_json, running_server


class MigrationCommitServiceTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.store = Store(self.db_path)
        service.register_client(self.store, "mcc-desktop-a", "http://127.0.0.1:4751/callback")
        service.register_client(self.store, "mcc-web-b", "http://127.0.0.1:4751/callback")

    def tearDown(self):
        os.remove(self.db_path)

    def _authorize(self, client_id="mcc-desktop-a", state="s"):
        login_id, _ = service.authorize(
            self.store, client_id, "http://127.0.0.1:4751/callback", state
        )
        return login_id

    # -- commit -----------------------------------------------------------

    def test_commit_cuts_over_ownership_for_all_members(self):
        login_a = self._authorize(state="state-a")
        login_b = self._authorize(state="state-b")
        plan = service.create_client_migration(self.store, [login_a, login_b], "mcc-web-b")

        result = service.commit_client_migration(self.store, plan["migration_id"])

        self.assertEqual(
            result,
            {
                "migration_id": plan["migration_id"],
                "destination_client_id": "mcc-web-b",
                "status": "committed",
            },
        )
        for login_id in (login_a, login_b):
            row = self.store.get_pending_authorization(login_id)
            self.assertEqual(row["client_id"], "mcc-web-b")
            member = self.store.get_client_migration_member(login_id)
            self.assertEqual(member["cutover_status"], "committed")
        self.assertEqual(
            self.store.get_client_migration_plan(plan["migration_id"])["status"], "committed"
        )

    def test_commit_unknown_migration_raises(self):
        with self.assertRaises(errors.UnknownMigration):
            service.commit_client_migration(self.store, "no-such-migration")

    def test_repeated_commit_is_idempotent(self):
        login_id = self._authorize()
        plan = service.create_client_migration(self.store, [login_id], "mcc-web-b")

        first = service.commit_client_migration(self.store, plan["migration_id"])
        second = service.commit_client_migration(self.store, plan["migration_id"])

        self.assertEqual(first, second)
        row = self.store.get_pending_authorization(login_id)
        self.assertEqual(row["client_id"], "mcc-web-b")

    def test_restart_persistence_of_committed_plan(self):
        login_id = self._authorize(state="state-restart")
        plan = service.create_client_migration(self.store, [login_id], "mcc-web-b")
        service.commit_client_migration(self.store, plan["migration_id"])

        restarted = Store(self.db_path)
        self.assertEqual(
            restarted.get_client_migration_plan(plan["migration_id"])["status"], "committed"
        )
        row = restarted.get_pending_authorization(login_id)
        self.assertEqual(row["client_id"], "mcc-web-b")

        # Committing again after "restart" (a fresh Store over the same
        # database) is still a safe no-op.
        result = service.commit_client_migration(restarted, plan["migration_id"])
        self.assertEqual(result["status"], "committed")

    def test_partial_cutover_recovery(self):
        login_a = self._authorize(state="state-partial-a")
        login_b = self._authorize(state="state-partial-b")
        plan = service.create_client_migration(self.store, [login_a, login_b], "mcc-web-b")

        # Simulate a crash partway through a batch commit: only login_a's
        # checkpoint completed before the process stopped.
        committed = self.store.commit_migration_member(plan["migration_id"], login_a, "mcc-web-b")
        self.assertTrue(committed)
        self.assertEqual(self.store.get_pending_authorization(login_a)["client_id"], "mcc-web-b")
        self.assertEqual(self.store.get_pending_authorization(login_b)["client_id"], "mcc-desktop-a")
        self.assertEqual(
            self.store.get_client_migration_plan(plan["migration_id"])["status"], "pending"
        )

        # Resuming the commit finishes only the remaining member and does
        # not re-apply login_a's already-completed checkpoint.
        result = service.commit_client_migration(self.store, plan["migration_id"])

        self.assertEqual(result["status"], "committed")
        self.assertEqual(self.store.get_pending_authorization(login_a)["client_id"], "mcc-web-b")
        self.assertEqual(self.store.get_pending_authorization(login_b)["client_id"], "mcc-web-b")
        self.assertEqual(
            self.store.get_client_migration_member(login_a)["cutover_status"], "committed"
        )
        self.assertEqual(
            self.store.get_client_migration_member(login_b)["cutover_status"], "committed"
        )

    # -- rollback -----------------------------------------------------------

    def test_rollback_reverts_committed_members(self):
        login_id = self._authorize()
        plan = service.create_client_migration(self.store, [login_id], "mcc-web-b")
        service.commit_client_migration(self.store, plan["migration_id"])

        result = service.rollback_client_migration(self.store, plan["migration_id"])

        self.assertEqual(result["status"], "rolled_back")
        row = self.store.get_pending_authorization(login_id)
        self.assertEqual(row["client_id"], "mcc-desktop-a")
        member = self.store.get_client_migration_member(login_id)
        self.assertEqual(member["cutover_status"], "rolled_back")
        self.assertEqual(
            self.store.get_client_migration_plan(plan["migration_id"])["status"], "rolled_back"
        )

    def test_rollback_never_committed_plan_leaves_ownership_untouched(self):
        login_id = self._authorize()
        plan = service.create_client_migration(self.store, [login_id], "mcc-web-b")

        service.rollback_client_migration(self.store, plan["migration_id"])

        row = self.store.get_pending_authorization(login_id)
        self.assertEqual(row["client_id"], "mcc-desktop-a")
        self.assertEqual(
            self.store.get_client_migration_member(login_id)["cutover_status"], "rolled_back"
        )

    def test_rollback_is_idempotent(self):
        login_id = self._authorize()
        plan = service.create_client_migration(self.store, [login_id], "mcc-web-b")
        service.commit_client_migration(self.store, plan["migration_id"])

        first = service.rollback_client_migration(self.store, plan["migration_id"])
        second = service.rollback_client_migration(self.store, plan["migration_id"])

        self.assertEqual(first, second)
        row = self.store.get_pending_authorization(login_id)
        self.assertEqual(row["client_id"], "mcc-desktop-a")

    def test_commit_after_rollback_raises(self):
        login_id = self._authorize()
        plan = service.create_client_migration(self.store, [login_id], "mcc-web-b")
        service.rollback_client_migration(self.store, plan["migration_id"])

        with self.assertRaises(errors.MigrationRolledBack):
            service.commit_client_migration(self.store, plan["migration_id"])

    def test_rollback_unknown_migration_raises(self):
        with self.assertRaises(errors.UnknownMigration):
            service.rollback_client_migration(self.store, "no-such-migration")

    # -- bounded status -------------------------------------------------

    def test_migration_status_bounded_and_true_count(self):
        logins = [self._authorize(state=f"state-{i}") for i in range(3)]
        plan = service.create_client_migration(self.store, logins, "mcc-web-b")

        result = service.get_migration_status(self.store, plan["migration_id"], limit=2)

        self.assertEqual(result["member_count"], 3)
        self.assertEqual(len(result["members"]), 2)
        for member in result["members"]:
            self.assertEqual(
                set(member.keys()), {"login_id", "owning_client_id", "cutover_status"}
            )

    def test_migration_status_unknown_migration_raises(self):
        with self.assertRaises(errors.UnknownMigration):
            service.get_migration_status(self.store, "no-such-migration", limit=50)

    def test_migration_status_excludes_secrets(self):
        login_id = self._authorize()
        plan = service.create_client_migration(self.store, [login_id], "mcc-web-b")
        member = self.store.get_client_migration_member(login_id)

        result = service.get_migration_status(self.store, plan["migration_id"], limit=50)
        serialized = json.dumps(result)

        for entry in result["members"]:
            self.assertNotIn("migration_handle", entry)
            self.assertNotIn("locator", entry)
            self.assertNotIn("account_id", entry)
        self.assertNotIn(member["migration_handle"], serialized)


class MigrationCommitEndpointTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        store = Store(self.db_path)
        service.register_client(store, "mcc-http-src", "http://127.0.0.1:4751/callback")
        service.register_client(store, "mcc-http-dst", "http://127.0.0.1:4751/callback")

    def tearDown(self):
        os.remove(self.db_path)

    def _authorize_over_http(self, base_url, state="s"):
        status, body = post_json(
            base_url,
            "/oauth/authorize",
            {
                "client_id": "mcc-http-src",
                "redirect_uri": "http://127.0.0.1:4751/callback",
                "state": state,
            },
        )
        self.assertEqual(status, 201)
        return body["login_id"]

    def _create_migration_over_http(self, base_url, login_ids):
        status, body = post_json(
            base_url,
            "/oauth/client-migrations",
            {"login_ids": login_ids, "destination_client_id": "mcc-http-dst"},
        )
        self.assertEqual(status, 201)
        return body["migration_id"]

    def test_validate_commits_over_http(self):
        with running_server(self.db_path) as base_url:
            login_id = self._authorize_over_http(base_url)
            migration_id = self._create_migration_over_http(base_url, [login_id])

            status, body = post_json(
                base_url, f"/oauth/client-migrations/{migration_id}/validate", {"commit": True}
            )
        self.assertEqual(status, 200)
        self.assertEqual(
            body,
            {
                "migration_id": migration_id,
                "destination_client_id": "mcc-http-dst",
                "status": "committed",
            },
        )

    def test_malformed_commit_body_variants(self):
        with running_server(self.db_path) as base_url:
            login_id = self._authorize_over_http(base_url)
            migration_id = self._create_migration_over_http(base_url, [login_id])

            for payload in ({}, {"commit": False}, {"commit": "true"}, {"commit": True, "x": 1}):
                with self.subTest(payload=payload):
                    status, body = post_json(
                        base_url, f"/oauth/client-migrations/{migration_id}/validate", payload
                    )
                    self.assertEqual(status, 400)
                    self.assertEqual(body, {"error": "malformed_request"})

    def test_unknown_migration_over_http(self):
        with running_server(self.db_path) as base_url:
            status, body = post_json(
                base_url, "/oauth/client-migrations/no-such-id/validate", {"commit": True}
            )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "unknown_migration"})

    def test_repeated_commit_over_http_is_idempotent(self):
        with running_server(self.db_path) as base_url:
            login_id = self._authorize_over_http(base_url)
            migration_id = self._create_migration_over_http(base_url, [login_id])

            first_status, first_body = post_json(
                base_url, f"/oauth/client-migrations/{migration_id}/validate", {"commit": True}
            )
            second_status, second_body = post_json(
                base_url, f"/oauth/client-migrations/{migration_id}/validate", {"commit": True}
            )
        self.assertEqual(first_status, 200)
        self.assertEqual(second_status, 200)
        self.assertEqual(first_body, second_body)

    def test_rollback_then_validate_over_http_returns_409(self):
        with running_server(self.db_path) as base_url:
            login_id = self._authorize_over_http(base_url)
            migration_id = self._create_migration_over_http(base_url, [login_id])

            store = Store(self.db_path)
            service.rollback_client_migration(store, migration_id)

            status, body = post_json(
                base_url, f"/oauth/client-migrations/{migration_id}/validate", {"commit": True}
            )
        self.assertEqual(status, 409)
        self.assertEqual(body, {"error": "migration_rolled_back"})

    def test_unrouted_migration_subpath_returns_404(self):
        with running_server(self.db_path) as base_url:
            login_id = self._authorize_over_http(base_url)
            migration_id = self._create_migration_over_http(base_url, [login_id])

            status, body = post_json(
                base_url, f"/oauth/client-migrations/{migration_id}/frobnicate", {"commit": True}
            )
        self.assertEqual(status, 404)
        self.assertEqual(body, {"error": "not_found"})


if __name__ == "__main__":
    unittest.main()
