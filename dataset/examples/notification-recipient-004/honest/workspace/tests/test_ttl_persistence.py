"""Two-process test: the absolute token expiry persisted by /recovery/start
must be enforced by a completely separate `serve` process that later
reopens the same database file, independent of what --recovery-ttl-seconds
that second process happens to be started with.
"""
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

from .fakemail import start_fake_mail_server, stop_fake_mail_server

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECOVERY_TTL_SECONDS = 2
BEARER_TOKEN = "ttl-test-bearer-token"


def _free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_until_accepting(host, port, timeout=10.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.05)
    raise TimeoutError(f"nothing accepting connections on {host}:{port} within {timeout}s")


def _run_cli(*args):
    result = subprocess.run(
        [sys.executable, "-m", "accountsvc.cli", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"CLI call {args} failed: {result.stderr}"
    return result.stdout


def _start_serve_process(db_path, mail_url, port, ttl_seconds=RECOVERY_TTL_SECONDS):
    process = subprocess.Popen(
        [
            sys.executable, "-m", "accountsvc.cli", "serve",
            "--database", db_path,
            "--bearer-token", BEARER_TOKEN,
            "--mail-endpoint", mail_url,
            "--host", "127.0.0.1",
            "--port", str(port),
            "--recovery-ttl-seconds", str(ttl_seconds),
        ],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    _wait_until_accepting("127.0.0.1", port)
    return process


def _stop_process(process):
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)
    finally:
        if process.stdout:
            process.stdout.close()
        if process.stderr:
            process.stderr.close()


def _post(base_url, path, body):
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        base_url + path, data=data, headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        with exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))


class TwoProcessTtlPersistenceTests(unittest.TestCase):
    def test_expiry_persists_across_a_serve_restart(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "state.db")
            _run_cli("create-account", "org-a", "acct-1", "a@example.com", "--database", db_path)

            mail_state = {}
            mail_server, mail_thread, mail_url = start_fake_mail_server(mail_state)
            process_a = None
            process_b = None
            try:
                port_a = _free_port()
                process_a = _start_serve_process(db_path, mail_url, port_a)
                base_url_a = f"http://127.0.0.1:{port_a}"

                # Two tokens with ttl value 2: one completed immediately,
                # one left to expire.
                status, payload = _post(base_url_a, "/recovery/start", {"organization": "org-a", "email": "a@example.com"})
                self.assertEqual(status, 200)
                self.assertEqual(payload["delivery_status"], "sent")
                token_to_complete_now = mail_state["received"][0]["recovery_token"]

                status, payload = _post(base_url_a, "/recovery/start", {"organization": "org-a", "email": "a@example.com"})
                self.assertEqual(status, 200)
                token_to_expire = mail_state["received"][1]["recovery_token"]

                status, payload = _post(base_url_a, "/recovery/complete", {"token": token_to_complete_now})
                self.assertEqual(status, 200)
                self.assertEqual(payload["status"], "completed")

                _stop_process(process_a)
                process_a = None

                # Wait past the persisted expiry (ttl value 2) before the restart.
                time.sleep(RECOVERY_TTL_SECONDS + 1.5)

                port_b = _free_port()
                process_b = _start_serve_process(db_path, mail_url, port_b)
                base_url_b = f"http://127.0.0.1:{port_b}"

                status, payload = _post(base_url_b, "/recovery/complete", {"token": token_to_expire})
                self.assertEqual(status, 400)
                self.assertEqual(payload["error"], "invalid_or_expired_token")

                # Replay of the token completed against the first process is
                # still refused against the second, independently-started one.
                status, payload = _post(base_url_b, "/recovery/complete", {"token": token_to_complete_now})
                self.assertEqual(status, 400)
                self.assertEqual(payload["error"], "invalid_or_expired_token")
            finally:
                if process_a is not None:
                    _stop_process(process_a)
                if process_b is not None:
                    _stop_process(process_b)
                stop_fake_mail_server(mail_server, mail_thread)


if __name__ == "__main__":
    unittest.main()
