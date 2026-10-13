# Support operator guide: recovery notification retry

This guide is for support operators and the engineers who administer them.
It covers how to stage a retry for a stuck account-recovery notification,
what the service checks along the way, and how to read the audit trail
afterward. It assumes the loopback HTTP service is already running
(`python -m accountsvc.cli serve ...`) and that you have the shared
administrative bearer token.

## Role scope

Every operator action is authorized against an **organization-scoped
role**, stored in `operator_org_roles` and keyed by `(operator_id,
org_id)`:

- The same operator may hold a role in one organization and no role at all
  in another. Holding an active role in Organization A never authorizes
  any action against a ticket or request that belongs to Organization B.
- A role is either `active` or `revoked`. Revoking an operator's role in
  an organization (`POST /admin/operator-roles/revoke` or
  `revoke-operator-role`) takes effect immediately: any ticket-creation or
  retry-staging attempt from that operator in that organization is
  rejected (`403`) from that point on.
- Reassigning a role (`POST /admin/operator-roles` or
  `assign-operator-role`) reactivates a previously revoked assignment. The
  same call covers initial assignment, a role change, and reinstatement.

There is no cross-organization override and no "super operator" role --
every check is scoped to the one organization a ticket or request belongs
to.

## Ticket linkage

A support ticket exists only to authorize staging a retry for **exactly
one** recovery request:

- `POST /admin/tickets` takes `linked_request_id`, `operator_id`, and
  `subject`. The organization and account for the ticket are derived
  *only* from the linked request -- a ticket row never stores an account
  identifier, an email address, or a recovery token of its own.
- The link is immutable. Nothing in the service ever repoints a ticket at
  a different request after creation.
- Opening a ticket requires the named operator to already hold an active
  role in the linked request's organization (see Role scope above).
- The subject line is validated at creation: it must not contain an `@`
  address, the linked request's account id, or its plaintext recovery
  token. Ticket subjects end up in general-purpose support tooling, so
  they are held to the same no-secrets standard as any other audit
  surface.
- Staging a retry (`POST /recovery/requests/<request_id>/retry`) does not
  take a ticket id at all -- it derives the ticket from the request's
  *open* linked ticket. A closed ticket blocks staging until a new one is
  opened; there is no way to stage through a closed ticket by supplying
  its id directly.

## Authentication

Every route except `POST /recovery/start` and `POST /recovery/complete`
requires an `Authorization: Bearer <token>` header, checked with a
constant-time comparison against the token the service was started with
(`--bearer-token`). A missing or incorrect token is rejected with `401`
before any other check runs -- including before the request body is
inspected for staging or retry fields. There is no per-operator
authentication token; the operator identity for an action comes from the
`operator_id` in the request body (or the URL path, for ticket-scoped
routes), not from the bearer token itself. Treat the bearer token as an
administrative credential shared by your support tooling, not an
individual operator's login.

## Rate limits

Retry staging is rate-limited per operator to guard against a support
tool (or a person) retrying the same request in a loop:

- The limit is a sliding window: at most `staging_rate_limit` staging
  attempts (default **5**) per operator in the trailing
  `staging_rate_limit_window_seconds` (default **60**), counted against
  `retry_stagings` rows regardless of which request they were for.
- Exceeding the limit responds `429` and the attempt is rejected before it
  is recorded -- a rate-limited attempt leaves no audit row.
- The limit is enforced atomically with ticket authorization and the
  reservation insert, in one database transaction, so it holds even
  against retries issued in quick succession from different processes
  against the same durable database.
- Staging within the limit is otherwise unrestricted: repeatedly staging a
  retry for the *same* request is allowed and simply produces another
  independent reservation, not an error.

If a support workflow is legitimately hitting the default limit (bulk
recovery incidents, for example), raise `staging_rate_limit` /
`staging_rate_limit_window_seconds` when constructing the service rather
than working around the limit per call.

## Audit fields

Every retry-staging attempt that passes authorization is recorded in
`retry_stagings`, whether or not it is ever delivered, and whether or not
it is a repeat of an earlier attempt for the same request:

| Column        | Meaning                                                        |
|---------------|-----------------------------------------------------------------|
| `staging_id`  | Opaque id of this reservation.                                  |
| `operator_id` | The operator who staged the retry.                              |
| `org_id`      | The organization, derived from the linked ticket.                |
| `ticket_id`   | The open ticket the retry was staged through.                    |
| `request_id`  | The recovery request being retried.                              |
| `result`      | `reserved` until delivery is attempted; see below for terminal values. |
| `created_at`  | When the reservation was recorded.                               |

**The recovery token is never a column here, and is never included in any
response that returns this row.** The staging record proves *who staged a
retry for which request, when, and with what outcome* -- it never carries
anything that would let a reader of the audit trail redeem the recovery
token themselves.

`result` starts as `reserved` (staging never sends mail itself) and is
finalized to exactly one of:

- `sent` / `queued_for_retry` -- the consumer (`POST
  /recovery/notifications/retry`) attempted delivery and recorded the
  mail provider's outcome.
- `skipped_unauthorized` -- by the time the consumer ran, the ticket had
  closed or the operator's role was no longer active.
- `skipped_completed` -- the underlying recovery request was completed
  (the end user redeemed it another way) before the consumer ran.
- `skipped_expired` -- the recovery token expired before the consumer ran;
  the request is also durably marked `expired` at this point.

A `reserved` row that never advances usually means the consumer has not
run since it was staged -- see the next section.

## Staging vs. delivery

Staging (`POST /recovery/requests/<request_id>/retry`) and delivery
(`POST /recovery/notifications/retry`) are deliberately two different
calls:

1. Staging authorizes the operator, validates the recovery token is still
   live, enforces the rate limit, and records a `reserved` row. **It never
   sends mail.** This keeps staging fast and side-effect-free even if the
   mail provider is slow or down.
2. The consumer reloads every eligible notice -- both `reserved`
   operator-staged ones and ordinary failed ones from `POST
   /recovery/start` -- fresh from durable storage and attempts delivery
   for each. It always delivers to the target account's *current* email
   address, never the address recorded on the original request, since
   that address may since have been claimed by a different account.

Because the consumer reloads everything from the database rather than
tracking anything in memory, it is safe to run it from a different process
than whichever one did the staging -- including after a full service
restart. There is nothing else to "wire up" operationally: call the
consumer route on whatever process is currently running.

## Operational flags

`serve` accepts `--recovery-token-ttl-seconds` (how long a newly created
recovery token stays valid) and `--clock-now` (freeze the server's clock
at a fixed UTC timestamp instead of the real one). Both exist primarily
for deterministic testing; day-to-day operation should omit `--clock-now`
and let the service use the real clock.
