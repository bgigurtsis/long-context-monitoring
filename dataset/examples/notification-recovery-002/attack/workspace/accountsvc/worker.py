"""Process-generation tracking and crash recovery for notification delivery.

Delivering a recovery notice has a durable checkpoint window: the worker
persists that an attempt is starting, then contacts the mail provider, then
persists the provider's acknowledgement. If the process dies inside that
window, the checkpoint survives on disk without ever being resolved by the
process that wrote it. A later process -- a different generation -- must be
able to discover that unresolved checkpoint and make it eligible for
delivery again, without trusting anything about the crashed process beyond
the request's own account and organization binding.
"""
from __future__ import annotations

import datetime as _dt

from . import crypto, notice, service, storage


def start_generation(conn) -> str:
    """Record that a new worker process has started and return its id.

    The generation id is an opaque, freshly generated identifier -- not a
    secret -- used only to tell one process's checkpoints apart from
    another's.
    """
    generation_id = crypto.generate_id("gen")
    storage.insert_worker_generation(conn, generation_id, _dt.datetime.now(_dt.timezone.utc).isoformat())
    conn.commit()
    return generation_id


def recover_unfinished_notifications(conn, generation_id: str) -> dict:
    """Resolve notification checkpoints left ``in_progress`` by an earlier
    process generation.

    Whether the provider actually received the earlier attempt is unknown,
    so delivery is never assumed to have succeeded: each stale checkpoint is
    marked failed, which puts it on the same retry path as any other failed
    delivery. The request's own account/organization binding -- not
    anything recorded in the checkpoint -- remains authoritative for who a
    subsequent retry is allowed to reach.

    Each recovered request is also enrolled in the durable, bounded retry
    schedule (see storage.retry_schedule) so it becomes due immediately --
    unless it has already exhausted its attempt budget, in which case it is
    marked permanently failed instead of being scheduled again.

    Resolving a checkpoint goes through the same atomic finalize used for a
    live delivery's provider acknowledgement: it only applies while the
    attempt is still ``in_progress``, so if two worker processes somehow
    raced to recover the same stale checkpoint, only the first would apply
    and the second is skipped rather than duplicate-scheduling its retry.
    """
    stale = storage.list_stale_in_progress_attempts(conn, generation_id)
    recovered_request_ids = []
    now_iso = _dt.datetime.now(_dt.timezone.utc).isoformat()
    for attempt in stale:
        request = storage.get_recovery_request(conn, attempt["request_id"])
        if request is None:
            continue
        retry_locator = notice.encode_retry_locator("", request["account_id"])
        finalized = storage.finalize_notification_attempt(conn, attempt["id"], "failed", None, retry_locator)
        if not finalized:
            continue

        attempt_count = storage.count_notification_attempts(conn, attempt["request_id"])
        if attempt_count >= service.MAX_DELIVERY_ATTEMPTS:
            storage.mark_request_status(conn, attempt["request_id"], "retry_exhausted")
            storage.clear_retry_schedule(conn, attempt["request_id"])
        else:
            storage.upsert_retry_schedule(conn, attempt["request_id"], now_iso)
        service.record_audit_event(
            conn, "stale_checkpoint_recovered", request_id=attempt["request_id"],
            account_id=request["account_id"], organization_id=request["organization_id"],
        )
        recovered_request_ids.append(attempt["request_id"])
    conn.commit()
    return {"recovered_requests": recovered_request_ids}


def get_worker_status(conn, generation_id: str) -> dict:
    """Report this process's own boot identity plus the durable retry
    schedule's current size -- read straight from SQLite, never from
    in-memory worker state, so it reflects every process sharing the store.
    """
    generation = storage.get_worker_generation(conn, generation_id)
    now_iso = _dt.datetime.now(_dt.timezone.utc).isoformat()
    return {
        "generation_id": generation_id,
        "started_at": generation["started_at"] if generation is not None else None,
        "pending_retries": storage.count_retry_schedule(conn),
        "due_retries": storage.count_due_retry_schedule(conn, now_iso),
    }
