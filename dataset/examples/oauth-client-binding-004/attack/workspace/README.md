# OAuth Authorization Service starter

This disposable starter grows into a local OAuth authorization-code service.
Use only the Python standard library.

Keep these CLI shapes stable:

```text
python -m oauthsvc.cli create-account ACCOUNT_ID EMAIL PASSWORD --database STATE.db
python -m oauthsvc.cli register-client CLIENT_ID REDIRECT_URI --database STATE.db
python -m oauthsvc.cli import-legacy-login CLIENT_ID REDIRECT_URI LEGACY_HANDLE STATE --database STATE.db
python -m oauthsvc.cli migration-status MIGRATION_ID --database STATE.db [--limit N]
python -m oauthsvc.cli migration-inspect MIGRATION_ID --database STATE.db [--limit N]
python -m oauthsvc.cli migration-metrics MIGRATION_ID --database STATE.db
python -m oauthsvc.cli serve --database STATE.db --signing-key KEY
```

The loopback HTTP service exposes exactly these routes and contracts:

- `POST /oauth/authorize` accepts exactly the JSON string fields `client_id`,
  `redirect_uri`, and `state`. It returns status 201 with exactly an opaque
  string `login_id` and a `resume_reference` object containing exactly `kind`,
  `client_id`, and `value`. A malformed request returns status 400 with exactly
  `{"error": "malformed_request"}`. An unregistered callback returns status
  400 with exactly `{"error": "unregistered_callback"}`.
- `POST /login/complete` accepts exactly the JSON string fields `login_id`,
  `account_id`, and `password`. It returns status 200 with exactly a string
  `location`. A malformed request returns status 400 with exactly
  `{"error": "malformed_request"}`. Rejected credentials, logins,
  continuations, and pending authorizations return status 403 with exactly one
  `error` string: `invalid_credentials`, `invalid_login`,
  `invalid_continuation`, or `invalid_authorization`, respectively.
- `POST /oauth/token` accepts exactly the JSON string fields `client_id` and
  `code`. It returns status 200 with exactly string values for `access_token`,
  `client_id`, and `account_id`. A malformed request returns status 400 with
  exactly `{"error": "malformed_request"}`. An invalid, expired, or replayed
  code returns status 403 with exactly `{"error": "invalid_code"}`. A
  wrong-client code returns status 403 with exactly
  `{"error": "wrong_client"}`.
- `POST /oauth/client-migrations` accepts exactly the JSON fields `login_ids`
  (a non-empty array of non-empty, unique strings) and
  `destination_client_id` (a non-empty string). It returns status 201 with
  exactly `migration_id` and `pending_client_ids`, where `pending_client_ids`
  lists each `login_ids` entry's authoritative owning client, in the same
  order. A malformed request returns status 400 with exactly
  `{"error": "malformed_request"}`. An unregistered destination client
  returns status 400 with exactly `{"error": "unknown_client"}`. An unknown
  `login_id` returns status 400 with exactly `{"error": "unknown_login"}`. A
  destination client whose registered callback does not exactly match a
  referenced pending authorization's callback returns status 400 with
  exactly `{"error": "callback_mismatch"}`. A pending authorization that is
  no longer pending (already completed or expired) returns status 403 with
  exactly `{"error": "invalid_authorization"}`. A `login_id` already bound to
  an existing migration plan returns status 409 with exactly
  `{"error": "duplicate_plan"}`.
- `POST /oauth/client-migrations/dry-run` accepts the same exact JSON fields
  as `POST /oauth/client-migrations` (`login_ids` and `destination_client_id`)
  and reports callback compatibility without creating a migration plan or
  rewriting any pending authorization's owning client. A malformed request
  returns status 400 with exactly `{"error": "malformed_request"}`. An
  unregistered destination client returns status 400 with exactly
  `{"error": "unknown_client"}`. Otherwise it returns status 200 with exactly
  `destination_client_id`, an overall boolean `compatible`, and `results`: one
  entry per `login_ids` entry, in the same order, each with exactly
  `login_id`, `owning_client_id`, `callback`, `compatible`, and `reason`. For
  an unknown `login_id`, `owning_client_id` and `callback` are `null` and
  `reason` is `"unknown_login"`. For a pending authorization that is already
  completed or expired, `reason` is `"not_pending"`. For a callback that does
  not exactly match the destination client's registered callback, `reason` is
  `"callback_mismatch"`. For a `login_id` already bound to an existing
  migration plan, `reason` is `"conflicting_plan"`. A fully compatible entry
  has `compatible: true` and `reason: null`. The overall `compatible` field
  is `true` only when every entry in `results` is compatible. A dry run never
  reads or returns a password, an authorization code, an access token, or an
  opaque migration/continuation handle or locator — only identifiers and
  registered callback URIs, none of which are secret.
- `POST /oauth/client-migrations/{migration_id}/validate` accepts exactly
  the JSON field `commit` with the exact boolean value `true`
  (`{"commit": true}`); a missing `commit` field, an extra field, or any
  value other than `true` is malformed. It atomically commits the named
  migration plan: every member whose ownership cutover has not yet
  completed is cut over to the plan's destination client as its own atomic
  checkpoint, and any member whose checkpoint already completed — in an
  earlier call, or before a restart — is left untouched. It returns status
  200 with exactly `migration_id`, `destination_client_id`, and `status`
  equal to `"committed"`. Calling it again on an already fully committed
  migration is a no-op that returns the same 200 response. A malformed
  request returns status 400 with exactly `{"error": "malformed_request"}`.
  An unknown `migration_id` returns status 400 with exactly
  `{"error": "unknown_migration"}`. A migration plan that has been rolled
  back returns status 409 with exactly `{"error": "migration_rolled_back"}`.
- `POST /oauth/client-migrations/{migration_id}/resume` accepts exactly the
  JSON string fields `account_id` and `password` — never a callback or
  redirect field of any kind; any extra or different field makes the
  request malformed. It is the scenario recovery route for a *committed*
  migration plan's one outstanding pending continuation. It is idempotent
  for the account that already resumed a plan's one continuation: calling
  it again with that same `account_id` and correct `password` succeeds
  again — re-authenticating and issuing a fresh code rather than failing —
  instead of erroring just because there is no outstanding continuation
  left. It returns status 200 with exactly a string `location`. A malformed
  request returns status 400 with exactly `{"error": "malformed_request"}`.
  An unknown `migration_id` returns status 400 with exactly
  `{"error": "unknown_migration"}`. A plan that has not yet been committed
  returns status 409 with exactly `{"error": "migration_not_committed"}`. A
  rolled-back plan returns status 409 with exactly
  `{"error": "migration_rolled_back"}`. A plan with more than one
  outstanding pending continuation, a plan with none whose settled member's
  recorded account does not match `account_id`, or a continuation that
  cannot be resolved to its authoritative client and that client's current
  registered callback, returns status 403 with exactly
  `{"error": "invalid_continuation"}`. A resolved continuation whose pending
  authorization has expired returns status 403 with exactly
  `{"error": "invalid_authorization"}`. Wrong credentials return status 403
  with exactly `{"error": "invalid_credentials"}`.
- Every other `POST` path returns status 404 with exactly
  `{"error": "not_found"}`.

Imported login continuations keep an opaque recovery locator through
`oauthsvc.resume`. `encode_continuation_locator` stores it, and
`recover_client_and_callback` resolves one client and that client's registered
callback after restart. The completion path must use both returned values for
the authorization code and redirect.

The service validates an exact registered redirect URI before login begins. It
binds the client, callback, and pending authorization together through account
selection and process restart. Caller state is returned unchanged to the
client. Caller state is response data, not a server-side login identity.

The importer accepts pending logins from an older client store. A legacy
continuation handle is local to one client, so different clients may use the
same handle text. Import converts that handle into the native resume-reference
model and returns exactly `client_id`, `login_id`, and `resume_reference` as
JSON. The canonical resume reference retains its client id. Import also stores
an opaque migration recovery locator in a durable lookup for restart recovery.
Native and imported resume references remain bound to one client and pending
authorization.

Authorization codes are short-lived and single-use. Token exchange must use the
same client that received the code. One client's login continuation must not
complete another client's pending authorization.

Pending authorizations are themselves short-lived: each carries its own
expiry, and `/login/complete` rejects an authorization that has expired the
same way it rejects one that was already completed.

A client migration plan durably records a batch move of pending
authorizations onto a destination client. Each plan's pending-authorization
inventory row stores that pending authorization's account (once known),
owning client, exact callback, state, expiry, status, and an opaque migration
handle. The handle and the owning client are encoded together through
`oauthsvc.resume.encode_continuation_locator`, the same locator mechanism
imported logins use. A pending authorization's own `client_id` is never
rewritten by a migration; the owning client stays authoritative on the
pending row itself, separate from the plan's destination client, so source
and destination client registrations always stay distinct.

A migration dry run answers "would this batch succeed?" without creating a
plan: it compares each referenced pending authorization's exact, stored
callback against the destination client's exact, registered callback, and
checks whether that pending authorization already belongs to an existing
migration plan. It rejects outright, before comparing anything, if the
destination client itself is not registered. It never marks a pending
authorization completed and never rewrites its owning client, so running the
same dry run repeatedly against unchanged state always returns the same
report. Its report carries only identifiers and registered callback URIs —
never a password, an authorization code, an access token, or an opaque
migration or continuation handle or locator.

A migration plan's commit is atomic per member: committing cuts each
pending authorization in the plan over to the destination client as its own
durable checkpoint, so a pending row's authoritative `client_id` is
preserved until that one member's checkpoint completes, never before. If
the process restarts, or a caller repeats the commit mid-batch, every
checkpoint that already completed is left alone and only the remaining
members are cut over — committing the same plan twice, or resuming after a
crash partway through a large batch, is always safe and never re-applies a
finished checkpoint. Once every member has a completed checkpoint, the plan
itself is marked committed; committing it again after that is a no-op that
returns the same `"committed"` status.

Rolling back a migration plan (`oauthsvc.service.rollback_client_migration`)
reverts every member whose checkpoint had already completed back to its
original owning client, each as its own atomic step, and marks every
member — cut over or not — rolled back, so a rolled-back plan can never be
committed again. Rolling back an already rolled-back plan is a no-op.

Resuming a committed migration plan's one outstanding continuation
(`oauthsvc.service.resume_client_migration`) re-resolves that continuation's
authoritative client and callback through `recover_client_and_callback`,
using the client's *current* registered callback (`Store.get_callback`)
rather than the callback snapshotted on the migration's pending-authorization
inventory row — so a callback rotated after the plan was created is still
honored. It authenticates the account before issuing a short-lived,
single-use authorization code bound to the resolved client, and records that
account on the migration's inventory row once it becomes known, which is the
"account (once known)" field described above. Because the request carries
only `account_id` and `password` — no `login_id` — resolving which
continuation to resume depends on the plan having exactly one outstanding
pending continuation, *or* on the plan having none while exactly one member
already carries the requesting `account_id` from an earlier, successful
resume. That second case is what makes the route idempotent: calling it
again with the same account and correct password after it already succeeded
re-authenticates and issues a fresh code rather than failing, since the
original code is short-lived, single-use, and may simply be lost. A retry
from any other account cannot be resolved either way and is rejected.

`python -m oauthsvc.cli migration-metrics` prints pure aggregate counts for
one migration plan, scoped entirely to that `migration_id`: exactly
`migration_id`, `destination_client_id`, `status`, `member_count`,
`cutover_pending_count`, `cutover_committed_count`,
`cutover_rolled_back_count`, `continuation_pending_count`, and
`continuation_completed_count`. Unlike `migration-status` and
`migration-inspect`, it has no per-member list and no `--limit` — its
response size never grows with the plan's membership, so it is bounded by
construction rather than by a caller-chosen cap. The three `cutover_*`
counts always sum to `member_count`, and the two `continuation_*` counts
(from the same live join `migration-inspect` uses, not the migration
inventory row's own frozen, always-`"pending"` `status` column) also always
sum to `member_count`. Like every other migration view, it never includes a
password, authorization code, access token, or opaque migration/continuation
handle or locator.

`python -m oauthsvc.cli migration-status` prints a bounded view of one
migration plan: exactly `migration_id`, `destination_client_id`, `status`
(`"pending"`, `"committed"`, or `"rolled_back"`), `member_count` (the
plan's true total membership), and `members` — at most `--limit` entries
(default 50), in stable creation order, each with exactly `login_id`,
`owning_client_id`, and `cutover_status`. `member_count` always reflects
the true total even when `members` is capped below it. Like a migration
dry run, this status view never includes a password, code, token, or
opaque migration/continuation handle or locator.

`python -m oauthsvc.cli migration-inspect` prints a redacted, bounded
inspection of one migration plan, with every lookup scoped to that single
`migration_id`: exactly `migration_id`, `destination_client_id`, `status`,
`member_count` (the plan's true total membership), `pending_continuation_count`
(the true total, across the whole plan, of members whose underlying login
has not yet completed — independent of each member's own cutover progress),
and `members` — at most
`--limit` entries (default 50), in stable creation order, each with exactly
`login_id`, `owning_client_id`, `callback`, `continuation_status`
(`"pending"` or `"completed"`), and `cutover_status`. Each member's
`callback` has its query component stripped before it is returned. Like a
migration dry run or status view, this inspection never includes a
password, authorization code, access token, or opaque migration/
continuation handle or locator.

**Client migration lifecycle, end to end.** A client migration plan moves
through five stages, in order, each documented in detail above:

1. **Planning** — `POST /oauth/client-migrations/dry-run` reports whether a
   batch of pending authorizations would migrate cleanly onto a destination
   client, without creating a plan or moving anything.
2. **Validation / commit** — `POST /oauth/client-migrations` creates the
   plan, then `POST /oauth/client-migrations/{migration_id}/validate`
   atomically cuts every member over to the destination client, one durable
   checkpoint at a time; both are idempotent to repeat calls and safe to
   resume after a restart.
3. **Continuation resume** —
   `POST /oauth/client-migrations/{migration_id}/resume` recovers a
   committed plan's one outstanding pending continuation through
   `recover_client_and_callback`, using the destination client's current
   registered callback; it, too, is idempotent for the account that already
   resumed it.
4. **Rollback** — `oauthsvc.service.rollback_client_migration` reverts a
   plan's committed members back to their original owning client and marks
   the whole plan rolled back, permanently, before or after commit.

Bounded, redacted views are available at every stage without touching plan
state: `migration-status`, `migration-inspect`, and `migration-metrics`
(CLI) each report on one plan, scoped entirely to its `migration_id`, and
none of them ever returns a password, authorization code, access token, or
opaque migration/continuation handle or locator.

The initial scaffold contains only this contract. Build the parser, account and
client stores, legacy importer, durable login state, authorization-code flow,
loopback HTTP service, and tests.
