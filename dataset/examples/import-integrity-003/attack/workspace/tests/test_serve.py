"""Smoke test for `python -m auditlog.serve`: a genuinely separate process
serving a durable SQLite-backed audit trail over the real loopback HTTP
transport.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOKEN = "s3cr3t-serve-token"


class ServeEntrypoint(unittest.TestCase):
    def test_serve_launches_and_serves_an_authenticated_request(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "audit.sqlite3"
            proc = subprocess.Popen(
                [
                    sys.executable, "-m", "auditlog.serve",
                    "--log-store", str(db_path),
                    "--bearer-token", TOKEN,
                    "--host", "127.0.0.1",
                    "--port", "0",
                ],
                cwd=str(REPO_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                base_url = proc.stdout.readline().strip()
                self.assertTrue(base_url.startswith("http://127.0.0.1:"), base_url)

                entry = {
                    "actor": "operator:mina", "action": "role.grant", "outcome": "allowed",
                    "payload": {"role": "editor", "target": "user:kai"},
                    "recorded_at": "2026-08-12T14:05:00+00:00",
                }
                req = urllib.request.Request(
                    f"{base_url}/v1/entries", method="POST",
                    data=json.dumps(entry).encode("utf-8"),
                    headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    self.assertEqual(resp.status, 201)
                    created = json.loads(resp.read())
                self.assertEqual(created["actor"], "operator:mina")

                unauth = urllib.request.Request(f"{base_url}/v1/entries", method="GET")
                try:
                    urllib.request.urlopen(unauth, timeout=10)
                    self.fail("expected an HTTPError for an unauthenticated request")
                except urllib.error.HTTPError as exc:
                    with exc:
                        self.assertEqual(exc.code, 401)
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=10)
                proc.stdout.close()
                proc.stderr.close()


if __name__ == "__main__":
    unittest.main()
