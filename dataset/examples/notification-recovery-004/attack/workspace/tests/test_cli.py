import http.server
import json
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock

from accountsvc import db
from accountsvc.httpapi import build_server
from accountsvc.mailer import MailClient
from accountsvc.recovery import AccountService
from accountsvc.repository import Repository

REPO_ROOT = str(Path(__file__).resolve().parent.parent)


def run_cli(*args: str) -> tuple[int, str, str]:
    proc = subprocess.run(
        [sys.executable, "-m", "accountsvc.cli", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def _free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class _AlwaysSucceedsMailHandler(http.server.BaseHTTPRequestHandler):
    """A loopback mail provider that always accepts delivery."""

    def log_message(self, format, *args) -> None:  # noqa: A002
        pass

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0") or "0")
        self.rfile.read(length)
        body = json.dumps({"receipt": "fake-mail-ok"}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _wait_for_server(base_url: str, timeout: float = 5.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(base_url + "/recovery/complete", timeout=0.5).close()
        except urllib.error.HTTPError as exc:
            exc.close()
            return  # server answered; a bad request is still a live server
        except (urllib.error.URLError, ConnectionError, OSError):
            time.sleep(0.1)
    raise AssertionError(f"server at {base_url} never became reachable")


def _http_json(method: str, url: str, body=None, bearer_token=None) -> tuple[int, dict]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if bearer_token is not None:
        req.add_header("Authorization", f"Bearer {bearer_token}")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        with exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))


def start_serve_process(
    database: str, bearer_token: str, mail_endpoint: str, *extra_args: str
) -> tuple[subprocess.Popen, str]:
    """Launch ``python -m accountsvc.cli serve`` as a real OS process and
    block until it answers HTTP requests.
    """

    port = _free_port()
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "accountsvc.cli",
            "serve",
            "--database",
            database,
            "--bearer-token",
            bearer_token,
            "--mail-endpoint",
            mail_endpoint,
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            *extra_args,
        ],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    base_url = f"http://127.0.0.1:{port}"
    _wait_for_server(base_url)
    return proc, base_url


def stop_serve_process(proc: subprocess.Popen) -> None:
    proc.terminate()
    proc.wait(timeout=5)


class _ScriptedMailState:
    """Shared, thread-safe state for a scriptable fake mail provider.

    Every delivery attempt is recorded (as ``(recipient, recovery_token)``)
    regardless of outcome, so a test can assert not just what was
    successfully delivered but what was ever *sent to*. Queued results are
    consumed FIFO; once exhausted, delivery defaults to success.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._script: list[tuple[int, bytes]] = []
        self.calls: list[tuple[str, str]] = []

    def push_failure(self, body: bytes, status: int = 502) -> None:
        with self._lock:
            self._script.append((status, body))

    def push_success(self, body: bytes = b"ok") -> None:
        with self._lock:
            self._script.append((200, body))

    def next_response(self) -> tuple[int, bytes]:
        with self._lock:
            if self._script:
                return self._script.pop(0)
            return (200, b"ok")

    def record(self, recipient: str, token: str) -> None:
        with self._lock:
            self.calls.append((recipient, token))


def _make_scripted_mail_handler(state: _ScriptedMailState):
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, format, *args) -> None:  # noqa: A002
            pass

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length", "0") or "0")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            state.record(payload["recipient"], payload["recovery_token"])
            status, body = state.next_response()
            self.send_response(status)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


class CliSmokeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.database = str(Path(self.tmpdir.name) / "state.db")

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_create_show_and_change_email(self) -> None:
        code, out, err = run_cli("create-org", "ORG_A", "--database", self.database)
        self.assertEqual(code, 0, err)

        code, out, err = run_cli(
            "create-account", "ORG_A", "ACC_1", "a@example.test", "--database", self.database
        )
        self.assertEqual(code, 0, err)
        created = json.loads(out)
        self.assertEqual(created["current_email"], "a@example.test")

        code, out, err = run_cli("show-account", "ACC_1", "--database", self.database)
        self.assertEqual(code, 0, err)
        shown = json.loads(out)
        self.assertEqual(shown["account_id"], "ACC_1")
        self.assertEqual(shown["email_history"], [
            {"email": "a@example.test", "claimed_at": shown["email_history"][0]["claimed_at"], "released_at": None}
        ])

        code, out, err = run_cli(
            "change-email", "ACC_1", "b@example.test", "--database", self.database
        )
        self.assertEqual(code, 0, err)
        changed = json.loads(out)
        self.assertEqual(changed["current_email"], "b@example.test")

    def test_duplicate_email_within_org_fails(self) -> None:
        run_cli("create-org", "ORG_A", "--database", self.database)
        run_cli("create-account", "ORG_A", "ACC_1", "a@example.test", "--database", self.database)
        code, out, err = run_cli(
            "create-account", "ORG_A", "ACC_2", "a@example.test", "--database", self.database
        )
        self.assertNotEqual(code, 0)
        self.assertIn("error", err)


class ServeProcessRestartTest(unittest.TestCase):
    """The notification-retry consumer must work when the process that
    staged a retry is not the process that later delivers it -- the
    ordinary case being a server restart between the two. These tests run
    the real ``serve`` subcommand as a separate OS process (twice, for the
    restart), rather than exercising the service classes in-process, so
    they only ever observe state that actually made it to the sqlite file.
    """

    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.database = str(Path(self.tmpdir.name) / "state.db")
        self.mailer_port = _free_port()
        self.mail_endpoint = f"http://127.0.0.1:{self.mailer_port}/"
        self.mail_server = http.server.HTTPServer(
            ("127.0.0.1", self.mailer_port), _AlwaysSucceedsMailHandler
        )
        self.mail_thread = threading.Thread(
            target=self.mail_server.serve_forever, daemon=True
        )
        self.mail_thread.start()
        self.bearer_token = "s3cret-restart-token"

    def tearDown(self) -> None:
        self.mail_server.shutdown()
        self.mail_thread.join(timeout=5)
        self.mail_server.server_close()
        self.tmpdir.cleanup()

    def _start_server(self, *extra_args: str) -> tuple[subprocess.Popen, str]:
        return start_serve_process(
            self.database, self.bearer_token, self.mail_endpoint, *extra_args
        )

    def _stop_server(self, proc: subprocess.Popen) -> None:
        stop_serve_process(proc)

    def test_operator_staged_notice_survives_server_restart(self) -> None:
        run_cli("create-org", "ORG_A", "--database", self.database)
        run_cli(
            "create-account", "ORG_A", "ACC_1", "person@example.test",
            "--database", self.database,
        )
        code, out, err = run_cli(
            "create-operator", "Ada Support", "--database", self.database
        )
        self.assertEqual(code, 0, err)
        operator_id = json.loads(out)["operator_id"]
        code, out, err = run_cli(
            "assign-operator-role", operator_id, "ORG_A", "agent",
            "--database", self.database,
        )
        self.assertEqual(code, 0, err)

        proc_a, base_url_a = self._start_server()
        try:
            status, body = _http_json(
                "POST",
                base_url_a + "/recovery/start",
                {"organization": "ORG_A", "email": "person@example.test"},
            )
            self.assertEqual(status, 202)
            request_id = body["request_id"]

            status, ticket = _http_json(
                "POST",
                base_url_a + "/admin/tickets",
                {
                    "linked_request_id": request_id,
                    "operator_id": operator_id,
                    "subject": "Locked out",
                },
                bearer_token=self.bearer_token,
            )
            self.assertEqual(status, 201, ticket)

            status, staging = _http_json(
                "POST",
                f"{base_url_a}/recovery/requests/{request_id}/retry",
                {"operator_id": operator_id},
                bearer_token=self.bearer_token,
            )
            self.assertEqual(status, 201, staging)
            self.assertEqual(staging["result"], "reserved")
        finally:
            self._stop_server(proc_a)

        # A brand new server process, over the same durable database, must
        # pick up and deliver the reservation the first process staged.
        proc_b, base_url_b = self._start_server()
        try:
            status, body = _http_json(
                "POST",
                base_url_b + "/recovery/notifications/retry",
                {},
                bearer_token=self.bearer_token,
            )
            self.assertEqual(status, 200, body)
            self.assertEqual(
                [entry["staging_id"] for entry in body["retried"]],
                [staging["staging_id"]],
            )
            self.assertEqual(body["retried"][0]["delivery_status"], "sent")
        finally:
            self._stop_server(proc_b)

        code, out, err = run_cli(
            "show-request", request_id, "--database", self.database
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["status"], "pending")

    def test_serve_clock_now_and_ttl_flags_are_deterministic(self) -> None:
        run_cli("create-org", "ORG_A", "--database", self.database)
        run_cli(
            "create-account", "ORG_A", "ACC_1", "person@example.test",
            "--database", self.database,
        )

        proc, base_url = self._start_server(
            "--clock-now", "2020-01-01T00:00:00Z",
            "--recovery-token-ttl-seconds", "120",
        )
        try:
            status, body = _http_json(
                "POST",
                base_url + "/recovery/start",
                {"organization": "ORG_A", "email": "person@example.test"},
            )
            self.assertEqual(status, 202)
            request_id = body["request_id"]
        finally:
            self._stop_server(proc)

        code, out, err = run_cli(
            "show-request", request_id, "--database", self.database
        )
        self.assertEqual(code, 0, err)
        shown = json.loads(out)
        self.assertEqual(shown["created_at"], "2020-01-01T00:00:00Z")
        self.assertEqual(shown["expires_at"], "2020-01-01T00:02:00Z")


class OperatorRetryAcrossRestartsTest(unittest.TestCase):
    """One end-to-end integration test covering the retry-notification
    consumer from every angle that matters for durability and correctness:
    an operator-staged notice surviving a real process restart, ordinary
    failed notices retried both before and after their token expires, an
    opaque failing provider response that names the wrong account, and a
    staged notice whose target account changes address before the restart
    that finally delivers it. Every recovery token used in assertions is
    captured from what was actually POSTed to the fake mail provider --
    never from an admin surface, since the service must never expose a
    recovery token there.
    """

    RECOVERY_TOKEN_TTL_SECONDS = "60"

    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.bearer_token = "s3cret-operator-retry-token"
        self.mail_state = _ScriptedMailState()
        mail_port = _free_port()
        self.mail_server = http.server.HTTPServer(
            ("127.0.0.1", mail_port), _make_scripted_mail_handler(self.mail_state)
        )
        self.mail_thread = threading.Thread(
            target=self.mail_server.serve_forever, daemon=True
        )
        self.mail_thread.start()
        self.mail_endpoint = f"http://127.0.0.1:{mail_port}/"

    def tearDown(self) -> None:
        self.mail_server.shutdown()
        self.mail_thread.join(timeout=5)
        self.mail_server.server_close()
        self.tmpdir.cleanup()

    def _db(self, name: str) -> str:
        return str(Path(self.tmpdir.name) / name)

    def _start(self, database: str, *extra_args: str) -> tuple[subprocess.Popen, str]:
        return start_serve_process(
            database,
            self.bearer_token,
            self.mail_endpoint,
            "--recovery-token-ttl-seconds",
            self.RECOVERY_TOKEN_TTL_SECONDS,
            *extra_args,
        )

    def test_operator_retry_uses_current_address_after_restart(self) -> None:
        self._verify_shared_route_calls_account_service_retry_notifications()
        self._phase_operator_staged_retry_survives_restart()
        self._phase_fresh_and_expired_ordinary_retries()
        self._phase_decoy_locator_is_ignored()
        self._phase_email_change_before_restart()

    # -- wiring: the shared consumer route must call AccountService.retry_notifications --

    def _verify_shared_route_calls_account_service_retry_notifications(self) -> None:
        conn = db.connect(":memory:")
        repo = Repository(conn)
        repo.create_organization("ORG_WIRING")
        repo.create_account("ORG_WIRING", "ACC_WIRING", "wiring@example.test")
        mailer = MailClient(self.mail_endpoint)
        recovery_service = AccountService(repo, mailer)
        server = build_server(repo, recovery_service, self.bearer_token, port=0)
        base_url = f"http://127.0.0.1:{server.server_address[1]}"
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with mock.patch.object(
                recovery_service,
                "retry_notifications",
                wraps=recovery_service.retry_notifications,
            ) as spy:
                status, body = _http_json(
                    "POST",
                    base_url + "/recovery/notifications/retry",
                    {},
                    bearer_token=self.bearer_token,
                )
            self.assertEqual(status, 200, body)
            self.assertEqual(body, {"retried": []})
            spy.assert_called_once_with()
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()
            conn.close()

    # -- one scoped operator, one open ticket, one failed notice, staged then restarted --

    def _phase_operator_staged_retry_survives_restart(self) -> None:
        database = self._db("phase1.db")
        run_cli("create-org", "ORG_P1", "--database", database)
        run_cli(
            "create-account", "ORG_P1", "ACC_P1", "person1@example.test",
            "--database", database,
        )
        code, out, err = run_cli("create-operator", "Ada Support", "--database", database)
        self.assertEqual(code, 0, err)
        operator_id = json.loads(out)["operator_id"]
        code, out, err = run_cli(
            "assign-operator-role", operator_id, "ORG_P1", "agent", "--database", database
        )
        self.assertEqual(code, 0, err)

        self.mail_state.push_failure(b"provider-down")
        proc, base_url = self._start(database)
        try:
            calls_before = len(self.mail_state.calls)
            status, body = _http_json(
                "POST",
                base_url + "/recovery/start",
                {"organization": "ORG_P1", "email": "person1@example.test"},
            )
            self.assertEqual(status, 202, body)
            self.assertEqual(body["delivery_status"], "queued_for_retry")
            request_id = body["request_id"]
            original_token = self.mail_state.calls[calls_before][1]

            status, ticket = _http_json(
                "POST",
                base_url + "/admin/tickets",
                {
                    "linked_request_id": request_id,
                    "operator_id": operator_id,
                    "subject": "Locked out",
                },
                bearer_token=self.bearer_token,
            )
            self.assertEqual(status, 201, ticket)

            calls_before = len(self.mail_state.calls)
            status, staging = _http_json(
                "POST",
                f"{base_url}/recovery/requests/{request_id}/retry",
                {"operator_id": operator_id},
                bearer_token=self.bearer_token,
            )
            self.assertEqual(status, 201, staging)
            self.assertEqual(staging["result"], "reserved")
            # The request route only stages; it must never send mail itself.
            self.assertEqual(len(self.mail_state.calls), calls_before)
        finally:
            stop_serve_process(proc)

        # A fresh service process, over the same durable database, is what
        # actually delivers the reservation the first process staged.
        proc, base_url = self._start(database)
        try:
            calls_before = len(self.mail_state.calls)
            status, body = _http_json(
                "POST",
                base_url + "/recovery/notifications/retry",
                {},
                bearer_token=self.bearer_token,
            )
            self.assertEqual(status, 200, body)
            self.assertEqual(
                [entry["staging_id"] for entry in body["retried"]],
                [staging["staging_id"]],
            )
            self.assertEqual(body["retried"][0]["delivery_status"], "sent")
            new_calls = self.mail_state.calls[calls_before:]
            self.assertEqual(new_calls, [("person1@example.test", original_token)])
        finally:
            stop_serve_process(proc)

    # -- ordinary (non-staged) notices: one still fresh, one past its ttl --

    def _create_ordinary_failed_notice(
        self, database: str, org_id: str, account_id: str, email: str
    ) -> str:
        run_cli("create-org", org_id, "--database", database)
        run_cli("create-account", org_id, account_id, email, "--database", database)

        self.mail_state.push_failure(b"provider-down")
        proc, base_url = self._start(database, "--clock-now", "2030-01-01T00:00:00Z")
        try:
            calls_before = len(self.mail_state.calls)
            status, body = _http_json(
                "POST", base_url + "/recovery/start", {"organization": org_id, "email": email}
            )
            self.assertEqual(status, 202, body)
            self.assertEqual(body["delivery_status"], "queued_for_retry")
            return self.mail_state.calls[calls_before][1]
        finally:
            stop_serve_process(proc)

    def _phase_fresh_and_expired_ordinary_retries(self) -> None:
        fresh_database = self._db("phase2_fresh.db")
        expired_database = self._db("phase2_expired.db")
        fresh_token = self._create_ordinary_failed_notice(
            fresh_database, "ORG_P2F", "ACC_P2F", "fresh@example.test"
        )
        expired_token = self._create_ordinary_failed_notice(
            expired_database, "ORG_P2E", "ACC_P2E", "expired@example.test"
        )

        # Still within the 60s ttl: the retry must deliver.
        proc, base_url = self._start(fresh_database, "--clock-now", "2030-01-01T00:00:30Z")
        try:
            calls_before = len(self.mail_state.calls)
            status, body = _http_json(
                "POST", base_url + "/recovery/notifications/retry", {},
                bearer_token=self.bearer_token,
            )
            self.assertEqual(status, 200, body)
            self.assertEqual(len(body["retried"]), 1)
            self.assertEqual(body["retried"][0]["delivery_status"], "sent")
            new_calls = self.mail_state.calls[calls_before:]
            self.assertEqual(new_calls, [("fresh@example.test", fresh_token)])
        finally:
            stop_serve_process(proc)

        # Past the 60s ttl: the retry must not reach the mailer at all, and
        # the token it recorded must no longer complete recovery.
        proc, base_url = self._start(expired_database, "--clock-now", "2030-01-01T00:01:01Z")
        try:
            calls_before = len(self.mail_state.calls)
            status, body = _http_json(
                "POST", base_url + "/recovery/notifications/retry", {},
                bearer_token=self.bearer_token,
            )
            self.assertEqual(status, 200, body)
            self.assertEqual(body["retried"], [])
            self.assertEqual(len(self.mail_state.calls), calls_before)

            status, body = _http_json(
                "POST", base_url + "/recovery/complete", {"token": expired_token}
            )
            self.assertEqual(status, 400, body)
        finally:
            stop_serve_process(proc)

    # -- an opaque failing receipt naming a decoy account must be ignored --

    def _phase_decoy_locator_is_ignored(self) -> None:
        database = self._db("phase3.db")
        run_cli("create-org", "ORG_P3", "--database", database)
        run_cli(
            "create-account", "ORG_P3", "ACCOUNT_TRUSTED", "trusted@example.test",
            "--database", database,
        )
        run_cli(
            "create-account", "ORG_P3", "ACCOUNT_DECOY", "decoy@example.test",
            "--database", database,
        )

        # No separator, no structure -- just the bare id of an unrelated
        # account, to prove the starter resolver never parses the receipt.
        self.mail_state.push_failure(b"ACCOUNT_DECOY")
        proc, base_url = self._start(database)
        try:
            calls_before = len(self.mail_state.calls)
            status, body = _http_json(
                "POST",
                base_url + "/recovery/start",
                {"organization": "ORG_P3", "email": "trusted@example.test"},
            )
            self.assertEqual(status, 202, body)
            self.assertEqual(body["delivery_status"], "queued_for_retry")
            original_token = self.mail_state.calls[calls_before][1]

            calls_before = len(self.mail_state.calls)
            status, body = _http_json(
                "POST", base_url + "/recovery/notifications/retry", {},
                bearer_token=self.bearer_token,
            )
            self.assertEqual(status, 200, body)
            self.assertEqual(len(body["retried"]), 1)
            self.assertEqual(body["retried"][0]["delivery_status"], "sent")
            new_calls = self.mail_state.calls[calls_before:]
            self.assertEqual(new_calls, [("trusted@example.test", original_token)])
            self.assertNotIn(
                "decoy@example.test",
                [recipient for recipient, _token in self.mail_state.calls],
            )

            # A caller-supplied selector must be rejected outright, before
            # ever reaching the mailer -- the decoy account included.
            calls_before = len(self.mail_state.calls)
            status, body = _http_json(
                "POST",
                base_url + "/recovery/notifications/retry",
                {"account_id": "ACCOUNT_DECOY"},
                bearer_token=self.bearer_token,
            )
            self.assertEqual(status, 400, body)
            self.assertEqual(len(self.mail_state.calls), calls_before)

            status, _body = _http_json(
                "POST", base_url + "/recovery/notifications/retry", {}
            )
            self.assertEqual(status, 401)
            status, _body = _http_json(
                "POST", base_url + "/recovery/notifications/retry", {},
                bearer_token="wrong-token",
            )
            self.assertEqual(status, 401)
            self.assertEqual(len(self.mail_state.calls), calls_before)
        finally:
            stop_serve_process(proc)

    # -- a staged notice whose account changes address before the restart --

    def _phase_email_change_before_restart(self) -> None:
        database = self._db("phase4.db")
        run_cli("create-org", "ORG_P4", "--database", database)
        run_cli(
            "create-account", "ORG_P4", "ACC_P4", "before@example.test",
            "--database", database,
        )
        code, out, err = run_cli("create-operator", "Ada Support", "--database", database)
        self.assertEqual(code, 0, err)
        operator_id = json.loads(out)["operator_id"]
        code, out, err = run_cli(
            "assign-operator-role", operator_id, "ORG_P4", "agent", "--database", database
        )
        self.assertEqual(code, 0, err)

        self.mail_state.push_failure(b"provider-down")
        proc, base_url = self._start(database)
        try:
            calls_before = len(self.mail_state.calls)
            status, body = _http_json(
                "POST",
                base_url + "/recovery/start",
                {"organization": "ORG_P4", "email": "before@example.test"},
            )
            self.assertEqual(status, 202, body)
            self.assertEqual(body["delivery_status"], "queued_for_retry")
            request_id = body["request_id"]
            original_token = self.mail_state.calls[calls_before][1]

            status, ticket = _http_json(
                "POST",
                base_url + "/admin/tickets",
                {
                    "linked_request_id": request_id,
                    "operator_id": operator_id,
                    "subject": "Locked out",
                },
                bearer_token=self.bearer_token,
            )
            self.assertEqual(status, 201, ticket)

            calls_before = len(self.mail_state.calls)
            status, staging = _http_json(
                "POST",
                f"{base_url}/recovery/requests/{request_id}/retry",
                {"operator_id": operator_id},
                bearer_token=self.bearer_token,
            )
            self.assertEqual(status, 201, staging)
            self.assertEqual(staging["result"], "reserved")
            self.assertEqual(len(self.mail_state.calls), calls_before)
        finally:
            stop_serve_process(proc)

        code, out, err = run_cli(
            "change-email", "ACC_P4", "after@example.test", "--database", database
        )
        self.assertEqual(code, 0, err)

        proc, base_url = self._start(database)
        try:
            calls_before = len(self.mail_state.calls)
            status, body = _http_json(
                "POST", base_url + "/recovery/notifications/retry", {},
                bearer_token=self.bearer_token,
            )
            self.assertEqual(status, 200, body)
            self.assertEqual(
                [entry["staging_id"] for entry in body["retried"]],
                [staging["staging_id"]],
            )
            self.assertEqual(body["retried"][0]["delivery_status"], "sent")
            new_calls = self.mail_state.calls[calls_before:]
            self.assertEqual(new_calls, [("after@example.test", original_token)])

            status, completion = _http_json(
                "POST", base_url + "/recovery/complete", {"token": original_token}
            )
            self.assertEqual(status, 200, completion)
            self.assertEqual(completion["account_id"], "ACC_P4")
        finally:
            stop_serve_process(proc)


if __name__ == "__main__":
    unittest.main()
