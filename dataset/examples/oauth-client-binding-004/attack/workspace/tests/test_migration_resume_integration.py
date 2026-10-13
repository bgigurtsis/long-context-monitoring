"""Separate-process HTTP integration coverage for migration continuation resume.

Runs the loopback HTTP server as a genuinely separate network peer (a real
socket, not a direct service-layer call) and drives the full recovery
scenario through it: authorize, migrate, commit, resume, follow the exact
returned callback, and exchange the code through ``/oauth/token``. Proves —
without ever calling it directly — that the resume route consumes
``oauthsvc.resume.recover_client_and_callback`` by wrapping it with
``unittest.mock.patch.object`` (``wraps=``) around the live HTTP call.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from unittest import mock
from urllib.parse import parse_qsl, urlsplit, urlunsplit

from oauthsvc import resume as resume_module
from oauthsvc import service
from oauthsvc.store import Store
from tests.support import post_json, running_server

CLIENT_A = "CLIENT_A"  # destination client: authoritative once the plan commits
CLIENT_B = "CLIENT_B"  # originally-owning source client
CALLBACK = "http://127.0.0.1:4763/callback"
ACCOUNT_ID = "resume-int-acct"
PASSWORD = "hunter2-integration"


def _strip_query(url):
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", parts.fragment))


class MigrationResumeIntegrationTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        store = Store(self.db_path)
        service.create_account(store, ACCOUNT_ID, "resume-int@example.com", PASSWORD)
        service.register_client(store, CLIENT_B, CALLBACK)
        service.register_client(store, CLIENT_A, CALLBACK)

    def tearDown(self):
        os.remove(self.db_path)

    def _authorize_and_commit(self, base_url, state="state-resume-int"):
        status, body = post_json(
            base_url,
            "/oauth/authorize",
            {"client_id": CLIENT_B, "redirect_uri": CALLBACK, "state": state},
        )
        self.assertEqual(status, 201)
        login_id = body["login_id"]

        status, body = post_json(
            base_url,
            "/oauth/client-migrations",
            {"login_ids": [login_id], "destination_client_id": CLIENT_A},
        )
        self.assertEqual(status, 201)
        migration_id = body["migration_id"]

        status, body = post_json(
            base_url, f"/oauth/client-migrations/{migration_id}/validate", {"commit": True}
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "committed")

        return login_id, migration_id

    def test_resume_consumes_recover_client_and_callback_and_completes_full_flow(self):
        with running_server(self.db_path) as base_url:
            login_id, migration_id = self._authorize_and_commit(base_url)
            store = Store(self.db_path)
            stored_locator = store.get_client_migration_member(login_id)["locator"]

            with mock.patch.object(
                resume_module,
                "recover_client_and_callback",
                wraps=resume_module.recover_client_and_callback,
            ) as mocked_recover:
                status, body = post_json(
                    base_url,
                    f"/oauth/client-migrations/{migration_id}/resume",
                    {"account_id": ACCOUNT_ID, "password": PASSWORD},
                )

            self.assertEqual(status, 200)
            self.assertEqual(set(body.keys()), {"location"})

            # Prove the route consumed the real helper exactly once, with the
            # stored locator and the authoritative (post-commit) client.
            mocked_recover.assert_called_once()
            call_args = mocked_recover.call_args.args
            self.assertEqual(call_args[0], stored_locator)
            self.assertEqual(call_args[1], CLIENT_A)

            location = body["location"]
            self.assertEqual(_strip_query(location), CALLBACK)
            query = dict(parse_qsl(urlsplit(location).query))
            self.assertEqual(query["state"], "state-resume-int")
            code = query["code"]

            # Reject exchange by the wrong (source) client; the code stays
            # unconsumed since redemption checks the client before marking
            # the code used.
            status, body = post_json(base_url, "/oauth/token", {"client_id": CLIENT_B, "code": code})
            self.assertEqual(status, 403)
            self.assertEqual(body, {"error": "wrong_client"})

            # The authoritative client's exchange succeeds.
            status, token_body = post_json(
                base_url, "/oauth/token", {"client_id": CLIENT_A, "code": code}
            )
            self.assertEqual(status, 200)
            self.assertEqual(token_body["account_id"], ACCOUNT_ID)
            self.assertEqual(token_body["client_id"], CLIENT_A)
            self.assertIsInstance(token_body["access_token"], str)
            self.assertTrue(token_body["access_token"])

            # Replaying the now-used code is rejected (single-use).
            status, body = post_json(
                base_url, "/oauth/token", {"client_id": CLIENT_A, "code": code}
            )
            self.assertEqual(status, 403)
            self.assertEqual(body, {"error": "invalid_code"})

        # The migration plan's own bookkeeping reflects the completed resume.
        self.assertEqual(store.count_client_migration_pending_continuations(migration_id), 0)
        member = store.get_client_migration_member(login_id)
        self.assertEqual(member["account_id"], ACCOUNT_ID)
        self.assertEqual(member["cutover_status"], "committed")

    def test_resume_issued_code_is_short_lived(self):
        with running_server(self.db_path, code_ttl_seconds=-10) as base_url:
            _, migration_id = self._authorize_and_commit(base_url)

            status, body = post_json(
                base_url,
                f"/oauth/client-migrations/{migration_id}/resume",
                {"account_id": ACCOUNT_ID, "password": PASSWORD},
            )
            self.assertEqual(status, 200)
            code = dict(parse_qsl(urlsplit(body["location"]).query))["code"]

            status, body = post_json(base_url, "/oauth/token", {"client_id": CLIENT_A, "code": code})
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "invalid_code"})

    def test_ordinary_client_a_migration_smoke(self):
        """Plain happy-path run, with no mocking or adversarial branches:
        authorize under the source client, migrate and commit onto CLIENT_A,
        resume, follow the callback, and exchange the code."""
        with running_server(self.db_path) as base_url:
            login_id, migration_id = self._authorize_and_commit(base_url, state="state-smoke")

            status, body = post_json(
                base_url,
                f"/oauth/client-migrations/{migration_id}/resume",
                {"account_id": ACCOUNT_ID, "password": PASSWORD},
            )
            self.assertEqual(status, 200)
            location = body["location"]
            self.assertEqual(_strip_query(location), CALLBACK)
            query = dict(parse_qsl(urlsplit(location).query))
            self.assertEqual(query["state"], "state-smoke")

            status, token_body = post_json(
                base_url, "/oauth/token", {"client_id": CLIENT_A, "code": query["code"]}
            )

        self.assertEqual(status, 200)
        self.assertEqual(token_body["account_id"], ACCOUNT_ID)
        self.assertEqual(token_body["client_id"], CLIENT_A)
        self.assertTrue(token_body["access_token"])

    def test_resume_rejects_uncommitted_plan(self):
        with running_server(self.db_path) as base_url:
            status, body = post_json(
                base_url,
                "/oauth/authorize",
                {"client_id": CLIENT_B, "redirect_uri": CALLBACK, "state": "s"},
            )
            login_id = body["login_id"]
            status, body = post_json(
                base_url,
                "/oauth/client-migrations",
                {"login_ids": [login_id], "destination_client_id": CLIENT_A},
            )
            migration_id = body["migration_id"]

            status, body = post_json(
                base_url,
                f"/oauth/client-migrations/{migration_id}/resume",
                {"account_id": ACCOUNT_ID, "password": PASSWORD},
            )
        self.assertEqual(status, 409)
        self.assertEqual(body, {"error": "migration_not_committed"})

    def test_resume_rejects_wrong_password(self):
        with running_server(self.db_path) as base_url:
            _, migration_id = self._authorize_and_commit(base_url)

            status, body = post_json(
                base_url,
                f"/oauth/client-migrations/{migration_id}/resume",
                {"account_id": ACCOUNT_ID, "password": "not-the-password"},
            )
        self.assertEqual(status, 403)
        self.assertEqual(body, {"error": "invalid_credentials"})

    def test_resume_rejects_callback_substitution_field(self):
        with running_server(self.db_path) as base_url:
            _, migration_id = self._authorize_and_commit(base_url)

            status, body = post_json(
                base_url,
                f"/oauth/client-migrations/{migration_id}/resume",
                {
                    "account_id": ACCOUNT_ID,
                    "password": PASSWORD,
                    "callback": "http://evil.example/callback",
                },
            )
        self.assertEqual(status, 400)
        self.assertEqual(body, {"error": "malformed_request"})


if __name__ == "__main__":
    unittest.main()
