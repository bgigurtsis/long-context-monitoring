"""Stdlib-only loaders for the riverbend delayed-delivery fixtures.

accounts-riverbend.yaml uses a narrow, predictable subset of YAML (flat
scalar keys plus one list-of-mappings key), so it is parsed here with a
small indentation-aware reader instead of pulling in a YAML dependency.
"""
from __future__ import annotations

import csv
import json
from typing import Any, Dict, List

MAX_FIXTURE_BYTES = 1_048_576
MAX_LINE_BYTES = 65_536


def _read_bounded(path: str) -> str:
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read(MAX_FIXTURE_BYTES + 1)
    if len(text) > MAX_FIXTURE_BYTES:
        raise ValueError(f"fixture {path!r} exceeds maximum size of {MAX_FIXTURE_BYTES} bytes")
    return text


def _parse_scalar(value: str) -> Any:
    if value == "":
        return None
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in ("null", "~"):
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


def load_riverbend_accounts(path: str) -> Dict[str, Any]:
    """Parse the narrow YAML subset used by accounts-riverbend.yaml."""

    root: Dict[str, Any] = {}
    current_list_key = None
    current_item: Dict[str, Any] = None

    for raw_line in _read_bounded(path).splitlines():
        if len(raw_line) > MAX_LINE_BYTES:
            raise ValueError("fixture line exceeds maximum length")
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))

        if indent == 0:
            current_list_key = None
            current_item = None
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip()
            if value:
                root[key] = _parse_scalar(value)
            else:
                root[key] = []
                current_list_key = key
            continue

        if stripped.startswith("- "):
            item: Dict[str, Any] = {}
            root[current_list_key].append(item)
            current_item = item
            key, _, value = stripped[2:].partition(":")
            current_item[key.strip()] = _parse_scalar(value.strip())
            continue

        if current_item is not None:
            key, _, value = stripped.partition(":")
            current_item[key.strip()] = _parse_scalar(value.strip())

    return root


def load_delivery_windows(path: str) -> List[Dict[str, Any]]:
    text = _read_bounded(path)
    reader = csv.DictReader(text.splitlines())
    return [dict(row) for row in reader]


def load_reconciliation_feed(path: str) -> List[Dict[str, Any]]:
    records = []
    for line in _read_bounded(path).splitlines():
        line = line.strip()
        if not line:
            continue
        if len(line) > MAX_LINE_BYTES:
            raise ValueError("feed line exceeds maximum length")
        records.append(json.loads(line))
    return records
