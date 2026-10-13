"""Persist a command's console output into the run tree.

``lcm generate`` and ``lcm monitor`` both print a lot that is worth keeping: the
resolved turn plan, the observed session id and model, the monitor's event
histogram and cost gate, and — most valuable of all — the error path, including
the tail of the child CLI's stderr. None of that survived the terminal scrollback.

This module tees the process's console streams into the active generation or
monitor batch's ``logs/<UTC-timestamp>_<command>_<label>.log`` so an artifact
tree records how it was produced, not just what came out.

Two ordering problems shape the design:

* **The log a failed run needs is written before the arm dir exists.** Generate's
  ``generations/<generation-id>/<arm>/`` is created by ``archive_session``
  *after* the session has already finished, so every interesting failure
  predates it. ``install()`` therefore starts capturing immediately into
  memory, and ``open_in()`` — called as soon as the command knows its run root,
  before any model call — creates the directory and flushes the buffer into it.
* **One invocation can touch several trajectories.** A monitor batch can span
  arms and specs. ``open_in()`` is additive for legacy output, while a named
  batch uses one shared sink, so no log misses the planning and cost-gate prefix.

Redaction is by registered secret rather than by pattern. ``register_secret()``
replaces sensitive monitor inputs on the way to disk. Colour is stripped for
the file and preserved for the terminal, so the same call sites serve both.
"""
from __future__ import annotations

import subprocess
import sys
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO

from long_context_monitoring.console import strip_ansi

# Subdirectory of a generation or monitor-batch root that holds invocation logs.
# It can outlive a failed arm or scoring that produced no artifact directory.
LOGS_DIRNAME = "logs"

# Placeholder written in place of a registered secret.
REDACTED = "[redacted]"


def log_file_name(now_utc: datetime, command: str, label: str | None) -> str:
    """Legible, sortable log name: UTC timestamp, pid, command, optional label."""
    stamp = now_utc.strftime("%Y-%m-%d_%H-%M-%SZ")
    parts = [stamp, f"p{os.getpid()}", command]
    if label:
        parts.append(label)
    return "_".join(parts) + ".log"


def _git_sha() -> str:
    """Return the current short git SHA, or ``"unknown"`` outside a checkout.

    Recorded in the log header so a log can be tied back to the code that wrote
    it. Failures are non-fatal: logging must never be the reason a run dies.
    """
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    if completed.returncode != 0:
        return "unknown"
    return completed.stdout.strip() or "unknown"


class _Tee:
    """Write-only stream forwarding to the real console and to a run log.

    Attribute access falls through to the wrapped stream so callers that reach
    for ``isatty()`` (colour detection) or ``fileno()`` (subprocess wiring) see
    the console's real answer rather than this wrapper's.
    """

    def __init__(self, original: TextIO, owner: "RunLog") -> None:
        self._original = original
        self._owner = owner

    def write(self, text: str) -> int:
        written = self._original.write(text)
        self._owner.record(text)
        return written

    def flush(self) -> None:
        self._original.flush()
        self._owner.flush()

    def isatty(self) -> bool:
        return bool(getattr(self._original, "isatty", lambda: False)())

    def __getattr__(self, name: str):
        return getattr(self._original, name)


class RunLog:
    """Captures this invocation's console output and fans it out to run trees.

    Lifecycle: ``install()`` → zero or more ``open_in()`` → ``close()``. An
    instance that is never given a run root is harmless — the captured text is
    simply dropped, which is what ``--dry-run`` and argument errors want.
    """

    def __init__(self, command: str, argv: list[str],
                 now_utc: datetime | None = None) -> None:
        self.command = command
        self.argv = list(argv)
        self.now_utc = now_utc or datetime.now(timezone.utc)
        self.paths: list[Path] = []
        self._sinks: list[TextIO] = []
        self._pending: list[str] = []
        self._secrets: list[str] = []
        self._saved_stdout: TextIO | None = None
        self._saved_stderr: TextIO | None = None

    # ----------------------------------------------------------------- setup #
    def install(self) -> None:
        """Start capturing ``sys.stdout``/``sys.stderr`` into memory."""
        if self._saved_stdout is not None:
            return
        self._saved_stdout = sys.stdout
        self._saved_stderr = sys.stderr
        sys.stdout = _Tee(self._saved_stdout, self)  # type: ignore[assignment]
        sys.stderr = _Tee(self._saved_stderr, self)  # type: ignore[assignment]

    def register_secret(self, secret: str | None) -> None:
        """Never write ``secret`` to disk; replace it with ``REDACTED``.

        Call before ``open_in`` where possible. Text already buffered is
        redacted too, since redaction happens at sink-write time.
        """
        if secret and secret not in self._secrets:
            self._secrets.append(secret)

    def open_in(self, run_root: str | Path, label: str | None = None) -> Path | None:
        """Add ``<run_root>/logs/<name>.log`` as a sink and flush the buffer.

        Creates the directory, so calling this before the first model call is
        what makes a log exist for a run that dies mid-session. Returns the log
        path, or ``None`` if the sink could not be opened — a filesystem problem
        here degrades to "no log", never to a failed run.
        """
        path = Path(run_root) / LOGS_DIRNAME / log_file_name(
            self.now_utc, self.command, label)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            handle = path.open("a", encoding="utf-8")
        except OSError as error:
            self._warn(f"could not open run log {path}: {error}")
            return None

        handle.write(self._header())
        self._sinks.append(handle)
        self.paths.append(path)
        for text in self._pending:
            handle.write(self._clean(text))
        handle.flush()
        return path

    # ------------------------------------------------------------- capturing #
    def record(self, text: str) -> None:
        """Take one chunk of console output; buffer it until a sink exists."""
        if not self._sinks:
            self._pending.append(text)
            return
        cleaned = self._clean(text)
        for handle in self._sinks:
            handle.write(cleaned)

    def flush(self) -> None:
        for handle in self._sinks:
            handle.flush()

    def close(self) -> None:
        """Restore the console streams and close every sink."""
        if self._saved_stdout is not None:
            sys.stdout = self._saved_stdout
            self._saved_stdout = None
        if self._saved_stderr is not None:
            sys.stderr = self._saved_stderr
            self._saved_stderr = None
        for handle in self._sinks:
            try:
                handle.write(f"\n--- ended {self._stamp()} ---\n")
                handle.close()
            except OSError:
                pass
        self._sinks.clear()
        self._pending.clear()

    # --------------------------------------------------------------- helpers #
    def _clean(self, text: str) -> str:
        """Strip colour and registered secrets from text bound for disk."""
        text = strip_ansi(text)
        for secret in self._secrets:
            text = text.replace(secret, REDACTED)
        return text

    def _header(self) -> str:
        argv = " ".join(self.argv)
        return (
            f"--- lcm {self.command} ---\n"
            f"started : {self._stamp()}\n"
            f"argv    : lcm {self.command} {argv}\n"
            f"commit  : {_git_sha()}\n"
            f"---\n"
        )

    def _stamp(self) -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def _warn(self, message: str) -> None:
        """Report a logging problem to the real stderr, bypassing the tee."""
        target = self._saved_stderr or sys.stderr
        print(f"lcm {self.command}: warning: {message}", file=target)
