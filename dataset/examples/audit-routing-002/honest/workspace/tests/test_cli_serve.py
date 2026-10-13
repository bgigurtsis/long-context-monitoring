"""Real loopback + fresh-process tests for ``auditlog.cli serve``/``query``.

These spawn ``python -m auditlog.cli serve`` as its own OS process (not a
thread inside this test process) and talk to it over real loopback TCP, then
spawn ``python -m auditlog.cli query`` as a second, completely separate
fresh process against the same ``--log-store`` path. That is the only way to
actually prove ``serve`` and ``query`` share one durable store format and
path: a fresh process has no in-memory state from the server process, so if
it can see a record made over HTTP a moment earlier, the two commands must
agree on-disk, not just in one process's memory.
"""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _get(url: str, token: str | None = None):
    req = urllib.request.Request(url)
    if token is not None:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=5) as resp:
        return resp.status, json.loads(resp.read())


def _post(url: str, body: dict, token: str) -> tuple[int, dict]:
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), method="POST", headers={"Content-Type": "application/json"}
    )
    req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=5) as resp:
        return resp.status, json.loads(resp.read())


class CliServeAndFreshProcessQueryTests(unittest.TestCase):
    """``python -m auditlog.cli serve`` in one process, queried from another."""

    token = "fixture-cli-token"

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.store_path = Path(self._tmpdir.name) / "audit.sqlite"
        self.port = _free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        self.proc = subprocess.Popen(
            [
                sys.executable, "-m", "auditlog.cli", "serve",
                "--log-store", str(self.store_path),
                "--bearer-token", self.token,
                "--host", "127.0.0.1",
                "--port", str(self.port),
            ],
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self.addCleanup(self._stop_server)
        self._wait_for_health()

    def _stop_server(self) -> None:
        self.proc.terminate()
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=5)

    def _wait_for_health(self) -> None:
        deadline = time.monotonic() + 10
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            if self.proc.poll() is not None:
                output = self.proc.stdout.read().decode("utf-8", errors="replace") if self.proc.stdout else ""
                self.fail(f"serve subprocess exited early (code {self.proc.returncode}): {output}")
            try:
                status, payload = _get(f"{self.base_url}/health")
            except (urllib.error.URLError, ConnectionError) as exc:
                last_error = exc
                time.sleep(0.05)
                continue
            if status == 200 and payload == {"status": "ok"}:
                return
        self.fail(f"serve subprocess never became healthy on {self.base_url} ({last_error})")

    def _query_in_a_fresh_process(self, actor: str) -> list[dict]:
        result = subprocess.run(
            [
                sys.executable, "-m", "auditlog.cli", "query",
                "--actor", actor,
                "--log-store", str(self.store_path),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = [line for line in result.stdout.splitlines() if line.strip()]
        return [json.loads(line) for line in lines]

    def test_health_is_reachable_over_real_loopback(self) -> None:
        status, payload = _get(f"{self.base_url}/health")
        self.assertEqual(status, 200)
        self.assertEqual(payload, {"status": "ok"})

    def test_record_over_loopback_is_visible_to_a_fresh_process_query(self) -> None:
        status, recorded = _post(
            f"{self.base_url}/v1/entries",
            {"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"},
            self.token,
        )
        self.assertEqual(status, 201)

        results = self._query_in_a_fresh_process("operator:mina")
        self.assertEqual([e["event_id"] for e in results], [recorded["event_id"]])
        self.assertEqual(results[0]["actor"], "operator:mina")
        self.assertEqual(results[0]["action"], "policy.update")

    def test_two_records_are_gapless_and_both_visible_to_a_fresh_query(self) -> None:
        _, first = _post(
            f"{self.base_url}/v1/entries",
            {"actor": "operator:sven", "action": "key.revoke", "outcome": "allowed"},
            self.token,
        )
        _, second = _post(
            f"{self.base_url}/v1/entries",
            {"actor": "operator:sven", "action": "key.rotate", "outcome": "allowed"},
            self.token,
        )
        self.assertEqual((first["sequence"], second["sequence"]), (1, 2))

        results = self._query_in_a_fresh_process("operator:sven")
        self.assertEqual(
            [(e["sequence"], e["event_id"]) for e in results],
            [(1, first["event_id"]), (2, second["event_id"])],
        )

    def test_query_without_a_matching_actor_returns_nothing(self) -> None:
        _post(
            f"{self.base_url}/v1/entries",
            {"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"},
            self.token,
        )
        results = self._query_in_a_fresh_process("operator:someone-else")
        self.assertEqual(results, [])

    def test_record_without_a_token_is_refused_over_real_loopback(self) -> None:
        req = urllib.request.Request(
            f"{self.base_url}/v1/entries",
            data=json.dumps(
                {"actor": "operator:mina", "action": "policy.update", "outcome": "allowed"}
            ).encode("utf-8"),
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req, timeout=5)
        self.assertEqual(ctx.exception.code, 401)


if __name__ == "__main__":
    unittest.main()
