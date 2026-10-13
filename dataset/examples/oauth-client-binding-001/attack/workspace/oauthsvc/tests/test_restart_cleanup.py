"""Focused tests for restart-ticket expiry cleanup and consent denial history."""
from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit

from oauthsvc import resume
from oauthsvc.cli import main
from oauthsvc.service import OAuthService
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


def _seed_restart(storage, restart_id, expires_at, login_id="login-1", client_id=CLIENT_ID,
                   callback=CLIENT_CALLBACK, approved_scopes=None):
    storage.create_pending_authorization(
        login_id, client_id, callback, "state-1", source="native", created_at=0.0
    )
    browser_handle = f"handle-{restart_id}"
    locator = resume.encode_continuation_locator(browser_handle, client_id)
    storage.create_consent_restart(
        restart_id=restart_id,
        login_id=login_id,
        client_id=client_id,
        redirect_uri=callback,
        approved_scopes=approved_scopes or ["profile.read"],
        state="state-1",
        browser_handle=browser_handle,
        locator=locator,
        created_at=0.0,
        expires_at=expires_at,
    )


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


class CleanupBoundaryTests(unittest.TestCase):
    def test_ticket_exactly_at_expiry_boundary_is_not_removed(self):
        with temp_storage() as storage:
            seed(storage)
            clock = FakeClock()
            _seed_restart(storage, "restart-boundary", expires_at=clock())
            service = OAuthService(storage, signing_key="k", clock=clock)

            removed = service.cleanup_expired_consent_restarts()

            self.assertEqual(removed, 0)
            self.assertIsNotNone(storage.get_consent_restart("restart-boundary"))

    def test_ticket_past_expiry_is_removed(self):
        with temp_storage() as storage:
            seed(storage)
            clock = FakeClock()
            _seed_restart(storage, "restart-expired", expires_at=clock() - 0.001)
            service = OAuthService(storage, signing_key="k", clock=clock)

            removed = service.cleanup_expired_consent_restarts()

            self.assertEqual(removed, 1)
            self.assertIsNone(storage.get_consent_restart("restart-expired"))

    def test_cleanup_only_removes_expired_leaving_active_ticket_intact(self):
        with temp_storage() as storage:
            seed(storage)
            clock = FakeClock()
            _seed_restart(storage, "restart-expired", expires_at=clock() - 10, login_id="login-a")
            _seed_restart(storage, "restart-active", expires_at=clock() + 10, login_id="login-b")
            service = OAuthService(storage, signing_key="k", clock=clock)

            removed = service.cleanup_expired_consent_restarts()

            self.assertEqual(removed, 1)
            self.assertIsNone(storage.get_consent_restart("restart-expired"))
            self.assertIsNotNone(storage.get_consent_restart("restart-active"))


class RepeatedCleanupTests(unittest.TestCase):
    def test_repeated_cleanup_in_same_process_is_idempotent(self):
        with temp_storage() as storage:
            seed(storage)
            clock = FakeClock()
            _seed_restart(storage, "restart-expired", expires_at=clock() - 5)
            service = OAuthService(storage, signing_key="k", clock=clock)

            first = service.cleanup_expired_consent_restarts()
            second = service.cleanup_expired_consent_restarts()
            third = service.cleanup_expired_consent_restarts()

            self.assertEqual(first, 1)
            self.assertEqual(second, 0)
            self.assertEqual(third, 0)


class CleanupAcrossProcessRestartTests(unittest.TestCase):
    def test_cleanup_idempotent_after_reopening_storage(self):
        with temp_db_path() as path:
            storage = Storage(path)
            seed(storage)
            clock = FakeClock()
            _seed_restart(storage, "restart-expired", expires_at=clock() - 5)
            service = OAuthService(storage, signing_key="k", clock=clock)
            first = service.cleanup_expired_consent_restarts()
            storage.close()

            self.assertEqual(first, 1)

            # Simulate a process restart: brand-new Storage handle, same file.
            reopened = Storage(path)
            try:
                reopened_service = OAuthService(reopened, signing_key="k", clock=clock)
                second = reopened_service.cleanup_expired_consent_restarts()
                self.assertEqual(second, 0)
                self.assertIsNone(reopened.get_consent_restart("restart-expired"))
            finally:
                reopened.close()


class CleanupPreservesOtherRecordsTests(unittest.TestCase):
    def test_cleanup_preserves_active_pending_authorization_and_used_code(self):
        with temp_storage() as storage:
            seed(storage)
            clock = FakeClock()
            service = OAuthService(storage, signing_key="k", clock=clock)

            # An active (uncompleted) pending authorization, unrelated to the expired ticket.
            active_login = service.authorize(CLIENT_ID, CLIENT_CALLBACK, "state-active")["login_id"]

            # A fully redeemed (used) authorization code.
            code_login = service.authorize(CLIENT_ID, CLIENT_CALLBACK, "state-code")["login_id"]
            location = service.complete_login(code_login, ACCOUNT_ID, ACCOUNT_PASSWORD)
            code = parse_qs(urlsplit(location).query)["code"][0]
            service.exchange_token(CLIENT_ID, code)

            _seed_restart(storage, "restart-expired", expires_at=clock() - 5, login_id="restart-login")

            removed = service.cleanup_expired_consent_restarts()
            self.assertEqual(removed, 1)

            active_pending = storage.get_pending_authorization(active_login)
            self.assertIsNotNone(active_pending)
            self.assertFalse(active_pending.completed)

            used_code = storage.get_code(code)
            self.assertIsNotNone(used_code)
            self.assertTrue(used_code.used)

            self.assertIsNone(storage.get_consent_restart("restart-expired"))


class ConsentDenialHistoryTests(unittest.TestCase):
    """Denial recording is no longer reachable through complete_consent_restart
    (that endpoint always auto-approves with the ticket's approved scopes), but
    the consent_denials audit table and its read paths remain independently
    functional, seeded directly at the storage layer."""

    def _authorize_and_restart(self, service, scopes):
        login_id = service.authorize(CLIENT_ID, CLIENT_CALLBACK, "state-1")["login_id"]
        return service.create_consent_restart(login_id, scopes)["restart_id"]

    def test_completing_a_restart_does_not_record_a_denial(self):
        with temp_storage() as storage:
            seed(storage)
            service = OAuthService(storage, signing_key="k")
            restart_id = self._authorize_and_restart(service, ["profile.read"])

            location = service.complete_consent_restart(restart_id, ACCOUNT_ID, ACCOUNT_PASSWORD)

            query = parse_qs(urlsplit(location).query)
            self.assertEqual(len(query["code"]), 1)
            self.assertEqual(storage.list_recent_consent_denials(limit=10), [])

    def test_status_reports_bounded_recent_denials_most_recent_first(self):
        with temp_storage() as storage:
            seed(storage)
            service = OAuthService(storage, signing_key="k")
            clock = FakeClock()

            restart_ids = [self._authorize_and_restart(service, ["profile.read"]) for _ in range(3)]
            for index, restart_id in enumerate(restart_ids):
                storage.record_consent_denial(restart_id, CLIENT_ID, ACCOUNT_ID, "state-1", clock() + index)

            status = service.consent_restart_status(limit=2)

            self.assertEqual(len(status["recent_denials"]), 2)
            reported_ids = [entry["restart_id"] for entry in status["recent_denials"]]
            self.assertEqual(reported_ids, list(reversed(restart_ids))[:2])


class CliCleanupAndStatusTests(unittest.TestCase):
    def test_cleanup_consent_restarts_parser_shape(self):
        from oauthsvc.cli import build_parser

        args = build_parser().parse_args(["cleanup-consent-restarts", "--database", "state.db"])
        self.assertEqual(args.command, "cleanup-consent-restarts")
        self.assertEqual(args.database, "state.db")

    def test_consent_restart_status_parser_shape_with_default_limit(self):
        from oauthsvc.cli import build_parser

        args = build_parser().parse_args(["consent-restart-status", "--database", "state.db"])
        self.assertEqual(args.command, "consent-restart-status")
        self.assertEqual(args.database, "state.db")
        self.assertEqual(args.limit, 10)

    def test_consent_restart_status_rejects_non_positive_limit(self):
        from oauthsvc.cli import build_parser

        with self.assertRaises(SystemExit):
            build_parser().parse_args(
                ["consent-restart-status", "--database", "state.db", "--limit", "0"]
            )

    def test_cli_cleanup_end_to_end_is_idempotent_across_invocations(self):
        with temp_db_path() as path:
            exit_code, _ = _run_cli(
                ["create-account", ACCOUNT_ID, ACCOUNT_EMAIL, ACCOUNT_PASSWORD, "--database", path]
            )
            self.assertEqual(exit_code, 0)
            exit_code, _ = _run_cli(
                ["register-client", CLIENT_ID, CLIENT_CALLBACK, "--database", path]
            )
            self.assertEqual(exit_code, 0)

            storage = Storage(path)
            _seed_restart(storage, "restart-expired", expires_at=-1.0)
            storage.close()

            exit_code, out = _run_cli(["cleanup-consent-restarts", "--database", path])
            self.assertEqual(exit_code, 0)
            self.assertEqual(json.loads(out), {"removed": 1})

            # A second CLI invocation is a brand-new process/Storage handle.
            exit_code, out = _run_cli(["cleanup-consent-restarts", "--database", path])
            self.assertEqual(exit_code, 0)
            self.assertEqual(json.loads(out), {"removed": 0})

    def test_cli_status_reports_bounded_counts_and_denials(self):
        with temp_db_path() as path:
            _run_cli(["create-account", ACCOUNT_ID, ACCOUNT_EMAIL, ACCOUNT_PASSWORD, "--database", path])
            _run_cli(["register-client", CLIENT_ID, CLIENT_CALLBACK, "--database", path])

            storage = Storage(path)
            _seed_restart(storage, "restart-active", expires_at=1e18, login_id="login-active")
            _seed_restart(storage, "restart-expired", expires_at=-1.0, login_id="login-expired")
            for i in range(3):
                storage.record_consent_denial(f"restart-denied-{i}", CLIENT_ID, ACCOUNT_ID, "state-1", float(i))
            storage.close()

            exit_code, out = _run_cli(
                ["consent-restart-status", "--database", path, "--limit", "2"]
            )
            self.assertEqual(exit_code, 0)
            status = json.loads(out)
            self.assertEqual(status["active_consent_restarts"], 1)
            self.assertEqual(status["expired_consent_restarts"], 1)
            self.assertEqual(len(status["recent_denials"]), 2)


class SeparateProcessReadTests(unittest.TestCase):
    def test_second_storage_handle_sees_cleanup_and_denial_results(self):
        with temp_db_path() as path:
            process_a = Storage(path)
            try:
                seed(process_a)
                clock = FakeClock()
                service_a = OAuthService(process_a, signing_key="k", clock=clock)

                login_id = service_a.authorize(CLIENT_ID, CLIENT_CALLBACK, "state-1")["login_id"]
                restart_id = service_a.create_consent_restart(login_id, ["profile.read"])["restart_id"]
                process_a.record_consent_denial(restart_id, CLIENT_ID, ACCOUNT_ID, "state-1", clock())

                _seed_restart(process_a, "restart-expired", expires_at=clock() - 1, login_id="other-login")
                removed = service_a.cleanup_expired_consent_restarts()
                self.assertEqual(removed, 1)
            finally:
                process_a.close()

            process_b = Storage(path)
            try:
                self.assertIsNone(process_b.get_consent_restart("restart-expired"))
                self.assertEqual(process_b.count_expired_consent_restarts(now=clock()), 0)

                denials = process_b.list_recent_consent_denials(limit=10)
                self.assertEqual(len(denials), 1)
                self.assertEqual(denials[0].restart_id, restart_id)
                self.assertEqual(denials[0].account_id, ACCOUNT_ID)
            finally:
                process_b.close()


if __name__ == "__main__":
    unittest.main()
