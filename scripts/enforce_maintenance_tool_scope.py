#!/usr/bin/env python3
"""Fail closed on Claude tool calls that cross a maintenance profile boundary."""

from __future__ import annotations

import json
import os
import shlex
import sys
from pathlib import Path


FILE_FIELDS = {
    "Read": ("file_path",),
    "Write": ("file_path",),
    "Edit": ("file_path",),
    "Glob": ("path", "pattern"),
    "Grep": ("path", "glob"),
}
SHELL_OPERATORS = {"|", "||", "&&", ";", ">", ">>", "<", "<<", "&"}


def decision(allowed: bool, reason: str) -> dict:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow" if allowed else "deny",
            "permissionDecisionReason": reason,
        }
    }


def resolved(path: str, workspace: Path) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = workspace / candidate
    return candidate.resolve(strict=False)


def inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def path_prefix(pattern: str) -> str:
    indexes = [index for marker in "*?[" if (index := pattern.find(marker)) >= 0]
    return pattern[: min(indexes)] if indexes else pattern


def matches_allowed(path: str, workspace: Path, patterns: list[str]) -> bool:
    prefix = path_prefix(path) or "."
    candidate = resolved(prefix, workspace)
    for pattern in patterns:
        allowed_prefix = path_prefix(pattern) or "."
        allowed_root = resolved(allowed_prefix, workspace)
        if inside(candidate, allowed_root):
            return True
    return False


def file_paths(tool: str, tool_input: dict) -> list[str]:
    if tool == "Glob":
        value = tool_input.get("path") or tool_input.get("pattern")
        return [value] if isinstance(value, str) and value.strip() else []
    if tool == "Grep":
        value = tool_input.get("path")
        return [value] if isinstance(value, str) and value.strip() else []
    values: list[str] = []
    for field in FILE_FIELDS.get(tool, ()):
        value = tool_input.get(field)
        if isinstance(value, str) and value.strip():
            values.append(value)
    return values


def shell_tokens(command: str) -> list[str]:
    if any(marker in command for marker in ("$(", "`", "${", "\n", "\r")):
        raise ValueError("shell substitution and multiline commands are disabled")
    lexer = shlex.shlex(command, posix=True, punctuation_chars="|&;<>")
    lexer.whitespace_split = True
    tokens = list(lexer)
    if any(token in SHELL_OPERATORS for token in tokens):
        raise ValueError("command chaining, pipelines, redirection, and background execution are disabled")
    if not tokens:
        raise ValueError("empty command")
    if "=" in tokens[0] or tokens[0] in {"env", "export", "unset", "set"}:
        raise ValueError("environment mutation is disabled")
    return tokens


def likely_path_tokens(command: str, tokens: list[str], workspace: Path) -> list[str]:
    command_name = Path(tokens[0]).name
    if command_name == "pwd":
        return []
    values: list[str] = []
    for token in tokens[1:]:
        if token.startswith("-"):
            continue
        if token in {"f", "d", "p", "true", "false"}:
            continue
        if any(character in token for character in ("/", "*", "?", "[")):
            values.append(token)
            continue
        if (workspace / token).exists():
            values.append(token)
    return values


def audit(payload: dict, allowed: bool, reason: str) -> None:
    path = os.environ.get("LCM_POLICY_AUDIT_LOG")
    if not path:
        return
    record = {
        "profile": os.environ.get("LCM_TOOL_PROFILE"),
        "turn": os.environ.get("LCM_PADDING_TURN"),
        "tool": payload.get("tool_name"),
        "allowed": allowed,
        "reason": reason,
    }
    with Path(path).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def evaluate(payload: dict, policy: dict, workspace: Path, profile: str, turn: str | None) -> tuple[bool, str]:
    workspace = workspace.resolve()
    tool = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    if not isinstance(tool, str) or not isinstance(tool_input, dict):
        return False, "Malformed tool input is outside the active maintenance policy."
    maintenance_root = resolved(policy["maintenance_root"], workspace)
    if profile == "compaction":
        return False, "Native compaction is tool-free."
    if profile == "application":
        for value in file_paths(tool, tool_input):
            candidate = resolved(path_prefix(value) or ".", workspace)
            if inside(candidate, maintenance_root):
                return False, "Application turns cannot access maintenance files."
        if tool == "Bash":
            command = str(tool_input.get("command", ""))
            if "maintenance" in command:
                return False, "Application shell commands cannot access maintenance files."
        return True, "Application tool call remains outside maintenance."
    if profile != "padding" or turn not in policy["turns"]:
        return False, "Unknown tool profile."
    if tool not in policy["allowed_tools"]:
        return False, "This maintenance turn allows only its declared local tools."
    turn_policy = policy["turns"][turn]
    writes = turn_policy["allowed_outputs"]
    if tool in FILE_FIELDS:
        values = file_paths(tool, tool_input)
        if not values:
            return False, f"{tool} did not provide a scoped path."
        if tool in {"Write", "Edit"}:
            paths_ok = all(matches_allowed(value, workspace, writes) for value in values)
        else:
            paths_ok = all(
                inside(resolved(path_prefix(value) or ".", workspace), maintenance_root)
                for value in values
            )
        if not paths_ok:
            return False, f"{tool} path is outside this maintenance turn."
        return True, f"{tool} path matches this maintenance turn."
    command = str(tool_input.get("command", ""))
    try:
        tokens = shell_tokens(command)
    except ValueError as error:
        return False, str(error)
    command_name = Path(tokens[0]).name
    if command_name not in policy["bash_commands"]:
        return False, f"{command_name} is outside the read-only command allowlist."
    values = likely_path_tokens(command, tokens, workspace)
    if command_name != "pwd" and not values:
        return False, "The read-only command must name a maintenance path."
    if not all(
        inside(resolved(path_prefix(value) or ".", workspace), maintenance_root)
        for value in values
    ):
        return False, "Shell path is outside this maintenance turn."
    return True, "Read-only maintenance command matches this turn."


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        policy_path = Path(os.environ["LCM_PADDING_POLICY"])
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        workspace = Path(str(payload.get("cwd") or os.getcwd())).resolve()
        profile = os.environ.get("LCM_TOOL_PROFILE", "")
        turn = os.environ.get("LCM_PADDING_TURN")
        allowed, reason = evaluate(payload, policy, workspace, profile, turn)
    except (KeyError, OSError, json.JSONDecodeError, TypeError, ValueError) as error:
        allowed, reason = False, f"Maintenance policy validation failed: {error}"
        payload = locals().get("payload", {})
    audit(payload, allowed, reason)
    print(json.dumps(decision(allowed, reason)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
