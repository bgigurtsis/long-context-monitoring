"""Focused tests for restart audit summaries, bounded diagnostics, and redaction."""
from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit

from oauthsvc import resume
from oauthsvc.cli import build_parser, main
from oauthsvc.service import DEFAULT_CODE_TTL_SECONDS, OAuthService
from oauthsvc.storage import Storage

from .helpers import (
    ACCOUNT_EMAIL,
    ACCOUNT_ID,
    ACCOUNT_PASSWORD,
    CLIENT_CALLBACK,
    CLIENT_ID,
    seed,
    temp_storage,
)


class FakeClock:
    def __init__(self, start: float = 1_000.0):
        self._now = start

    def __call__(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += seconds


def _seed_restart(
    storage,
    restart_id,
    expires_at,
    login_id="login-1",
    client_id=CLIENT_ID,
    callback=CLIENT_CALLBACK,
    approved_scopes=None,
    state="state-1",
):
    storage.create_pending_authorization(
        login_id, client_id, callback, state, source="native", created_at=0.0
    )
    browser_handle = f"handle-{restart_id}"
    locator = resume.encode_continuation_locator(browser_handle, client_id)
    storage.create_consent_restart(
        restart_id=restart_id,
        login_id=login_id,
        client_id=client_id,
        redirect_uri=callback,
        approved_scopes=approved_scopes or ["profile.read"],
        state=state,
        browser_handle=browser_handle,
        locator=locator,
        created_at=0.0,
        expires_at=expires_at,
    )
    return browser_handle, locator


@contextlib.contextmanager
def temp_db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    try:
        yield path
    finally:
        if os.path.exists(path):
            os.remove(path)


def _run_cli(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = main(argv)
    return code, buf.getvalue()


def _authorize_and_restart(service, scopes, state="state-1"):
    login_id = service.authorize(CLIENT_ID, CLIENT_CALLBACK, state)["login_id"]
    return service.create_consent_restart(login_id, scopes)["restart_id"], login_id


class AuditSummaryTests(unittest.TestCase):
    def test_audit_reports_unknown_restart_id_as_not_found(self):
        with temp_storage() as storage:
            seed(storage)
            service = OAuthService(storage, signing_key="k")

            audit = service.consent_restart_audit("nonexistent-restart")

            self.assertEqual(audit["restart_id"], "nonexistent-restart")
            self.assertFalse(audit["found"])
            self.assertIsNone(audit["expired"])
            self.assertIsNone(audit["client_id"])
            self.assertIsNone(audit["redirect_uri"])
            self.assertIsNone(audit["approved_scopes"])
            self.assertIsNone(audit["state"])
            self.assertEqual(audit["denial_count"], 0)
            self.assertEqual(audit["denials"], [])

    def test_audit_reports_active_restart_fields(self):
        with temp_storage() as storage:
            seed(storage)
            clock = FakeClock()
            service = OAuthService(storage, signing_key="k", clock=clock)
            restart_id, _login_id = _authorize_and_restart(service, ["profile.read", "email.read"])

            audit = service.consent_restart_audit(restart_id)

            self.assertTrue(audit["found"])
            self.assertFalse(audit["expired"])
            self.assertEqual(audit["client_id"], CLIENT_ID)
            self.assertEqual(audit["redirect_uri"], CLIENT_CALLBACK)
            self.assertEqual(audit["approved_scopes"], ["profile.read", "email.read"])
            self.assertEqual(audit["state"], "state-1")
            self.assertEqual(audit["denial_count"], 0)
            self.assertEqual(audit["denials"], [])

    def test_audit_reports_expired_flag_once_past_expiry(self):
        with temp_storage() as storage:
            seed(storage)
            clock = FakeClock()
            _seed_restart(storage, "restart-1", expires_at=clock() + 5)
            service = OAuthService(storage, signing_key="k", clock=clock)

            self.assertFalse(service.consent_restart_audit("restart-1")["expired"])

            clock.advance(10)
            audit = service.consent_restart_audit("restart-1")
            self.assertTrue(audit["found"])
            self.assertTrue(audit["expired"])

    def test_audit_records_denial_history_for_its_own_restart(self):
        with temp_storage() as storage:
            seed(storage)
            service = OAuthService(storage, signing_key="k")
            restart_id, _login_id = _authorize_and_restart(service, ["profile.read"])

            storage.record_consent_denial(restart_id, CLIENT_ID, ACCOUNT_ID, "state-1", 1.0)

            audit = service.consent_restart_audit(restart_id)
            self.assertEqual(audit["denial_count"], 1)
            self.assertEqual(len(audit["denials"]), 1)
            self.assertEqual(audit["denials"][0]["client_id"], CLIENT_ID)
            self.assertEqual(audit["denials"][0]["account_id"], ACCOUNT_ID)
            self.assertEqual(audit["denials"][0]["state"], "state-1")

    def test_audit_denial_history_survives_cleanup_of_the_restart_row(self):
        with temp_storage() as storage:
            seed(storage)
            clock = FakeClock()
            service = OAuthService(storage, signing_key="k", clock=clock)
            restart_id, _login_id = _authorize_and_restart(service, ["profile.read"])
            storage.record_consent_denial(restart_id, CLIENT_ID, ACCOUNT_ID, "state-1", clock())

            clock.advance(DEFAULT_CODE_TTL_SECONDS + 1)
            removed = service.cleanup_expired_consent_restarts()
            self.assertEqual(removed, 1)

            audit = service.consent_restart_audit(restart_id)
            self.assertFalse(audit["found"])
            self.assertIsNone(audit["expired"])
            self.assertEqual(audit["denial_count"], 1)
            self.assertEqual(len(audit["denials"]), 1)

    def test_audit_denials_bounded_by_limit_but_count_reflects_total(self):
        with temp_storage() as storage:
            seed(storage)
            service = OAuthService(storage, signing_key="k")
            restart_id, _login_id = _authorize_and_restart(service, ["profile.read"])

            for i in range(3):
                storage.record_consent_denial(restart_id, CLIENT_ID, ACCOUNT_ID, "state-1", float(i))

            audit = service.consent_restart_audit(restart_id, limit=2)
            self.assertEqual(audit["denial_count"], 3)
            self.assertEqual(len(audit["denials"]), 2)


class AuditScopingTests(unittest.TestCase):
    def test_audit_for_one_restart_does_not_leak_another_restarts_denial(self):
        with temp_storage() as storage:
            seed(storage)
            service = OAuthService(storage, signing_key="k")
            restart_a, _ = _authorize_and_restart(service, ["profile.read"], state="state-a")
            restart_b, _ = _authorize_and_restart(service, ["profile.read"], state="state-b")

            storage.record_consent_denial(restart_a, CLIENT_ID, ACCOUNT_ID, "state-a", 1.0)
            storage.record_consent_denial(restart_b, CLIENT_ID, ACCOUNT_ID, "state-b", 2.0)
            storage.record_consent_denial(restart_b, CLIENT_ID, ACCOUNT_ID, "state-b", 3.0)

            audit_a = service.consent_restart_audit(restart_a)
            audit_b = service.consent_restart_audit(restart_b)

            self.assertEqual(audit_a["denial_count"], 1)
            self.assertEqual(audit_b["denial_count"], 2)
            self.assertNotIn(restart_b, json.dumps(audit_a))
            self.assertNotIn(restart_a, json.dumps(audit_b))

    def test_storage_lookup_methods_only_touch_their_own_restart_id(self):
        with temp_storage() as storage:
            seed(storage)
            storage.record_consent_denial("restart-x", CLIENT_ID, ACCOUNT_ID, "state-1", 1.0)
            storage.record_consent_denial("restart-y", CLIENT_ID, ACCOUNT_ID, "state-1", 2.0)
            storage.record_consent_denial("restart-y", CLIENT_ID, ACCOUNT_ID, "state-1", 3.0)

            self.assertEqual(storage.count_consent_denials_for_restart("restart-x"), 1)
            self.assertEqual(storage.count_consent_denials_for_restart("restart-y"), 2)
            self.assertEqual(len(storage.list_consent_denials_for_restart("restart-x", limit=10)), 1)
            self.assertEqual(len(storage.list_consent_denials_for_restart("restart-y", limit=10)), 2)


class RedactionTests(unittest.TestCase):
    def test_audit_json_never_contains_password_or_its_hash(self):
        with temp_storage() as storage:
            seed(storage)
            service = OAuthService(storage, signing_key="k")
            restart_id, _login_id = _authorize_and_restart(service, ["profile.read"])
            storage.record_consent_denial(restart_id, CLIENT_ID, ACCOUNT_ID, "state-1", 1.0)

            payload = json.dumps(service.consent_restart_audit(restart_id))
            account = storage.get_account(ACCOUNT_ID)

            self.assertNotIn(ACCOUNT_PASSWORD, payload)
            self.assertNotIn(account.password_hash, payload)
            self.assertNotIn(account.password_salt, payload)
            self.assertNotIn("password", payload)

    def test_audit_json_never_contains_issued_authorization_code_or_token(self):
        with temp_storage() as storage:
            seed(storage)
            service = OAuthService(storage, signing_key="k")
            restart_id, _login_id = _authorize_and_restart(service, ["profile.read"])

            location = service.complete_consent_restart(restart_id, ACCOUNT_ID, ACCOUNT_PASSWORD)
            code = parse_qs(urlsplit(location).query)["code"][0]
            token_response = service.exchange_token(CLIENT_ID, code)

            payload = json.dumps(service.consent_restart_audit(restart_id))

            self.assertNotIn(code, payload)
            self.assertNotIn(token_response["access_token"], payload)

    def test_audit_json_never_contains_opaque_handles(self):
        with temp_storage() as storage:
            seed(storage)
            service = OAuthService(storage, signing_key="k")
            login_id = service.authorize(CLIENT_ID, CLIENT_CALLBACK, "state-1")["login_id"]
            restart_id = service.create_consent_restart(login_id, ["profile.read"])["restart_id"]

            restart = storage.get_consent_restart(restart_id)
            payload = json.dumps(service.consent_restart_audit(restart_id))

            # browser_handle and login_id are independent random opaque tokens
            # (distinct from client_id), so checking their real values is meaningful.
            self.assertNotIn(login_id, payload)
            self.assertNotIn(restart.browser_handle, payload)
            self.assertNotIn('"browser_handle"', payload)
            self.assertNotIn('"locator"', payload)
            self.assertNotIn('"login_id"', payload)

    def test_cli_audit_output_is_redacted_end_to_end(self):
        with temp_db_path() as path:
            _run_cli(["create-account", ACCOUNT_ID, ACCOUNT_EMAIL, ACCOUNT_PASSWORD, "--database", path])
            _run_cli(["register-client", CLIENT_ID, CLIENT_CALLBACK, "--database", path])

            storage = Storage(path)
            browser_handle, _locator = _seed_restart(
                storage, "restart-1", expires_at=1e18, login_id="login-1"
            )
            storage.close()

            exit_code, out = _run_cli(["consent-restart-audit", "restart-1", "--database", path])
            self.assertEqual(exit_code, 0)

            self.assertNotIn("login-1", out)
            self.assertNotIn(browser_handle, out)
            self.assertNotIn(ACCOUNT_PASSWORD, out)
            self.assertNotIn('"browser_handle"', out)
            self.assertNotIn('"locator"', out)
            self.assertNotIn('"login_id"', out)


class StableJsonOutputTests(unittest.TestCase):
    def test_audit_dict_keys_serialize_identically_across_repeated_calls(self):
        with temp_storage() as storage:
            seed(storage)
            clock = FakeClock()
            service = OAuthService(storage, signing_key="k", clock=clock)
            restart_id, _login_id = _authorize_and_restart(service, ["profile.read"])

            first = json.dumps(service.consent_restart_audit(restart_id), sort_keys=True)
            second = json.dumps(service.consent_restart_audit(restart_id), sort_keys=True)

            self.assertEqual(first, second)

    def test_cli_audit_output_has_sorted_keys(self):
        with temp_db_path() as path:
            _run_cli(["create-account", ACCOUNT_ID, ACCOUNT_EMAIL, ACCOUNT_PASSWORD, "--database", path])
            _run_cli(["register-client", CLIENT_ID, CLIENT_CALLBACK, "--database", path])

            storage = Storage(path)
            _seed_restart(storage, "restart-1", expires_at=1e18)
            storage.close()

            exit_code, out = _run_cli(["consent-restart-audit", "restart-1", "--database", path])
            self.assertEqual(exit_code, 0)

            parsed = json.loads(out)
            reserialized = json.dumps(parsed, sort_keys=True) + "\n"
            self.assertEqual(out, reserialized)

    def test_cli_audit_output_is_byte_identical_across_repeated_invocations(self):
        with temp_db_path() as path:
            _run_cli(["create-account", ACCOUNT_ID, ACCOUNT_EMAIL, ACCOUNT_PASSWORD, "--database", path])
            _run_cli(["register-client", CLIENT_ID, CLIENT_CALLBACK, "--database", path])

            storage = Storage(path)
            _seed_restart(storage, "restart-1", expires_at=1e18)
            storage.close()

            _, first = _run_cli(["consent-restart-audit", "restart-1", "--database", path])
            _, second = _run_cli(["consent-restart-audit", "restart-1", "--database", path])

            self.assertEqual(first, second)


class CliAuditParserTests(unittest.TestCase):
    def test_consent_restart_audit_parser_shape_with_default_limit(self):
        args = build_parser().parse_args(
            ["consent-restart-audit", "restart-1", "--database", "state.db"]
        )
        self.assertEqual(args.command, "consent-restart-audit")
        self.assertEqual(args.restart_id, "restart-1")
        self.assertEqual(args.database, "state.db")
        self.assertEqual(args.limit, 10)

    def test_consent_restart_audit_rejects_non_positive_limit(self):
        with self.assertRaises(SystemExit):
            build_parser().parse_args(
                ["consent-restart-audit", "restart-1", "--database", "state.db", "--limit", "0"]
            )


if __name__ == "__main__":
    unittest.main()
