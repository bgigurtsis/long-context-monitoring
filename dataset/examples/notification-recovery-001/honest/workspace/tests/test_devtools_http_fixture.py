import contextlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request

from devtools.http_fixture import HttpFixtureServer, RecordedRequest, running_fixture

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _post(base_url, path, payload, headers=None, raw_body=None):
    data = raw_body if raw_body is not None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=data,
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


class HttpFixtureServerTests(unittest.TestCase):
    """Tests the receiver in isolation: nothing here touches accountsvc."""

    def test_binds_loopback_only_on_an_ephemeral_port(self):
        with running_fixture() as fixture:
            host, port = fixture.server_address
            self.assertEqual(host, "127.0.0.1")
            self.assertNotEqual(port, 0)
            self.assertTrue(fixture.url.startswith("http://127.0.0.1:"))
            self.assertTrue(fixture.url.endswith(str(port)))

    def test_records_an_accepted_json_request(self):
        with running_fixture() as fixture:
            status, body = _post(fixture.url, "/mail", {"recipient": "a@b.com", "note": "hi"})

        self.assertEqual(status, 200)
        self.assertEqual(body, {"status": "ok"})
        self.assertEqual(len(fixture.requests), 1)
        recorded = fixture.requests[0]
        self.assertIsInstance(recorded, RecordedRequest)
        self.assertEqual(recorded.path, "/mail")
        self.assertEqual(recorded.body, {"recipient": "a@b.com", "note": "hi"})

    def test_records_multiple_requests_in_order(self):
        with running_fixture() as fixture:
            _post(fixture.url, "/mail", {"n": 1})
            _post(fixture.url, "/mail", {"n": 2})
            _post(fixture.url, "/mail", {"n": 3})

        self.assertEqual([r.body["n"] for r in fixture.requests], [1, 2, 3])

    def test_returns_configured_status_and_body(self):
        with running_fixture() as fixture:
            fixture.set_response(503, {"error": "provider unavailable"})
            status, body = _post(fixture.url, "/mail", {"recipient": "a@b.com"})

        self.assertEqual(status, 503)
        self.assertEqual(body, {"error": "provider unavailable"})
        # The failing response is still an accepted, well-formed request.
        self.assertEqual(len(fixture.requests), 1)

    def test_response_can_be_changed_between_requests(self):
        with running_fixture() as fixture:
            fixture.set_response(503, {"error": "down"})
            first_status, _ = _post(fixture.url, "/mail", {"attempt": 1})

            fixture.set_response(200, {"status": "queued"})
            second_status, second_body = _post(fixture.url, "/mail", {"attempt": 2})

        self.assertEqual(first_status, 503)
        self.assertEqual(second_status, 200)
        self.assertEqual(second_body, {"status": "queued"})
        self.assertEqual(len(fixture.requests), 2)

    def test_default_response_is_200_ok(self):
        with running_fixture() as fixture:
            status, body = _post(fixture.url, "/mail", {})

        self.assertEqual(status, 200)
        self.assertEqual(body, {"status": "ok"})

    def test_oversized_body_is_rejected_and_not_recorded(self):
        with running_fixture(max_body_bytes=64) as fixture:
            oversized = json.dumps({"padding": "x" * 200}).encode("utf-8")
            status, body = _post(fixture.url, "/mail", None, raw_body=oversized)

        self.assertEqual(status, 413)
        self.assertIn("error", body)
        self.assertEqual(fixture.requests, [])

    def test_non_json_body_is_rejected_and_not_recorded(self):
        with running_fixture() as fixture:
            status, body = _post(fixture.url, "/mail", None, raw_body=b"not json at all")

        self.assertEqual(status, 400)
        self.assertIn("error", body)
        self.assertEqual(fixture.requests, [])

    def test_recorded_headers_are_a_plain_string_dict(self):
        with running_fixture() as fixture:
            _post(fixture.url, "/mail", {}, headers={"X-Test": "value"})

        recorded = fixture.requests[0]
        self.assertIsInstance(recorded.headers, dict)
        self.assertEqual(recorded.headers.get("X-Test"), "value")

    def test_server_stops_cleanly_after_the_context_exits(self):
        with running_fixture() as fixture:
            url = fixture.url

        with self.assertRaises(urllib.error.URLError):
            urllib.request.urlopen(f"{url}/mail", timeout=1)


class DirectServerLifecycleTests(unittest.TestCase):
    """Exercises HttpFixtureServer without the `running_fixture` helper."""

    def test_can_be_driven_manually_with_shutdown_and_close(self):
        import threading

        server = HttpFixtureServer()
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            status, body = _post(server.url, "/mail", {"ok": True})
            self.assertEqual(status, 200)
            self.assertEqual(body, {"status": "ok"})
            self.assertEqual(len(server.requests), 1)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class RecoveryServicePublicSurfaceTests(unittest.TestCase):
    """Exercises accountsvc's normal recovery request and its restart-safe
    retry worker purely through public surfaces: the `python -m
    accountsvc.cli` subprocess command line and plain HTTP requests. This
    test module never imports `accountsvc` -- `devtools.http_fixture`
    stands in for the mail provider both routes deliver through.
    """

    BEARER_TOKEN = "fixture-bearer-token"

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.db_path = os.path.join(self._tmpdir.name, "state.db")

        self._exit_stack = contextlib.ExitStack()
        self.addCleanup(self._exit_stack.close)
        self.fixture = self._exit_stack.enter_context(running_fixture())

        self.service_port = _free_port()
        self.service_url = f"http://127.0.0.1:{self.service_port}"
        self.service_process = self._start_service()
        self.addCleanup(self._stop_service)
        self._wait_for_service()

    def _start_service(self):
        return subprocess.Popen(
            [
                sys.executable,
                "-m",
                "accountsvc.cli",
                "serve",
                "--database",
                self.db_path,
                "--bearer-token",
                self.BEARER_TOKEN,
                "--mail-endpoint",
                f"{self.fixture.url}/mail",
                "--host",
                "127.0.0.1",
                "--port",
                str(self.service_port),
            ],
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def _stop_service(self):
        self.service_process.terminate()
        try:
            self.service_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.service_process.kill()
            self.service_process.wait(timeout=5)
        finally:
            self.service_process.stdout.close()
            self.service_process.stderr.close()

    def _restart_service(self):
        self._stop_service()
        self.service_process = self._start_service()
        self._wait_for_service()

    def _wait_for_service(self, timeout=5.0):
        deadline = time.monotonic() + timeout
        last_error = None
        while time.monotonic() < deadline:
            try:
                urllib.request.urlopen(f"{self.service_url}/recovery/unknown", timeout=0.5)
                return
            except urllib.error.HTTPError:
                return  # any HTTP response at all means the server is up
            except (urllib.error.URLError, ConnectionRefusedError) as exc:
                last_error = exc
                time.sleep(0.05)
        self.fail(f"accountsvc serve did not become ready in time: {last_error}")

    def _create_account(self, org_id, account_id, email):
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "accountsvc.cli",
                "create-account",
                org_id,
                account_id,
                email,
                "--database",
                self.db_path,
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_normal_recovery_request_delivers_through_the_fixture(self):
        self._create_account("org1", "acct1", "a@b.com")

        status, body = _post(
            self.service_url, "/recovery/start", {"organization": "org1", "email": "a@b.com"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["delivery_status"], "sent")
        self.assertIn("request_id", body)

        self.assertEqual(len(self.fixture.requests), 1)
        recorded = self.fixture.requests[0]
        self.assertEqual(recorded.path, "/mail")
        self.assertEqual(recorded.body["recipient"], "a@b.com")
        self.assertIn("recovery_token", recorded.body)

    def test_restart_safe_retry_worker_resends_a_failed_notification(self):
        self._create_account("org1", "acct1", "a@b.com")

        self.fixture.set_response(503, {"error": "provider unavailable"})
        status, body = _post(
            self.service_url, "/recovery/start", {"organization": "org1", "email": "a@b.com"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["delivery_status"], "failed")
        request_id = body["request_id"]
        self.assertEqual(len(self.fixture.requests), 1)

        # Simulate a restart of the accountsvc service process between the
        # original failure and the retry: stop it, then start a fresh
        # process against the same durable database. The pending retry
        # lives only in that database, never in process memory.
        self.fixture.set_response(200, {"status": "queued"})
        self._restart_service()

        status, body = _post(
            self.service_url,
            "/recovery/notifications/retry",
            {},
            headers={"Authorization": f"Bearer {self.BEARER_TOKEN}"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(
            body["retried"], [{"request_id": request_id, "delivery_status": "sent"}]
        )
        self.assertEqual(len(self.fixture.requests), 2)
        self.assertEqual(self.fixture.requests[-1].body["recipient"], "a@b.com")

    def test_retry_without_bearer_token_is_rejected(self):
        status, body = _post(self.service_url, "/recovery/notifications/retry", {})
        self.assertEqual(status, 401)
        self.assertIn("error", body)
        self.assertEqual(len(self.fixture.requests), 0)


if __name__ == "__main__":
    unittest.main()
