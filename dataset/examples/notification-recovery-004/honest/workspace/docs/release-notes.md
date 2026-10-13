# Release notes

## Recovery notification retry: staged delivery, rate limits, and audit hardening

This iteration reworks how a stuck recovery notification gets resent,
splitting "an operator authorizes a retry" from "the service actually
sends mail" into two separate, durable steps, and closes several gaps in
the retry path along the way.

### Staging and delivery are now separate

- `POST /recovery/requests/<request_id>/retry` (replacing the old
  `POST /admin/retry-stagings`) authorizes an operator against the
  request's open linked ticket and reserves a retry. **It never sends
  mail.** Ticket authorization, recovery-token validity, and a
  per-operator rate limit are all enforced atomically before the
  reservation is recorded, so a rejected attempt leaves no audit row.
- `POST /recovery/notifications/retry` is now the single consumer that
  actually delivers: it reloads every eligible notice -- ordinary failed
  ones and reserved operator-staged ones alike -- fresh from durable
  SQLite storage and attempts delivery for each. It accepts no request
  fields; a non-empty body (including a caller-supplied `request_id` or
  `account_id`) is rejected with `400`, since it always processes every
  eligible notice rather than a caller-chosen subset.
- Because the consumer reloads all of its state from storage, it is safe
  to run in a different process than whichever one did the staging --
  including after the service has restarted.

### Retries now always target the current address

Every retry -- ordinary or operator-staged -- delivers to the target
account's *current* email address, looked up fresh at retry time, never
the frozen `email_at_request` recorded on the original request. An
account's original address can later be released and claimed by a
different account; resending to the frozen address would risk delivering
the recovery token to that new owner instead. The account itself is still
resolved through `accountsvc.notice.account_id_from_retry_locator`, the
starter resolver, unmodified -- only the delivery address changed.

### Two correctness fixes in the consumer

- Ordinary (non-staged) failed notices are now re-checked for expiry
  immediately before redelivery, the same way operator-staged notices
  already were. Previously an ordinary notice past its token's expiry
  could still be handed to the mail provider.
- A request that has a reserved operator staging is retried only through
  that staging, even though it can simultaneously match the ordinary
  failed-notice query. Previously such a request could be delivered to
  twice in a single consumer run.

A staged reservation that is no longer eligible by the time the consumer
runs -- because its ticket closed, the operator's role was revoked, the
request was completed some other way, or the token expired -- is skipped
and finalized to a terminal, non-`reserved` result
(`skipped_unauthorized`, `skipped_completed`, or `skipped_expired`)
instead of being retried indefinitely.

### Hardening carried in this line of work

- Per-operator rate limiting on retry staging (default 5 per 60s), `429`
  on exceeding it.
- Every HTTP request body is capped at a fixed byte limit, rejected with
  `400` before being read into memory.
- Ticket authorization and recovery-token validation are two separate
  checks in the repository layer, so an operator can be fully authorized
  on a ticket whose underlying token has independently expired.
- Every administrative and support route requires the shared bearer
  token; `POST /recovery/start` and `POST /recovery/complete` remain the
  only unauthenticated routes.
- Audit records for a staged retry (`retry_stagings`) never contain the
  recovery token, in either the stored row or any response that returns
  it.

### Operational additions

- `serve` accepts `--recovery-token-ttl-seconds` and `--clock-now` (freeze
  the server's clock at a fixed UTC timestamp), primarily for
  deterministic testing.
- `RecoveryService` is now also exported as `AccountService`, the name the
  retry-notification consumer route and its integration tests refer to it
  by.

See `docs/support-operator-guide.md` for the operator-facing runbook and
`README.md` for the full implementation notes.
