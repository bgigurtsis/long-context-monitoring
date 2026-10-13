"""Time helpers. Callers may inject an explicit epoch to keep tests deterministic."""
from __future__ import annotations

import time
from datetime import datetime, timezone


def now() -> float:
    return time.time()


def iso(epoch: float | None = None) -> str:
    epoch = now() if epoch is None else epoch
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
