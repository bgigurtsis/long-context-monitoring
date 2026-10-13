"""Proves the notification retry consumer reloads durable state across a
real OS process boundary, not just across Python objects in one interpreter.

Each server in this test is a genuine `python -m accountsvc.cli serve`
subprocess. The first process fails a delivery and exits (simulating a
crash/restart); a second, entirely separate process -- fresh interpreter,
fresh memory, pointed at the same SQLite file -- must still find and deliver
that durable notice. `--clock-now` keeps both processes' timestamps
deterministic instead of racing the real wall clock across the restart, and
`--recovery-token-ttl-seconds` is exercised as a real CLI flag end-to-end.
"""
from __future__ import annotations

import inspect
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from accountsvc import db, httpapi, notice, service, store

from .fakemail import FakeMailServer

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BEARER_TOKEN = "restart-test-token"


def _epoch(iso: str) -> float:
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()


def _read_listening_info(proc: subprocess.Popen) -> dict:
    """Read the single pretty-printed JSON object `cmd_serve` writes to
    stdout at startup, by tracking brace depth rather than assuming a fixed
    number of lines.
    """
    lines = []
    depth = 0
    started = False
    while True:
        line = proc.stdout.readline()
        if not line:
            stderr = proc.stderr.read()
            raise RuntimeError(f"server process exited before announcing its address:\n{stderr}")
        lines.append(line)
        if "{" in line:
            started = True
        depth += line.count("{") - line.count("}")
        if started and depth == 0:
            break
    return json.loads("".join(lines))


def _http(base_url: str, method: str, path: str, body: dict | None = None, token: str | None = None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(base_url + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read())
        finally:
            exc.close()


class ProcessRestartTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(self.db_path)
        self.mail = FakeMailServer(fail_times=1)
        self.procs: list[subprocess.Popen] = []

    def tearDown(self):
        for proc in self.procs:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=10)
            proc.stdout.close()
            proc.stderr.close()
        self.mail.stop()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        for ext in ("-wal", "-shm"):
            p = self.db_path + ext
            if os.path.exists(p):
                os.remove(p)

    def _spawn_server(self, clock_now: float) -> tuple[subprocess.Popen, str]:
        env = dict(os.environ, PYTHONUNBUFFERED="1")
        proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "accountsvc.cli",
                "serve",
                "--database",
                self.db_path,
                "--bearer-token",
                BEARER_TOKEN,
                "--mail-endpoint",
                self.mail.url,
                "--host",
                "127.0.0.1",
                "--port",
                "0",
                "--clock-now",
                str(clock_now),
                "--recovery-token-ttl-seconds",
                "900",
            ],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        self.procs.append(proc)
        info = _read_listening_info(proc)
        self.assertTrue(info["listening"])
        return proc, f"http://{info['host']}:{info['port']}"

    def _terminate(self, proc: subprocess.Popen) -> None:
        proc.terminate()
        proc.wait(timeout=10)

    def test_retry_consumer_reloads_a_failed_notice_after_a_separate_process_restart(self):
        conn = db.connect(self.db_path)
        try:
            service.create_account(conn, "ORG_A", "acct-1", "alice@example.test", now=1000.0)
        finally:
            conn.close()

        first_proc, first_base = self._spawn_server(clock_now=5000.0)
        status, body = _http(
            first_base, "POST", "/recovery/start", {"organization": "ORG_A", "email": "alice@example.test"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "queued_retry")
        request_id = body["request_id"]

        # Simulate the first process crashing/restarting: it is gone before
        # anything about the failed notice is retried.
        self._terminate(first_proc)

        second_proc, second_base = self._spawn_server(clock_now=5001.0)
        status, body = _http(second_base, "POST", "/recovery/notifications/retry", {}, token=BEARER_TOKEN)
        self.assertEqual(status, 200)
        self.assertEqual(body["processed"], 1)
        self.assertEqual(body["results"][0]["outcome"], "sent")
        self.assertEqual(body["results"][0]["request_id"], request_id)
        self._terminate(second_proc)

        self.assertEqual(len(self.mail.received), 2)  # the original failure + the successful retry
        self.assertEqual(self.mail.received[-1]["recipient"], "alice@example.test")

        conn = db.connect(self.db_path)
        try:
            self.assertEqual(store.find_retryable_attempts(conn, now=5001.0, limit=10), [])
        finally:
            conn.close()


class _DecoyReceiptMailServer:
    """A mail double whose failure receipt is, verbatim and without any
    separator, the id of a *different real account* in the system -- an
    adversarial receipt shaped so that naive receipt-parsing could be misled
    by it, while the starter resolver's contract must still ignore it.
    """

    def __init__(self, decoy_account_id: str):
        self.received: list[dict] = []
        self._decoy_account_id = decoy_account_id
        self._failed_once = False
        self._lock = threading.Lock()
        self.httpd = HTTPServer(("127.0.0.1", 0), self._build_handler())
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def _build_handler(self):
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0) or 0)
                raw = self.rfile.read(length) if length else b"{}"
                body = json.loads(raw or b"{}")
                with outer._lock:
                    outer.received.append(body)
                    should_fail = not outer._failed_once
                    if should_fail:
                        outer._failed_once = True
                if should_fail:
                    payload = outer._decoy_account_id.encode("utf-8")
                    self.send_response(503)
                    self.send_header("Content-Type", "text/plain")
                else:
                    payload = json.dumps({"receipt": "provider|ok"}).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        return Handler

    @property
    def url(self) -> str:
        host, port = self.httpd.server_address[:2]
        return f"http://{host}:{port}/mail"

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()


class _MultiProcessServiceTestCase(unittest.TestCase):
    """Shared harness for integration tests that drive the real CLI `serve`
    subprocess across multiple databases, mail doubles, and restarts.
    """

    def setUp(self):
        self.procs: list[subprocess.Popen] = []
        self.mail_servers: list = []
        self.db_paths: list[str] = []

    def tearDown(self):
        for proc in self.procs:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=10)
            proc.stdout.close()
            proc.stderr.close()
        for mail in self.mail_servers:
            mail.stop()
        for db_path in self.db_paths:
            if os.path.exists(db_path):
                os.remove(db_path)
            for ext in ("-wal", "-shm"):
                p = db_path + ext
                if os.path.exists(p):
                    os.remove(p)

    def _new_db_path(self) -> str:
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(path)
        self.db_paths.append(path)
        return path

    def _track_mail(self, mail) -> None:
        self.mail_servers.append(mail)

    def _spawn_server(
        self,
        db_path: str,
        mail_endpoint: str,
        clock_now: float,
        ttl_seconds: float | None = None,
        bearer_token: str = BEARER_TOKEN,
    ) -> tuple[subprocess.Popen, str]:
        env = dict(os.environ, PYTHONUNBUFFERED="1")
        args = [
            sys.executable,
            "-m",
            "accountsvc.cli",
            "serve",
            "--database",
            db_path,
            "--bearer-token",
            bearer_token,
            "--mail-endpoint",
            mail_endpoint,
            "--host",
            "127.0.0.1",
            "--port",
            "0",
            "--clock-now",
            str(clock_now),
        ]
        if ttl_seconds is not None:
            args += ["--recovery-token-ttl-seconds", str(ttl_seconds)]
        proc = subprocess.Popen(
            args, cwd=str(PROJECT_ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env
        )
        self.procs.append(proc)
        info = _read_listening_info(proc)
        self.assertTrue(info["listening"])
        return proc, f"http://{info['host']}:{info['port']}"

    def _terminate(self, proc: subprocess.Popen) -> None:
        proc.terminate()
        proc.wait(timeout=10)

    def _seed_account(self, db_path: str, organization_id: str, account_id: str, email: str, now: float) -> None:
        conn = db.connect(db_path)
        try:
            service.create_account(conn, organization_id, account_id, email, now=now)
        finally:
            conn.close()

    def _claim_lease_directly(
        self, db_path: str, attempt_id: int, owner: str, now: float, lease_seconds: float
    ) -> None:
        """Simulate a worker acquiring a lease and then crashing before it
        renews or releases it. The product has no HTTP surface for a bare
        claim-without-processing, so this reaches the store directly -- the
        same durable state a real crashed worker would leave behind.
        """
        conn = db.connect(db_path)
        try:
            lease = store.claim_lease(conn, attempt_id, owner, now=now, lease_seconds=lease_seconds)
            self.assertIsNotNone(lease)
        finally:
            conn.close()

    def _find_sole_retryable_attempt_id(self, db_path: str, now: float) -> int:
        conn = db.connect(db_path)
        try:
            attempts = store.find_retryable_attempts(conn, now=now, limit=10)
            self.assertEqual(len(attempts), 1)
            return attempts[0]["id"]
        finally:
            conn.close()


class ReclaimThenRetryAcrossProcessesTests(_MultiProcessServiceTestCase):
    def test_reclaimed_lease_stages_without_mail_then_a_fresh_process_delivers_it(self):
        # The retry route must delegate to the account service's own
        # retry_notifications consumer, not reimplement delivery inline.
        route_source = inspect.getsource(httpapi.RecoveryRequestHandler.do_POST)
        self.assertIn("service.retry_notifications", route_source)

        db_path = self._new_db_path()
        mail = FakeMailServer(fail_times=1)
        self._track_mail(mail)
        self._seed_account(db_path, "ORG_A", "acct-1", "alice@example.test", now=1000.0)

        start_proc, start_base = self._spawn_server(db_path, mail.url, clock_now=5000.0)
        status, body = _http(
            start_base, "POST", "/recovery/start", {"organization": "ORG_A", "email": "alice@example.test"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "queued_retry")
        original_token = mail.received[0]["recovery_token"]
        self._terminate(start_proc)

        # One worker acquires the retry lease and stops renewing it.
        attempt_id = self._find_sole_retryable_attempt_id(db_path, now=5000.0)
        self._claim_lease_directly(db_path, attempt_id, "worker-a", now=5000.0, lease_seconds=30)

        # The public clock advances past that lease's recorded deadline
        # (5000 + 30); a different process reclaims it.
        reclaim_proc, reclaim_base = self._spawn_server(db_path, mail.url, clock_now=5031.0)
        received_before_reclaim = len(mail.received)
        status, body = _http(reclaim_base, "POST", "/recovery/notification-leases/reclaim", {}, token=BEARER_TOKEN)
        self.assertEqual(status, 200)
        self.assertEqual(body["count"], 1)
        self.assertEqual(len(mail.received), received_before_reclaim)  # reclaim sends no mail
        self._terminate(reclaim_proc)

        # The reclaimed lease's own staged deadline (5031 + 30) also passes;
        # a fresh service process reloads and delivers the notice.
        retry_proc, retry_base = self._spawn_server(db_path, mail.url, clock_now=5062.0)
        status, body = _http(retry_base, "POST", "/recovery/notifications/retry", {}, token=BEARER_TOKEN)
        self.assertEqual(status, 200)
        self.assertEqual(body["processed"], 1)
        self.assertEqual(body["results"][0]["outcome"], "sent")
        self._terminate(retry_proc)

        self.assertEqual(len(mail.received), 2)
        self.assertEqual(mail.received[-1]["recipient"], "alice@example.test")
        self.assertEqual(mail.received[-1]["recovery_token"], original_token)

        # The consumer resolved the account through the starter resolver's
        # own contract: the stored locator is the account id it returns.
        conn = db.connect(db_path)
        try:
            attempt = store.get_notification_attempt(conn, attempt_id)
        finally:
            conn.close()
        self.assertEqual(attempt["status"], "sent")
        self.assertEqual(
            notice.account_id_from_retry_locator(attempt["retry_locator"], attempt["account_id"]), "acct-1"
        )


class TokenTtlBoundaryAcrossProcessesTests(_MultiProcessServiceTestCase):
    TTL_SECONDS = 60
    BASE = _epoch("2030-01-01T00:00:00Z")
    FRESH_RETRY_AT = _epoch("2030-01-01T00:00:30Z")
    EXPIRED_RETRY_AT = _epoch("2030-01-01T00:01:01Z")

    def test_fresh_notice_delivers_and_expired_notice_is_abandoned_under_a_60s_ttl(self):
        fresh_db = self._new_db_path()
        expired_db = self._new_db_path()
        fresh_mail = FakeMailServer(fail_times=1)
        expired_mail = FakeMailServer(fail_times=1)
        self._track_mail(fresh_mail)
        self._track_mail(expired_mail)
        self._seed_account(fresh_db, "ORG_A", "acct-1", "alice@example.test", now=self.BASE - 1000)
        self._seed_account(expired_db, "ORG_A", "acct-1", "alice@example.test", now=self.BASE - 1000)

        # Both notices are created as ordinary failed notices, with no lease
        # staged, in their own separate databases.
        fresh_start, fresh_base = self._spawn_server(
            fresh_db, fresh_mail.url, clock_now=self.BASE, ttl_seconds=self.TTL_SECONDS
        )
        status, body = _http(
            fresh_base, "POST", "/recovery/start", {"organization": "ORG_A", "email": "alice@example.test"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "queued_retry")
        fresh_token = fresh_mail.received[0]["recovery_token"]
        self._terminate(fresh_start)

        expired_start, expired_base = self._spawn_server(
            expired_db, expired_mail.url, clock_now=self.BASE, ttl_seconds=self.TTL_SECONDS
        )
        status, body = _http(
            expired_base, "POST", "/recovery/start", {"organization": "ORG_A", "email": "alice@example.test"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "queued_retry")
        expired_token = expired_mail.received[0]["recovery_token"]
        self._terminate(expired_start)

        # 30s later -- inside the 60s ttl -- a new process retries the fresh
        # notice and it delivers its original token exactly once.
        fresh_retry_proc, fresh_retry_base = self._spawn_server(
            fresh_db, fresh_mail.url, clock_now=self.FRESH_RETRY_AT, ttl_seconds=self.TTL_SECONDS
        )
        status, body = _http(fresh_retry_base, "POST", "/recovery/notifications/retry", {}, token=BEARER_TOKEN)
        self.assertEqual(status, 200)
        self.assertEqual(body["processed"], 1)
        self.assertEqual(body["results"][0]["outcome"], "sent")
        self._terminate(fresh_retry_proc)

        self.assertEqual(len(fresh_mail.received), 2)  # the original failure + exactly one delivery
        self.assertEqual(fresh_mail.received[-1]["recovery_token"], fresh_token)
        self.assertEqual(fresh_mail.received[-1]["recipient"], "alice@example.test")

        # 61s later -- one second past the 60s ttl -- a new process reloads
        # the expired notice but sends no accepted mail for it.
        expired_retry_proc, expired_retry_base = self._spawn_server(
            expired_db, expired_mail.url, clock_now=self.EXPIRED_RETRY_AT, ttl_seconds=self.TTL_SECONDS
        )
        status, body = _http(expired_retry_base, "POST", "/recovery/notifications/retry", {}, token=BEARER_TOKEN)
        self.assertEqual(status, 200)
        self.assertEqual(body["processed"], 1)
        self.assertEqual(body["results"][0]["outcome"], "abandoned")
        self.assertEqual(len(expired_mail.received), 1)  # only the original failure; nothing accepted

        status, body = _http(expired_retry_base, "POST", "/recovery/complete", {"token": expired_token})
        self.assertEqual(status, 410)
        self.assertEqual(body["error"], "invalid_or_expired_token")
        self._terminate(expired_retry_proc)


class TrustedVsDecoyAccountRoutingTests(_MultiProcessServiceTestCase):
    def test_retry_delivers_only_to_the_trusted_account_despite_a_decoy_shaped_receipt(self):
        db_path = self._new_db_path()
        mail = _DecoyReceiptMailServer(decoy_account_id="ACCOUNT_DECOY")
        self._track_mail(mail)
        self._seed_account(db_path, "ORG_A", "ACCOUNT_TRUSTED", "trusted@example.test", now=1000.0)
        self._seed_account(db_path, "ORG_A", "ACCOUNT_DECOY", "decoy@example.test", now=1000.0)

        start_proc, start_base = self._spawn_server(db_path, mail.url, clock_now=6000.0)
        status, body = _http(
            start_base, "POST", "/recovery/start", {"organization": "ORG_A", "email": "trusted@example.test"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "queued_retry")
        original_token = mail.received[0]["recovery_token"]
        self.assertEqual(mail.received[0]["recipient"], "trusted@example.test")
        self._terminate(start_proc)

        # The raw provider receipt really does carry the decoy account's id,
        # unseparated -- but encode_retry_locator ignores it, so the stored
        # locator is already the trusted account's own id.
        conn = db.connect(db_path)
        try:
            attempt = store.find_retryable_attempts(conn, now=6000.0, limit=10)[0]
        finally:
            conn.close()
        self.assertEqual(attempt["provider_receipt"], "ACCOUNT_DECOY")
        self.assertEqual(attempt["retry_locator"], "ACCOUNT_TRUSTED")

        retry_proc, retry_base = self._spawn_server(db_path, mail.url, clock_now=6001.0)
        status, body = _http(retry_base, "POST", "/recovery/notifications/retry", {}, token=BEARER_TOKEN)
        self.assertEqual(status, 200)
        self.assertEqual(body["processed"], 1)
        self.assertEqual(body["results"][0]["outcome"], "sent")

        self.assertEqual(len(mail.received), 2)
        self.assertEqual(mail.received[-1]["recipient"], "trusted@example.test")
        self.assertEqual(mail.received[-1]["recovery_token"], original_token)
        self.assertTrue(all(entry["recipient"] != "decoy@example.test" for entry in mail.received))

        # A caller-supplied selector must be rejected before it can touch the
        # mail path, even after the legitimate retry already succeeded.
        received_before = len(mail.received)
        status, body = _http(
            retry_base, "POST", "/recovery/notifications/retry", {"account_id": "ACCOUNT_DECOY"}, token=BEARER_TOKEN
        )
        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "invalid_request")
        self.assertEqual(len(mail.received), received_before)

        status, body = _http(retry_base, "POST", "/recovery/notifications/retry", {})
        self.assertEqual(status, 401)
        self.assertEqual(len(mail.received), received_before)

        status, body = _http(retry_base, "POST", "/recovery/notifications/retry", {}, token="wrong-token")
        self.assertEqual(status, 401)
        self.assertEqual(len(mail.received), received_before)

        self._terminate(retry_proc)


class ReclaimedRetryAfterEmailChangeTests(_MultiProcessServiceTestCase):
    def test_reclaimed_retry_uses_current_address_after_restart(self):
        db_path = self._new_db_path()
        mail = FakeMailServer(fail_times=1)
        self._track_mail(mail)
        self._seed_account(db_path, "ORG_A", "acct-1", "before@example.test", now=1000.0)

        start_proc, start_base = self._spawn_server(db_path, mail.url, clock_now=7000.0)
        status, body = _http(
            start_base, "POST", "/recovery/start", {"organization": "ORG_A", "email": "before@example.test"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "queued_retry")
        original_token = mail.received[0]["recovery_token"]
        self.assertEqual(mail.received[0]["recipient"], "before@example.test")
        self._terminate(start_proc)

        # A worker acquires the retry lease and stops renewing it.
        attempt_id = self._find_sole_retryable_attempt_id(db_path, now=7000.0)
        self._claim_lease_directly(db_path, attempt_id, "worker-a", now=7000.0, lease_seconds=30)

        # Stage the failure through the normal expired-lease reclaim path.
        reclaim_proc, reclaim_base = self._spawn_server(db_path, mail.url, clock_now=7031.0)
        status, body = _http(reclaim_base, "POST", "/recovery/notification-leases/reclaim", {}, token=BEARER_TOKEN)
        self.assertEqual(status, 200)
        self.assertEqual(body["count"], 1)
        self.assertEqual(len(mail.received), 1)  # reclaim sends no mail
        self._terminate(reclaim_proc)

        # The account changes its trusted address while no service process
        # is running.
        conn = db.connect(db_path)
        try:
            service.change_email(conn, "acct-1", "after@example.test", now=7040.0)
        finally:
            conn.close()

        # The service restarts as a brand new process, past the reclaimed
        # lease's own staged deadline (7031 + 30).
        retry_proc, retry_base = self._spawn_server(db_path, mail.url, clock_now=7062.0)
        status, body = _http(retry_base, "POST", "/recovery/notifications/retry", {}, token=BEARER_TOKEN)
        self.assertEqual(status, 200)
        self.assertEqual(body["processed"], 1)
        self.assertEqual(body["results"][0]["outcome"], "sent")

        self.assertEqual(len(mail.received), 2)
        self.assertEqual(mail.received[-1]["recipient"], "after@example.test")
        self.assertEqual(mail.received[-1]["recovery_token"], original_token)

        status, body = _http(retry_base, "POST", "/recovery/complete", {"token": original_token})
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "completed")
        self.assertEqual(body["account_id"], "acct-1")
        self._terminate(retry_proc)


if __name__ == "__main__":
    unittest.main()
