"""Append-only persistence for a single log-store file.

A log-store file is JSON: ``{"store_version": N, "entries": [...]}``. Version
2 is the current, writable format, where each entry already carries its own
content-derived ``event_id`` and ``sequence``. Version 1 is the older,
read-only archive format handled by :mod:`auditlog.archive`. Recording always
appends to (or creates) a version-2 store; querying and repairing accept
either version and normalize to the same canonical
:class:`~auditlog.models.AuditEvent` shape, so callers never need to know
which format they are reading.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional

from . import archive
from .filelock import FileLock
from .models import (
    AuditEvent,
    IdempotencyConflictError,
    SequenceError,
    check_gapless_sequence,
    content_digest,
)


class ArchiveIsReadOnlyError(RuntimeError):
    """Raised when a caller tries to append to a version-1 archive store."""


@dataclass(frozen=True)
class RepairReport:
    """Result of an integrity scan. Repair only reports; it never mutates the trail."""

    log_store: str
    entry_count: int
    tampered_event_ids: tuple[str, ...] = ()
    sequence_error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return not self.tampered_event_ids and self.sequence_error is None


def _read_raw(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"store_version": 2, "entries": [], "idempotency": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_raw_atomic(path: Path, raw: dict[str, Any]) -> None:
    """Write ``raw`` so a crash mid-write can never leave a truncated file.

    The new content is written to a sibling temp file first, then moved into
    place with ``os.replace``, which is atomic on both POSIX and Windows: a
    reader always sees either the complete old file or the complete new one,
    never a partial write.
    """

    tmp_path = path.with_name(f"{path.name}.tmp-{os.getpid()}-{uuid.uuid4().hex}")
    tmp_path.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp_path, path)


def load_events(log_store: str) -> List[AuditEvent]:
    """Read every entry from ``log_store``, normalized to canonical events."""

    raw = _read_raw(Path(log_store))
    if raw.get("store_version", 2) == 1:
        return archive.to_canonical_events(raw.get("entries", []))
    return [
        AuditEvent(
            event_id=entry["event_id"],
            sequence=entry["sequence"],
            actor=entry["actor"],
            action=entry["action"],
            outcome=entry["outcome"],
            recorded_at=entry["recorded_at"],
            source_version=2,
            metadata=entry.get("metadata", {}),
        )
        for entry in raw.get("entries", [])
    ]


def append_event(
    log_store: str,
    actor: str,
    action: str,
    outcome: str,
    metadata: Optional[dict[str, Any]] = None,
    client_key: Optional[str] = None,
) -> AuditEvent:
    """Append one new entry to a version-2 store, creating it if needed.

    Never rewrites or reorders prior entries: the new entry's ``sequence`` is
    one past the current entry count, and its ``event_id`` is derived solely
    from its own recorded content.

    ``client_key`` is an optional caller-chosen idempotency token, version-
    neutral (nothing here knows or cares whether a V1 or V2 request path
    supplied it). Replaying the same ``client_key`` with the same
    actor/action/outcome returns the original canonical event without
    appending a second one. Replaying it with different actor/action/outcome
    raises :class:`~auditlog.models.IdempotencyConflictError` instead of
    silently recording a different event under the same key. The whole
    read-check-write cycle runs under a cross-process file lock, and the
    write itself is atomic, so concurrent callers (same process, other
    threads, or other processes) and a crash mid-write can never produce two
    entries for one key or a corrupt store file.
    """

    path = Path(log_store)
    with FileLock(f"{log_store}.lock"):
        raw = _read_raw(path)
        if raw.get("store_version", 2) != 2:
            raise ArchiveIsReadOnlyError(
                f"{log_store!r} is a version-1 archive; archives are read-only"
            )

        entries = raw.setdefault("entries", [])
        idempotency = raw.setdefault("idempotency", {})

        if client_key is not None and client_key in idempotency:
            existing = next(e for e in entries if e["event_id"] == idempotency[client_key])
            if (existing["actor"], existing["action"], existing["outcome"]) != (
                actor,
                action,
                outcome,
            ):
                raise IdempotencyConflictError(
                    f"client_key {client_key!r} was already used to record a different operation"
                )
            return AuditEvent(
                event_id=existing["event_id"],
                sequence=existing["sequence"],
                actor=existing["actor"],
                action=existing["action"],
                outcome=existing["outcome"],
                recorded_at=existing["recorded_at"],
                source_version=2,
                metadata=existing.get("metadata", {}),
            )

        recorded_at = datetime.now(timezone.utc).isoformat(timespec="microseconds").replace(
            "+00:00", "Z"
        )
        sequence = len(entries) + 1
        event_id = content_digest(actor, action, outcome, recorded_at)
        entries.append(
            {
                "event_id": event_id,
                "sequence": sequence,
                "actor": actor,
                "action": action,
                "outcome": outcome,
                "recorded_at": recorded_at,
                "metadata": metadata or {},
            }
        )
        if client_key is not None:
            idempotency[client_key] = event_id
        raw["store_version"] = 2
        _write_raw_atomic(path, raw)
        return AuditEvent(
            event_id=event_id,
            sequence=sequence,
            actor=actor,
            action=action,
            outcome=outcome,
            recorded_at=recorded_at,
            source_version=2,
            metadata=metadata or {},
        )


def repair(log_store: str) -> RepairReport:
    """Scan the trail for tampered content or sequence corruption.

    This rebuilds the derived integrity view from scratch on every call; it
    never edits the stored entries themselves, since a compliance trail's
    history is corrected by recording a further entry, not by editing it.
    """

    events = load_events(log_store)
    tampered = tuple(event.event_id for event in events if event.event_id != event.recomputed_id())
    sequence_error: Optional[str] = None
    try:
        check_gapless_sequence(events)
    except SequenceError as exc:
        sequence_error = str(exc)
    return RepairReport(
        log_store=log_store,
        entry_count=len(events),
        tampered_event_ids=tampered,
        sequence_error=sequence_error,
    )
