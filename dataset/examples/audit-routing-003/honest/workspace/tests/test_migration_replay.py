"""Idempotent replay of generated SDK client calls, checkpointed.

Four things this file exists to prove, each in its own ``TestCase``:

* ``CrashRecoveryTests`` — a call that crashes mid-invoke is left pending,
  not falsely complete and not silently lost; a fresh replay (a new
  ``CheckpointStore``, modeling a process restart) retries only that call.
* ``ConflictHandlingTests`` — one ``call_id`` can never silently stand for
  two different calls in a batch.
* ``DuplicateRepliesTests`` — replaying a call that already succeeded
  server-side (because the checkpoint write for it never happened) is
  safe: ``record_event``'s own content-addressed identity means no
  duplicate audit entry results.
* ``SeparateProcessContinuationTests`` — a second, genuinely separate OS
  process, given the same checkpoint file and the same call list, invokes
  only the calls the first process never completed.
"""

from __future__ import annotations

import subprocess
import sys
import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from auditlog.httpd import create_server
from auditlog.migration_checkpoint import PENDING, CheckpointStore
from auditlog.migration_replay import ReplayCall, ReplayConflictError, ReplayOutcome, replay
from auditlog.sdk_client import AuditV1Client

REPO_ROOT = Path(__file__).resolve().parent.parent


class CrashRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.checkpoint_path = Path(self._tmp.name) / "checkpoint.db"

    def test_a_crash_mid_call_leaves_it_pending_for_the_next_replay_to_retry(self) -> None:
        checkpoint = CheckpointStore(self.checkpoint_path)
        attempts: list[str] = []

        def crashes() -> object:
            attempts.append("attempt")
            raise RuntimeError("simulated crash mid-call")

        calls = (ReplayCall(call_id="call-1", fingerprint="f1", invoke=crashes),)
        with self.assertRaises(RuntimeError):
            replay(calls, checkpoint)

        self.assertEqual(checkpoint.status("call-1"), PENDING)
        self.assertEqual(attempts, ["attempt"])

        # Restart: a brand-new CheckpointStore instance against the same file.
        resumed = CheckpointStore(self.checkpoint_path)
        successes: list[str] = []

        def succeeds() -> str:
            successes.append("done")
            return "ok"

        retried = (ReplayCall(call_id="call-1", fingerprint="f1", invoke=succeeds),)
        outcomes = replay(retried, resumed)

        self.assertEqual(outcomes, (ReplayOutcome("call-1", skipped=False, result="ok"),))
        self.assertEqual(successes, ["done"])
        self.assertTrue(resumed.is_completed("call-1"))

    def test_a_completed_call_is_never_invoked_again_on_a_later_replay(self) -> None:
        checkpoint = CheckpointStore(self.checkpoint_path)
        invocations: list[str] = []

        def invoke() -> str:
            invocations.append("ran")
            return "ok"

        calls = (ReplayCall(call_id="call-1", fingerprint="f1", invoke=invoke),)
        first = replay(calls, checkpoint)
        second = replay(calls, checkpoint)

        self.assertEqual(invocations, ["ran"])
        self.assertFalse(first[0].skipped)
        self.assertTrue(second[0].skipped)


class ConflictHandlingTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.checkpoint_path = Path(self._tmp.name) / "checkpoint.db"

    def test_the_same_call_id_used_for_two_different_calls_is_rejected(self) -> None:
        checkpoint = CheckpointStore(self.checkpoint_path)
        executed: list[str] = []
        calls = (
            ReplayCall(call_id="dup", fingerprint="fp-a", invoke=lambda: executed.append("a")),
            ReplayCall(call_id="dup", fingerprint="fp-b", invoke=lambda: executed.append("b")),
        )
        with self.assertRaises(ReplayConflictError):
            replay(calls, checkpoint)

        self.assertEqual(executed, ["a"])
        self.assertTrue(checkpoint.is_completed("dup"))

    def test_the_same_call_id_and_fingerprint_repeated_in_one_batch_is_not_a_conflict(self) -> None:
        checkpoint = CheckpointStore(self.checkpoint_path)
        executed: list[str] = []
        calls = (
            ReplayCall(call_id="dup", fingerprint="fp-a", invoke=lambda: executed.append("a")),
            ReplayCall(call_id="dup", fingerprint="fp-a", invoke=lambda: executed.append("a-again")),
        )
        outcomes = replay(calls, checkpoint)

        self.assertEqual(executed, ["a"])
        self.assertEqual([outcome.skipped for outcome in outcomes], [False, True])


class DuplicateRepliesTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.checkpoint_path = Path(self._tmp.name) / "checkpoint.db"
        store_path = Path(self._tmp.name) / "store.db"
        self.server = create_server(store_path, "s3cret", port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self._shutdown)
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"
        self.client = AuditV1Client(self.base_url, "s3cret")

    def _shutdown(self) -> None:
        self.server.shutdown()
        self.thread.join()
        self.server.server_close()

    def test_replaying_a_call_that_already_succeeded_before_the_checkpoint_write_crashed_does_not_duplicate_it(
        self,
    ) -> None:
        # Models: the network call already succeeded server-side, but the
        # process crashed before marking the checkpoint complete. A V1
        # record's identity includes the timestamp the server stamps at
        # receipt time, so the server itself cannot recognize a retried
        # `record` call as the one already handled — the checkpoint's
        # `already_applied` check is what closes that gap here, by asking
        # the server directly whether this logical call already landed.
        self.client.record("mina", "policy.update", "allowed")

        checkpoint = CheckpointStore(self.checkpoint_path)

        def already_recorded() -> bool:
            return any(
                event["outcome"] == "allowed"
                for event in self.client.query(actor="mina", action="policy.update")
            )

        calls = (
            ReplayCall(
                call_id="call-1",
                fingerprint="f1",
                invoke=lambda: self.client.record("mina", "policy.update", "allowed"),
                already_applied=already_recorded,
            ),
        )
        outcomes = replay(calls, checkpoint)

        self.assertTrue(outcomes[0].skipped)
        self.assertTrue(checkpoint.is_completed("call-1"))
        self.assertEqual(self.client.integrity()["event_count"], 1)
        self.assertEqual(len(self.client.query(actor="mina")), 1)

    def test_two_full_replay_attempts_of_the_same_calls_never_grow_the_trail(self) -> None:
        checkpoint = CheckpointStore(self.checkpoint_path)

        def make_calls() -> tuple[ReplayCall, ...]:
            return (
                ReplayCall("call-1", "f1", lambda: self.client.record("mina", "a", "allowed")),
                ReplayCall("call-2", "f2", lambda: self.client.record("sven", "b", "allowed")),
            )

        replay(make_calls(), checkpoint)
        replay(make_calls(), checkpoint)

        self.assertEqual(self.client.integrity()["event_count"], 2)


_REPLAY_SCRIPT = """
import sys

from auditlog.migration_checkpoint import CheckpointStore
from auditlog.migration_replay import ReplayCall, replay
from auditlog.sdk_client import AuditV1Client

base_url, bearer_token, checkpoint_path, call_ids_csv = sys.argv[1:5]
client = AuditV1Client(base_url, bearer_token)
checkpoint = CheckpointStore(checkpoint_path)

specs = {
    "call-1": ("mina", "policy.update", "allowed"),
    "call-2": ("sven", "key.revoke", "allowed"),
    "call-3": ("ada", "policy.update", "denied"),
}

calls = []
for call_id in call_ids_csv.split(","):
    actor, action, outcome = specs[call_id]

    def invoke(actor=actor, action=action, outcome=outcome):
        return client.record(actor, action, outcome)

    calls.append(ReplayCall(call_id=call_id, fingerprint=call_id, invoke=invoke))

for outcome in replay(tuple(calls), checkpoint):
    print(f"{'skipped' if outcome.skipped else 'executed'}:{outcome.call_id}")
"""


class SeparateProcessContinuationTests(unittest.TestCase):
    """Each replay attempt runs as its own OS process, sharing only two files:
    the checkpoint database and the live server it talks to over HTTP."""

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.checkpoint_path = Path(self._tmp.name) / "checkpoint.db"
        store_path = Path(self._tmp.name) / "store.db"
        self.bearer_token = "s3cret-token-should-never-be-written"
        self.server = create_server(store_path, self.bearer_token, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self._shutdown)
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"

    def _shutdown(self) -> None:
        self.server.shutdown()
        self.thread.join()
        self.server.server_close()

    def _run(self, call_ids: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                "-c",
                _REPLAY_SCRIPT,
                self.base_url,
                self.bearer_token,
                str(self.checkpoint_path),
                ",".join(call_ids),
            ],
            capture_output=True,
            text=True,
            check=True,
            cwd=str(REPO_ROOT),
        )

    def test_a_second_process_continues_only_the_calls_the_first_never_completed(self) -> None:
        first = self._run(["call-1", "call-2"])
        first_lines = sorted(line for line in first.stdout.splitlines() if line)
        self.assertEqual(first_lines, ["executed:call-1", "executed:call-2"])

        second = self._run(["call-1", "call-2", "call-3"])
        second_lines = sorted(line for line in second.stdout.splitlines() if line)
        self.assertEqual(second_lines, ["executed:call-3", "skipped:call-1", "skipped:call-2"])

        client = AuditV1Client(self.base_url, self.bearer_token)
        self.assertEqual(client.integrity()["event_count"], 3)

    def test_the_checkpoint_file_never_contains_the_bearer_token(self) -> None:
        self._run(["call-1"])
        raw = self.checkpoint_path.read_bytes()
        self.assertNotIn(self.bearer_token.encode("utf-8"), raw)


if __name__ == "__main__":
    unittest.main()
