"""Drive a persisted Codex CLI thread through the app-server protocol.

The ordinary ``codex exec`` surface can resume a thread, but it cannot request a
manual compaction.  ``codex app-server`` is still a Codex CLI surface and exposes
the exact operation used by the TUI: ``thread/compact/start``.  Keeping one
app-server process alive also gives us a simple request/notification boundary
for turn completion without scraping terminal prose.
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
from collections import deque
from pathlib import Path
from typing import Callable

from . import delivery
from .session import IDLE_TIMEOUT_SECONDS, SessionError, log


POLICY_MODEL = "gpt-5.6-sol"
POLICY_EFFORT = "high"


def prepare_codex_home(parent: Path) -> Path:
    """Create an isolated Codex home while reusing only the operator's auth.

    User config, global AGENTS instructions, plugins, memories, and MCP servers
    are experimental contamination.  The auth symlink is deliberately the sole
    inherited file; the generated session store therefore lives beside the
    temporary workspace and remains available for crash resume.
    """

    home = parent / "codex-home"
    home.mkdir(parents=True, exist_ok=True)
    source = Path.home() / ".codex" / "auth.json"
    target = home / "auth.json"
    if source.is_file() and not target.exists():
        target.symlink_to(source)
    return home


def find_session_file(session_id: str, codex_home: Path) -> Path | None:
    """Locate a native rollout whose session metadata owns ``session_id``."""

    for path in sorted((codex_home / "sessions").glob("**/*.jsonl")):
        try:
            first = json.loads(path.open(encoding="utf-8").readline())
        except (OSError, json.JSONDecodeError):
            continue
        payload = first.get("payload") or {}
        if first.get("type") == "session_meta" and payload.get("id") == session_id:
            return path
    return None


def child_session_files(session_id: str, codex_home: Path) -> list[tuple[Path, dict]]:
    """Return the recursively spawned Codex threads beneath ``session_id``."""

    records: dict[str, tuple[Path, dict]] = {}
    for path in sorted((codex_home / "sessions").glob("**/*.jsonl")):
        try:
            first = json.loads(path.open(encoding="utf-8").readline())
        except (OSError, json.JSONDecodeError):
            continue
        if first.get("type") != "session_meta":
            continue
        payload = first.get("payload") or {}
        thread_id = payload.get("id")
        if isinstance(thread_id, str):
            records[thread_id] = (path, payload)

    descendants: list[tuple[Path, dict]] = []
    parents = {session_id}
    while True:
        found: list[tuple[Path, dict]] = []
        for thread_id, record in records.items():
            if thread_id == session_id:
                continue
            if record[1].get("parent_thread_id") in parents:
                found.append(record)
        new_ids = {record[1].get("id") for record in found}
        if not new_ids - parents:
            break
        for record in found:
            if record not in descendants:
                descendants.append(record)
        parents.update(new_ids)
    return descendants


def version() -> str:
    """Best-effort installed Codex CLI version."""

    try:
        completed = subprocess.run(
            ["codex", "--version"], capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
        return completed.stdout.strip() or "unknown"
    except OSError:
        return "unknown"


class AppServer:
    """Small synchronous JSON-RPC client for one Codex app-server process."""

    def __init__(self, workspace: Path, codex_home: Path):
        environment = os.environ.copy()
        environment["CODEX_HOME"] = str(codex_home)
        self.process = subprocess.Popen(
            ["codex", "app-server", "--stdio"],
            cwd=workspace,
            env=environment,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            encoding="utf-8",
            errors="replace",
        )
        self.messages: queue.Queue[dict | None] = queue.Queue()
        self.stderr_tail: deque[str] = deque(maxlen=50)
        self.pending: list[dict] = []
        self.next_id = 1

        def drain_stdout() -> None:
            for line in self.process.stdout:
                try:
                    value = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(value, dict):
                    self.messages.put(value)
            self.messages.put(None)

        def drain_stderr() -> None:
            for line in self.process.stderr:
                self.stderr_tail.append(line)

        threading.Thread(target=drain_stdout, daemon=True).start()
        threading.Thread(target=drain_stderr, daemon=True).start()
        try:
            self.request(
                "initialize",
                {
                    "clientInfo": {
                        "name": "lcm", "title": "LCM generator", "version": "1",
                    },
                    "capabilities": {"experimentalApi": True},
                },
            )
            self.notify("initialized")
        except Exception:
            self.close()
            raise

    def notify(self, method: str, params: dict | None = None) -> None:
        payload: dict = {"method": method}
        if params is not None:
            payload["params"] = params
        try:
            self.process.stdin.write(json.dumps(payload) + "\n")
            self.process.stdin.flush()
        except (BrokenPipeError, ValueError) as error:
            raise SessionError(f"could not send Codex notification {method}") from error

    def _read_fresh(self) -> dict:
        try:
            message = self.messages.get(timeout=IDLE_TIMEOUT_SECONDS)
        except queue.Empty as error:
            self.process.kill()
            raise SessionError("Codex app-server produced no output before timeout") from error
        if message is None:
            tail = "".join(list(self.stderr_tail)[-5:]).strip()
            raise SessionError(f"Codex app-server exited unexpectedly: {tail}")
        return message

    def request(self, method: str, params: dict) -> dict:
        request_id = self.next_id
        self.next_id += 1
        payload = {"id": request_id, "method": method, "params": params}
        try:
            self.process.stdin.write(json.dumps(payload) + "\n")
            self.process.stdin.flush()
        except (BrokenPipeError, ValueError) as error:
            raise SessionError(f"could not send Codex request {method}") from error

        deferred = self.pending
        self.pending = []
        while True:
            message = self._read_fresh()
            if message.get("id") != request_id:
                deferred.append(message)
                continue
            self.pending.extend(deferred)
            if "error" in message:
                raise SessionError(f"Codex {method} failed: {message['error']}")
            return message.get("result") or {}

    def wait_notification(
        self,
        method: str | tuple[str, ...],
        predicate: Callable[[dict], bool] | None = None,
    ) -> dict:
        methods = (method,) if isinstance(method, str) else method
        deferred: list[dict] = []
        while True:
            if self.pending:
                message = self.pending.pop(0)
            else:
                message = self._read_fresh()
            params = message.get("params") or {}
            if message.get("method") in methods and (
                predicate is None or predicate(params)
            ):
                self.pending = deferred + self.pending
                return params
            deferred.append(message)

    def close(self) -> None:
        try:
            self.process.stdin.close()
        except (BrokenPipeError, ValueError):
            pass
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            self.process.wait(timeout=10)


def _thread_params(
    workspace: Path,
    model: str,
    compaction_mode: str,
) -> dict:
    config: dict = {
        "project_doc_max_bytes": 0,
        "mcp_servers": {},
        "features": {"memories": False, "plugins": False},
    }
    if compaction_mode == "manual":
        # App-server does not expose a boolean disable switch.  Put its automatic
        # threshold far beyond every model context so only our explicit
        # thread/compact/start operations can create boundaries.
        config["model_auto_compact_token_limit"] = 1_000_000_000
    elif compaction_mode != "automatic":
        raise ValueError(f"unknown compaction mode {compaction_mode!r}")
    return {
        "model": model,
        "cwd": str(workspace),
        "runtimeWorkspaceRoots": [str(workspace)],
        "approvalPolicy": "never",
        "approvalsReviewer": "user",
        "sandbox": "danger-full-access",
        "allowProviderModelFallback": False,
        "ephemeral": False,
        "config": config,
    }


def _send_turn(
    server: AppServer,
    thread_id: str,
    label: str,
    text: str,
    model: str,
    effort: str | None,
) -> None:
    log(f">>> {label}")
    params: dict = {
        "threadId": thread_id,
        "input": [{"type": "text", "text": text}],
        "model": model,
        "effort": effort,
    }
    result = server.request(
        "turn/start",
        params,
    )
    turn_id = (result.get("turn") or {}).get("id")
    if not turn_id:
        raise SessionError("Codex turn/start returned no turn id")
    completed = server.wait_notification(
        "turn/completed", lambda params: (params.get("turn") or {}).get("id") == turn_id
    )
    status = (completed.get("turn") or {}).get("status")
    if status != "completed":
        raise SessionError(f"{label} ended with Codex status {status!r}")


def _compact(server: AppServer, thread_id: str, label: str) -> None:
    log(f">>> {label}")
    server.request("thread/compact/start", {"threadId": thread_id})

    def completed_compaction(params: dict) -> bool:
        if params.get("threadId") != thread_id:
            return False
        if "item" in params:
            return (params.get("item") or {}).get("type") == "contextCompaction"
        return "turnId" in params

    # New app-server versions complete compaction with an item/completed
    # contextCompaction event. Keep accepting the deprecated thread/compacted
    # notification so runs remain compatible with older installed CLIs.
    server.wait_notification(
        ("thread/compacted", "item/completed"), completed_compaction
    )


def _attach_thread(
    server, thread_id, workspace, policy_model, compaction_mode, observed
):
    """Start or resume one native thread and retain its reported provenance."""
    if thread_id is None:
        result = server.request(
            "thread/start",
            _thread_params(workspace, policy_model, compaction_mode),
        )
        thread = result.get("thread") or {}
        thread_id = thread.get("id")
        observed["policy_model"] = result.get("model") or policy_model
        if not thread_id:
            raise SessionError("Codex thread/start returned no thread id")
        observed["session_id"] = thread_id
        log(f"  session {thread_id} model {observed['policy_model']}")
    else:
        params = _thread_params(workspace, policy_model, compaction_mode)
        params["threadId"] = thread_id
        params.pop("allowProviderModelFallback", None)
        params.pop("ephemeral", None)
        server.request("thread/resume", params)

    return thread_id


def _drive_messages(
    server,
    thread_id,
    remaining,
    base,
    on_turn_complete,
    policy_model,
    policy_effort,
    observed,
):
    """Checkpoint only completed native turns, including explicit compactions."""
    for local_index, (label, text) in enumerate(remaining, start=1):
        if label.startswith("compaction"):
            _compact(server, thread_id, label)
            observed["compaction_model"] = observed["policy_model"]
        else:
            _send_turn(
                server,
                thread_id,
                label,
                text,
                policy_model,
                policy_effort,
            )
        on_turn_complete(base + local_index, thread_id)


def drive_segments(
    plan_segments: list[delivery.Segment],
    already_completed: int,
    workspace: Path,
    resume_session_id: str | None,
    on_turn_complete: Callable[[int, str], None],
    policy_model: str = POLICY_MODEL,
    compaction_mode: str = "manual",
    policy_effort: str | None = POLICY_EFFORT,
    codex_home: Path | None = None,
) -> dict:
    """Run all plan segments in one persisted Codex thread.

    Codex keeps one persisted honest thread across all segments.
    """

    if codex_home is None:
        codex_home = prepare_codex_home(workspace.parent)
    observed = {
        "session_id": resume_session_id,
        "policy_model": policy_model,
        "compaction_model": None,
        "native_home": str(codex_home),
    }
    server = AppServer(workspace, codex_home)
    try:
        thread_id = resume_session_id
        offset = 0
        for segment in plan_segments:
            remaining = segment.messages[max(0, already_completed - offset) :]
            if not remaining:
                offset += len(segment.messages)
                continue
            thread_id = _attach_thread(
                server, thread_id, workspace, policy_model, compaction_mode, observed
            )

            base = offset + max(0, already_completed - offset)
            _drive_messages(
                server,
                thread_id,
                remaining,
                base,
                on_turn_complete,
                policy_model,
                policy_effort,
                observed,
            )
            offset += len(segment.messages)
    finally:
        server.close()
    if observed["session_id"] is None:
        raise SessionError("no Codex segment reported a session id")
    return observed


def redacted_invocation(
    resume_session_id: str | None,
    policy_model: str,
    policy_effort: str | None,
) -> list[str]:
    """Human-auditable, secret-free description of app-server delivery."""

    argv = ["codex", "app-server", "--stdio", "thread/start"]
    if resume_session_id is not None:
        argv[-1] = "thread/resume"
        argv += ["<session-id>"]
    argv += ["--model", policy_model]
    if policy_effort is not None:
        argv += ["--effort", policy_effort]
    return argv
