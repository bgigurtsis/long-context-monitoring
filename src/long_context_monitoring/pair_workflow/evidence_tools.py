"""Recognize the native operations the offline constructor can reconcile.

This is deliberately a small grammar, not a shell sandbox. Unknown shell
programs and edits to an affected file require choosing another source/anchor.
"""

from __future__ import annotations

import posixpath
import shlex
from pathlib import PurePosixPath, PureWindowsPath
from typing import Collection

from .models import ManualPairError


def affected_path(raw: object, cwd: object, paths: Collection[str]) -> str | None:
    """Use the native working directory instead of matching arbitrary suffixes."""
    if not isinstance(raw, str):
        return None
    normalized = posixpath.normpath(raw.replace("\\", "/"))
    windows = bool(PureWindowsPath(normalized).drive) or (
        isinstance(cwd, str) and bool(PureWindowsPath(cwd).drive)
    )
    path_type = PureWindowsPath if windows else PurePosixPath
    observed = path_type(normalized)
    if observed.is_absolute():
        if isinstance(cwd, str):
            try:
                observed = observed.relative_to(path_type(cwd.replace("\\", "/")))
            except ValueError:
                return None
        elif any(normalized.endswith("/" + path) for path in paths):
            raise ManualPairError("absolute tool path requires native cwd for reconciliation")
        else:
            return None
    if ".." in observed.parts or observed.drive:
        raise ManualPairError("cannot establish tool path inside the native workspace")
    for path in paths:
        if observed == path_type(path):
            return path
    return None


def _shell_tokens(command: object) -> list[str]:
    # Reject expansion and composition before shlex removes quote boundaries.
    if not isinstance(command, str) or any(c in command for c in "$`;&|<>\n\r*?[]{}~"):
        raise ManualPairError("cannot validate shell expansion, composition, or redirection after insertion")
    try:
        tokens = shlex.split(command)
    except ValueError as error:
        raise ManualPairError("cannot parse shell command after insertion") from error
    if not tokens:
        raise ManualPairError("empty shell command after insertion")
    return tokens


def _test_command(tokens: list[str]) -> bool:
    """Retain ordinary test invocations, without script execution or plugin flags."""
    if tokens[0] in {"python", "python3"} and tokens[1:3] in [["-m", "pytest"], ["-m", "unittest"]]:
        arguments = tokens[3:]
    elif tokens[0] == "pytest":
        arguments = tokens[1:]
    else:
        return False
    return all(
        not argument.startswith("-") or argument in {"-v", "-vv", "-q", "-s", "-x", "--verbose", "--quiet"}
        for argument in arguments
    )


def shell_read_path(tool: dict, entry: dict, paths: Collection[str]) -> str | None:
    """Return a verified full-file read; preserve diagnostic/test output verbatim."""
    tokens = _shell_tokens(tool.get("input", {}).get("command"))
    program, arguments = tokens[0], tokens[1:]
    if _test_command(tokens):
        return None
    if program == "cat":
        operands = arguments[1:] if arguments[:1] == ["--"] else arguments
        if len(operands) == 1 and not operands[0].startswith("-"):
            return affected_path(operands[0], entry.get("cwd"), paths)
    if program in {"pwd", "true"} and not arguments:
        return None
    if program in {"wc", "file", "sha256sum", "shasum"}:
        # These programs do not return source text. Disallow command-execution flags.
        if all(not arg.startswith("-") or arg in {"-l", "-w", "-c", "-b", "-a", "--"}
               for arg in arguments):
            return None
    if program == "git" and arguments[:1] in [["show"], ["diff"], ["status"], ["log"], ["ls-files"]]:
        # No -c, --output, external-diff, textconv, aliases, or arbitrary options.
        if all(not arg.startswith("-") or arg in {"--", "--short", "--porcelain", "--oneline"}
               for arg in arguments[1:]):
            return None
    raise ManualPairError(
        "cannot validate shell command after insertion; use another source or later anchor"
    )


def tool_read_path(tool: dict, entry: dict, paths: Collection[str]) -> str | None:
    """Reject unverifiable writes and identify only reads of the active edited files."""
    name = tool.get("name")
    if name == "Bash":
        try:
            return shell_read_path(tool, entry, paths)
        except ManualPairError as error:
            raise ManualPairError(f"{error} at native row {entry.get('uuid')}") from error
    tool_input = tool.get("input")
    if not isinstance(tool_input, dict):
        raise ManualPairError("native tool has no structured input")
    if name in {"Read", "Write", "Edit"}:
        raw = tool_input.get("file_path")
        if not isinstance(raw, str) or not raw.strip():
            raise ManualPairError("native file operation has no file_path")
    path = affected_path(tool_input.get("file_path"), entry.get("cwd"), paths)
    if name in {"Write", "Edit"}:
        if path is not None:
            raise ManualPairError(
                f"native {name} changes an edited file after insertion: {path} at {entry.get('uuid')}"
            )
        return None
    if name == "Read":
        return path
    if name in {"TodoWrite", "Glob"}:
        return None
    raise ManualPairError(f"cannot validate native tool {name!r} after insertion")
