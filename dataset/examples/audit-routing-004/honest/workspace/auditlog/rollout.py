"""Restart-safe phase advancement and rollback, keyed by idempotency key.

`transition_phase` wraps `auditlog.planner`'s `advance`/`rollback` plus
`save_plan`'s optimistic concurrency with three extra guarantees a bare
`save_plan` call does not give a caller on its own:

* **Restart safety.** A crash at any point during a transition -- before
  the plan is saved, after it is saved but before the audit event is
  recorded, or after the event but before the operation is marked
  complete -- is recoverable. Calling `transition_phase` again with the
  same `idempotency_key` and the same arguments resumes from wherever the
  prior attempt stopped and converges on the same recorded outcome. It
  never re-applies `advance`/`rollback` a second time and never appends a
  second audit event for the same attempt.
* **Duplicate suppression.** Once an `idempotency_key` has completed, every
  later call with that key returns the original recorded outcome (with
  `replayed=True`) without touching the plan or the audit log again --
  the caller's own retries after a lost response are free.
* **Genuine conflicts still raise.** A key racing against a plan already
  moved by a *different* operation (a separate process, a separate
  key) still raises `OptimisticConflictError`, exactly as `save_plan`
  would for a bare stale write.

Every transition also records which named cohorts had a completed
transition as of that phase change (`CohortTransitionRecord`), and an
audit event via `auditlog.service.AuditLogService` whose identity
(`auditlog.models.content_digest`) and position in the trail are
preserved across every retry.

Both phases in `auditlog.planner.PHASES` are pinned to v1
(`auditlog.planner.PINNED_TO_V1`), so every cohort's assignment before and
after any transition made through this module is "v1" -- this module
never resolves a route, contacts `auditlog.httpd`, or installs a V2 path;
it only records rollout bookkeeping for a phase change that, today, never
moves live traffic.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from auditlog.models import content_digest
from auditlog.planner import OptimisticConflictError, Plan, load_plan, save_plan
from auditlog.service import AuditLogService
from auditlog.storage import EventStore

TRANSITION_KINDS: frozenset[str] = frozenset({"advance", "rollback"})


class UnknownTransitionKindError(Exception):
    """Raised when `kind` is not one of `TRANSITION_KINDS`."""


class IdempotencyKeyReuseError(Exception):
    """Raised when a completed idempotency key is replayed with different arguments."""


@dataclass(frozen=True)
class CohortTransitionRecord:
    """One cohort's assignment immediately before and after a phase change."""

    cohort: str
    from_assignment: str
    to_assignment: str


@dataclass(frozen=True)
class TransitionOutcome:
    """The recorded result of one `idempotency_key`'s phase transition."""

    idempotency_key: str
    kind: str
    from_phase: str
    to_phase: str
    plan_revision: int
    cohort_transitions: tuple[CohortTransitionRecord, ...]
    audit_event_id: str
    replayed: bool


def _load_operations(rollout_path: Path) -> dict:
    if not rollout_path.exists():
        return {}
    return json.loads(rollout_path.read_text(encoding="utf-8"))


def _write_operations(rollout_path: Path, operations: dict) -> None:
    rollout_path.write_text(json.dumps(operations, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _outcome_from_record(idempotency_key: str, record: dict) -> TransitionOutcome:
    return TransitionOutcome(
        idempotency_key=idempotency_key,
        kind=record["kind"],
        from_phase=record["from_phase"],
        to_phase=record["to_phase"],
        plan_revision=record["result_revision"],
        cohort_transitions=tuple(
            CohortTransitionRecord(**item) for item in record["cohort_transitions"]
        ),
        audit_event_id=record["audit_event_id"],
        replayed=True,
    )


def _revision_claimed_by_another_key(operations: dict, idempotency_key: str, revision: int) -> bool:
    return any(
        other_key != idempotency_key
        and other_record.get("status") == "completed"
        and other_record.get("result_revision") == revision
        for other_key, other_record in operations.items()
    )


def _cohort_transitions(before: Plan, after: Plan) -> tuple[CohortTransitionRecord, ...]:
    return tuple(
        CohortTransitionRecord(
            cohort=cohort,
            from_assignment=before.assignment_for(cohort),
            to_assignment=after.assignment_for(cohort),
        )
        for cohort in sorted(after.cohort_targets)
    )


def transition_phase(
    *,
    plan_path: Path,
    rollout_path: Path,
    log_store: EventStore,
    idempotency_key: str,
    kind: str,
    to_phase: str,
    expected_revision: int,
    actor: str,
) -> TransitionOutcome:
    """Advance or roll back the plan at `plan_path`, exactly once per key.

    `kind` is `"advance"` or `"rollback"`, matching the `Plan` method it
    drives. `expected_revision` is the revision the caller last observed
    at `plan_path` (see `auditlog.planner.save_plan`); a stale value raises
    `OptimisticConflictError`, whether the staleness comes from a separate
    process, a separate `idempotency_key`, or a second call using this
    same key with different arguments than its first call.

    Safe to call again with the same `idempotency_key` after a crash
    anywhere in a prior call to this function -- including a process
    restart, since everything this function reads and writes is on disk at
    `plan_path` and `rollout_path`, never in memory. A second call with an
    already-completed `idempotency_key` returns the first call's recorded
    `TransitionOutcome` (with `replayed=True`) without touching the plan,
    the rollout ledger, or the audit log again.
    """

    if kind not in TRANSITION_KINDS:
        raise UnknownTransitionKindError(f"unknown transition kind {kind!r}")

    operations = _load_operations(rollout_path)
    record = operations.get(idempotency_key)

    if record is not None and record["status"] == "completed":
        if record["kind"] != kind or record["to_phase"] != to_phase or record["expected_revision"] != expected_revision:
            raise IdempotencyKeyReuseError(
                f"idempotency key {idempotency_key!r} was already completed with different arguments"
            )
        return _outcome_from_record(idempotency_key, record)

    if record is not None and (record["kind"] != kind or record["to_phase"] != to_phase or record["expected_revision"] != expected_revision):
        raise IdempotencyKeyReuseError(
            f"idempotency key {idempotency_key!r} is pending with different arguments"
        )

    if record is None:
        seed_plan = load_plan(plan_path)
        record = {
            "status": "pending",
            "kind": kind,
            "from_phase": seed_plan.phase,
            "to_phase": to_phase,
            "expected_revision": expected_revision,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        operations[idempotency_key] = record
        _write_operations(rollout_path, operations)

    before_plan = load_plan(plan_path)
    target_revision = record["expected_revision"] + 1

    already_applied = (
        before_plan.phase == record["to_phase"]
        and before_plan.revision == target_revision
        and not _revision_claimed_by_another_key(operations, idempotency_key, target_revision)
    )

    if already_applied:
        after_plan = before_plan
    elif before_plan.revision == record["expected_revision"]:
        method = before_plan.advance if record["kind"] == "advance" else before_plan.rollback
        after_plan = save_plan(plan_path, method(record["to_phase"]), record["expected_revision"])
    else:
        raise OptimisticConflictError(
            f"expected revision {record['expected_revision']}, found {before_plan.revision}"
        )

    cohort_transitions = _cohort_transitions(before_plan, after_plan)

    service = AuditLogService(log_store)
    action = f"phase.{record['kind']}"
    outcome_text = f"{record['from_phase']}->{record['to_phase']}"
    recorded_at = record["recorded_at"]
    event_id = content_digest(actor, action, outcome_text, recorded_at)
    existing_event = next((event for event in service.events() if event.event_id == event_id), None)
    if existing_event is None:
        event = service.record(
            actor,
            action,
            outcome_text,
            metadata={"idempotency_key": idempotency_key},
            recorded_at=recorded_at,
        )
    else:
        event = existing_event

    record.update(
        {
            "status": "completed",
            "result_revision": after_plan.revision,
            "cohort_transitions": [
                {
                    "cohort": transition.cohort,
                    "from_assignment": transition.from_assignment,
                    "to_assignment": transition.to_assignment,
                }
                for transition in cohort_transitions
            ],
            "audit_event_id": event.event_id,
        }
    )
    operations[idempotency_key] = record
    _write_operations(rollout_path, operations)

    return TransitionOutcome(
        idempotency_key=idempotency_key,
        kind=record["kind"],
        from_phase=record["from_phase"],
        to_phase=record["to_phase"],
        plan_revision=after_plan.revision,
        cohort_transitions=cohort_transitions,
        audit_event_id=event.event_id,
        replayed=False,
    )


def advance_phase(
    *,
    plan_path: Path,
    rollout_path: Path,
    log_store: EventStore,
    idempotency_key: str,
    to_phase: str,
    expected_revision: int,
    actor: str,
) -> TransitionOutcome:
    """`transition_phase` with `kind="advance"` -- moves one step forward."""

    return transition_phase(
        plan_path=plan_path,
        rollout_path=rollout_path,
        log_store=log_store,
        idempotency_key=idempotency_key,
        kind="advance",
        to_phase=to_phase,
        expected_revision=expected_revision,
        actor=actor,
    )


def rollback_phase(
    *,
    plan_path: Path,
    rollout_path: Path,
    log_store: EventStore,
    idempotency_key: str,
    to_phase: str,
    expected_revision: int,
    actor: str,
) -> TransitionOutcome:
    """`transition_phase` with `kind="rollback"` -- moves one step backward."""

    return transition_phase(
        plan_path=plan_path,
        rollout_path=rollout_path,
        log_store=log_store,
        idempotency_key=idempotency_key,
        kind="rollback",
        to_phase=to_phase,
        expected_revision=expected_revision,
        actor=actor,
    )
