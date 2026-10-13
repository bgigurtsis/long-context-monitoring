"""Idempotent replay of generated SDK client calls against a checkpoint store.

Replaying a list of calls must never re-issue a call whose ``call_id`` is
already marked complete (``auditlog.migration_checkpoint.CheckpointStore``),
and must never let two different calls share one ``call_id`` — that would
make the checkpoint ambiguous about which call it actually refers to.

A crash between a call succeeding and its checkpoint being marked complete
is the one gap the checkpoint alone cannot close: a V1 record's identity
includes the timestamp the server stamps at the moment it receives the
request (see ``auditlog.models.IDENTIFYING_FIELDS``), by design, so the
server itself cannot recognize a retried record call as "the same call
already handled" the way it recognizes identical content submitted twice
with the same recorded time. A caller who can tell independently whether a
given call already took effect — for example, by querying for it — closes
that gap by passing ``ReplayCall.already_applied``: replay checks it before
invoking, so a call that already succeeded is marked complete without ever
being issued again.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .migration_checkpoint import CheckpointStore


class ReplayConflictError(ValueError):
    """Raised when two calls in one replay batch share a call_id but differ."""


@dataclass(frozen=True)
class ReplayCall:
    """One call to (re)issue.

    ``fingerprint`` is compared only in memory, against other calls in the
    same replay batch — it is never persisted — purely to catch a reused
    ``call_id`` that actually addresses two different calls.

    ``already_applied``, if given, is consulted before ``invoke`` for a
    call not yet marked complete: if it reports the call's effect already
    happened, replay marks the call complete without invoking it again.
    """

    call_id: str
    fingerprint: str
    invoke: Callable[[], object]
    already_applied: Callable[[], bool] | None = None


@dataclass(frozen=True)
class ReplayOutcome:
    """What happened for one call: skipped because it was already complete
    (or already applied), or actually invoked (in which case ``result`` is
    what ``invoke`` returned).
    """

    call_id: str
    skipped: bool
    result: object | None


def replay(
    calls: tuple[ReplayCall, ...], checkpoint: CheckpointStore
) -> tuple[ReplayOutcome, ...]:
    """Issue every not-yet-completed call, in order, checkpointing as it goes.

    A call already marked complete is skipped outright — its ``invoke`` is
    never called again. Otherwise, if the call carries an
    ``already_applied`` check and it reports the call already took effect,
    the call is marked complete without being invoked. Only then is the
    call marked pending, invoked, and marked complete, so a crash during
    ``invoke`` leaves the call pending (not silently lost, not falsely
    complete) for the next replay to retry.
    """

    seen_fingerprints: dict[str, str] = {}
    outcomes: list[ReplayOutcome] = []
    for call in calls:
        prior_fingerprint = seen_fingerprints.get(call.call_id)
        if prior_fingerprint is not None and prior_fingerprint != call.fingerprint:
            raise ReplayConflictError(
                f"call_id {call.call_id!r} addresses two different calls in this batch"
            )
        seen_fingerprints[call.call_id] = call.fingerprint

        if checkpoint.is_completed(call.call_id):
            outcomes.append(ReplayOutcome(call.call_id, skipped=True, result=None))
            continue

        if call.already_applied is not None and call.already_applied():
            checkpoint.mark_completed(call.call_id)
            outcomes.append(ReplayOutcome(call.call_id, skipped=True, result=None))
            continue

        checkpoint.mark_pending(call.call_id)
        result = call.invoke()
        checkpoint.mark_completed(call.call_id)
        outcomes.append(ReplayOutcome(call.call_id, skipped=False, result=result))

    return tuple(outcomes)
