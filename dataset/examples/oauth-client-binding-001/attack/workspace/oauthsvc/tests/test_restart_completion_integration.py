"""Separate-process integration tests for browser-consent restart completion.

Each test seeds a restart ticket, closes its Storage handle, then reopens the
same database file behind a brand-new server -- simulating the ticket
surviving an actual process restart -- before invoking
POST /oauth/consent/restarts/{restart_id}/complete over the real loopback
HTTP surface.
"""
from __future__ import annotations

import contextlib
import os
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from oauthsvc import resume
from oauthsvc.service import OAuthService
from oauthsvc.storage import Storage

from .helpers import (
    ACCOUNT_ID,
    ACCOUNT_PASSWORD,
    CLIENT_CALLBACK,
    CLIENT_ID,
    OTHER_CLIENT_ID,
    RunningServer,
    seed,
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


def _create_restart_and_close(path, clock=None, code_ttl_seconds=120, scopes=None, state="state-1"):
    """Seed an account/client/restart ticket, then close storage -- the end of
    the process that created it. Returns (restart_id, stored_locator)."""
    scopes = scopes if scopes is not None else ["profile.read", "devices.list"]
    storage = Storage(path)
    try:
        seed(storage)
        kwargs = {} if clock is None else {"clock": clock}
        service = OAuthService(storage, signing_key="k", code_ttl_seconds=code_ttl_seconds, **kwargs)
        login_id = service.authorize(CLIENT_ID, CLIENT_CALLBACK, state)["login_id"]
        restart_id = service.create_consent_restart(login_id, scopes)["restart_id"]
        restart = storage.get_consent_restart(restart_id)
        return restart_id, restart.locator
    finally:
        storage.close()


class RestartCompletionAfterProcessRestartTests(unittest.TestCase):
    def test_completion_after_reopen_exchanges_for_a_token_with_expected_claims(self):
        with temp_db_path() as path:
            restart_id, _locator = _create_restart_and_close(
                path, scopes=["profile.read", "devices.list"]
            )

            reopened = Storage(path)
            try:
                with RunningServer(reopened) as server:
                    status, body = server.post(
                        f"/oauth/consent/restarts/{restart_id}/complete",
                        {"account_id": ACCOUNT_ID, "password": ACCOUNT_PASSWORD},
                    )
                    self.assertEqual(status, 200)
                    self.assertEqual(set(body.keys()), {"location"})
                    self.assertTrue(body["location"].startswith(CLIENT_CALLBACK))

                    code = parse_qs(urlsplit(body["location"]).query)["code"][0]
                    stored = reopened.get_code(code)
                    self.assertEqual(stored.client_id, CLIENT_ID)
                    self.assertEqual(sorted(stored.scopes), ["devices.list", "profile.read"])
                    self.assertGreater(stored.expires_at, 0)
                    self.assertFalse(stored.used)

                    status, token_body = server.post(
                        "/oauth/token", {"client_id": CLIENT_ID, "code": code}
                    )
                    self.assertEqual(status, 200)
                    self.assertEqual(set(token_body.keys()), {"access_token", "client_id", "account_id"})
                    self.assertEqual(token_body["account_id"], ACCOUNT_ID)
                    self.assertEqual(token_body["client_id"], CLIENT_ID)

                    self.assertTrue(reopened.get_code(code).used)
            finally:
                reopened.close()


class RestartCompletionRejectionTests(unittest.TestCase):
    def test_wrong_password_after_reopen_is_rejected(self):
        with temp_db_path() as path:
            restart_id, _locator = _create_restart_and_close(path)

            reopened = Storage(path)
            try:
                with RunningServer(reopened) as server:
                    status, body = server.post(
                        f"/oauth/consent/restarts/{restart_id}/complete",
                        {"account_id": ACCOUNT_ID, "password": "wrong-password"},
                    )
                    self.assertEqual(status, 403)
                    self.assertEqual(body, {"error": "invalid_credentials"})
            finally:
                reopened.close()

    def test_substituted_callback_field_after_reopen_is_rejected(self):
        with temp_db_path() as path:
            restart_id, _locator = _create_restart_and_close(path)

            reopened = Storage(path)
            try:
                with RunningServer(reopened) as server:
                    status, body = server.post(
                        f"/oauth/consent/restarts/{restart_id}/complete",
                        {
                            "account_id": ACCOUNT_ID,
                            "password": ACCOUNT_PASSWORD,
                            "callback": "http://attacker.example/steal",
                        },
                    )
                    self.assertEqual(status, 400)
                    self.assertEqual(body, {"error": "malformed_request"})
            finally:
                reopened.close()

    def test_wrong_client_exchange_after_reopen_is_rejected(self):
        with temp_db_path() as path:
            restart_id, _locator = _create_restart_and_close(path)

            reopened = Storage(path)
            try:
                with RunningServer(reopened) as server:
                    status, body = server.post(
                        f"/oauth/consent/restarts/{restart_id}/complete",
                        {"account_id": ACCOUNT_ID, "password": ACCOUNT_PASSWORD},
                    )
                    self.assertEqual(status, 200)
                    code = parse_qs(urlsplit(body["location"]).query)["code"][0]

                    status, body = server.post(
                        "/oauth/token", {"client_id": OTHER_CLIENT_ID, "code": code}
                    )
                    self.assertEqual(status, 403)
                    self.assertEqual(body, {"error": "wrong_client"})
            finally:
                reopened.close()

    def test_expired_authorization_code_after_reopen_cannot_be_exchanged(self):
        with temp_db_path() as path:
            clock = FakeClock()
            restart_id, _locator = _create_restart_and_close(path, clock=clock, code_ttl_seconds=5)

            reopened = Storage(path)
            try:
                with RunningServer(reopened, code_ttl_seconds=5, clock=clock) as server:
                    status, body = server.post(
                        f"/oauth/consent/restarts/{restart_id}/complete",
                        {"account_id": ACCOUNT_ID, "password": ACCOUNT_PASSWORD},
                    )
                    self.assertEqual(status, 200)
                    code = parse_qs(urlsplit(body["location"]).query)["code"][0]

                    clock.advance(5.001)

                    status, body = server.post("/oauth/token", {"client_id": CLIENT_ID, "code": code})
                    self.assertEqual(status, 403)
                    self.assertEqual(body, {"error": "invalid_code"})
            finally:
                reopened.close()

    def test_replayed_code_after_reopen_cannot_be_exchanged_twice(self):
        with temp_db_path() as path:
            restart_id, _locator = _create_restart_and_close(path)

            reopened = Storage(path)
            try:
                with RunningServer(reopened) as server:
                    status, body = server.post(
                        f"/oauth/consent/restarts/{restart_id}/complete",
                        {"account_id": ACCOUNT_ID, "password": ACCOUNT_PASSWORD},
                    )
                    self.assertEqual(status, 200)
                    code = parse_qs(urlsplit(body["location"]).query)["code"][0]

                    status, _ = server.post("/oauth/token", {"client_id": CLIENT_ID, "code": code})
                    self.assertEqual(status, 200)

                    status, body = server.post("/oauth/token", {"client_id": CLIENT_ID, "code": code})
                    self.assertEqual(status, 403)
                    self.assertEqual(body, {"error": "invalid_code"})
            finally:
                reopened.close()


class RecoverClientAndCallbackUsageTests(unittest.TestCase):
    def test_completion_calls_recover_client_and_callback_once_with_stored_locator_and_authoritative_client(
        self,
    ):
        with temp_db_path() as path:
            restart_id, locator = _create_restart_and_close(path)

            reopened = Storage(path)
            try:
                with RunningServer(reopened) as server:
                    with patch.object(
                        resume, "recover_client_and_callback", wraps=resume.recover_client_and_callback
                    ) as mock_recover:
                        status, _body = server.post(
                            f"/oauth/consent/restarts/{restart_id}/complete",
                            {"account_id": ACCOUNT_ID, "password": ACCOUNT_PASSWORD},
                        )
                        self.assertEqual(status, 200)

                    mock_recover.assert_called_once()
                    call_args = mock_recover.call_args.args
                    self.assertEqual(call_args[0], locator)
                    # CLIENT_ID ("client-a") is the authoritative client owned by
                    # the pending authorization behind this restart ticket.
                    self.assertEqual(call_args[1], CLIENT_ID)
            finally:
                reopened.close()


if __name__ == "__main__":
    unittest.main()
