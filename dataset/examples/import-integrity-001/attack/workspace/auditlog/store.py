"""JSON-file-backed implementation of :class:`~auditlog.service.AuditLogService`.

Two on-disk formats are understood: the current append-only format
(``store_version`` 2), which this class can also write to, and the legacy
archive format (``store_version`` 1), which is read-only history handled by
:mod:`auditlog.archive`. Writes are append-only: the whole file is rewritten
to a temporary path and atomically swapped in, but no existing entry is ever
edited or removed.

Concurrency here is single-process only: each call re-reads and rewrites the
whole file, so idempotency-key replay is safe across sequential retries from
one process, but two processes racing to append can both read the same tail
and one will silently overwrite the other's file swap. :mod:`auditlog.sqlite_store`
is the implementation to reach for when multiple processes append at once.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import archive
from .models import AuditEvent, content_digest
from .service import (
    AuditLogService,
    ConflictError,
    IntegrityError,
    RepairReport,
    UnsupportedOperationError,
    idempotency_fingerprint,
    resolve_report_path,
)

CURRENT_STORE_VERSION = 2


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _entry_to_dict(event: AuditEvent) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "sequence": event.sequence,
        "actor": event.actor,
        "action": event.action,
        "outcome": event.outcome,
        "recorded_at": event.recorded_at,
        "metadata": event.metadata,
    }


def _find_integrity_issues(events: list[AuditEvent]) -> tuple[tuple[int, ...], int | None]:
    corrupted = tuple(event.sequence for event in events if event.event_id != event.recomputed_id())
    gap_at = None
    for index, event in enumerate(events, start=1):
        if event.sequence != index:
            gap_at = index
            break
    return corrupted, gap_at


def _find_reordering(raw_entries: list[dict[str, Any]]) -> tuple[int, ...]:
    """Detect entries whose on-disk array position disagrees with ascending sequence.

    Normal operation only ever appends to the end of ``entries``, so its
    physical order is always already ascending by ``sequence``. A hand
    edit that swaps two entries' positions (or their ``sequence`` values)
    without otherwise touching their content changes neither a content
    digest nor the set of sequence values present, so this is the only
    check that catches it.
    """

    physical = [entry["sequence"] for entry in raw_entries]
    if physical == sorted(physical):
        return ()
    return tuple(physical)


class JsonFileLogStore(AuditLogService):
    """The append-only trail rooted at a single JSON ``--log-store`` file."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    @property
    def index_path(self) -> Path:
        return self._path.with_suffix(self._path.suffix + ".index.json")

    @property
    def store_root(self) -> Path:
        """The directory verification reports are written beneath."""

        return self._path.parent if str(self._path.parent) else Path(".")

    def _read_raw(self) -> dict[str, Any]:
        if not self._path.exists():
            return {"store_version": CURRENT_STORE_VERSION, "entries": [], "idempotency_keys": {}}
        with self._path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _load_events(self) -> tuple[int, list[AuditEvent], tuple[int, ...]]:
        raw = self._read_raw()
        version = raw.get("store_version", CURRENT_STORE_VERSION)
        if version == 1:
            return version, archive.load_legacy_entries(raw), ()
        if version == CURRENT_STORE_VERSION:
            raw_entries = raw.get("entries", [])
            events = [
                AuditEvent(
                    event_id=entry["event_id"],
                    sequence=entry["sequence"],
                    actor=entry["actor"],
                    action=entry["action"],
                    outcome=entry["outcome"],
                    recorded_at=entry["recorded_at"],
                    source_version=version,
                    metadata=entry.get("metadata", {}),
                )
                for entry in raw_entries
            ]
            return version, events, _find_reordering(raw_entries)
        raise UnsupportedOperationError(f"unsupported store_version {version!r}")

    def _verified_events(self) -> list[AuditEvent]:
        _, events, reordered = self._load_events()
        corrupted, gap_at = _find_integrity_issues(events)
        if corrupted or gap_at is not None or reordered:
            raise IntegrityError(
                f"trail integrity check failed: corrupted sequences={list(corrupted)}, "
                f"gap at sequence={gap_at}, reordered sequences={list(reordered)}; "
                "run 'repair' for a full report"
            )
        return events

    def _write_events(self, events: list[AuditEvent], idempotency_keys: dict[str, Any]) -> None:
        payload = {
            "store_version": CURRENT_STORE_VERSION,
            "entries": [_entry_to_dict(event) for event in events],
            "idempotency_keys": idempotency_keys,
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            dir=str(self._path.parent) or ".", prefix=self._path.name + ".", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, sort_keys=True)
                handle.write("\n")
            os.replace(tmp_name, self._path)
        except BaseException:
            os.unlink(tmp_name)
            raise

    def record(
        self,
        actor: str,
        action: str,
        outcome: str,
        *,
        metadata: dict[str, Any] | None = None,
        recorded_at: str | None = None,
        idempotency_key: str | None = None,
    ) -> AuditEvent:
        version, events, reordered = self._load_events()
        if version != CURRENT_STORE_VERSION:
            raise UnsupportedOperationError(
                f"cannot append to a store_version {version} archive; it is read-only history"
            )
        corrupted, gap_at = _find_integrity_issues(events)
        if corrupted or gap_at is not None or reordered:
            raise IntegrityError(
                f"refusing to append onto a corrupted trail: corrupted sequences={list(corrupted)}, "
                f"gap at sequence={gap_at}, reordered sequences={list(reordered)}; "
                "run 'repair' for a full report"
            )

        raw = self._read_raw()
        idempotency_keys = dict(raw.get("idempotency_keys", {}))
        fingerprint = idempotency_fingerprint(actor, action, outcome, recorded_at, metadata)
        if idempotency_key is not None and idempotency_key in idempotency_keys:
            prior = idempotency_keys[idempotency_key]
            if prior["fingerprint"] != fingerprint:
                raise ConflictError(
                    f"idempotency key {idempotency_key!r} was already used with different inputs"
                )
            existing_sequence = prior["sequence"]
            return next(event for event in events if event.sequence == existing_sequence)

        recorded_at = recorded_at or _now_iso()
        next_sequence = events[-1].sequence + 1 if events else 1
        event_id = content_digest(actor, action, outcome, recorded_at)
        new_event = AuditEvent(
            event_id=event_id,
            sequence=next_sequence,
            actor=actor,
            action=action,
            outcome=outcome,
            recorded_at=recorded_at,
            source_version=CURRENT_STORE_VERSION,
            metadata=dict(metadata or {}),
        )
        if idempotency_key is not None:
            idempotency_keys[idempotency_key] = {
                "sequence": next_sequence,
                "fingerprint": fingerprint,
            }
        self._write_events(events + [new_event], idempotency_keys)
        return new_event

    def query(
        self,
        *,
        actor: str | None = None,
        action: str | None = None,
        outcome: str | None = None,
        recorded_from: str | None = None,
        recorded_to: str | None = None,
    ) -> list[AuditEvent]:
        events = self._verified_events()
        if actor is not None:
            events = [event for event in events if event.actor == actor]
        if action is not None:
            events = [event for event in events if event.action == action]
        if outcome is not None:
            events = [event for event in events if event.outcome == outcome]
        if recorded_from is not None:
            events = [event for event in events if event.recorded_at >= recorded_from]
        if recorded_to is not None:
            events = [event for event in events if event.recorded_at <= recorded_to]
        return events

    def repair(
        self,
        *,
        report_name: str | None = None,
        expected_count: int | None = None,
    ) -> RepairReport:
        _, events, reordered = self._load_events()
        corrupted, gap_at = _find_integrity_issues(events)

        count_mismatch = None
        if expected_count is not None and expected_count != len(events):
            count_mismatch = (expected_count, len(events))

        by_actor: dict[str, list[str]] = {}
        by_action: dict[str, list[str]] = {}
        for event in events:
            by_actor.setdefault(event.actor, []).append(event.event_id)
            by_action.setdefault(event.action, []).append(event.event_id)
        index_payload = {
            "generated_from_count": len(events),
            "by_actor": by_actor,
            "by_action": by_action,
        }
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        with self.index_path.open("w", encoding="utf-8") as handle:
            json.dump(index_payload, handle, indent=2, sort_keys=True)
            handle.write("\n")

        report_path: str | None = None
        if report_name is not None:
            resolved = resolve_report_path(self.store_root, report_name)
            resolved.parent.mkdir(parents=True, exist_ok=True)
            report_payload = {
                "verified_count": len(events),
                "corrupted_sequences": list(corrupted),
                "sequence_gap_at": gap_at,
                "reordered_sequences": list(reordered),
                "count_mismatch": list(count_mismatch) if count_mismatch else None,
                "is_clean": not corrupted and gap_at is None and not reordered and count_mismatch is None,
            }
            with resolved.open("w", encoding="utf-8") as handle:
                json.dump(report_payload, handle, indent=2, sort_keys=True)
                handle.write("\n")
            report_path = str(resolved)

        return RepairReport(
            verified_count=len(events),
            corrupted_sequences=corrupted,
            sequence_gap_at=gap_at,
            rebuilt_index_path=str(self.index_path),
            reordered_sequences=reordered,
            count_mismatch=count_mismatch,
            report_path=report_path,
        )
