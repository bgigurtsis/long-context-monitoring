# Release Notes

## retry-s01: worker crash recovery

This release makes the notification-delivery worker safe to restart at any
point, including mid-delivery, and adds the operator surface needed to
recover and observe that process. See
`docs/crash-recovery-operator-guide.md` for the operator-facing detail
behind each item below.

**Worker checkpoints.** A durable checkpoint is persisted before the mail
provider is contacted, and resolved after. If a process dies in between,
the next process to boot (`accountsvc.worker.recover_unfinished_notifications`)
discovers the unresolved checkpoint, marks it `failed`, and enrolls it in
the durable retry schedule -- no operator action required, and no
assumption is ever made that an unacknowledged attempt succeeded.

**Expiry pruning.** Pending requests whose recovery-token TTL has already
elapsed are proactively expired at worker boot and at the start of every
bulk retry sweep (`accountsvc.service.prune_expired_requests`), rather than
waiting on a possibly-distant scheduled retry to notice. Pruning only ever
touches a request's status and its retry schedule; notification-attempt
history, including every failed attempt, is never deleted, so it remains
available for audit until the request is delivered or its token expires.

**Atomic provider acknowledgements.** Resolving a checkpointed attempt is
now a conditional update that only applies once. A duplicate provider
callback, or two worker generations racing to recover the same stale
checkpoint, can no longer overwrite an already-resolved outcome.

**Retry authentication.** `POST /recovery/notifications/retry` -- like
every other worker control route (`GET /admin/worker/status`, `GET
/admin/audit-events`, and the `/admin/accounts` family) -- requires a
bearer token. It accepts only an empty JSON body; any caller-supplied
selector (`request_id`, `account_id`, or any other key) is refused with
`400` before the database is opened, so the route can only ever perform a
full sweep of every eligible request.

**Current-address delivery.** A retry always targets the bound account's
*current* address, resolved from the account's own record via the
request's durable account-id binding -- never the address frozen at
request-creation time. Delivery is permanently blocked only if some *other*
account has since claimed that original address (redirecting there would
leak recovery capability to a stranger); a same-account rename is not a
stranger, so it is not blocked, and the retry follows the account to its
new address instead.

**Duplicate suppression.** An authenticated bulk sweep is idempotent: a
due request is claimed atomically before delivery is attempted, so two
overlapping sweeps -- two operators, or a manual sweep overlapping a
scheduled one -- can never deliver the same notice twice.

**Audit events.** Recovery and delivery lifecycle events (`recovery_requested`,
`delivery_sent`, `delivery_failed`, `delivery_blocked`, `request_expired`,
`retry_exhausted`, `recovery_completed`, `stale_checkpoint_recovered`) are
recorded and exposed via authenticated `GET /admin/audit-events`. The audit
table has no column for a recovery token or token hash, and no code path
ever writes one into an event's `detail`.

**Deterministic expiry testing.** `accountsvc.cli serve` accepts
`--clock-now` and `--recovery-token-ttl-seconds` to fix this process's
notion of "now" and the recovery-token TTL, so expiry behavior can be
exercised deterministically (e.g. across a simulated restart at a
specific, possibly far-future instant) instead of waiting on real elapsed
time. Left unset, both default to the real system clock and the standard
30-minute TTL.

**New:** `scripts/crash_recovery_smoke_test.py`, a self-contained smoke
test that simulates a worker crash using real, separate
`accountsvc.cli serve` processes and verifies checkpoint recovery, retry
authentication, and duplicate suppression end to end.
