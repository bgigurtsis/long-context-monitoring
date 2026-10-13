"""Storage- and transport-independent audit service.

``AuditService`` depends only on the ``AppendOnlyLog`` protocol below. It has
no knowledge of JSON files, HTTP, or the CLI -- ``auditlog.cli`` and
``auditlog.httpd`` are both callers of this service, not part of it. Any
object that implements ``read_all``/``append`` (and optionally
``rebuild_index``) can back it, in tests or otherwise.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from .models import AuditEvent, ensure_identity_fields
from .proxy_rollout import (
    PROXY_ROLLOUT_ACTOR,
    ProxyRolloutImportError,
    ProxyRolloutRecord,
    translate_proxy_rollout_record,
)


class AppendOnlyLog(Protocol):
    """The minimal storage contract AuditService relies on."""

    def read_all(self) -> list[AuditEvent]:
        ...

    def append(
        self,
        actor: str,
        action: str,
        outcome: str,
        recorded_at: str,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        ...


@dataclass(frozen=True)
class RepairReport:
    """Result of a repair pass: what was checked and what was rebuilt."""

    entries_checked: int
    index_rebuilt: bool


@dataclass(frozen=True)
class ProxyRolloutReconciliationReport:
    """Result of reconciling a batch of proxy rollout records into the trail.

    ``imported`` is how many of ``source_records`` were newly appended by
    this call; ``already_present`` is how many were recognized -- by their
    deterministic identity, not a separate cursor -- as having been imported
    by an earlier call. A repeated or resumed call over the same records
    always yields ``imported + already_present == source_records``.
    """

    source_records: int
    imported: int
    already_present: int
    entries_checked: int


class AuditService:
    """Record, query, and repair operations over an append-only audit trail."""

    def __init__(self, store: AppendOnlyLog) -> None:
        self._store = store

    def record(
        self,
        actor: str,
        action: str,
        outcome: str,
        *,
        metadata: dict[str, Any] | None = None,
        recorded_at: str | None = None,
    ) -> AuditEvent:
        """Append one new entry and return it as actually stored.

        ``actor`` may not be ``proxy_rollout.PROXY_ROLLOUT_ACTOR``: that
        identity is reserved for entries imported by
        ``reconcile_proxy_rollout``, so a native call can never collide with,
        or be mistaken for, an imported one.
        """

        if actor == PROXY_ROLLOUT_ACTOR:
            raise ValueError(f"actor {actor!r} is reserved for proxy rollout imports")
        if recorded_at is None:
            recorded_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        ensure_identity_fields(actor, action, outcome, recorded_at)
        return self._store.append(actor, action, outcome, recorded_at, metadata)

    def query(self, *, actor: str | None = None, action: str | None = None) -> list[AuditEvent]:
        """Return matching entries in sequence order."""

        events = self._store.read_all()
        if actor is not None:
            events = [event for event in events if event.actor == actor]
        if action is not None:
            events = [event for event in events if event.action == action]
        return events

    def repair(self) -> RepairReport:
        """Re-verify the trail and rebuild any derived index the store keeps.

        ``read_all`` itself performs the strict verification (gapless
        sequence, every event_id matching its own content); repair's job is
        to run that check on demand and rebuild whatever derived index the
        store maintains from the now-verified trail.
        """

        events = self._store.read_all()
        rebuild_index = getattr(self._store, "rebuild_index", None)
        index_rebuilt = False
        if callable(rebuild_index):
            rebuild_index(events)
            index_rebuilt = True
        return RepairReport(entries_checked=len(events), index_rebuilt=index_rebuilt)

    def reconcile_proxy_rollout(
        self, records: list[ProxyRolloutRecord]
    ) -> ProxyRolloutReconciliationReport:
        """Restart-safely import proxy rollout records into the trail.

        Each record is looked up by the deterministic identity
        ``translate_proxy_rollout_record`` derives from it and appended only
        if that identity is not already present -- so calling this again
        after a crash mid-import, or concurrently from another thread or
        process, resumes cleanly: already-imported records are recognized
        and skipped, nothing already stored is ever deleted or reordered, and
        no record is imported twice.

        Before appending anything, this (a) verifies the existing trail
        (``read_all``'s own strict check) and (b) checks that no record in
        this batch claims a ``sequence`` the trail has already imported under
        a *different* ``event`` name -- the proxy contradicting its own prior
        report is treated as a source integrity failure, not silently
        recorded as a second, conflicting entry.
        """

        existing = self._store.read_all()
        previously_imported_actions: dict[int, str] = {
            event.metadata["proxy_source_sequence"]: event.action
            for event in existing
            if event.actor == PROXY_ROLLOUT_ACTOR and "proxy_source_sequence" in event.metadata
        }

        append_if_absent = getattr(self._store, "append_if_absent", None)
        if not callable(append_if_absent):
            raise TypeError("store does not support restart-safe proxy rollout reconciliation")

        ordered_records = sorted(records, key=lambda record: record.sequence)
        for record in ordered_records:
            prior_action = previously_imported_actions.get(record.sequence)
            if prior_action is not None and prior_action != record.event:
                raise ProxyRolloutImportError(
                    f"proxy sequence {record.sequence} was previously imported as "
                    f"{prior_action!r}, now reported as {record.event!r}"
                )

        imported = 0
        already_present = 0
        for record in ordered_records:
            _, created = append_if_absent(*translate_proxy_rollout_record(record))
            if created:
                imported += 1
            else:
                already_present += 1

        entries_checked = len(self._store.read_all())
        return ProxyRolloutReconciliationReport(
            source_records=len(ordered_records),
            imported=imported,
            already_present=already_present,
            entries_checked=entries_checked,
        )
