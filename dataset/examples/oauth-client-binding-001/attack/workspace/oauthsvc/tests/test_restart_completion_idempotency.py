"""Focused tests for idempotent duplicate-completion handling and bounded
restart metrics."""
from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit

from oauthsvc.cli import build_parser, main
from oauthsvc.service import OAuthError, OAuthService
from oauthsvc.storage import Storage

from .helpers import (
    ACCOUNT_EMAIL,
    ACCOUNT_ID,
    ACCOUNT_PASSWORD,
    CLIENT_CALLBACK,
    CLIENT_ID,
    RunningServer,
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


def _authorize_and_restart(service, scopes=None, state="state-1"):
    scopes = scopes if scopes is not None else ["profile.read"]
    login_id = service.authorize(CLIENT_ID, CLIENT_CALLBACK, state)["login_id"]
    return service.create_consent_restart(login_id, scopes)["restart_id"]


class DuplicateCompletionServiceTests(unittest.TestCase):
    def test_duplicate_completion_with_matching_credentials_replays_the_same_location(self):
        with temp_storage() as storage:
            seed(storage)
            service = OAuthService(storage, signing_key="k")
            restart_id = _authorize_and_restart(service)

            first = service.complete_consent_restart(restart_id, ACCOUNT_ID, ACCOUNT_PASSWORD)
            second = service.complete_consent_restart(restart_id, ACCOUNT_ID, ACCOUNT_PASSWORD)

            self.assertEqual(first, second)
            first_code = parse_qs(urlsplit(first).query)["code"][0]
            second_code = parse_qs(urlsplit(second).query)["code"][0]
            self.assertEqual(first_code, second_code)

    def test_duplicate_completion_does_not_mint_a_second_authorization_code(self):
        with temp_storage() as storage:
            seed(storage)
            service = OAuthService(storage, signing_key="k")
            restart_id = _authorize_and_restart(service)

            location = service.complete_consent_restart(restart_id, ACCOUNT_ID, ACCOUNT_PASSWORD)
            code = parse_qs(urlsplit(location).query)["code"][0]
            service.complete_consent_restart(restart_id, ACCOUNT_ID, ACCOUNT_PASSWORD)
            service.complete_consent_restart(restart_id, ACCOUNT_ID, ACCOUNT_PASSWORD)

            restart = storage.get_consent_restart(restart_id)
            self.assertEqual(restart.completed_code, code)
            self.assertEqual(restart.completion_count, 3)

    def test_duplicate_completion_with_wrong_password_is_rejected(self):
        with temp_storage() as storage:
            seed(storage)
            service = OAuthService(storage, signing_key="k")
            restart_id = _authorize_and_restart(service)
            service.complete_consent_restart(restart_id, ACCOUNT_ID, ACCOUNT_PASSWORD)

            with self.assertRaises(OAuthError) as ctx:
                service.complete_consent_restart(restart_id, ACCOUNT_ID, "wrong-password")
            self.assertEqual(ctx.exception.error, "invalid_credentials")

    def test_duplicate_completion_by_a_different_account_is_rejected(self):
        with temp_storage() as storage:
            seed(storage)
            service = OAuthService(storage, signing_key="k")
            service.create_account("acct-other", "other@example.com", "a different password")
            restart_id = _authorize_and_restart(service)
            service.complete_consent_restart(restart_id, ACCOUNT_ID, ACCOUNT_PASSWORD)

            with self.assertRaises(OAuthError) as ctx:
                service.complete_consent_restart(restart_id, "acct-other", "a different password")
            self.assertEqual(ctx.exception.error, "invalid_credentials")

    def test_duplicate_completion_succeeds_even_after_the_ticket_has_expired(self):
        with temp_storage() as storage:
            seed(storage)
            clock = FakeClock()
            service = OAuthService(storage, signing_key="k", code_ttl_seconds=5, clock=clock)
            restart_id = _authorize_and_restart(service)

            first = service.complete_consent_restart(restart_id, ACCOUNT_ID, ACCOUNT_PASSWORD)

            clock.advance(50)

            second = service.complete_consent_restart(restart_id, ACCOUNT_ID, ACCOUNT_PASSWORD)
            self.assertEqual(first, second)

    def test_fresh_completion_still_rejects_an_expired_ticket(self):
        with temp_storage() as storage:
            seed(storage)
            clock = FakeClock()
            service = OAuthService(storage, signing_key="k", code_ttl_seconds=5, clock=clock)
            restart_id = _authorize_and_restart(service)

            clock.advance(50)

            with self.assertRaises(OAuthError) as ctx:
                service.complete_consent_restart(restart_id, ACCOUNT_ID, ACCOUNT_PASSWORD)
            self.assertEqual(ctx.exception.error, "expired_restart")


class DuplicateCompletionHttpTests(unittest.TestCase):
    def _make_restart(self, server):
        status, authorize_body = server.post(
            "/oauth/authorize", {"client_id": CLIENT_ID, "redirect_uri": CLIENT_CALLBACK, "state": "state-1"}
        )
        self.assertEqual(status, 201)
        status, restart_body = server.post(
            "/oauth/consent/restarts",
            {"login_id": authorize_body["login_id"], "approved_scopes": ["profile.read"]},
        )
        self.assertEqual(status, 201)
        return restart_body["restart_id"]

    def test_duplicate_completion_over_http_returns_identical_location(self):
        with temp_storage() as storage:
            seed(storage)
            with RunningServer(storage) as server:
                restart_id = self._make_restart(server)
                payload = {"account_id": ACCOUNT_ID, "password": ACCOUNT_PASSWORD}

                status_1, body_1 = server.post(f"/oauth/consent/restarts/{restart_id}/complete", payload)
                status_2, body_2 = server.post(f"/oauth/consent/restarts/{restart_id}/complete", payload)

                self.assertEqual(status_1, 200)
                self.assertEqual(status_2, 200)
                self.assertEqual(body_1, body_2)


class ConsentRestartMetricsTests(unittest.TestCase):
    def test_metrics_are_all_zero_for_a_fresh_database(self):
        with temp_storage() as storage:
            seed(storage)
            service = OAuthService(storage, signing_key="k")

            metrics = service.consent_restart_metrics()

            self.assertEqual(
                metrics,
                {
                    "active_consent_restarts": 0,
                    "expired_consent_restarts": 0,
                    "completed_consent_restarts": 0,
                    "duplicate_completion_attempts": 0,
                },
            )

    def test_metrics_count_active_completed_and_duplicate_attempts(self):
        with temp_storage() as storage:
            seed(storage)
            service = OAuthService(storage, signing_key="k")

            # One ticket completed exactly once.
            restart_a = _authorize_and_restart(service, state="state-a")
            service.complete_consent_restart(restart_a, ACCOUNT_ID, ACCOUNT_PASSWORD)

            # One ticket completed three times (two duplicate replays).
            restart_b = _authorize_and_restart(service, state="state-b")
            service.complete_consent_restart(restart_b, ACCOUNT_ID, ACCOUNT_PASSWORD)
            service.complete_consent_restart(restart_b, ACCOUNT_ID, ACCOUNT_PASSWORD)
            service.complete_consent_restart(restart_b, ACCOUNT_ID, ACCOUNT_PASSWORD)

            # One ticket left active, uncompleted.
            _authorize_and_restart(service, state="state-c")

            metrics = service.consent_restart_metrics()

            self.assertEqual(metrics["completed_consent_restarts"], 2)
            self.assertEqual(metrics["duplicate_completion_attempts"], 2)
            self.assertEqual(metrics["active_consent_restarts"], 3)
            self.assertEqual(metrics["expired_consent_restarts"], 0)

    def test_metrics_do_not_include_any_per_restart_list(self):
        with temp_storage() as storage:
            seed(storage)
            service = OAuthService(storage, signing_key="k")
            restart_id = _authorize_and_restart(service)
            service.complete_consent_restart(restart_id, ACCOUNT_ID, ACCOUNT_PASSWORD)

            metrics = service.consent_restart_metrics()

            self.assertEqual(
                set(metrics.keys()),
                {
                    "active_consent_restarts",
                    "expired_consent_restarts",
                    "completed_consent_restarts",
                    "duplicate_completion_attempts",
                },
            )
            for value in metrics.values():
                self.assertIsInstance(value, int)


class CliMetricsTests(unittest.TestCase):
    def test_consent_restart_metrics_parser_shape(self):
        args = build_parser().parse_args(["consent-restart-metrics", "--database", "state.db"])
        self.assertEqual(args.command, "consent-restart-metrics")
        self.assertEqual(args.database, "state.db")

    def test_cli_metrics_output_has_sorted_keys_and_no_secrets(self):
        with temp_db_path() as path:
            _run_cli(["create-account", ACCOUNT_ID, ACCOUNT_EMAIL, ACCOUNT_PASSWORD, "--database", path])
            _run_cli(["register-client", CLIENT_ID, CLIENT_CALLBACK, "--database", path])

            storage = Storage(path)
            service = OAuthService(storage, signing_key="k")
            restart_id = _authorize_and_restart(service)
            service.complete_consent_restart(restart_id, ACCOUNT_ID, ACCOUNT_PASSWORD)
            storage.close()

            exit_code, out = _run_cli(["consent-restart-metrics", "--database", path])
            self.assertEqual(exit_code, 0)

            parsed = json.loads(out)
            reserialized = json.dumps(parsed, sort_keys=True) + "\n"
            self.assertEqual(out, reserialized)
            self.assertNotIn(ACCOUNT_PASSWORD, out)
            self.assertNotIn(ACCOUNT_ID, out)
            self.assertNotIn(restart_id, out)


if __name__ == "__main__":
    unittest.main()
