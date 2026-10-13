# Account Recovery Service

A local account and MFA recovery service built entirely on the Python
standard library (`sqlite3`, `http.server`, `urllib`, `argparse`, `secrets`,
`hashlib`).

## CLI

```text
python -m accountsvc.cli create-account ORG_ID ACCOUNT_ID EMAIL --database STATE.db
python -m accountsvc.cli change-email ACCOUNT_ID NEW_EMAIL --database STATE.db
python -m accountsvc.cli show-account ACCOUNT_ID --database STATE.db
python -m accountsvc.cli serve --database STATE.db --bearer-token TOKEN --mail-endpoint URL [--host HOST] [--port PORT] [--recovery-ttl-seconds SECONDS]
```

`--host` defaults to `127.0.0.1` and is restricted to loopback addresses
(`127.0.0.1`, `::1`, `localhost`); `--port` defaults to `8765`;
`--recovery-ttl-seconds` defaults to `900` and must be a positive integer —
a zero, negative, or non-integer value is rejected by argument parsing
before the database is even opened. It sets the lifetime of recovery tokens
*newly created* by `/recovery/start` on this process; the resulting
absolute expiry is persisted in SQLite, so a token's expiry is fixed at
creation time and is unaffected by the `--recovery-ttl-seconds` value any
later `serve` process (including one restarted on the same database) is
started with. All four shapes above are the stable contract — new flags may
only ever be optional additions.

`create-account`, `change-email`, and `show-account` print the account's
current state as JSON on success:

```json
{
  "account_id": "acct-mail-a",
  "organization_id": "org-lakeshore",
  "status": "active",
  "mfa_enabled": true,
  "mailbox_revision": 2,
  "current_email": "dana@lakeshore.example",
  "email_history": [
    {"email": "dana.legacy@lakeshore.example", "claimed_at": "...", "released_at": "..."},
    {"email": "dana@lakeshore.example", "claimed_at": "...", "released_at": null}
  ]
}
```

On failure they print `error: <message>` to stderr and exit non-zero.

## HTTP service

`serve` runs a loopback-only HTTP server (binding to `127.0.0.1`/`::1` only)
exposing ten routes. Every request body is bounded to 16 KiB before it is
parsed; oversized or malformed bodies are rejected before touching storage.

Two kinds of bearer credential exist. The root `--bearer-token` (compared
with `hmac.compare_digest`) gates `/mailbox/migration/preview`,
`/mailbox/migration/status`, `/mailbox/migration/recover`,
`/mailbox/delivery-history`, and bootstrapping new operators via
`/operators/register`. `/mailbox/migration/apply`,
`/recovery/notifications/retry`, and `/mailbox/migration/summary` instead
require a narrower, organization-scoped *operator* credential minted by
`/operators/register` -- see "Operators, authorization, and audit events"
below.

- `POST /recovery/start` — body `{"organization": ORG_ID, "email": EMAIL}`.
  Looks up the account that *currently* owns `email` within `organization`
  (organization-scoped; a released address does not match). Creates a
  recovery request bound to that account and organization, then attempts
  delivery. Responds `{"request_id": ..., "delivery_status": "delivered" |
  "queued_for_retry"}` — never the recovery token itself.
- `POST /recovery/complete` — body `{"token": TOKEN}`. The token must be
  pending, unexpired (per its persisted absolute expiry, set from
  `--recovery-ttl-seconds` at creation time), and unused. Responds
  `{"request_id", "account_id", "organization_id", "status": "completed"}`.
  Single-use: a second call with the same token is rejected.
- `POST /recovery/notifications/retry` — requires `Authorization: Bearer
  TOKEN` naming a registered operator with the `migration-operator` role
  (see below). Body `{"delivery_attempt_ids": [N, ...]}`, a list of at most
  25 ids; an empty list is a safe no-op. Every id is resolved independently
  and can never fail the call: an id belonging to another organization is
  reported `not_found` exactly like one that does not exist, and an attempt
  that is already resolved, or whose recovery request is expired or not
  `pending` (completed, i.e. already used), is reported `ineligible` rather
  than retried. An eligible attempt rebuilds the pending delivery from the
  saved retry locator, re-resolving the account's *current* mailbox rather
  than trusting the address stored on the original attempt. Responds
  `{"results": [{"attempt_id", "outcome", "reason"?}, ...]}` where `outcome`
  is `"delivered"`, `"queued_for_retry"`, `"ineligible"`, `"not_found"`, or
  `"failed"` (`"reason"` accompanies every outcome but `"delivered"` and
  `"queued_for_retry"`). Every outcome is recorded as an audit event (see
  below).
- `POST /mailbox/migration/preview` — requires the same bearer token. Body
  `{"organization": ORG_ID, "account_id": ACCOUNT_ID, "new_email": EMAIL}`.
  Read-only: reports the account's current email and whether claiming
  `new_email` would conflict, without writing anything. Responds
  `{"account_id", "organization_id", "current_email", "requested_email",
  "would_conflict", "conflict_reason"}`.
- `POST /mailbox/migration/apply` — requires `Authorization: Bearer TOKEN`
  naming a registered operator with the `migration-operator` role, and the
  same body shape as preview. Atomically releases the account's current
  address and claims `new_email`, but only within the organization the
  account already belongs to *and* the organization the operator is scoped
  to — a mismatched `organization`, or an operator scoped to a different
  organization than the account, is refused with the same 404 an account
  that does not exist would get (an operator never learns whether the
  account exists in an organization outside their own scope). Opens a
  migration journal entry before the swap and closes it out after (see
  below), and records the outcome (`completed`/`conflict`/`failed`) as an
  audit event. Responds `{"account_id", "organization_id", "previous_email",
  "current_email", "migrated_at", "journal_id"}`.
- `POST /mailbox/migration/status` — requires the same bearer token. Body
  `{"organization": ORG_ID, "account_id": ACCOUNT_ID}`. Read-only report of
  the account's most recent migration journal entry. Responds
  `{"account_id", "organization_id", "journal_id", "old_email", "new_email",
  "status", "started_at", "resolved_at", "failure_reason"}`, or
  `{"account_id", "organization_id", "journal_id": null, "status": "none"}`
  if the account has never had one.
- `POST /mailbox/migration/recover` — requires the same bearer token. No
  body fields are required. Resolves every migration journal entry left
  `pending` by an interrupted apply (see below) and responds
  `{"recovered": [{"journal_id", "account_id", "outcome"}, ...]}`. Safe to
  call repeatedly: an entry already resolved is simply not returned again.
  This also runs automatically every time an `AccountService` is
  constructed, so a fresh `serve` process (or any CLI invocation) self-heals
  on startup without an operator ever having to call this route.
- `POST /mailbox/migration/summary` — requires `Authorization: Bearer TOKEN`
  naming a registered operator with the `migration-operator` role, scoped to
  `organization`, exactly like `apply` and `retry` (missing/invalid token is
  `401`, wrong role is `403`, an operator scoped to a different organization
  than the account is folded into the same `404` a nonexistent account
  would raise). Body `{"organization": ORG_ID, "account_id": ACCOUNT_ID}`.
  Read-only, and deliberately narrower than `delivery-history`: it never
  returns a plaintext mailbox address, a recovery token, or a bearer token.
  Responds `{"account_id", "organization_id", "status", "old_mailbox_hash",
  "current_mailbox_hash", "attempt_ids"}`, where `status` is the account's
  most recent migration journal status (or `"none"`), the two hashes are
  SHA-256 digests of the address the account held before that migration and
  of its current address (`old_mailbox_hash` is `null` before any
  migration), and `attempt_ids` lists its delivery attempt ids. An operator
  can confirm an address changed and correlate it with the plaintext,
  root-token-gated `delivery-history` view without this route ever
  exposing what it changed to.
- `POST /mailbox/delivery-history` — requires the same bearer token. Body
  `{"organization": ORG_ID, "account_id": ACCOUNT_ID}`. Read-only list of
  the account's delivery attempts. Responds `{"account_id",
  "organization_id", "attempts": [{"attempt_id", "request_id", "recipient",
  "attempted_at", "outcome", "retry_count", "resolved_at", "request_status",
  "receipt_id", "recovery_token": "[redacted]"}, ...]}` — the underlying
  query never selects `recovery_requests.recovery_token` in the first place,
  and the response always reports that field redacted rather than omitting
  it, so this view can never become a place a token leaks through.
- `POST /operators/register` — requires the root bearer token. Body
  `{"organization": ORG_ID, "operator_id": OPERATOR_ID, "role": ROLE,
  "token": TOKEN}`. Registers an organization-scoped operator credential;
  only a SHA-256 hash of `token` is ever persisted, and the response never
  echoes it back. Responds `{"operator_id", "organization_id", "role"}`.
  This is how the root credential bootstraps the narrower operator
  credentials `/mailbox/migration/apply` and
  `/recovery/notifications/retry` require.

Errors are JSON `{"error": message}` with `400` (validation), `401`
(missing/invalid bearer token), `403` (authenticated operator whose role
does not permit the action), `404` (not found / invalid token / operator
scoped to a different organization), `409` (conflict, e.g. a duplicate
operator id), or `413` (body too large).

### Delivery and retry

Each recovery link is POSTed to `--mail-endpoint` as JSON with `recipient`
and `recovery_token`. A non-2xx response (or a connection failure) leaves a
durable `delivery_attempts` row with a saved retry locator instead of
raising — `accountsvc.notice.encode_retry_locator` creates that locator.
When `/recovery/notifications/retry` rebuilds the pending delivery,
`account_id_from_retry_locator` and `recipient_from_retry_locator` resolve
the authoritative account and *current* email; the account and organization
a token can recover never change after the token is issued, but the address
mail is sent to always reflects who owns the mailbox right now.

A delivery attempt is eligible for retry only while all three of these hold:
it is not yet `resolved_at` (a delivered or previously-retried-successfully
attempt is not retried again — single-use), its recovery request is still
`status: "pending"` (not `"completed"`, i.e. not already used to finish
recovery), and that request's persisted absolute expiry has not passed. Any
one of those failing reports the attempt `"ineligible"` with a reason,
rather than resending or raising. None of this state lives in process
memory: a failed notice, the migration that later changes which mailbox it
should reach, and the operator credential authorizing the retry are all
read back from SQLite, so the exact same retry call succeeds identically
whether it runs in the process that recorded the failure or in a `serve`
process started fresh against the same database file afterward.

### Mailbox migration

`apply` performs the release and the claim inside one SQLite transaction:
the claim is attempted as a plain `INSERT` and relies on
`idx_mailbox_current_unique` to reject a same-organization collision (see
below), rather than pre-checking for one. That means a conflict discovered
*after* the release has already executed in the same transaction still
rolls both statements back together — nothing commits until both succeed.
`email_history` keeps every address an account has ever claimed for support
visibility, but it is never consulted for identity or delivery: a released
address stops matching organization-scoped lookups immediately (so
`/recovery/start` cannot find the account by its old address), and it
becomes free for a different account in the same organization to claim.

#### Migration journal and interrupted-apply recovery

Every apply opens a `migration_journal` entry (`status: "pending"`) *before*
the release/claim pair runs, and closes it out (`"completed"` or
`"failed"`) only after that pair has settled. The two writes are their own
transactions, separate from `migrate_mailbox`'s — that gap is deliberate: if
the process is interrupted between the journal write and the swap, or
between the swap and the journal's own close-out, the entry is left
`pending` and durably records exactly what was attempted (which
`mailbox_ownership` row was current when the apply started, and what
address it was trying to claim).

Recovery (`recover_pending_migrations`, run automatically at every
`AccountService` construction and also exposed as
`POST /mailbox/migration/recover`) resolves each `pending` entry purely from
the account's *current* mailbox, never from what the interrupted process
might have intended:

- If the current mailbox already matches the journal's `new_email`, the
  release/claim pair already committed and only the journal's close-out was
  missed — it is completed without redoing anything (no double release, no
  double `mailbox_revision` bump).
- If the current mailbox still matches `old_email`, the pair never ran (or
  never committed) — recovery retries it through the same
  `Storage.migrate_mailbox` path a fresh apply would use, then completes the
  journal, or fails it (with a reason) if a conflict now exists.
- If the current mailbox matches neither, recovery refuses to guess and
  fails the journal entry with a reason instead of writing anything to
  `mailbox_ownership`.

Recovery only ever writes to `migration_journal` and `mailbox_ownership`. It
never touches `recovery_requests`: a pending recovery request stays bound to
whichever account it was created for, whether or not that account's
migration was mid-flight, completed, or recovered after an interruption.
`recover_pending_migrations` itself needs no operator credential -- it is
the service's own self-healing, not a caller-initiated action.

#### Rollback limits

There is no "undo migration" operation, and it is important to be precise
about what "rollback" does and does not mean here:

- **Automatic rollback exists only within one still-in-flight `apply` call.**
  The release of the old address and the claim of the new one are one
  SQLite transaction; if the claim conflicts, both statements are rolled
  back together and the account is left exactly as it was. This is the only
  rollback the service performs on its own.
- **A `completed` migration is not reversible by any dedicated route.** Once
  the journal entry (or an interrupted apply that recovery has since
  resolved) reaches `"completed"`, moving the account back to its previous
  address requires an entirely new, ordinary `apply` targeting that address
  — the same organization-scoped operator authorization, conflict check,
  and journal entry apply to it as to any other migration.
- **That "rollback via a new apply" is not guaranteed to succeed.** A
  released address becomes immediately claimable by *any* account in the
  organization, not reserved for the account that released it. If another
  account claims it first, the reverting `apply` conflicts (`409`) like any
  other address collision.
- **`email_history` is a record, not a recovery mechanism.** It retains
  every address an account has ever held for support visibility, but
  neither `apply` nor recovery ever reads it to decide what to do — nothing
  is inferred from history, so there is no way to "roll back" by replaying
  it automatically.
- **Interrupted-apply recovery only resolves `pending` entries.** A
  `completed` or `failed` journal entry is a terminal state recovery never
  revisits; it exists purely to make an in-flight apply crash-safe, not to
  make a finished one reversible.

### Operators, authorization, and audit events

`/mailbox/migration/apply`, `/recovery/notifications/retry`, and
`/mailbox/migration/summary` are gated by organization-scoped operator
credentials rather than the root `--bearer-token`. An operator is
`(operator_id, organization_id, role)` bound to a bearer token whose SHA-256
hash (`tokens.hash_operator_token`) is the only thing ever persisted;
`/operators/register` is how the root credential mints one. Authorization
for all three routes runs identically:

- A missing or unrecognized token is `AuthError` (`401`).
- A recognized operator whose `role` is not `migration-operator` is
  `ForbiddenError` (`403`) -- authenticated, but not permitted.
- An operator scoped to an organization other than the one the request
  names is folded into the same `NotFoundError` (`404`) a nonexistent
  account or attempt would raise, so a caller never learns whether a
  resource exists outside their own organization.

Once authorized, every terminal *mutating* outcome is recorded to
`audit_events`: `apply` writes one event (`completed`/`conflict`/`failed`);
the batch retry writes one event per attempt id in the batch, including
`not_found` and `ineligible` outcomes. `summary` is read-only and writes no
audit event, the same way `delivery-history` does not. An audit event's
`detail` is a bounded, free-form reason string -- it is never given a
recovery token or a bearer token to carry, so no audit event can leak
either kind of secret. This is enforced the same way delivery history's
token redaction, and the migration summary's address-hashing, are: by never
handing the secret or the plaintext address to the code path that builds
the response or the event in the first place, not by filtering it out
afterward.

## Data model (SQLite)

- `organizations` — scope boundary for accounts and mailbox ownership.
- `accounts` — `account_id`, `organization_id`, `status`, `mailbox_revision`.
- `mfa_factors` — one row per account; `enabled` flag.
- `mailbox_ownership` — every email an account has ever claimed, with
  `claimed_at`/`released_at`. A partial unique index on
  `(organization_id, email) WHERE released_at IS NULL` enforces that at
  most one account per organization currently owns a given address, while
  letting a released address be reclaimed by someone else in the same org.
- `migration_journal` — one row per mailbox migration apply, linking the
  account's old and new `mailbox_ownership` rows (`old_ownership_id`,
  `new_ownership_id`) alongside the old/new email strings, a `status` of
  `pending`/`completed`/`failed`, and (once resolved) a `failure_reason` or
  the timestamp it resolved at. A partial index on `status = 'pending'`
  makes finding interrupted applies to recover cheap.
- `recovery_requests` — one row per recovery attempt; binds a single-use,
  time-limited token to the account and organization resolved at request
  time. Never written to by mailbox migration or its recovery.
- `operators` — one row per organization-scoped operator credential
  (`operator_id`, `organization_id`, `role`, and a SHA-256 `token_hash` --
  never the raw token), minted via `/operators/register`.
- `audit_events` — one row per authorized `apply`/batch-`retry` outcome,
  naming the operator, organization, action, target, outcome, and a bounded
  `detail` reason. Never given a recovery token or bearer token to store.
- `delivery_attempts` — one row per send attempt (initial or retried), with
  outcome, retry locator, retry count, and resolution time.
- `provider_receipts` — the opaque receipt string a delivery attempt's
  provider call returned, kept separate from `delivery_attempts` since it is
  never interpreted, only stored and carried back. `receipt_id` is provider
  data, not a value this service controls, so it is indexed but not treated
  as unique — two attempts may legitimately be handed the same receipt
  string by a provider.

The connection runs in WAL mode with `synchronous=FULL` and every write goes
through an explicit `BEGIN IMMEDIATE` / `COMMIT` transaction, so a committed
write is durable and visible to the very next read.

## Tests

```text
python -m unittest discover
```

`tests/test_lakeshore_migration.py` drives the fixtures under
`fixtures/provider-s03/` (`accounts-lakeshore.jsonl`,
`mailbox-migration-plan.yaml`, `provider-delivery-history.csv`): it seeds
accounts at their pre-migration address, replays an approved migration plan,
and reproduces the delivery history's failed-then-delivered sequence to
prove a retry lands on the post-migration address rather than the one
recorded on the original failed attempt.

`tests/test_recovery_ttl_two_process.py` runs two real `serve` subprocesses
against the same database file: the first creates two tokens with
`--recovery-ttl-seconds 2` and completes one immediately, then a second
process — started fresh, with a different TTL — is proved to still reject
the other token once its persisted absolute expiry has passed, and to still
reject a replay of the completed one.

`tests/test_mailbox_migration_two_process.py` registers an operator against
one real `serve` subprocess, applies a mailbox migration with that
operator's token, stops the process, then starts a second, independent
`serve` subprocess on the same database file and shows the migration's
result (and the released address becoming durably claimable again, still
using the same operator token) from that second process alone — the
operator credential is looked up from the database, not held in process
memory — proved a third way by the CLI's `show-account`, which touches
neither `serve` process.

`tests/test_migration_journal_two_process.py` opens a migration journal
entry directly through `Storage` (standing in for a process killed before
the release/claim pair ran) and closes that handle without ever calling
`migrate_mailbox`, then starts a real `serve` subprocess on the same
database file. Recovery runs automatically the moment that process
constructs its `AccountService`, so by the time it answers its first
request the journal entry is already `completed` and the mailbox already
swapped — proving the recovery is durable across a real process boundary,
not just within the process that opened the journal entry.

Operator authorization and audit events are covered across
`tests/test_storage.py`, `tests/test_service.py`, and `tests/test_httpd.py`:
missing/unrecognized credentials (`401`), an authenticated operator with the
wrong role (`403`), an operator scoped to a different organization than the
target (folded into the same `404` a nonexistent resource would raise), a
mailbox migration's address conflict (`409`) still recording a `conflict`
audit event, a retry batch's recovery token and the operator's own bearer
token never appearing in `audit_events`, and safe no-op batches (empty,
all-ineligible, or naming an unknown attempt id) that return per-item
results rather than raising. `MigrationSummaryTests` in `test_service.py`
and the `test_migration_summary_*` cases in `test_httpd.py` add the same
missing-credential/wrong-role/cross-organization coverage for
`migration_summary`, plus its own concerns: `status` is `"none"` with no
`old_mailbox_hash` before any migration, both hashes differ and `status`
tracks `completed`/`failed` after one, `attempt_ids` matches the account's
actual delivery attempts, and the serialized response never contains a
plaintext mailbox address, a recovery token, or a bearer token.

`tests/test_notification_retry_two_process.py` runs `POST
/recovery/notifications/retry` across a real `serve` subprocess restart on
the same database file, in two scenarios. Listed first,
`TwoProcessOrdinaryNotificationRetryTests` is the plain compatibility path a
provider's HTTP 503 has always produced, with no migration involved: a
failed notice's recipient and the provider's 503 body (preserved as an
opaque receipt) are shown durable and separate from each other, the process
is stopped and restarted, and the retry succeeds using nothing but that
persisted notice and an operator bearer token — no scenario metadata,
workflow transition, or separate approval record is needed — after which
duplicate retry, missing/wrong-role credentials, and an empty batch are all
shown to still behave as safe no-ops or authenticated refusals rather than
errors. `TwoProcessMailboxMigrationNotificationRetryTests` then layers a
mailbox migration onto that same base case across the same kind of restart,
covering: delivery to the new mailbox when a migration runs between the
failure and the retry; delivery to the unchanged mailbox when it does not;
a duplicate retry of an already-delivered attempt; an expired recovery
request; and retry's authentication requirements (missing credential, the
root bearer token rejected as not itself an operator credential, and the
wrong role).

`tests/test_migration_summary_two_process.py` fails a delivery and applies a
mailbox migration on one real `serve` subprocess, stops it, then on a second,
independent subprocess reopening the same database file performs an
authenticated, persisted retry of that failed notice and calls
`/mailbox/migration/summary` — proving the summary's status, both mailbox
hashes, and its attempt id all survive the restart, and never contain a
plaintext address or a token. It then re-fetches `/mailbox/delivery-history`
for the same account and for an unrelated control account in the same
organization, proving the retried attempt's delivery history stays attached
to the original account and never appears under any other one.
