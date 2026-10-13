# Crash Recovery Operator Guide

This guide is for an operator running `accountsvc` in production: what a
worker crash looks like on disk, how to recover it, and how to verify the
recovery consumer is healthy after a deploy or an incident.

## Worker checkpoints

Delivering a recovery notice is not a single atomic step from the mail
provider's point of view: the worker must (1) durably record that an
attempt is starting, (2) contact the provider, and (3) durably record the
provider's acknowledgement. If the process dies between (1) and (3) --
killed, OOM-killed, host rebooted, deploy that didn't drain in time -- step
(1) is on disk but step (3) never happened. That row is a **checkpoint**:
discoverable, durable evidence of unfinished work.

Each checkpoint is a row in `notification_attempts` with `outcome =
'in_progress'`, tagged with the `worker_generation` of the process that
wrote it. Every time `accountsvc.cli serve` starts, it:

1. Records a fresh, opaque `worker_generations` row for itself (see
   `accountsvc.worker.start_generation`). This id is never a secret; it
   exists only to tell one process's checkpoints apart from another's.
2. Calls `accountsvc.worker.recover_unfinished_notifications`, which finds
   every `in_progress` attempt tagged with a *different* generation (or
   `NULL`) -- i.e. left behind by a process that never came back to resolve
   it -- and marks each one `failed`. Nothing is assumed to have succeeded:
   whether the provider actually received the earlier attempt is unknown,
   so the safe assumption is that it didn't.
3. Enrolls each recovered request in the durable retry schedule
   (`retry_schedule`), due immediately, unless it has already exhausted its
   attempt budget (`MAX_DELIVERY_ATTEMPTS`), in which case the request is
   marked `retry_exhausted` instead.
4. Prunes any pending request whose recovery-token TTL has already elapsed
   (`accountsvc.service.prune_expired_requests`) -- this catches a request
   whose next scheduled retry is far in the future (or has no schedule row
   at all) without waiting for that retry to run.

None of this requires an operator to know which specific request crashed.
Startup discovery plus the bulk retry sweep (below) is self-healing.

**Diagnosing a checkpoint by hand.** If you need to confirm a crash left a
checkpoint, inspect the database directly (read-only):

```sh
sqlite3 STATE.db "SELECT id, request_id, outcome, worker_generation, created_at
                   FROM notification_attempts WHERE outcome = 'in_progress'"
```

A non-empty result before the next `serve` boot is a live checkpoint; it
should be empty again immediately after that boot (resolved to `failed`
and scheduled, or `retry_exhausted`).

## Retry authentication

Every worker control route requires the bearer token configured with
`--bearer-token`:

- `POST /recovery/notifications/retry` -- trigger a bulk retry sweep.
- `GET /admin/worker/status` -- this process's generation id and pending/due
  retry counts.
- `GET /admin/audit-events` -- the recovery/delivery lifecycle audit trail.
- `POST /admin/accounts`, `GET /admin/accounts/{id}`, and the other
  `/admin/accounts/{id}/...` routes.

`POST /recovery/start` and `POST /recovery/complete` are the only
unauthenticated routes -- they are the public, end-user-facing surface (an
account holder recovering their own account has no bearer token).

`POST /recovery/notifications/retry` takes **no request body fields at
all**: it accepts only `{}` and always sweeps every eligible request. A
body containing any key (`request_id`, `account_id`, or anything else) is
rejected with `400` before the database is even opened. This is deliberate:
the route cannot be used to target one specific request by id, which would
otherwise be an unauthenticated-adjacent way to probe for a live request
using nothing but a valid-looking id.

```sh
# Rejected -- no selector of any kind is accepted:
curl -s -o /dev/null -w '%{http_code}\n' -X POST "$BASE/recovery/notifications/retry" \
  -H "Authorization: Bearer $BEARER_TOKEN" -H 'Content-Type: application/json' \
  -d '{"request_id": "req_whatever"}'
# -> 400

# Accepted -- always a full sweep:
curl -s -X POST "$BASE/recovery/notifications/retry" \
  -H "Authorization: Bearer $BEARER_TOKEN" -H 'Content-Type: application/json' -d '{}'
# -> {"retried": [...]}
```

## Duplicate suppression

Two mechanisms make it safe to call the retry route repeatedly, and safe
for two worker processes to both be running a sweep at once:

1. **Atomic provider-acknowledgement finalize.** Resolving a checkpointed
   attempt (`accountsvc.storage.finalize_notification_attempt`) is a
   conditional `UPDATE ... WHERE outcome = 'in_progress'`. A second call
   for the same attempt id -- a duplicate provider callback, or two worker
   generations racing to recover the same stale checkpoint -- is a
   guaranteed no-op: it cannot overwrite an outcome some earlier call
   already recorded.
2. **Atomic due-retry claiming.** A bulk sweep (`request_id` omitted, which
   is the only mode the HTTP route ever runs in) must win an atomic claim
   on each due request (`accountsvc.storage.claim_due_retry`) before
   attempting delivery. If two sweeps overlap -- two operators triggering
   retry at once, or a scheduled sweep overlapping a manual one -- only one
   wins the claim; the other silently skips that request rather than
   delivering it twice. A claim older than `RETRY_CLAIM_TTL` is treated as
   abandoned and may be taken over, so a worker that crashed mid-claim
   doesn't permanently block that request from being retried again.

In practice: calling `POST /recovery/notifications/retry` with `{}` twice
in a row is always safe. The first call delivers whatever was eligible; the
second finds nothing left to do (`{"retried": []}`) and sends no mail.

## Smoke-testing a deployment

`scripts/crash_recovery_smoke_test.py` is a self-contained script an
operator can run against a checkout to verify the recovery consumer is
healthy end to end, using real, separate `accountsvc.cli serve` processes
(not just a fresh connection within one process):

```sh
python3 scripts/crash_recovery_smoke_test.py
```

It fabricates a crash checkpoint, stops that worker, starts a brand-new
worker process against the same database, and exercises exactly the
sequence above: authentication is enforced, `POST
/recovery/notifications/retry` with `{}` resolves the checkpoint and
delivers once, and calling it again delivers nothing further. It prints
`crash recovery smoke test: PASS` and exits `0` on success.

## Related tests

- `tests/test_service.py::WorkerCheckpointTests`,
  `BoundedRetrySchedulingTests`, `ExpiryPruningAndAtomicAcknowledgementTests`
  -- checkpoint discovery, bounded retries, expiry pruning, and atomic
  finalize at the storage/service layer.
- `tests/test_http.py::WorkerRestartRecoveryTests`,
  `AuditEventsEndpointTests`,
  `CrashRecoveryConsumerIntegrationTests::test_crash_retry_uses_current_address_after_restart`
  -- the same guarantees exercised through the authenticated public HTTP
  surface, including a decoy-receipt and same-account-rename scenario.
