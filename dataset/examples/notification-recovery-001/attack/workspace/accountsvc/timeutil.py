"""Timestamp helpers shared across the account recovery service.

All timestamps are fixed-width ISO-8601 strings in UTC so that they remain
correctly orderable as plain strings (used for expiry comparisons without a
parse step).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def future_iso(seconds: int) -> str:
    when = datetime.now(timezone.utc) + timedelta(seconds=seconds)
    return when.isoformat(timespec="seconds")
