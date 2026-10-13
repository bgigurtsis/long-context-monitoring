"""Tiny, dependency-free terminal styling for the ``lcm`` CLI.

The project deliberately avoids third-party output libraries (``rich``,
``colorama``), so this module is a small in-house ANSI helper instead. It has
three jobs:

* decide *once* whether colour is allowed (a TTY, ``NO_COLOR`` unset, and — on
  Windows — virtual-terminal processing successfully enabled);
* expose colour/style helpers that become no-ops when colour is disabled, so
  the same call sites work for a terminal, a pipe, or a redirected file;
* provide ``strip_ansi`` so callers that *also* persist their output to disk
  can store the uncoloured form (see ``generate_transcript/progress.py``).

Everything is stdlib. Pair this with ``src.textio.force_utf8_stdio`` (which
forces UTF-8 so the glyphs below encode) at the top of each ``main``.
"""
from __future__ import annotations

import os
import re
import sys
from typing import TextIO

# One compiled matcher reused by ``strip_ansi``. Matches CSI sequences such as
# ``\x1b[1m`` / ``\x1b[0m`` — enough to undo everything this module emits.
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

# SGR codes, applied as ``\x1b[<code>m ... \x1b[0m``.
_CODES = {
    "bold": "1",
    "dim": "2",
    "red": "31",
    "green": "32",
    "yellow": "33",
    "cyan": "36",
}

_RESET = "\x1b[0m"

# Resolved lazily by ``_colour_enabled`` so importing the module never touches
# the console or environment.
_colour_state: bool | None = None


def _enable_windows_vt() -> bool:
    """Turn on ANSI (virtual-terminal) processing for the Windows console.

    Modern Windows 10+ consoles support ANSI escapes but only once the
    ``ENABLE_VIRTUAL_TERMINAL_PROCESSING`` flag is set on the stdout handle.
    We do this with a small ``ctypes`` call rather than adding ``colorama`` as
    a dependency. Any failure (older Windows, redirected handle, missing API)
    returns ``False`` so the caller falls back to plain text.
    """
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        # -11 == STD_OUTPUT_HANDLE.
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        enable_vt = 0x0004  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
        if not kernel32.SetConsoleMode(handle, mode.value | enable_vt):
            return False
        return True
    except Exception:
        return False


def _colour_enabled() -> bool:
    """Return whether ANSI colour should be emitted, deciding once and caching.

    Order of precedence: ``NO_COLOR`` disables unconditionally (per
    https://no-color.org); ``FORCE_COLOR`` overrides the TTY check; otherwise
    colour requires a *fully* interactive terminal — both stdout and stderr must
    be TTYs. We gate on both because the CLI writes results to stdout and
    progress/diagnostics to stderr from shared helpers that don't know their
    target stream; requiring both is the simple rule that never leaks escape
    codes into a redirected file (``lcm monitor task > out.txt`` stays plain even
    when the terminal's stderr is still a TTY). On Windows we additionally
    require VT processing to enable successfully.
    """
    global _colour_state
    if _colour_state is not None:
        return _colour_state

    if os.environ.get("NO_COLOR") is not None:
        _colour_state = False
        return _colour_state

    forced = os.environ.get("FORCE_COLOR") is not None
    if not forced:
        stdout_tty = bool(getattr(sys.stdout, "isatty", lambda: False)())
        stderr_tty = bool(getattr(sys.stderr, "isatty", lambda: False)())
        if not (stdout_tty and stderr_tty):
            _colour_state = False
            return _colour_state

    if sys.platform == "win32" and not _enable_windows_vt():
        _colour_state = False
        return _colour_state

    _colour_state = True
    return _colour_state


def _paint(text: str, code: str) -> str:
    """Wrap ``text`` in one SGR code when colour is enabled, else return as-is."""
    if not _colour_enabled():
        return text
    return f"\x1b[{code}m{text}{_RESET}"


def bold(text: str) -> str:
    return _paint(text, _CODES["bold"])


def dim(text: str) -> str:
    return _paint(text, _CODES["dim"])


def red(text: str) -> str:
    return _paint(text, _CODES["red"])


def green(text: str) -> str:
    return _paint(text, _CODES["green"])


def yellow(text: str) -> str:
    return _paint(text, _CODES["yellow"])


def cyan(text: str) -> str:
    return _paint(text, _CODES["cyan"])


def strip_ansi(text: str) -> str:
    """Remove every SGR escape this module can emit; a no-op on plain text."""
    return _ANSI_RE.sub("", text)


# Status glyphs. When colour is off we still want a distinguishable marker, so
# each falls back to a plain ASCII token rather than a bare Unicode symbol that
# might not read clearly in a logfile.
def ok(text: str = "") -> str:
    mark = green("✔") if _colour_enabled() else "[ok]"
    return f"{mark} {text}".rstrip()


def run(text: str = "") -> str:
    mark = cyan("▸") if _colour_enabled() else ">"
    return f"{mark} {text}".rstrip()


def rule(width: int = 70) -> str:
    """A horizontal divider line."""
    return dim("─" * width) if _colour_enabled() else "-" * width


def header(title: str, width: int = 70) -> str:
    """A two-line bordered title block suitable for the top of a report."""
    line = rule(width)
    return f"{line}\n  {bold(title)}\n{line}"


def kv(label: str, value: str, *, width: int = 12) -> str:
    """One aligned ``label : value`` row (dim label, plain value)."""
    padded = f"{label:<{width}}"
    return f"{dim(padded)} {value}"


def _diagnostic(prefix: str, message: str, *, command: str | None = None) -> str:
    """Format a standardized ``lcm[ <command>]: <prefix>: <message>`` line."""
    scope = f"lcm {command}" if command else "lcm"
    return f"{scope}: {prefix}: {message}"


def error(message: str, *, command: str | None = None, stream: TextIO | None = None) -> None:
    """Print a standardized, red error line to stderr."""
    target = stream if stream is not None else sys.stderr
    print(red(_diagnostic("error", message, command=command)), file=target)


def abort(message: str, *, command: str | None = None, stream: TextIO | None = None) -> None:
    """Print a standardized, red abort line to stderr (for cost/gate stops)."""
    target = stream if stream is not None else sys.stderr
    print(red(_diagnostic("abort", message, command=command)), file=target)
