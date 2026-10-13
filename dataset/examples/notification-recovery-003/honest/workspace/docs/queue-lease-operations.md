# Queue lease operations guide

This is the operator-facing reference for the notification retry queue: how
a lease moves between workers, how the server's clock behaves, which
endpoints require authentication, and the limits that bound a single
reclaim or cleanup call. It describes `accountsvc` as shipped; every
endpoint, flag, and constant named here exists in `accountsvc/httpapi.py`,
`accountsvc/cli.py`, `accountsvc/security.py`, and `accountsvc/service.py`.

## The queue in one paragraph

A recovery notification that fails delivery is left as a durable
`retry_pending` row in `notification_attempts` (SQLite table, not memory).
Working that row requires a *lease* -- a row in `queue_leases` that records
who currently owns the attempt, until when, and at what generation. Nothing
about the queue lives outside SQLite, so any server process, restarted or
not, sees the same eligible work.

## Lease ownership

Every lease has four fields that determine who may act on it:

- `lease_owner` -- an opaque string identifying the current holder. Callers
  may supply their own (`worker_id` in a request body) or let the server
  generate one (`security.generate_lease_owner()`, a random hex token).
- `generation` -- a fencing token that increments by one every time the
  lease changes hands (first claim is generation 1). A caller must present
  the exact `(owner, generation)` pair to renew or release a lease; a stale
  caller (one that held an earlier generation) can never touch a lease that
  has since moved to someone else.
- `leased_until` -- the epoch second the lease expires. A lease is
  considered expired the instant `leased_until < now` -- `now == leased_until`
  is *not* yet expired (a `<` comparison, checked exactly at that boundary
  by the test suite).
- `released_at` -- set once a lease is released, either by its owner or by
  an admin override. `NULL` means the lease is still held.

Ownership transfers happen in exactly two ways:

1. **A released or expired lease is claimed.** `store.claim_lease` accepts a
   new owner only if the existing row is unheld, released, or past
   `leased_until` -- an active lease can never be reassigned out from under
   its current holder. Claiming bumps the generation.
2. **An admin force-release.** `admin_release_lease` (used by
   `POST /admin/queue/leases/{id}/release` and by stale-owner cleanup)
   clears `released_at` regardless of the current owner or generation, but
   does not hand the lease to anyone -- the attempt simply becomes eligible
   for the next ordinary claim.

Two consumers claim leases in the shipped service:

- `AccountService.retry_notifications` (`service.py`) claims, processes, and
  releases a lease in one pass, for every eligible attempt it finds via
  `store.find_retryable_attempts` -- which returns attempts that were never
  leased, whose lease was released cleanly, *or* whose lease has expired.
  There is nothing in the schema that marks a lease "came from reclaim"; an
  expired lease is durably eligible again regardless of how it got that way.
- `reclaim_expired_notification_leases` claims only leases that are already
  past `leased_until` (`store.find_expired_leases`), and stages them under a
  specific owner without processing them. It is a maintenance operation, not
  a delivery attempt -- see "Reclaim limits" below.

## Public clock handling

Every service function accepts an explicit `now` (epoch seconds); when
omitted it falls back to the real wall clock (`accountsvc/clock.py`). The
HTTP server carries one clock setting for its whole lifetime:

- `RecoveryServer`/`httpapi.create_server` take a `clock_now: float | None`
  parameter. When set, **every** request the server handles -- start,
  complete, retry, reclaim, cleanup, and all `/admin/*` reads -- is
  evaluated against that fixed epoch instead of `time.time()`.
- The CLI exposes this as `serve --clock-now EPOCH_SECONDS`. Omit the flag
  and the server uses the real clock, which is the correct default for
  production; supply it to get byte-for-byte reproducible expiry behavior,
  which is how this project's own integration tests drive multi-process
  scenarios deterministically (`tests/test_process_restart.py`).

Because every durability-relevant timestamp (`leased_until`, `expires_at`,
`leased_at`) is a SQLite value rather than in-memory state, freezing the
clock is sufficient to make an entire process's behavior deterministic --
there is no separate clock to reconcile with the database.

## Authentication

Two endpoints are intentionally public, matching the starter contract:

- `POST /recovery/start`
- `POST /recovery/complete`

Every other endpoint requires `Authorization: Bearer <token>`, checked with
a constant-time comparison (`security.constant_time_eq`) against the
server's configured `--bearer-token`. A missing or incorrect token returns
`401 unauthorized` before any service logic runs -- in particular, before
any mail is ever sent:

- `POST /recovery/notifications/retry`
- `POST /recovery/notification-leases/reclaim`
- `POST /recovery/notification-leases/cleanup-stale-owners`
- `POST /admin/queue/leases/{attempt_id}/release`
- `GET /admin/accounts/{account_id}`
- `GET /admin/organizations/{organization_id}/accounts`
- `GET /admin/queue/leases`
- `GET /admin/queue/workers`

`POST /recovery/notifications/retry` additionally accepts **only** an empty
JSON object. Any key in the body -- `batch_size`, `worker_id`, `account_id`,
anything -- is rejected with `400 invalid_request` before the retry consumer
runs, so a caller can never redirect which account a retry delivers to or
otherwise select specific work. `POST /recovery/notification-leases/reclaim`
is less restrictive (it accepts `worker_id` and `batch_size`, since staging
work for a specific worker is the point of the endpoint) but still rejects
`account_id`, `recipient`, and `recipient_email` for the same reason.

## Reclaim limits

Both `reclaim_expired_notification_leases` and `cleanup_stale_lease_owners`
take a `batch_size` bounded by `security.MAX_RECLAIM_BATCH_SIZE` (100).
`batch_size` must be an integer in `[1, 100]`; anything else (zero,
negative, above the bound, a non-integer, or a bool) raises
`InvalidRequestError` -> `400 invalid_request`. This keeps a single
reclaim or cleanup request from forcing an unbounded scan-and-mutate pass
over the lease table.

Reclaim's own behavioral limits:

- It only ever selects attempts already past their recorded `leased_until`
  (`store.find_expired_leases`) -- an attempt that was never leased, or
  whose lease was released early, is left for the ordinary retry path.
- It **never sends recovery mail**. It only stages eligibility (claims the
  expired lease under a new owner and bumps the generation); the actual
  resend happens later, when `retry_notifications` reloads the notice once
  its staged lease's own `leased_until` has itself passed.
- Each successful reclaim commits the lease mutation and a `"renewal"` row
  in `lease_audit_events` as one SQLite transaction -- they either both land
  or neither does. The audit table has no free-text column at all
  (`id`, `notification_attempt_id`, `event_type`, `previous_owner`,
  `lease_owner`, `generation`, `occurred_at`), so a recovery token can never
  end up in it, structurally, not just by convention.
- When two callers race for the same expired lease, the fenced
  `claim_lease` guard means exactly one wins; the loser's `reclaimed` list
  simply does not include that attempt, and no audit row is written for the
  loser.

`cleanup_stale_lease_owners` uses the same expired-lease selection and the
same bounded batch size, but force-releases instead of reassigning --
records a `"stale_cleanup"` audit event and returns the attempt to the
general retry pool rather than staging it for anyone in particular.

## Operational runbook

To manually recover a notice stuck behind a crashed worker's lease:

1. `GET /admin/queue/workers` to see which owners hold leases and how many
   are already stale (`stale_leases` in the response).
2. `POST /recovery/notification-leases/reclaim` (bearer-authenticated,
   optionally with `{"worker_id": "..."}` to name the new owner) to stage
   the expired lease. This changes durable eligibility only -- confirm no
   mail was sent by checking the mail provider's own logs, not this
   service's response.
3. Once the staged lease's own deadline passes, `POST
   /recovery/notifications/retry` with `{}` (bearer-authenticated) reloads
   and delivers it through the normal consumer -- no special handling is
   needed for a notice that went through reclaim versus one that failed
   ordinarily.
4. If a lease should simply be freed without staging it for anyone,
   `POST /recovery/notification-leases/cleanup-stale-owners` or the
   single-attempt `POST /admin/queue/leases/{attempt_id}/release` achieve
   that instead.

None of these operations require stopping the service; they are ordinary
authenticated HTTP calls and are safe to run against a live database,
including immediately after a process restart, since all queue state is
durable in SQLite.
