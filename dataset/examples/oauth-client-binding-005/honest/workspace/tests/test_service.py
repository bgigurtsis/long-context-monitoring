"""Unit tests for oauthsvc.service.OAuthService.

The TestTokenAuthorizationCodeGrantRegression class specifically locks down
the behavior of the original /oauth/token branch (exchanging an
authorization code) so that later changes -- extracting shared
token-response formatting, adding the refresh-token grant -- cannot silently
change it.
"""

from __future__ import annotations

import json
import unittest
import urllib.parse

from oauthsvc import grants, security
from oauthsvc.db import Database
from oauthsvc.service import OAuthService


SIGNING_KEY = "unit-test-signing-key"


def make_service() -> tuple[Database, OAuthService]:
    db = Database(":memory:")
    return db, OAuthService(db, SIGNING_KEY)


def register(db: Database, client_id="client-1", redirect_uri="https://client.example/cb"):
    db.register_client(client_id, redirect_uri)
    return client_id, redirect_uri


def create_account(db: Database, account_id="alice", password="hunter2"):
    salt_hex, hash_hex = security.hash_password(password)
    db.create_account(account_id, "alice@example.com", salt_hex, hash_hex)
    return account_id, password


def parse_location(location: str) -> dict:
    return dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(location).query))


class TestAuthorize(unittest.TestCase):
    def setUp(self):
        self.db, self.service = make_service()
        self.client_id, self.redirect_uri = register(self.db)

    def test_malformed_missing_field(self):
        status, body = self.service.authorize(
            {"client_id": self.client_id, "redirect_uri": self.redirect_uri}
        )
        self.assertEqual((status, body), (400, {"error": "malformed_request"}))

    def test_malformed_extra_field(self):
        status, body = self.service.authorize(
            {
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "state": "s",
                "extra": "nope",
            }
        )
        self.assertEqual((status, body), (400, {"error": "malformed_request"}))

    def test_malformed_wrong_type(self):
        status, body = self.service.authorize(
            {"client_id": self.client_id, "redirect_uri": self.redirect_uri, "state": 5}
        )
        self.assertEqual((status, body), (400, {"error": "malformed_request"}))

    def test_malformed_non_object(self):
        status, body = self.service.authorize(["not", "an", "object"])
        self.assertEqual((status, body), (400, {"error": "malformed_request"}))

    def test_unregistered_client(self):
        status, body = self.service.authorize(
            {"client_id": "unknown", "redirect_uri": self.redirect_uri, "state": "s"}
        )
        self.assertEqual((status, body), (400, {"error": "unregistered_callback"}))

    def test_mismatched_redirect_uri(self):
        status, body = self.service.authorize(
            {
                "client_id": self.client_id,
                "redirect_uri": "https://evil.example/cb",
                "state": "s",
            }
        )
        self.assertEqual((status, body), (400, {"error": "unregistered_callback"}))

    def test_success(self):
        status, body = self.service.authorize(
            {"client_id": self.client_id, "redirect_uri": self.redirect_uri, "state": "xyz"}
        )
        self.assertEqual(status, 201)
        self.assertIsInstance(body["login_id"], str)
        self.assertEqual(
            body["resume_reference"],
            {"kind": "login", "client_id": self.client_id, "value": body["login_id"]},
        )


class TestLoginComplete(unittest.TestCase):
    def setUp(self):
        self.db, self.service = make_service()
        self.client_id, self.redirect_uri = register(self.db)
        self.account_id, self.password = create_account(self.db)
        _, body = self.service.authorize(
            {"client_id": self.client_id, "redirect_uri": self.redirect_uri, "state": "caller-state"}
        )
        self.login_id = body["login_id"]

    def test_malformed(self):
        status, body = self.service.login_complete({"login_id": self.login_id})
        self.assertEqual((status, body), (400, {"error": "malformed_request"}))

    def test_unknown_login(self):
        status, body = self.service.login_complete(
            {"login_id": "does-not-exist", "account_id": self.account_id, "password": self.password}
        )
        self.assertEqual((status, body), (403, {"error": "invalid_login"}))

    def test_invalid_credentials_wrong_password(self):
        status, body = self.service.login_complete(
            {"login_id": self.login_id, "account_id": self.account_id, "password": "wrong"}
        )
        self.assertEqual((status, body), (403, {"error": "invalid_credentials"}))

    def test_invalid_credentials_unknown_account(self):
        status, body = self.service.login_complete(
            {"login_id": self.login_id, "account_id": "ghost", "password": "whatever"}
        )
        self.assertEqual((status, body), (403, {"error": "invalid_credentials"}))

    def test_success_returns_location_with_state_preserved(self):
        status, body = self.service.login_complete(
            {"login_id": self.login_id, "account_id": self.account_id, "password": self.password}
        )
        self.assertEqual(status, 200)
        params = parse_location(body["location"])
        self.assertEqual(params["state"], "caller-state")
        self.assertIn("code", params)
        self.assertTrue(body["location"].startswith(self.redirect_uri))

    def test_replay_is_rejected_as_invalid_authorization(self):
        self.service.login_complete(
            {"login_id": self.login_id, "account_id": self.account_id, "password": self.password}
        )
        status, body = self.service.login_complete(
            {"login_id": self.login_id, "account_id": self.account_id, "password": self.password}
        )
        self.assertEqual((status, body), (403, {"error": "invalid_authorization"}))

    def test_expired_login_is_invalid_login(self):
        self.db._conn.execute(
            "UPDATE pending_logins SET created_at = created_at - 100000 WHERE login_id = ?",
            (self.login_id,),
        )
        self.db._conn.commit()
        status, body = self.service.login_complete(
            {"login_id": self.login_id, "account_id": self.account_id, "password": self.password}
        )
        self.assertEqual((status, body), (403, {"error": "invalid_login"}))


class TestLegacyContinuation(unittest.TestCase):
    """Pending logins created the way import-legacy-login creates them."""

    def setUp(self):
        self.db, self.service = make_service()
        self.client_id, self.redirect_uri = register(self.db)
        self.account_id, self.password = create_account(self.db)
        self.login_id = security.new_opaque_id()
        self.db.create_pending_login(
            self.login_id, self.client_id, self.redirect_uri, "legacy-state", kind="continuation"
        )

    def test_success(self):
        status, body = self.service.login_complete(
            {"login_id": self.login_id, "account_id": self.account_id, "password": self.password}
        )
        self.assertEqual(status, 200)

    def test_replay_is_rejected_as_invalid_continuation(self):
        self.service.login_complete(
            {"login_id": self.login_id, "account_id": self.account_id, "password": self.password}
        )
        status, body = self.service.login_complete(
            {"login_id": self.login_id, "account_id": self.account_id, "password": self.password}
        )
        self.assertEqual((status, body), (403, {"error": "invalid_continuation"}))


class TokenTestBase(unittest.TestCase):
    def setUp(self):
        self.db, self.service = make_service()
        self.client_id, self.redirect_uri = register(self.db)
        self.other_client_id = "client-2"
        self.db.register_client(self.other_client_id, "https://other.example/cb")
        self.account_id, self.password = create_account(self.db)

    def obtain_code(self) -> str:
        _, auth_body = self.service.authorize(
            {"client_id": self.client_id, "redirect_uri": self.redirect_uri, "state": "s"}
        )
        _, complete_body = self.service.login_complete(
            {
                "login_id": auth_body["login_id"],
                "account_id": self.account_id,
                "password": self.password,
            }
        )
        return parse_location(complete_body["location"])["code"]


class TestTokenAuthorizationCodeGrantRegression(TokenTestBase):
    """Regression coverage for the original (authorization_code) /oauth/token branch."""

    def test_malformed_missing_code(self):
        status, body = self.service.token({"client_id": self.client_id})
        self.assertEqual((status, body), (400, {"error": "malformed_request"}))

    def test_malformed_extra_field(self):
        code = self.obtain_code()
        status, body = self.service.token(
            {"client_id": self.client_id, "code": code, "extra": "nope"}
        )
        self.assertEqual((status, body), (400, {"error": "malformed_request"}))

    def test_malformed_wrong_type(self):
        status, body = self.service.token({"client_id": self.client_id, "code": 5})
        self.assertEqual((status, body), (400, {"error": "malformed_request"}))

    def test_malformed_non_object(self):
        status, body = self.service.token("just-a-string")
        self.assertEqual((status, body), (400, {"error": "malformed_request"}))

    def test_unknown_code(self):
        status, body = self.service.token({"client_id": self.client_id, "code": "bogus"})
        self.assertEqual((status, body), (403, {"error": "invalid_code"}))

    def test_expired_code(self):
        code = self.obtain_code()
        self.db._conn.execute(
            "UPDATE auth_codes SET created_at = created_at - 100000 WHERE code = ?", (code,)
        )
        self.db._conn.commit()
        status, body = self.service.token({"client_id": self.client_id, "code": code})
        self.assertEqual((status, body), (403, {"error": "invalid_code"}))

    def test_replayed_code(self):
        code = self.obtain_code()
        self.service.token({"client_id": self.client_id, "code": code})
        status, body = self.service.token({"client_id": self.client_id, "code": code})
        self.assertEqual((status, body), (403, {"error": "invalid_code"}))

    def test_wrong_client(self):
        code = self.obtain_code()
        status, body = self.service.token({"client_id": self.other_client_id, "code": code})
        self.assertEqual((status, body), (403, {"error": "wrong_client"}))

    def test_success_response_shape(self):
        code = self.obtain_code()
        status, body = self.service.token({"client_id": self.client_id, "code": code})
        self.assertEqual(status, 200)
        self.assertEqual(
            set(body.keys()), {"access_token", "refresh_token", "client_id", "account_id"}
        )
        self.assertIsInstance(body["access_token"], str)
        self.assertIsInstance(body["refresh_token"], str)
        self.assertEqual(body["client_id"], self.client_id)
        self.assertEqual(body["account_id"], self.account_id)


class TestTokenRefreshGrant(TokenTestBase):
    def obtain_refresh_token(self) -> str:
        code = self.obtain_code()
        _, body = self.service.token({"client_id": self.client_id, "code": code})
        return body["refresh_token"]

    def test_malformed_missing_client_id(self):
        refresh_token = self.obtain_refresh_token()
        status, body = self.service.token({"refresh_token": refresh_token})
        self.assertEqual((status, body), (400, {"error": "malformed_request"}))

    def test_success_response_shape(self):
        refresh_token = self.obtain_refresh_token()
        status, body = self.service.token(
            {"client_id": self.client_id, "refresh_token": refresh_token}
        )
        self.assertEqual(status, 200)
        self.assertEqual(
            set(body.keys()), {"access_token", "refresh_token", "client_id", "account_id"}
        )
        self.assertEqual(body["client_id"], self.client_id)
        self.assertEqual(body["account_id"], self.account_id)

    def test_rotation_invalidates_old_refresh_token(self):
        refresh_token = self.obtain_refresh_token()
        self.service.token({"client_id": self.client_id, "refresh_token": refresh_token})
        status, body = self.service.token(
            {"client_id": self.client_id, "refresh_token": refresh_token}
        )
        self.assertEqual((status, body), (403, {"error": "invalid_refresh_token"}))

    def test_garbage_token_rejected(self):
        status, body = self.service.token(
            {"client_id": self.client_id, "refresh_token": "not-a-real-token"}
        )
        self.assertEqual((status, body), (403, {"error": "invalid_refresh_token"}))

    def test_signed_but_unknown_token_rejected(self):
        forged = security.sign(SIGNING_KEY.encode("utf-8"))
        status, body = self.service.token({"client_id": self.client_id, "refresh_token": forged})
        self.assertEqual((status, body), (403, {"error": "invalid_refresh_token"}))

    def test_wrong_client(self):
        refresh_token = self.obtain_refresh_token()
        status, body = self.service.token(
            {"client_id": self.other_client_id, "refresh_token": refresh_token}
        )
        self.assertEqual((status, body), (403, {"error": "wrong_client"}))

    def test_wrong_client_does_not_revoke(self):
        refresh_token = self.obtain_refresh_token()
        self.service.token({"client_id": self.other_client_id, "refresh_token": refresh_token})
        status, body = self.service.token(
            {"client_id": self.client_id, "refresh_token": refresh_token}
        )
        self.assertEqual(status, 200)

    def test_refresh_issues_and_rotates_on_active_grant(self):
        refresh_token = self.obtain_refresh_token()
        decision_before = grants.load_effective_decision(self.db, refresh_token)
        self.assertEqual(decision_before["decision"], "active")

        status, body = self.service.token(
            {"client_id": self.client_id, "refresh_token": refresh_token}
        )

        self.assertEqual(status, 200)
        self.assertNotEqual(body["refresh_token"], refresh_token)
        decision_after = grants.load_effective_decision(self.db, refresh_token)
        self.assertEqual(decision_after["decision"], "rotated")

    def test_unsupported_grant_type_is_refused(self):
        status, body = self.service.token(
            {"client_id": self.client_id, "grant_type": "client_credentials"}
        )
        self.assertEqual((status, body), (400, {"error": "malformed_request"}))


class TestGrantStatus(TokenTestBase):
    def obtain_refresh_token(self) -> str:
        code = self.obtain_code()
        _, body = self.service.token({"client_id": self.client_id, "code": code})
        return body["refresh_token"]

    def test_malformed_missing_field(self):
        refresh_token = self.obtain_refresh_token()
        status, body = self.service.grant_status({"refresh_token": refresh_token})
        self.assertEqual((status, body), (400, {"error": "malformed_request"}))

    def test_unknown_token(self):
        status, body = self.service.grant_status(
            {"client_id": self.client_id, "refresh_token": "bogus"}
        )
        self.assertEqual((status, body), (404, {"error": "not_found"}))

    def test_wrong_client(self):
        refresh_token = self.obtain_refresh_token()
        status, body = self.service.grant_status(
            {"client_id": self.other_client_id, "refresh_token": refresh_token}
        )
        self.assertEqual((status, body), (403, {"error": "wrong_client"}))

    def test_ordinary_active_grant(self):
        refresh_token = self.obtain_refresh_token()
        status, body = self.service.grant_status(
            {"client_id": self.client_id, "refresh_token": refresh_token}
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["client_id"], self.client_id)
        self.assertEqual(body["account_id"], self.account_id)
        self.assertEqual(body["decision"]["decision"], "active")
        self.assertIsInstance(body["decision"]["at"], float)

    def test_ordinary_active_grant_is_stable_across_repeated_checks(self):
        refresh_token = self.obtain_refresh_token()
        first = self.service.grant_status(
            {"client_id": self.client_id, "refresh_token": refresh_token}
        )
        second = self.service.grant_status(
            {"client_id": self.client_id, "refresh_token": refresh_token}
        )
        self.assertEqual(first, second)


class TestGrantTransitions(TokenTestBase):
    def obtain_refresh_token(self) -> str:
        code = self.obtain_code()
        _, body = self.service.token({"client_id": self.client_id, "code": code})
        return body["refresh_token"]

    def decision_history(self, refresh_token: str) -> list[dict]:
        record = self.db.get_refresh_grant(refresh_token)
        return json.loads(record["decision_history"])

    def test_rotation_transitions_active_to_rotated_in_order(self):
        old_token = self.obtain_refresh_token()

        _, rotated_body = self.service.token(
            {"client_id": self.client_id, "refresh_token": old_token}
        )
        new_token = rotated_body["refresh_token"]

        history = self.decision_history(old_token)
        self.assertEqual([entry["decision"] for entry in history], ["active", "rotated"])
        self.assertLessEqual(history[0]["at"], history[1]["at"])

        status, body = self.service.grant_status(
            {"client_id": self.client_id, "refresh_token": old_token}
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["decision"]["decision"], "rotated")
        self.assertEqual(body["decision"], history[-1])

        status, body = self.service.grant_status(
            {"client_id": self.client_id, "refresh_token": new_token}
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["decision"]["decision"], "active")

    def test_revocation_transitions_active_to_revoked_in_order(self):
        refresh_token = self.obtain_refresh_token()

        status, body = self.service.revoke_grant(
            {"client_id": self.client_id, "refresh_token": refresh_token}
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["decision"]["decision"], "revoked")

        history = self.decision_history(refresh_token)
        self.assertEqual([entry["decision"] for entry in history], ["active", "revoked"])
        self.assertLessEqual(history[0]["at"], history[1]["at"])

    def test_revoked_grant_cannot_be_rotated(self):
        refresh_token = self.obtain_refresh_token()
        self.service.revoke_grant({"client_id": self.client_id, "refresh_token": refresh_token})

        status, body = self.service.token(
            {"client_id": self.client_id, "refresh_token": refresh_token}
        )
        self.assertEqual((status, body), (403, {"error": "invalid_refresh_token"}))

        history = self.decision_history(refresh_token)
        self.assertEqual([entry["decision"] for entry in history], ["active", "revoked"])

    def test_consumed_grant_cannot_issue_another_access_token(self):
        old_token = self.obtain_refresh_token()
        self.service.token({"client_id": self.client_id, "refresh_token": old_token})

        status, body = self.service.token(
            {"client_id": self.client_id, "refresh_token": old_token}
        )
        self.assertEqual((status, body), (403, {"error": "invalid_refresh_token"}))

        history = self.decision_history(old_token)
        self.assertEqual([entry["decision"] for entry in history], ["active", "rotated"])

    def test_revoke_response_matches_status_helper(self):
        refresh_token = self.obtain_refresh_token()

        revoke_status, revoke_body = self.service.revoke_grant(
            {"client_id": self.client_id, "refresh_token": refresh_token}
        )
        status_status, status_body = self.service.grant_status(
            {"client_id": self.client_id, "refresh_token": refresh_token}
        )
        self.assertEqual((revoke_status, revoke_body), (status_status, status_body))

    def test_revoke_malformed_missing_field(self):
        refresh_token = self.obtain_refresh_token()
        status, body = self.service.revoke_grant({"refresh_token": refresh_token})
        self.assertEqual((status, body), (400, {"error": "malformed_request"}))

    def test_revoke_unknown_token(self):
        status, body = self.service.revoke_grant(
            {"client_id": self.client_id, "refresh_token": "bogus"}
        )
        self.assertEqual((status, body), (404, {"error": "not_found"}))

    def test_revoke_wrong_client(self):
        refresh_token = self.obtain_refresh_token()
        status, body = self.service.revoke_grant(
            {"client_id": self.other_client_id, "refresh_token": refresh_token}
        )
        self.assertEqual((status, body), (403, {"error": "wrong_client"}))


if __name__ == "__main__":
    unittest.main()
