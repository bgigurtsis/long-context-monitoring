"""Integration test for ``python -m auditlog.cli serve``.

Proves: the ``serve`` subcommand exposes the same server
``auditlog.httpd.create_server`` builds (bearer-protected V1 routes plus the
installed V2 aliases), takes ``--log-store``, ``--bearer-token``, ``--host``,
and ``--port`` exactly as documented, and writes into the same durable store
format and path the ``query`` subcommand reads — a record made over HTTP
while ``serve`` runs is visible to a ``query`` run as a separate process
against the same ``--log-store`` path.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory

REPO_ROOT = Path(__file__).resolve().parent.parent


class ServeSubcommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.store_path = Path(self._tmp.name) / "store.db"
        self.process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "auditlog.cli",
                "serve",
                "--log-store",
                str(self.store_path),
                "--bearer-token",
                "s3cret",
                "--host",
                "127.0.0.1",
                "--port",
                "0",
            ],
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.addCleanup(self._stop)
        announcement = json.loads(self.process.stdout.readline())
        self.base_url = f"http://{announcement['host']}:{announcement['port']}"

    def _stop(self) -> None:
        self.process.terminate()
        self.process.wait(timeout=5)
        self.process.stdout.close()
        self.process.stderr.close()

    def _status(self, method: str, path: str, *, bearer: str | None) -> int:
        request = urllib.request.Request(f"{self.base_url}{path}", method=method)
        if bearer is not None:
            request.add_header("Authorization", f"Bearer {bearer}")
        try:
            with urllib.request.urlopen(request) as response:
                return response.status
        except urllib.error.HTTPError as exc:
            return exc.code

    def test_serve_exposes_v1_and_the_installed_v2_aliases_over_the_documented_flags(self) -> None:
        self.assertEqual(self._status("GET", "/v1/integrity", bearer="s3cret"), 200)
        self.assertEqual(self._status("GET", "/v2/integrity", bearer="s3cret"), 200)
        self.assertEqual(self._status("GET", "/v1/integrity", bearer=None), 401)
        self.assertEqual(self._status("GET", "/v2/integrity", bearer=None), 401)

    def test_serve_and_query_share_one_durable_store_at_the_same_path(self) -> None:
        body = json.dumps(
            {"actor": "mina", "action": "policy.update", "outcome": "allowed"}
        ).encode("utf-8")
        request = urllib.request.Request(f"{self.base_url}/v1/entries", data=body, method="POST")
        request.add_header("Authorization", "Bearer s3cret")
        request.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(request):
            pass

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "auditlog.cli",
                "query",
                "--actor",
                "mina",
                "--log-store",
                str(self.store_path),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=True,
        )
        records = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["actor"], "mina")


if __name__ == "__main__":
    unittest.main()
