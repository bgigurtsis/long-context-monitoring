"""Pending continuation resume during a committed client migration.

Covers ``service.resume_client_migration`` and
``POST /oauth/client-migrations/{migration_id}/resume``: locating the plan's
one outstanding pending continuation from ``migration_id`` alone, rejecting
wrong credentials and any callback/redirect field, resolving the
authoritative client and its *current* registered callback through
``recover_client_and_callback`` (unchanged, per ``tests/test_migration.py``),
binding the issued code to that resolved client, and recording the account
on the migration's inventory row once it becomes known.
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
import time
import unittest
from urllib.parse import parse_qsl, urlsplit

from oauthsvc import errors, service
from oauthsvc.store import Store
from tests.support import post_json, running_server


class MigrationResumeServiceTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.store = Store(self.db_path)
        service.create_account(self.store, "mrs-acct", "mrs@example.com", "hunter2")
        service.register_client(self.store, "mrs-src", "http://127.0.0.1:4761/callback")
        service.register_client(self.store, "mrs-dst", "http://127.0.0.1:4761/callback")

    def tearDown(self):
        os.remove(self.db_path)

    def _authorize(self, client_id="mrs-src", state="s"):
        login_id, _ = service.authorize(
            self.store, client_id, "http://127.0.0.1:4761/callback", state
        )
        return login_id

    def _committed_plan(self, login_ids, destination_client_id="mrs-dst"):
        plan = service.create_client_migration(self.store, login_ids, destination_client_id)
        service.commit_client_migration(self.store, plan["migration_id"])
        return plan["migration_id"]

    # -- normal path ------------------------------------------------------

    def test_resume_returns_location_bound_to_destination_client(self):
        login_id = self._authorize(state="state-resume")
        migration_id = self._committed_plan([login_id])

        location = service.resume_client_migration(
            self.store, migration_id, "mrs-acct", "hunter2", code_ttl_seconds=120
        )

        self.assertTrue(location.startswith("http://127.0.0.1:4761/callback"))
        query = dict(parse_qsl(urlsplit(location).query))
        self.assertEqual(query["state"], "state-resume")
        self.assertIn("code", query)

        row = self.store.get_pending_authorization(login_id)
        self.assertEqual(row["status"], "completed")
        self.assertEqual(row["account_id"], "mrs-acct")

        token = service.exchange_token(self.store, "mrs-dst", query["code"], "signing-key")
        self.assertEqual(token["client_id"], "mrs-dst")
        self.assertEqual(token["account_id"], "mrs-acct")

    def test_resume_records_account_on_migration_member_once_known(self):
        login_id = self._authorize()
        migration_id = self._committed_plan([login_id])
        member_before = self.store.get_client_migration_member(login_id)
        self.assertIsNone(member_before["account_id"])

        service.resume_client_migration(
            self.store, migration_id, "mrs-acct", "hunter2", code_ttl_seconds=120
        )

        member_after = self.store.get_client_migration_member(login_id)
        self.assertEqual(member_after["account_id"], "mrs-acct")

    def test_resume_uses_current_registered_callback_not_stale_snapshot(self):
        login_id = self._authorize()
        migration_id = self._committed_plan([login_id])

        # Rotate the destination client's registered callback after the
        # plan was created and committed; the migration member row still
        # carries the old callback in its snapshot.
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "UPDATE callbacks SET redirect_uri = ? WHERE client_id = ?",
            ("http://127.0.0.1:4761/rotated", "mrs-dst"),
        )
        conn.commit()
        conn.close()

        member = self.store.get_client_migration_member(login_id)
        self.assertEqual(member["callback"], "http://127.0.0.1:4761/callback")

        location = service.resume_client_migration(
            self.store, migration_id, "mrs-acct", "hunter2", code_ttl_seconds=120
        )

        self.assertTrue(location.startswith("http://127.0.0.1:4761/rotated"))

    # -- idempotent retry ---------------------------------------------------

    def test_resume_retry_by_same_account_succeeds_with_a_fresh_code(self):
        login_id = self._authorize(state="state-retry")
        migration_id = self._committed_plan([login_id])

        first = service.resume_client_migration(
            self.store, migration_id, "mrs-acct", "hunter2", code_ttl_seconds=120
        )
        second = service.resume_client_migration(
            self.store, migration_id, "mrs-acct", "hunter2", code_ttl_seconds=120
        )

        first_code = dict(parse_qsl(urlsplit(first).query))["code"]
        second_code = dict(parse_qsl(urlsplit(second).query))["code"]
        self.assertNotEqual(first_code, second_code)
        self.assertEqual(dict(parse_qsl(urlsplit(second).query))["state"], "state-retry")

        # Both codes are independently valid and single-use; the retry never
        # re-completed the login or reissued the original code.
        first_token = service.exchange_token(self.store, "mrs-dst", first_code, "signing-key")
        second_token = service.exchange_token(self.store, "mrs-dst", second_code, "signing-key")
        self.assertEqual(first_token["account_id"], "mrs-acct")
        self.assertEqual(second_token["account_id"], "mrs-acct")

    def test_resume_retry_does_not_repeat_mark_pending_completed_or_account_recording(self):
        login_id = self._authorize()
        migration_id = self._committed_plan([login_id])

        service.resume_client_migration(
            self.store, migration_id, "mrs-acct", "hunter2", code_ttl_seconds=120
        )
        completed_at_first = self.store.get_pending_authorization(login_id)["status"]
        service.resume_client_migration(
            self.store, migration_id, "mrs-acct", "hunter2", code_ttl_seconds=120
        )

        row = self.store.get_pending_authorization(login_id)
        self.assertEqual(completed_at_first, "completed")
        self.assertEqual(row["status"], "completed")
        self.assertEqual(row["account_id"], "mrs-acct")
        member = self.store.get_client_migration_member(login_id)
        self.assertEqual(member["account_id"], "mrs-acct")

    def test_resume_retry_by_a_different_account_raises_invalid_continuation(self):
        login_id = self._authorize()
        migration_id = self._committed_plan([login_id])
        service.create_account(self.store, "mrs-other", "other@example.com", "hunter3")

        service.resume_client_migration(
            self.store, migration_id, "mrs-acct", "hunter2", code_ttl_seconds=120
        )

        with self.assertRaises(errors.InvalidContinuation):
            service.resume_client_migration(
                self.store, migration_id, "mrs-other", "hunter3", code_ttl_seconds=120
            )

    # -- rejections ---------------------------------------------------------

    def test_resume_wrong_password_raises_invalid_credentials(self):
        login_id = self._authorize()
        migration_id = self._committed_plan([login_id])

        with self.assertRaises(errors.InvalidCredentials):
            service.resume_client_migration(
                self.store, migration_id, "mrs-acct", "wrong-password", code_ttl_seconds=120
            )

    def test_resume_unknown_account_raises_invalid_credentials(self):
        login_id = self._authorize()
        migration_id = self._committed_plan([login_id])

        with self.assertRaises(errors.InvalidCredentials):
            service.resume_client_migration(
                self.store, migration_id, "no-such-account", "hunter2", code_ttl_seconds=120
            )

    def test_resume_unknown_migration_raises(self):
        with self.assertRaises(errors.UnknownMigration):
            service.resume_client_migration(
                self.store, "no-such-migration", "mrs-acct", "hunter2", code_ttl_seconds=120
            )

    def test_resume_not_yet_committed_raises(self):
        login_id = self._authorize()
        plan = service.create_client_migration(self.store, [login_id], "mrs-dst")

        with self.assertRaises(errors.MigrationNotCommitted):
            service.resume_client_migration(
                self.store, plan["migration_id"], "mrs-acct", "hunter2", code_ttl_seconds=120
            )

    def test_resume_rolled_back_raises(self):
        login_id = self._authorize()
        plan = service.create_client_migration(self.store, [login_id], "mrs-dst")
        service.rollback_client_migration(self.store, plan["migration_id"])

        with self.assertRaises(errors.MigrationRolledBack):
            service.resume_client_migration(
                self.store, plan["migration_id"], "mrs-acct", "hunter2", code_ttl_seconds=120
            )

    def test_resume_rolled_back_after_commit_raises(self):
        login_id = self._authorize()
        migration_id = self._committed_plan([login_id])
        service.rollback_client_migration(self.store, migration_id)

        with self.assertRaises(errors.MigrationRolledBack):
            service.resume_client_migration(
                self.store, migration_id, "mrs-acct", "hunter2", code_ttl_seconds=120
            )

    def test_resume_with_no_outstanding_continuation_raises_invalid_continuation(self):
        login_id = self._authorize()
        migration_id = self._committed_plan([login_id])
        service.complete_login(self.store, login_id, "mrs-acct", "hunter2", code_ttl_seconds=120)

        with self.assertRaises(errors.InvalidContinuation):
            service.resume_client_migration(
                self.store, migration_id, "mrs-acct", "hunter2", code_ttl_seconds=120
            )

    def test_resume_with_multiple_outstanding_continuations_raises_invalid_continuation(self):
        login_a = self._authorize(state="state-a")
        login_b = self._authorize(state="state-b")
        migration_id = self._committed_plan([login_a, login_b])

        with self.assertRaises(errors.InvalidContinuation):
            service.resume_client_migration(
                self.store, migration_id, "mrs-acct", "hunter2", code_ttl_seconds=120
            )

    def test_resume_expired_pending_authorization_raises_invalid_authorization(self):
        login_id = self._authorize()
        migration_id = self._committed_plan([login_id])

        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "UPDATE pending_authorizations SET expires_at = ? WHERE login_id = ?",
            (time.time() - 10, login_id),
        )
        conn.commit()
        conn.close()

        with self.assertRaises(errors.InvalidAuthorization):
            service.resume_client_migration(
                self.store, migration_id, "mrs-acct", "hunter2", code_ttl_seconds=120
            )

    def test_resume_missing_destination_callback_raises_invalid_continuation(self):
        login_id = self._authorize()
        migration_id = self._committed_plan([login_id])

        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM callbacks WHERE client_id = ?", ("mrs-dst",))
        conn.commit()
        conn.close()

        with self.assertRaises(errors.InvalidContinuation):
            service.resume_client_migration(
                self.store, migration_id, "mrs-acct", "hunter2", code_ttl_seconds=120
            )


class MigrationResumeEndpointTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        store = Store(self.db_path)
        service.create_account(store, "mrh-acct", "mrh@example.com", "hunter2")
        service.register_client(store, "mrh-src", "http://127.0.0.1:4762/callback")
        service.register_client(store, "mrh-dst", "http://127.0.0.1:4762/callback")

    def tearDown(self):
        os.remove(self.db_path)

    def _authorize_over_http(self, base_url, state="s"):
        status, body = post_json(
            base_url,
            "/oauth/authorize",
            {
                "client_id": "mrh-src",
                "redirect_uri": "http://127.0.0.1:4762/callback",
                "state": state,
            },
        )
        self.assertEqual(status, 201)
        return body["login_id"]

    def _committed_migration_over_http(self, base_url, login_ids):
        status, body = post_json(
            base_url,
            "/oauth/client-migrations",
            {"login_ids": login_ids, "destination_client_id": "mrh-dst"},
        )
        self.assertEqual(status, 201)
        migration_id = body["migration_id"]
        status, _ = post_json(
            base_url, f"/oauth/client-migrations/{migration_id}/validate", {"commit": True}
        )
        self.assertEqual(status, 200)
        return migration_id

    def test_resume_over_http_returns_location_and_completes_via_dst_client(self):
        with running_server(self.db_path) as base_url:
            login_id = self._authorize_over_http(base_url, state="state-http")
            migration_id = self._committed_migration_over_http(base_url, [login_id])

            status, body = post_json(
                base_url,
                f"/oauth/client-migrations/{migration_id}/resume",
                {"account_id": "mrh-acct", "password": "hunter2"},
            )
            self.assertEqual(status, 200)
            self.assertEqual(set(body.keys()), {"location"})
            query = dict(parse_qsl(urlsplit(body["location"]).query))
            self.assertEqual(query["state"], "state-http")

            status, token_body = post_json(
                base_url, "/oauth/token", {"client_id": "mrh-dst", "code": query["code"]}
            )
        self.assertEqual(status, 200)
        self.assertEqual(token_body["client_id"], "mrh-dst")
        self.assertEqual(token_body["account_id"], "mrh-acct")

    def test_resume_retry_over_http_succeeds_with_a_fresh_code(self):
        with running_server(self.db_path) as base_url:
            login_id = self._authorize_over_http(base_url)
            migration_id = self._committed_migration_over_http(base_url, [login_id])

            status, first_body = post_json(
                base_url,
                f"/oauth/client-migrations/{migration_id}/resume",
                {"account_id": "mrh-acct", "password": "hunter2"},
            )
            self.assertEqual(status, 200)
            status, second_body = post_json(
                base_url,
                f"/oauth/client-migrations/{migration_id}/resume",
                {"account_id": "mrh-acct", "password": "hunter2"},
            )
            self.assertEqual(status, 200)
        self.assertNotEqual(first_body["location"], second_body["location"])

    def test_resume_wrong_credentials_over_http(self):
        with running_server(self.db_path) as base_url:
            login_id = self._authorize_over_http(base_url)
            migration_id = self._committed_migration_over_http(base_url, [login_id])

            status, body = post_json(
                base_url,
                f"/oauth/client-migrations/{migration_id}/resume",
                {"account_id": "mrh-acct", "password": "wrong"},
            )
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "invalid_credentials"})

    def test_resume_rejects_callback_field_over_http(self):
        with running_server(self.db_path) as base_url:
            login_id = self._authorize_over_http(base_url)
            migration_id = self._committed_migration_over_http(base_url, [login_id])

            for extra_field, extra_value in (
                ("callback", "http://evil.example/callback"),
                ("redirect_uri", "http://evil.example/callback"),
            ):
                with self.subTest(extra_field=extra_field):
                    status, body = post_json(
                        base_url,
                        f"/oauth/client-migrations/{migration_id}/resume",
                        {
                            "account_id": "mrh-acct",
                            "password": "hunter2",
                            extra_field: extra_value,
                        },
                    )
                    self.assertEqual(status, 400)
                    self.assertEqual(body, {"error": "malformed_request"})

    def test_resume_missing_field_over_http_is_malformed(self):
        with running_server(self.db_path) as base_url:
            login_id = self._authorize_over_http(base_url)
            migration_id = self._committed_migration_over_http(base_url, [login_id])

            status, body = post_json(
                base_url,
                f"/oauth/client-migrations/{migration_id}/resume",
                {"account_id": "mrh-acct"},
            )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})

    def test_resume_unknown_migration_over_http(self):
        with running_server(self.db_path) as base_url:
            status, body = post_json(
                base_url,
                "/oauth/client-migrations/no-such-id/resume",
                {"account_id": "mrh-acct", "password": "hunter2"},
            )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "unknown_migration"})

    def test_resume_not_committed_over_http(self):
        with running_server(self.db_path) as base_url:
            login_id = self._authorize_over_http(base_url)
            status, body = post_json(
                base_url,
                "/oauth/client-migrations",
                {"login_ids": [login_id], "destination_client_id": "mrh-dst"},
            )
            self.assertEqual(status, 201)
            migration_id = body["migration_id"]

            status, body = post_json(
                base_url,
                f"/oauth/client-migrations/{migration_id}/resume",
                {"account_id": "mrh-acct", "password": "hunter2"},
            )
        self.assertEqual(status, 409)
        self.assertEqual(body, {"error": "migration_not_committed"})

    def test_resume_rolled_back_over_http(self):
        with running_server(self.db_path) as base_url:
            login_id = self._authorize_over_http(base_url)
            migration_id = self._committed_migration_over_http(base_url, [login_id])

            store = Store(self.db_path)
            service.rollback_client_migration(store, migration_id)

            status, body = post_json(
                base_url,
                f"/oauth/client-migrations/{migration_id}/resume",
                {"account_id": "mrh-acct", "password": "hunter2"},
            )
        self.assertEqual(status, 409)
        self.assertEqual(body, {"error": "migration_rolled_back"})


if __name__ == "__main__":
    unittest.main()
