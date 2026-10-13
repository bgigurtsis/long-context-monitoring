"""A tiny parser for the constrained YAML subset used by redrive batch files.

Only the standard library is available, and the redrive batch documents are
simple by design: block-style scalar mappings, one level (or more) of nested
mappings, and lists of bare scalars. This module handles exactly that shape.
It does not attempt flow style (``{a: 1}``), multi-line strings, anchors, or
tags -- a real YAML document that uses those features will raise ValueError
or produce wrong results.
"""
from __future__ import annotations

from pathlib import Path


def load_path(path: str | Path) -> dict:
    return loads(Path(path).read_text(encoding="utf-8"))


def loads(text: str) -> dict:
    entries = _tokenize(text)
    if not entries:
        return {}
    value, consumed = _parse_block(entries, 0, entries[0][0])
    if consumed != len(entries):
        raise ValueError("trailing content after top-level document")
    if not isinstance(value, dict):
        raise ValueError("redrive batch documents must be a top-level mapping")
    return value


def _tokenize(text: str) -> list[tuple[int, str]]:
    entries = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        entries.append((indent, stripped))
    return entries


def _parse_block(entries: list[tuple[int, str]], idx: int, indent: int):
    if idx >= len(entries) or entries[idx][0] != indent:
        return None, idx
    if entries[idx][1].startswith("- "):
        return _parse_list(entries, idx, indent)
    return _parse_mapping(entries, idx, indent)


def _parse_list(entries, idx, indent):
    items = []
    while idx < len(entries) and entries[idx][0] == indent and entries[idx][1].startswith("- "):
        item_text = entries[idx][1][2:].strip()
        idx += 1
        if ":" in item_text:
            raise ValueError(f"list items of mappings are not supported: {item_text!r}")
        items.append(_parse_scalar(item_text))
    return items, idx


def _parse_mapping(entries, idx, indent):
    mapping: dict = {}
    while idx < len(entries) and entries[idx][0] == indent and not entries[idx][1].startswith("- "):
        content = entries[idx][1]
        if ":" not in content:
            raise ValueError(f"expected 'key: value' but found {content!r}")
        key, _, rest = content.partition(":")
        key = key.strip()
        rest = rest.strip()
        idx += 1
        if rest:
            mapping[key] = _parse_scalar(rest)
        elif idx < len(entries) and entries[idx][0] > indent:
            child_indent = entries[idx][0]
            mapping[key], idx = _parse_block(entries, idx, child_indent)
        else:
            mapping[key] = None
    return mapping, idx


def _parse_scalar(text: str):
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1]
    lowered = text.lower()
    if lowered in ("null", "~"):
        return None
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        pass
    return text
