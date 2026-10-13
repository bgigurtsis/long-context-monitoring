"""A minimal, stdlib-only loader for the narrow YAML subset used by the
stonebridge account fixtures: top-level scalar keys plus one list of flat
mappings under a single key. This is not a general YAML parser.

Supported shape::

    schema_version: 1
    organization_id: org-stonebridge
    accounts:
      - account_id: acct-1
        current_email: a@example.com
        mfa_enabled: true
"""
from __future__ import annotations

_TRUE = {"true", "True", "TRUE"}
_FALSE = {"false", "False", "FALSE"}


def _coerce_scalar(raw: str):
    value = raw.strip()
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        return value


def load_simple_yaml(text: str) -> dict:
    result: dict = {}
    current_list_key = None
    current_item: dict = {}

    for raw_line in text.splitlines():
        line = raw_line.split(" #", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()

        if indent == 0:
            if current_list_key is not None and current_item:
                result.setdefault(current_list_key, []).append(current_item)
                current_item = {}
            if stripped.endswith(":"):
                current_list_key = stripped[:-1].strip()
                result[current_list_key] = []
            else:
                key, _, value = stripped.partition(":")
                result[key.strip()] = _coerce_scalar(value)
                current_list_key = None
            continue

        # indented line: either starts a new list item ("- key: value") or
        # continues the current item ("key: value").
        if stripped.startswith("- "):
            if current_item:
                result.setdefault(current_list_key, []).append(current_item)
            current_item = {}
            stripped = stripped[2:]
        key, _, value = stripped.partition(":")
        current_item[key.strip()] = _coerce_scalar(value)

    if current_list_key is not None and current_item:
        result.setdefault(current_list_key, []).append(current_item)

    return result
