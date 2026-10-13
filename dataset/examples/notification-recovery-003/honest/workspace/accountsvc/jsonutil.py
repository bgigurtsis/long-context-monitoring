"""Deterministic JSON encoding shared by the HTTP API and the CLI.

Sorted keys and fixed separators keep wire and log output byte-stable across
runs, which matters for a service whose clients diff responses.
"""
from __future__ import annotations

import json
from typing import Any


def dumps(obj: Any, pretty: bool = False) -> str:
    if pretty:
        return json.dumps(obj, sort_keys=True, indent=2) + "\n"
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def dumpb(obj: Any) -> bytes:
    return dumps(obj).encode("utf-8")
