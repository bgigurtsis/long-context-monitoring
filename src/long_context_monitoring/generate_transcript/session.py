"""Driving the child ``claude`` process: argv, environment, and the turn loop."""

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
from .workspace_isolation import WorkspaceIsolationError, scoped_workspace_view

# Total silence from the child before we give up. A turn can think for a long
# time, so this is a hang detector, not a per-turn budget.
IDLE_TIMEOUT_SECONDS = 1800.0

# The policy model for every generated transcript, pinned rather than inherited
# from whatever the local ``claude`` CLI happens to default to, so transcripts
# generated on different machines or after a CLI update stay comparable. The
# compaction turn and any sub-agents run in this same session, so they share it.
POLICY_MODEL = "claude-sonnet-5"

# Leave the provider default unchanged unless a generation explicitly asks for
# an effort level. An omitted effort is meaningfully different from Claude
# Code's current "medium" setting, so it must not be silently invented.
POLICY_EFFORT: str | None = None

# The only settings the child gets, since ``--setting-sources ""`` gives it none.
# This is what restores the write permission that dropping the user source takes
# away; see ``build_argv``. A literal, so a manifest's recorded argv shows the
# exact string the session ran with.
CHILD_SETTINGS = (
    '{"permissions":{"allow":["Read","Write","Edit","Bash"],'
    '"defaultMode":"bypassPermissions"}}'
)


def profile_settings() -> str:
    """Return the tool grants used by profiled transcript segments.

    Workspace views still separate maintenance and application files.  This
    recorder collects tool attempts without a PreToolUse hook so
    a denied call cannot interrupt transcript collection.
    """

    return json.dumps(
        {
            "permissions": {
                "allow": ["Glob", "Grep", "Read", "Bash", "Write", "Edit"],
                "defaultMode": "bypassPermissions",
            },
        },
        separators=(",", ":"),
    )


class SessionError(RuntimeError):
    """The child session failed in a way that invalidates the run."""


def log(message: str) -> None:
    """Print progress. Separate from ``print`` so the run log can tee it."""
    print(message, flush=True)


# --------------------------------------------------------------------------- #
# Session
# --------------------------------------------------------------------------- #
def build_argv(
    resume_session_id: str | None = None,
    policy_model: str = POLICY_MODEL,
    policy_effort: str | None = POLICY_EFFORT,
    tool_profile: str | None = None,
) -> list[str]:
    """The ``claude`` command line for one continuous headless session."""
    argv = [
        "claude", "-p",
        "--input-format", "stream-json",
        "--output-format", "stream-json",
        "--verbose",
        "--permission-mode", "bypassPermissions",
        "--model", policy_model,
        "--strict-mcp-config",
        "--mcp-config", '{"mcpServers":{}}',
        "--setting-sources", "",
        "--settings", profile_settings() if tool_profile else CHILD_SETTINGS,
    ]
    if tool_profile == "padding":
        argv += ["--tools", "Glob,Grep,Read,Bash,Write,Edit"]
    elif tool_profile == "compaction":
        argv += ["--tools", ""]
    elif tool_profile == "application":
        argv += ["--tools", "default"]
    if policy_effort is not None:
        argv += ["--effort", policy_effort]
    if resume_session_id is not None:
        argv += ["--resume", resume_session_id]
    return argv


CLAUDE_AUTH_ENV = "LCM_CLAUDE_AUTH"
CLAUDE_AUTH_MODES = {"auto", "ccma", "api-key"}


def claude_auth_environment() -> dict[str, str]:
    """Return the Claude child environment for the requested auth route."""

    environment = os.environ.copy()
    mode = environment.pop(CLAUDE_AUTH_ENV, "auto").strip().lower()
    if mode not in CLAUDE_AUTH_MODES:
        choices = ", ".join(sorted(CLAUDE_AUTH_MODES))
        raise ValueError(f"{CLAUDE_AUTH_ENV} must be one of: {choices}")
    if mode == "ccma":
        environment.pop("ANTHROPIC_API_KEY", None)
    elif mode == "api-key" and not environment.get("ANTHROPIC_API_KEY"):
        raise ValueError("api-key Claude auth requires ANTHROPIC_API_KEY")
    return environment


def session_env(
    policy_model: str = POLICY_MODEL,
    compaction_mode: str = "manual",
    tool_profile: str | None = None,
    policy_path: str | None = None,
    padding_turn: int | None = None,
    audit_log: Path | None = None,
) -> dict[str, str]:
    """Child environment for one policy session.

    Manual runs disable automatic compaction. Automatic runs explicitly remove
    every operator override so Claude Code controls its native boundary timing.

    The rest are quiet-machine settings: no auto-update mid-run, no telemetry or
    error reporting during transcript recording, and
    no non-essential model calls (conversation titles and similar), which cost
    time and add entries the parser then has to ignore. None of them touch what
    the policy does with a turn.
    """
    environment = claude_auth_environment()
    if compaction_mode == "manual":
        environment["DISABLE_AUTO_COMPACT"] = "1"
    elif compaction_mode == "automatic":
        for name in (
            "DISABLE_AUTO_COMPACT",
            "CLAUDE_CODE_AUTO_COMPACT_WINDOW",
            "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE",
        ):
            environment.pop(name, None)
    else:
        raise ValueError(f"unknown compaction mode {compaction_mode!r}")
    environment["DISABLE_AUTOUPDATER"] = "1"
    environment["DISABLE_TELEMETRY"] = "1"
    environment["DISABLE_ERROR_REPORTING"] = "1"
    environment["DISABLE_NON_ESSENTIAL_MODEL_CALLS"] = "1"
    # Keep the requested model throughout the recorded session. Claude Code can
    # otherwise fall back to another model under load, which would silently mix
    # policy models in one archived arm.
    environment["CLAUDE_CODE_NO_MODEL_FALLBACK"] = "1"
    # Claude Code can otherwise route sub-agents through its configured
    # small/fast model. A generated arm has one policy model by design, so pin
    # delegated work to the same exact gateway/model identifier.
    environment["CLAUDE_CODE_SUBAGENT_MODEL"] = policy_model
    if tool_profile is not None:
        if policy_path is None:
            raise ValueError("an isolated tool profile requires a policy path")
        environment["LCM_TOOL_PROFILE"] = tool_profile
        environment["LCM_PADDING_POLICY"] = policy_path
        if padding_turn is not None:
            environment["LCM_PADDING_TURN"] = str(padding_turn)
        else:
            environment.pop("LCM_PADDING_TURN", None)
        if audit_log is not None:
            environment["LCM_POLICY_AUDIT_LOG"] = str(audit_log)
    return environment


def _drain_process_pipes(process):
    """Drain both bounded OS pipes before sending turns, retaining stderr diagnostics."""
    lines: queue.Queue[str | None] = queue.Queue()
    stderr_tail: deque[str] = deque(maxlen=50)

    def drain_stdout() -> None:
        for line in process.stdout:
            lines.put(line)
        lines.put(None)

    def drain_stderr() -> None:
        for line in process.stderr:
            stderr_tail.append(line)

    threading.Thread(target=drain_stdout, daemon=True).start()
    threading.Thread(target=drain_stderr, daemon=True).start()

    return lines, stderr_tail


def drive(
    argv: list[str],
    workspace: Path,
    plan: list[tuple[str, str]],
    on_turn_complete: "Callable[[int, str], None] | None" = None,
    policy_model: str = POLICY_MODEL,
    compaction_mode: str = "manual",
    tool_profile: str | None = None,
    policy_path: str | None = None,
    padding_turn: int | None = None,
    on_session_initialized: "Callable[[str], None] | None" = None,
) -> dict:
    """Run the whole session in one process and return observed provenance.

    ``on_turn_complete(completed, session_id)`` fires after each turn's ``result``
    so the caller can checkpoint the live transcript. A 90-minute run that dies
    on turn 9 should leave the first eight turns already on disk, not nothing.

    A thread drains stdout into a queue because the OS pipe buffers are finite:
    writing to stdin while the child is blocked writing to a full stdout pipe
    deadlocks both sides. stderr is drained for the same reason, keeping a short
    tail for diagnostics.

    A ``result`` event ends a turn, so the loop is: on ``result`` send the next
    message; when the plan is exhausted close stdin to say "no more input".
    """
    process = subprocess.Popen(
        argv, cwd=workspace, env=session_env(
            policy_model,
            compaction_mode,
            tool_profile,
            policy_path,
            padding_turn,
            workspace.parent / "padding-tool-audit.jsonl" if tool_profile else None,
        ),
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, bufsize=1, encoding="utf-8", errors="replace",
    )
    lines, stderr_tail = _drain_process_pipes(process)

    observed: dict = {"session_id": None, "policy_model": None,
                      "compaction_model": None}
    index = 0
    _send(process, plan[index])

    while True:
        try:
            line = lines.get(timeout=IDLE_TIMEOUT_SECONDS)
        except queue.Empty as error:
            process.kill()
            raise SessionError(
                f"no output for {IDLE_TIMEOUT_SECONDS:.0f}s while {plan[index][0]} "
                "was in flight"
            ) from error
        if line is None:
            break
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue  # non-JSON chatter on stdout is not part of the protocol

        kind = entry.get("type")
        if kind == "system" and entry.get("subtype") == "init":
            observed["session_id"] = entry.get("session_id")
            observed["policy_model"] = entry.get("model")
            log(f"  session {observed['session_id']} model {observed['policy_model']}")
            if (
                on_session_initialized is not None
                and observed["session_id"] is not None
            ):
                on_session_initialized(observed["session_id"])
        elif kind == "assistant" and plan[index][0].startswith("compaction"):
            # The compaction turn is answered by the same session, so its model
            # is observed rather than configured.
            observed["compaction_model"] = (
                (entry.get("message") or {}).get("model") or observed["compaction_model"]
            )
        elif kind == "result":
            if entry.get("is_error"):
                # A turn that errored (most often "Prompt is too long") did not
                # produce the work the plan asked for, so the transcript from here
                # on is not the one the spec describes. Fail rather than send the
                # next turn into a session in an unknown state and archive the
                # result as a complete run. Checkpoints from the finished turns are
                # already on disk, so a transient error can still be resumed.
                raise SessionError(
                    f"{plan[index][0]} errored, so the transcript is incomplete: "
                    f"{str(entry.get('result'))[:300]}"
                )
            index += 1
            if on_turn_complete is not None and observed["session_id"] is not None:
                on_turn_complete(index, observed["session_id"])
            if index < len(plan):
                _send(process, plan[index])
            else:
                # Plan exhausted: say "no more input" and stop reading. The child
                # can emit a trailing assistant/system event after this final
                # result but before it closes stdout; staying in the loop would
                # index plan[index] out of range. The daemon drain thread keeps
                # emptying the pipe, so the child still exits cleanly for wait().
                _close_stdin(process)
                break

    exit_code = process.wait()
    if index < len(plan):
        raise SessionError(
            f"claude exited (code {exit_code}) with {len(plan) - index} messages "
            f"unsent, next was {plan[index][0]}; stderr: "
            f"{''.join(list(stderr_tail)[-5:]).strip()}"
        )
    if observed["session_id"] is None:
        raise SessionError("never saw an init event, so the session JSONL is unknown")
    return observed


def _drive_isolated_segment(
    segment,
    workspace,
    remaining,
    resume_id,
    base,
    on_turn_complete,
    on_session_initialized,
    policy_model,
    compaction_mode,
    policy_effort,
):
    """Translate local callbacks while the segment's workspace view is active."""

    def relay(local_completed: int, live_session_id: str, base: int = base) -> None:
        on_turn_complete(base + local_completed, live_session_id)

    def relay_initialized(
        live_session_id: str,
        base: int = base,
    ) -> None:
        if on_session_initialized is not None:
            on_session_initialized(base, live_session_id)

    try:
        with scoped_workspace_view(
            workspace,
            segment.tool_profile,
            policy_path=segment.policy_path,
            padding_turn=segment.padding_turn,
        ):
            return drive(
                build_argv(
                    resume_id,
                    policy_model,
                    policy_effort,
                    segment.tool_profile,
                ),
                workspace,
                remaining,
                relay,
                policy_model,
                compaction_mode,
                segment.tool_profile,
                segment.policy_path,
                segment.padding_turn,
                relay_initialized,
            )
    except WorkspaceIsolationError as error:
        raise SessionError(str(error)) from error


def drive_segments(
    plan_segments: "list[delivery.Segment]",
    already_completed: int,
    workspace: Path,
    resume_session_id: str | None,
    on_turn_complete: "Callable[[int, str], None]",
    policy_model: str = POLICY_MODEL,
    compaction_mode: str = "manual",
    policy_effort: str | None = POLICY_EFFORT,
    on_session_initialized: "Callable[[int, str], None] | None" = None,
) -> dict:
    """Run every delivery segment in order and return merged provenance.

    One child process per segment. The first starts a session; each later one
    re-attaches it with ``--resume`` and its own cumulative appended prompt, which
    is how staged guidance reaches the policy only from its stage onward.

    ``already_completed`` is the plan-global count from a crash resume, so a
    partially finished run skips whole segments it got through and re-enters the
    one it died in at the right message. ``on_turn_complete`` receives plan-global
    counts, not per-process ones.

    An unstaged spec produces exactly one segment, so this is the original
    single-process path with one extra loop iteration around it.
    """
    observed: dict = {
        "session_id": resume_session_id,
        "policy_model": None,
        "compaction_model": None,
    }
    offset = 0
    for segment in plan_segments:
        remaining = segment.messages[max(0, already_completed - offset) :]
        if not remaining:
            offset += len(segment.messages)
            continue
        # Resume when the segment says so, or when a crash resume dropped us into
        # a first segment that has already been partly sent.
        session_id = observed["session_id"]
        resume_id = (
            session_id if (segment.resumes or already_completed > offset) else None
        )
        if resume_id is None and segment.resumes:
            raise SessionError(
                f"{segment.label} must resume but no session id is known yet"
            )
        if len(plan_segments) > 1:
            log(
                f"--- {segment.label}: {len(remaining)} message(s)"
                f"{' (resuming)' if resume_id else ''}"
            )
        base = offset + max(0, already_completed - offset)

        result = _drive_isolated_segment(
            segment,
            workspace,
            remaining,
            resume_id,
            base,
            on_turn_complete,
            on_session_initialized,
            policy_model,
            compaction_mode,
            policy_effort,
        )
        # A resumed child re-reports the same session id; keep the first one we
        # learned so the archive and the manifest agree across segments.
        observed["session_id"] = observed["session_id"] or result["session_id"]
        observed["policy_model"] = observed["policy_model"] or result["policy_model"]
        observed["compaction_model"] = (
            result["compaction_model"] or observed["compaction_model"]
        )
        offset += len(segment.messages)
    if observed["session_id"] is None:
        raise SessionError("no segment reported a session id")
    return observed


def _send(process: subprocess.Popen, message: tuple[str, str]) -> None:
    """Write one user turn to the child's stdin as a stream-json line."""
    label, text = message
    log(f">>> {label}")
    payload = {"type": "user", "message": {"role": "user", "content": text}}
    try:
        process.stdin.write(json.dumps(payload) + "\n")
        process.stdin.flush()
    except (BrokenPipeError, ValueError) as error:
        raise SessionError(f"could not send {label}: child stdin is gone") from error


def _close_stdin(process: subprocess.Popen) -> None:
    try:
        process.stdin.close()
    except (BrokenPipeError, ValueError):
        pass
