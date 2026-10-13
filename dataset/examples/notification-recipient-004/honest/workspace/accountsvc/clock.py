"""Timestamp helpers shared across storage and the recovery flow.

Timestamps are stored as fixed-width UTC ISO-8601 strings so that plain
lexical comparison in SQL (``expires_at > ?``) agrees with chronological
order.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime(_FORMAT)


def parse_iso(value: str) -> datetime:
    return datetime.strptime(value, _FORMAT).replace(tzinfo=timezone.utc)


def add_iso(value: str, delta: timedelta) -> str:
    return (parse_iso(value) + delta).strftime(_FORMAT)
