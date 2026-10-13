"""Apply the exact Python function replacements registered in a spec."""
from __future__ import annotations

import ast
import hashlib
import textwrap
from dataclasses import dataclass
from pathlib import Path

from long_context_monitoring.generate_transcript.session import SessionError
from long_context_monitoring.generate_transcript.side_task import SpecError

FunctionNode = ast.FunctionDef | ast.AsyncFunctionDef


@dataclass(frozen=True)
class FunctionEdit:
    path: str
    function: str
    expected_signature: str
    replacement: str


@dataclass(frozen=True)
class AppliedFunctionEdit:
    path: Path
    old_string: str
    new_string: str
    file_sha256_before: str
    file_sha256_after: str
    function_sha256_before: str
    function_sha256_after: str


def confined_workspace_path(workspace: Path, raw: str) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise SpecError("edit path is empty")
    candidate = Path(raw.strip().replace("\\", "/"))
    if candidate.is_absolute() or any(part == ".." for part in candidate.parts):
        raise SpecError(f"edit path must stay inside the workspace: {raw!r}")
    root = workspace.resolve()
    resolved = (root / candidate).resolve()
    if not resolved.is_relative_to(root):
        raise SpecError(f"edit path escapes the workspace: {raw!r}")
    return resolved


def apply_function_edit(workspace: Path, edit: FunctionEdit) -> AppliedFunctionEdit:
    target = confined_workspace_path(workspace, edit.path)
    original_bytes = _read_python_file(target, edit.path)
    original = original_bytes.decode("utf-8")
    existing = _find_function(_parse_module(original, edit.path), edit.function, edit.path)
    expected = _parse_signature(edit.expected_signature, edit.path)
    replacement = _parse_replacement(edit)
    _require_signature(existing, expected, edit)
    _require_signature(replacement, expected, edit)
    old_string = _function_source(original, existing)
    new_string = _replacement_at_indent(edit.replacement, existing.col_offset)
    updated = _replace_function_source(original, existing, new_string)
    try:
        compile(updated, str(target), "exec")
    except SyntaxError as error:
        raise SessionError(
            f"replacement leaves {edit.path} invalid: {error.msg} at line {error.lineno}"
        ) from error
    target.write_text(updated, encoding="utf-8")
    matched, reason = verify_function_edit(workspace, edit)
    if not matched:
        target.write_bytes(original_bytes)
        raise SessionError(f"postcondition failed for {edit.path}:{edit.function}: {reason}")
    resulting_bytes = target.read_bytes()
    return AppliedFunctionEdit(
        path=target,
        old_string=old_string,
        new_string=new_string,
        file_sha256_before=hashlib.sha256(original_bytes).hexdigest(),
        file_sha256_after=hashlib.sha256(resulting_bytes).hexdigest(),
        function_sha256_before=hashlib.sha256(old_string.encode()).hexdigest(),
        function_sha256_after=hashlib.sha256(new_string.encode()).hexdigest(),
    )


def verify_function_edit(workspace: Path, edit: FunctionEdit) -> tuple[bool, str]:
    try:
        target = confined_workspace_path(workspace, edit.path)
        current = _find_function(
            _parse_module(_read_python_file(target, edit.path).decode(), edit.path),
            edit.function,
            edit.path,
        )
        replacement = _parse_replacement_at_indent(edit, current.col_offset)
    except (SpecError, SessionError) as error:
        return False, str(error)
    if ast.dump(current, include_attributes=False) != ast.dump(replacement, include_attributes=False):
        return False, "function body or signature changed after the edit"
    return True, "registered replacement remains present"


def _read_python_file(target: Path, display_path: str) -> bytes:
    if not target.is_file():
        raise SessionError(f"edit path {display_path!r} is not a file in the workspace")
    try:
        raw = target.read_bytes()
        raw.decode("utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise SessionError(f"could not read UTF-8 Python file {display_path}: {error}") from error
    return raw


def _parse_module(source: str, label: str) -> ast.Module:
    try:
        return ast.parse(source, filename=label)
    except SyntaxError as error:
        raise SessionError(f"{label} is not valid Python: {error.msg} at line {error.lineno}") from error


def _parse_signature(signature: str, label: str) -> FunctionNode:
    header = signature.strip()
    if not header.endswith(":"):
        raise SessionError(f"expected_signature for {label} must end with ':'")
    tree = _parse_module(f"{header}\n    pass\n", f"{label} expected_signature")
    if len(tree.body) != 1 or not isinstance(tree.body[0], (ast.FunctionDef, ast.AsyncFunctionDef)):
        raise SessionError(f"expected_signature for {label} must define one function")
    return tree.body[0]


def _parse_replacement(edit: FunctionEdit) -> FunctionNode:
    tree = _parse_module(_normalized_replacement(edit.replacement), edit.path)
    if len(tree.body) != 1 or not isinstance(tree.body[0], (ast.FunctionDef, ast.AsyncFunctionDef)):
        raise SessionError(f"replacement for {edit.path}:{edit.function} must define one function")
    node = tree.body[0]
    if node.name != edit.function.rsplit(".", 1)[-1]:
        raise SessionError(f"replacement function {node.name!r} does not match {edit.function!r}")
    return node


def _parse_replacement_at_indent(edit: FunctionEdit, spaces: int) -> FunctionNode:
    """Parse the replacement exactly as it appears at its destination indent.

    Indenting a class method also indents the contents of multiline string
    literals. Comparing the installed method with the dedented registration
    therefore produces a false mismatch even though the exact registered text
    was inserted. A synthetic block lets the parser observe the destination
    form without weakening the AST postcondition.
    """

    if spaces == 0:
        return _parse_replacement(edit)
    wrapped = "if True:\n" + _replacement_at_indent(edit.replacement, spaces)
    tree = _parse_module(wrapped, edit.path)
    block = tree.body[0]
    if not isinstance(block, ast.If) or len(block.body) != 1:
        raise SessionError(f"replacement for {edit.path}:{edit.function} must define one function")
    node = block.body[0]
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        raise SessionError(f"replacement for {edit.path}:{edit.function} must define one function")
    return node


def _find_function(tree: ast.Module, selector: str, label: str) -> FunctionNode:
    parts = selector.split(".")
    if len(parts) == 1:
        nodes, name = tree.body, parts[0]
    elif len(parts) == 2:
        classes = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == parts[0]]
        if len(classes) != 1:
            raise SessionError(f"class {parts[0]!r} is missing or ambiguous in {label}")
        nodes, name = classes[0].body, parts[1]
    else:
        raise SessionError(f"function selector {selector!r} must be a name or Class.method")
    matches = [node for node in nodes if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name]
    if len(matches) != 1:
        raise SessionError(f"function {selector!r} is missing or ambiguous in {label}")
    return matches[0]


def _signature_key(node: FunctionNode) -> tuple[str, str, str | None]:
    returns = ast.dump(node.returns, include_attributes=False) if node.returns else None
    return type(node).__name__, ast.dump(node.args, include_attributes=False), returns


def _require_signature(actual: FunctionNode, expected: FunctionNode, edit: FunctionEdit) -> None:
    if actual.name != edit.function.rsplit(".", 1)[-1] or _signature_key(actual) != _signature_key(expected):
        raise SessionError(f"signature differs for {edit.path}:{edit.function}")


def _function_source(source: str, node: FunctionNode) -> str:
    start = min([node.lineno, *(item.lineno for item in node.decorator_list)]) - 1
    if node.end_lineno is None:
        raise SessionError(f"Python did not report the end of function {node.name!r}")
    return "".join(source.splitlines(keepends=True)[start:node.end_lineno])


def _replace_function_source(source: str, node: FunctionNode, replacement: str) -> str:
    start = min([node.lineno, *(item.lineno for item in node.decorator_list)]) - 1
    if node.end_lineno is None:
        raise SessionError(f"Python did not report the end of function {node.name!r}")
    lines = source.splitlines(keepends=True)
    return "".join([*lines[:start], replacement, *lines[node.end_lineno:]])


def _normalized_replacement(source: str) -> str:
    return source.strip("\n") + "\n"


def _replacement_at_indent(source: str, spaces: int) -> str:
    return textwrap.indent(_normalized_replacement(source), " " * spaces)
