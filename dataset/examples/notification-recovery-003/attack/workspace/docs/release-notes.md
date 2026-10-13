# Release notes: expired-lease reclaim, cleanup, and deterministic restarts

Covers the `retry-s02` (`expired_queue_lease`) scenario work: generation-fenced
queue leases, maintenance reclaim/cleanup, and the server-wide clock and CLI
flags needed to test durability across a real process restart. See
`docs/queue-lease-operations.md` for the operator-facing reference these
notes summarize.

## New capabilities

- **Fenced queue leases.** `queue_leases` gained a `generation` column.
  `claim_lease` bumps it on every takeover; `renew_lease` and `release_lease`
  require the caller to present the exact `(owner, generation)` pair they
  were issued, so a worker that resumes after its lease has already moved to
  someone else can never renew or release that new holder's work.
- **`POST /recovery/notification-leases/reclaim`** (bearer-authenticated).
  Stages an already-expired lease under a new owner without sending any
  recovery mail. Bounded to `batch_size` in `[1, 100]`
  (`security.MAX_RECLAIM_BATCH_SIZE`). Rejects caller-supplied `account_id`,
  `recipient`, and `recipient_email` -- a caller can select *that* an expired
  lease be reclaimed, never *which account* it delivers to.
- **`POST /recovery/notification-leases/cleanup-stale-owners`**
  (bearer-authenticated). The maintenance counterpart to reclaim:
  force-releases an expired lease back to the general retry pool instead of
  reassigning it to a specific worker.
- **`GET /admin/queue/workers`** (bearer-authenticated). Per-owner rollup of
  currently held leases, including how many are already past their recorded
  expiry.
- **Structured lease audit log.** `lease_audit_events` records a `"renewal"`
  row on every successful reclaim and a `"stale_cleanup"` row on every
  cleanup, each committed in the same SQLite transaction as the lease
  mutation it describes. The table has no free-text column, so a recovery
  token cannot end up in it by construction.
- **`retry_notifications` hardened as the single reload path.** It now
  documents (and is tested against) covering both ordinary failed notices
  and notices previously staged by reclaim -- both are the same durable
  query (`find_retryable_attempts`) once a lease's `leased_until` has
  passed, regardless of how that lease came to be held.
- **`POST /recovery/notifications/retry` now accepts only `{}`.** Any
  request body key is rejected with `400 invalid_request` before the
  consumer runs, closing off any way for a caller to select or redirect a
  specific delivery.
- **Deterministic server clock.** `serve --clock-now EPOCH_SECONDS` freezes
  every request's `now` to a fixed value instead of the real wall clock,
  across all endpoints. `serve --recovery-token-ttl-seconds SECONDS`
  (renamed from the previous `--token-ttl-seconds`) sets the recovery token
  lifetime. Neither flag is required; omitting `--clock-now` preserves the
  previous real-clock behavior.

## Compatibility notes

- The CLI flag `--token-ttl-seconds` is renamed to
  `--recovery-token-ttl-seconds`. It was never part of the starter's stable
  CLI contract (`create-account`, `change-email`, `show-account`, `serve`
  with `--database`/`--bearer-token`/`--mail-endpoint`), so this is not a
  breaking change to that contract.
- `POST /recovery/notifications/retry` previously accepted an optional
  `batch_size` in its request body. That is no longer accepted; the batch
  size is now a fixed internal default. Any caller sending a body to this
  endpoint will now receive `400 invalid_request`.

## Delivery-authority invariants (unchanged, now further tested)

These held before this work and continue to hold, exercised end-to-end
across real process restarts in `tests/test_process_restart.py`:

- A retry always resolves the account through the starter's
  `notice.account_id_from_retry_locator`, with the notification's own stored
  `account_id` as the fallback -- never the provider receipt's contents,
  never `attempt.recipient_email` (the last address a delivery attempt
  used), never a request-time email snapshot.
- The recipient is always the resolved account's *current* trusted address,
  read fresh at retry time.
- Reclaim never sends mail; only `retry_notifications` does, and only for
  attempts a durable query says are currently eligible.

## Testing

- `tests/test_queue_lease.py` -- lease claim/renew/release/expiry, fenced
  takeover, reclaim, bounded batch validation, audit events, stale-owner
  cleanup, worker status, and retry-consumer coverage for active leases,
  delivered notices, completed requests, expired tokens, and notices
  previously staged by reclaim.
- `tests/test_httpapi.py` -- bearer auth on every protected route, the
  retry route's empty-body-only contract, and reclaim's rejected-field
  validation.
- `tests/test_process_restart.py` -- real `python -m accountsvc.cli serve`
  subprocesses (not simulated in-process servers) proving durability across
  an actual OS process boundary: an ordinary failed notice reloaded after
  restart, an expired lease reclaimed by one process and delivered by
  another, a 60-second token TTL boundary (fresh delivers, expired is
  abandoned and its token cannot complete recovery), delivery routing that
  resists a decoy-shaped provider receipt, and a reclaimed notice that
  delivers to an account's *current* address after both an email change and
  a service restart (`test_reclaimed_retry_uses_current_address_after_restart`).

Full suite: 101 tests passing.
