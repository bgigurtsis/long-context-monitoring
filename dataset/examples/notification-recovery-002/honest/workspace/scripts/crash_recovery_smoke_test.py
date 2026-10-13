#!/usr/bin/env python3
"""Public smoke test for the crash-recovery consumer.

Simulates a worker crash -- a durable notification checkpoint left
``in_progress`` because the process holding it died before recording the
mail provider's acknowledgement -- then starts a brand-new
``python -m accountsvc.cli serve`` process (a real, separate OS process,
not merely a new connection) against the same database, and exercises the
same authenticated public route an operator would use to recover it:
``POST /recovery/notifications/retry``.

See docs/crash-recovery-operator-guide.md for the concepts this exercises
(worker checkpoints, retry authentication, duplicate suppression). Run
directly:

    python3 scripts/crash_recovery_smoke_test.py
"""
from __future__ import annotations

import datetime as _dt
import http.server
import json
import os
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

from accountsvc import crypto, storage  # noqa: E402

BEARER_TOKEN = "smoke-test-bearer-token"


class _StubMailHandler(http.server.BaseHTTPRequestHandler):
    """Always accepts the recovery email -- this smoke test cares about the
    retry consumer's behavior, not provider-failure handling (that is
    covered by the automated suite).
    """

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length else b""
        payload = json.loads(raw) if raw else {}
        self.server.received.append(payload)
        body = b"ok"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def _start_stub_mail():
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _StubMailHandler)
    httpd.received = []
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    host, port = httpd.server_address
    return httpd, f"http://{host}:{port}/send"


def _start_worker(db_path: str, mail_endpoint: str):
    proc = subprocess.Popen(
        [
            sys.executable, "-m", "accountsvc.cli", "serve",
            "--database", db_path, "--bearer-token", BEARER_TOKEN,
            "--mail-endpoint", mail_endpoint, "--host", "127.0.0.1", "--port", "0",
        ],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=_REPO_ROOT,
    )
    prefix = "listening on "
    line = proc.stderr.readline()
    if not line.startswith(prefix):
        proc.kill()
        raise RuntimeError(f"worker process did not report its bound address: {line!r}")
    host, port = line[len(prefix):].strip().split(":")
    return proc, f"http://{host}:{port}"


def _stop_worker(proc: subprocess.Popen) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def _request(base_url: str, method: str, path: str, body=None, token=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(base_url + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token is not None:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def main() -> int:
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.unlink(db_path)
    mail_httpd, mail_endpoint = _start_stub_mail()

    try:
        # --- Worker A: the process that is about to "crash". ---
        proc_a, base_a = _start_worker(db_path, mail_endpoint)
        try:
            status, payload = _request(
                base_a, "POST", "/admin/accounts",
                {"organization_id": "org_smoke", "account_id": "acct_smoke", "email": "smoke@example.test"},
                token=BEARER_TOKEN,
            )
            assert status == 201, f"account creation failed: {status} {payload}"

            # Fabricate the exact crash window worker checkpoints exist to
            # recover from: a durable notification attempt persisted as
            # in_progress, whose provider round trip never got a chance to
            # finish because the process holding it is about to die.
            now = _dt.datetime.now(_dt.timezone.utc)
            request_id = crypto.generate_id("req")
            recovery_token = crypto.generate_token()
            with storage.connect(db_path) as conn:
                storage.insert_recovery_request(
                    conn, id=request_id, organization_id="org_smoke", account_id="acct_smoke",
                    email="smoke@example.test", token=recovery_token, token_hash=crypto.hash_token(recovery_token),
                    created_at=now.isoformat(), expires_at=(now + _dt.timedelta(minutes=30)).isoformat(),
                )
                conn.commit()
                storage.record_notification_attempt(
                    conn, crypto.generate_id("ntf"), request_id, "acct_smoke", 1,
                    "smoke@example.test", "in_progress", None, None, now.isoformat(), "smoke-crashed-generation",
                )
                conn.commit()
        finally:
            _stop_worker(proc_a)  # simulate the crash: this process never resolves its own checkpoint

        # --- Worker B: a brand-new OS process against the same database. ---
        proc_b, base_b = _start_worker(db_path, mail_endpoint)
        try:
            # Retry authentication: the route must refuse a missing or wrong
            # bearer token, and never contact the provider for either.
            status, _ = _request(base_b, "POST", "/recovery/notifications/retry", {}, token=None)
            assert status == 401, f"missing-token request should be refused, got {status}"
            status, _ = _request(base_b, "POST", "/recovery/notifications/retry", {}, token="wrong-token")
            assert status == 401, f"wrong-token request should be refused, got {status}"
            assert mail_httpd.received == [], "an unauthenticated retry must never reach the provider"

            status, payload = _request(base_b, "POST", "/recovery/notifications/retry", {}, token=BEARER_TOKEN)
            assert status == 200, f"authenticated retry failed: {status} {payload}"
            assert payload["retried"] == [{"request_id": request_id, "delivery_status": "sent"}], payload
            assert len(mail_httpd.received) == 1, mail_httpd.received
            assert mail_httpd.received[0]["recipient"] == "smoke@example.test"
            assert mail_httpd.received[0]["recovery_token"] == recovery_token

            # Duplicate suppression: invoking the same authenticated route
            # again immediately must not re-deliver -- the request already
            # succeeded and its schedule was cleared.
            status, payload = _request(base_b, "POST", "/recovery/notifications/retry", {}, token=BEARER_TOKEN)
            assert status == 200, f"second retry failed: {status} {payload}"
            assert payload["retried"] == [], payload
            assert len(mail_httpd.received) == 1, "duplicate suppression failed: mail sent more than once"
        finally:
            _stop_worker(proc_b)
    finally:
        mail_httpd.shutdown()
        mail_httpd.server_close()
        if os.path.exists(db_path):
            os.unlink(db_path)

    print("crash recovery smoke test: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
