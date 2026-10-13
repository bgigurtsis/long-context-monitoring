"""Parsing and identity mapping for proxy rollout event imports.

A fronting proxy reports its own rollout events (canary start, verification,
etc.) as newline-delimited JSON, numbered by its own ``sequence`` counter.
Those events are not audit entries recorded by a caller through
``AuditService.record`` -- they are an external source ``AuditService``
reconciles into the trail. This module owns the narrower questions of (a)
whether a batch of proxy-reported records is even fit to import, and (b) how
one such record maps onto an ``AuditEvent``'s identity and provenance.

Identity mapping is deliberately fixed and deterministic:

  * ``actor`` is always ``PROXY_ROLLOUT_ACTOR`` and ``outcome`` is always
    ``PROXY_ROLLOUT_OUTCOME`` -- a reserved pair no native
    ``AuditService.record`` call is allowed to use (see
    ``auditlog.service.AuditService.record``), so a proxy-imported entry can
    never be confused with, or collide with, a native one.
  * ``action`` is the proxy's own event name.
  * ``recorded_at`` is synthesized from the proxy's ``sequence`` number, not
    a wall-clock time. This is what makes reconciliation restart-safe: parsing
    the same source line always yields the same identity, so
    ``AuditService.reconcile_proxy_rollout`` can recognize "already imported"
    from the trail's own content and skip it, rather than trusting a
    separate, potentially stale cursor.

Everything else the proxy reported (``peer``, ``protected_routes``, and any
other field) is provenance, not identity -- it is carried in ``metadata`` and
never influences an entry's event id or whether it is retained.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PROXY_ROLLOUT_ACTOR = "proxy-rollout-import"
PROXY_ROLLOUT_OUTCOME = "imported"


class ProxyRolloutImportError(Exception):
    """A proxy rollout event source is not fit to import."""


@dataclass(frozen=True)
class ProxyRolloutRecord:
    """One proxy-reported rollout event, before translation to an AuditEvent."""

    sequence: int
    event: str
    details: dict[str, Any] = field(default_factory=dict)


def parse_proxy_rollout_events(text: str) -> list[ProxyRolloutRecord]:
    """Parse newline-delimited proxy rollout event JSON into records.

    Blank lines are skipped. Each line must carry an integer ``sequence`` and
    a non-empty ``event``; every other field becomes descriptive provenance.
    Two lines sharing a ``sequence`` make the source ambiguous -- reconciliation
    relies on ``sequence`` to know what has already been imported, so that
    case is rejected outright rather than guessed at. Records are returned in
    ascending ``sequence`` order regardless of the order lines appeared in.
    """

    records: list[ProxyRolloutRecord] = []
    seen_sequences: set[int] = set()
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ProxyRolloutImportError(f"line {line_number}: not valid JSON") from exc

        try:
            sequence = raw["sequence"]
            event = raw["event"]
        except KeyError as exc:
            raise ProxyRolloutImportError(f"line {line_number}: missing required field {exc}") from exc

        if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
            raise ProxyRolloutImportError(f"line {line_number}: sequence must be an integer >= 1")
        if not event:
            raise ProxyRolloutImportError(f"line {line_number}: event must not be empty")
        if sequence in seen_sequences:
            raise ProxyRolloutImportError(f"line {line_number}: duplicate proxy sequence {sequence}")
        seen_sequences.add(sequence)

        details = {key: value for key, value in raw.items() if key not in ("sequence", "event")}
        records.append(ProxyRolloutRecord(sequence=sequence, event=event, details=details))

    records.sort(key=lambda record: record.sequence)
    return records


def read_proxy_rollout_events(path: str | Path) -> list[ProxyRolloutRecord]:
    """Read and parse a proxy rollout event source file."""

    return parse_proxy_rollout_events(Path(path).read_text(encoding="utf-8"))


def translate_proxy_rollout_record(record: ProxyRolloutRecord) -> tuple[str, str, str, str, dict[str, Any]]:
    """Map one proxy rollout record onto (actor, action, outcome, recorded_at, metadata)."""

    actor = PROXY_ROLLOUT_ACTOR
    action = record.event
    outcome = PROXY_ROLLOUT_OUTCOME
    recorded_at = f"proxy-rollout-seq-{record.sequence:012d}"
    metadata = {"proxy_source_sequence": record.sequence, "proxy_details": dict(record.details)}
    return actor, action, outcome, recorded_at, metadata
