"""Canonical timestamp handling shared by every log-store reader.

Both store formats can spell the same instant differently (a trailing
``Z`` vs an explicit ``+00:00`` offset, an elided vs an explicit zero
fractional part). Comparing normalized text, not raw strings, is what lets
the archive reader recognize repeated exports of one underlying event.
"""

from __future__ import annotations

from datetime import datetime, timezone


def canonical_timestamp(raw: str) -> str:
    """Return one canonical spelling for an ISO-8601 UTC instant."""

    text = raw.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    moment = datetime.fromisoformat(text)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    moment = moment.astimezone(timezone.utc)
    return moment.isoformat().replace("+00:00", "Z")


def now_utc() -> str:
    """The current instant, in the same canonical spelling as stored entries."""

    return canonical_timestamp(datetime.now(timezone.utc).isoformat())
