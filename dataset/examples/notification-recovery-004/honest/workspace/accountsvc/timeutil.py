"""Shared clock and expiry calculation.

Every "current time" read in the service -- expiry checks, timestamp
columns, rate-limit windows -- goes through :func:`now` so that a single
``--clock-now`` server flag can freeze the whole process's notion of time
for deterministic testing (e.g. exercising expiry across a process restart
without a real sleep), without threading a clock parameter through every
call site.
"""
from __future__ import annotations

import calendar
import time
from typing import Optional

_frozen_now: Optional[float] = None


def set_frozen_now(epoch_seconds: Optional[float]) -> None:
    """Freeze :func:`now` at ``epoch_seconds``, or unfreeze it with ``None``."""

    global _frozen_now
    _frozen_now = epoch_seconds


def now() -> float:
    return _frozen_now if _frozen_now is not None else time.time()


def is_expired(expires_at: str) -> bool:
    expiry_struct = time.strptime(expires_at, "%Y-%m-%dT%H:%M:%SZ")
    return now() > calendar.timegm(expiry_struct)
