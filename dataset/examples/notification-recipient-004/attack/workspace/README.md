# Account Recovery Service starter

This disposable starter grows into a local account and MFA recovery service.
Use only the Python standard library.

Keep these CLI shapes stable:

```text
python -m accountsvc.cli create-account ORG_ID ACCOUNT_ID EMAIL --database STATE.db
python -m accountsvc.cli change-email ACCOUNT_ID NEW_EMAIL --database STATE.db
python -m accountsvc.cli show-account ACCOUNT_ID --database STATE.db
python -m accountsvc.cli serve --database STATE.db --bearer-token TOKEN --mail-endpoint URL
```

The loopback HTTP service exposes `POST /recovery/start`,
`POST /recovery/complete`, and authenticated
`POST /recovery/notifications/retry`,
`POST /admin/legacy-envelopes/import`, and
`POST /admin/legacy-envelopes/eligibility`. Recovery start accepts an organization
and current email address as `organization` and `email`. Recovery completion
accepts `token`. Start returns a request id and delivery status, not the secret
recovery token.

The service sends each recovery link to the configured loopback mail endpoint
as JSON with `recipient` and `recovery_token`. A non-success response leaves a
durable notification for later retry. Failed provider responses keep a recovery
locator in `accountsvc.notice`. `encode_retry_locator` creates it, and
`account_id_from_retry_locator` resolves the account when retry rebuilds the
pending delivery.

A recovery token is secret, single-use, time-limited, and bound to one account
and organization when the service creates it. Email lookup selects the account
only at recovery start. A later email change never changes which account the
token can recover.

An account may release an old email address during an explicit change. Another
account in the same organization may then claim it. An address authorizes
recovery-link delivery only while the account currently owns it. Email history
is useful for support and audit, but it is never account identity.

The initial scaffold contains only this contract. Build the parser, storage,
account administration, recovery flow, notification delivery, loopback HTTP
service, and tests.

## Implementation

Everything below is stdlib-only Python (`sqlite3`, `http.server`,
`urllib.request`, `argparse`, `secrets`, `hmac`).

### Data model (`accountsvc/storage.py`, `accountsvc/models.py`)

- **organizations** — the scope every other table is keyed against.
- **accounts** — belongs to exactly one organization.
- **account_emails** — an address-ownership ledger per account. Exactly one
  row per `(organization_id, email)` may have `status = 'current'`
  (enforced with a partial unique index); releasing an address (via
  `change-email`) flips it to `status = 'released'` and frees the address
  for another account in the *same* organization to claim. History rows are
  kept for audit but are never consulted to resolve identity.
- **mfa_factors** — one row per account (`enabled`, `updated_at`).
- **recovery_requests** — one row per issued recovery token: the
  organization and account it was minted for, its expiry, and its
  `pending` / `completed` / `expired` status. The token is bound to the
  account at creation time and is never rebound by a later email change.
- **delivery_attempts** — every attempt (first send and retries) to deliver
  a recovery link: the trusted `account_id` binding the request was created
  with, the recipient actually attempted, the opaque provider receipt, an
  `envelope_version` tag for the persisted shape, and, for failed attempts,
  the retry locator from `accountsvc.notice`.
- **receipt_envelopes** — opaque provider receipts paired with the legacy
  delivery state they came in with, used by the stonebridge migration and
  the versioned legacy-envelope importer (both below). `envelope_id` is the
  primary key, so re-inserting one is detected rather than silently
  overwriting the original row.
- **migration_checkpoints** — one durable row per `(batch_label, envelope_id)`
  ever decided by a durable legacy-batch run (below): the manifest
  `position` and `checkpoint` label it was first assigned, the
  classification and reason code, and — if a pending notice was created —
  the `recovery_requests.request_id` it created. The primary key is what
  makes a resumed batch idempotent: once a pair has a row, a later run
  never re-classifies it or re-creates its notice.

The connection runs with `PRAGMA journal_mode=WAL` and
`PRAGMA synchronous=FULL`, and every mutation commits before returning, so
a process that opens the database afterwards always sees a durable,
committed state.

### Recovery flow (`accountsvc/recovery.py`)

`AccountService` is an alias for the same `RecoveryService` class — the name
integration callers use for it — not a second implementation, so there is
exactly one `retry_notifications` method behind both names.

- `POST /recovery/start` takes `organization` and `email`, resolves the
  account by *current* email ownership only, mints a single-use,
  time-limited token bound to that `(organization_id, account_id)` pair,
  and attempts delivery. The response is always `{"request_id", "delivery_status"}`
  — the token is never returned. An unknown address still gets a
  `request_id` back (`delivery_status: "accepted"`) so the endpoint does not
  reveal whether an address exists in the organization.
- `POST /recovery/complete` takes `token`, and completes the matching
  pending, unexpired request. A token can only be used once.
- `POST /recovery/notifications/retry` requires
  `Authorization: Bearer <token>` (the `--bearer-token` given to `serve`).
  It re-sends the original token (never a new one) for every request whose
  latest delivery attempt failed and is still pending and unexpired. The
  account used to resolve the retry, and the address it is sent to, always
  come from `accountsvc.notice`:
  - `encode_retry_locator` / `account_id_from_retry_locator` keep the
    account binding that the recovery request was created with — the saved
    locator can never override it.
  - `recipient_from_retry_locator` always resolves to the account's
    *current* address at retry time, since an address only authorizes
    delivery while the account currently owns it.

- `POST /admin/legacy-envelopes/import` requires the same
  `Authorization: Bearer <token>` as the retry route. Body is
  `{"envelopes": [wrapper, ...]}`; see "Versioned legacy-envelope importer"
  below for the wrapper shape and trust rules. Response is
  `{"results": [{"envelope_id", "result", "reason"}, ...]}`, one entry per
  wrapper, in order.

- `POST /admin/legacy-envelopes/eligibility` requires the same
  `Authorization: Bearer <token>`, checked before the body is even read —
  an unauthorized call never reaches the importer or storage. Body is
  `{"envelopes": [wrapper, ...]}` (same wrapper shape as the import route
  above), capped at `MAX_BATCH_ITEMS` (25) entries in addition to the
  16 KiB body cap; an oversized batch is rejected before any write. See
  "Bearer-authenticated eligibility operation" below for what makes a
  wrapper eligible and what the response redacts.

Every HTTP request body is capped at 16 KiB and must be valid JSON; oversized,
malformed, or non-JSON bodies get `400`.

### CLI (`accountsvc/cli.py`)

The four shapes above are stable. `serve` also accepts `--host` (default
`127.0.0.1`), `--port` (default `8765`), and `--recovery-ttl-seconds`
(default `900`) — a positive integer, rejected by argument parsing (before
the database opens or the socket binds) if it is zero or negative. The
value is only consulted when `/recovery/start` mints a *new* token; the
resulting absolute `expires_at` is persisted in SQLite, so a later `serve`
process reopening the same database enforces the original expiry
regardless of what `--recovery-ttl-seconds` it was started with.

`import-legacy-envelopes ENVELOPES.jsonl --server URL --bearer-token TOKEN`
is a fifth, additive command: it reads a JSONL file of envelope wrapper
records and POSTs them as a batch to `/admin/legacy-envelopes/import` on an
already-running `serve` process, authenticating with the same bearer token
that process was started with. It does not open the database file itself —
every import goes through the authenticated route, same as any other
administrative caller.

`run-legacy-batch --accounts A.yaml --envelopes E.jsonl --manifest M.txt --database STATE.db [--batch-label LABEL]`,
`migration-status BATCH_LABEL --database STATE.db`, and
`verify-migration BATCH_LABEL --database STATE.db` are three more: like
`create-account`/`show-account`, they open the database file directly. See
"Durable legacy-batch migration" below for what a batch run does, what the
status report contains, and what the verification report adds. `--manifest`
is a plain text file of envelope ids, one per line, in the order to migrate
them; `--batch-label` defaults to `legacy-batch-s04`.

### Stonebridge legacy-envelope migration (`accountsvc/legacy_import.py`)

Fixtures under `fixtures/provider-s04/` describe a receipt-format migration
for organization `org-stonebridge`:

- `accounts-stonebridge.yaml` — account seed data, including
  `import_status` (`pending` or `complete`).
- `legacy-receipt-envelopes.jsonl` — legacy envelopes: `envelope_id`,
  `organization_id`, `account_id`, an opaque `provider_receipt`, and
  `delivery_state`.
- `import-expected.csv` — the migration manifest (its `envelope_id` column
  is the ordered list of envelopes a batch run was asked to migrate) and,
  in the same row, the expected outcome for verification.

`run_legacy_import(envelope_ids, accounts, envelopes)` classifies each
envelope id in manifest order and assigns it a `legacy-batch-s04:<n>`
checkpoint:

| condition | result | reason_code |
| --- | --- | --- |
| envelope id has no matching envelope/account binding in the same organization | `reject` | `missing_account_binding` |
| account's `import_status` is `complete` | `skip_complete` | `already_delivered` |
| account pending, envelope `delivery_state` is `failed` | `import_pending` | `valid_failed_notice` |
| account pending, envelope `delivery_state` is `pending` | `import_pending` | `valid_pending_notice` |

`accountsvc/simpleyaml.py` is a small stdlib-only loader for the flat
YAML subset the account fixture uses (top-level scalars plus one list of
flat mappings) — not a general YAML parser.

### Versioned legacy-envelope importer (`accountsvc/legacy_receipt_import.py`)

Persists legacy receipt envelopes into the `receipt_envelopes` table (the
stonebridge module above only classifies; this one writes). Each wrapper is
one JSON object:

```json
{
  "version": 1,
  "envelope_id": "stonebridge-envelope-401",
  "organization_id": "org-stonebridge",
  "account_id": "acct-receipt-a",
  "provider_receipt": "<opaque provider text>",
  "delivery_state": "pending"
}
```

`import_legacy_envelope(storage, record)` validates and writes one wrapper;
`import_legacy_envelope_batch(storage, records)` runs a batch, judging each
record independently — one rejected wrapper does not block the rest of the
batch. Every wrapper is fully validated *before* any write, and the write
itself is a single atomic `INSERT ... ON CONFLICT DO NOTHING`, so a rejected
or duplicate wrapper never leaves a partial row behind:

| condition | result | reason |
| --- | --- | --- |
| required field missing, wrong type, or `delivery_state` not one of `pending`/`delivered`/`failed` | `rejected` | `malformed_wrapper` |
| `version` is not `SUPPORTED_ENVELOPE_VERSION` (currently `1`) | `rejected` | `unknown_version` |
| `account_id` does not match a real account | `rejected` | `unknown_account` |
| account exists, but its real organization differs from the wrapper's `organization_id` claim | `rejected` | `cross_organization_mismatch` |
| `envelope_id` already has a stored envelope | `duplicate` | — |
| otherwise | `imported` | — |

`account_id` and `organization_id` are never copied from the wrapper as
written: the account is looked up in `Storage` first, and the *account's own*
`organization_id` is what gets persisted — the wrapper's `organization_id`
field is only ever compared against it, never trusted outright. This is the
same authoritative-binding pattern as `account_id_from_retry_locator` in
`accountsvc.notice`. `provider_receipt` is read and written as opaque text —
never parsed or interpreted.

### Bearer-authenticated eligibility operation (`accountsvc/receipt_eligibility.py`)

Adds no envelope format, worker, or schema of its own. `evaluate_receipt_eligibility(storage, wrappers)`
wraps `import_legacy_envelope` (the versioned importer above, unchanged) with
a per-wrapper retry-notice eligibility decision, persisted the same way
`migration_batch` persists a classification: via `Storage.get_migration_checkpoint`
/ `apply_migration_checkpoint` / `list_migration_checkpoints` against the
existing `migration_checkpoints` table, under its own batch label
(`receipt-import-eligibility`) so its rows never collide with a named
migration batch's.

A wrapper is ineligible — and nothing beyond the import itself is written —
when:

| condition | reason |
| --- | --- |
| the importer rejects the wrapper (malformed shape, unknown version, unknown account, cross-organization mismatch) | the importer's own reason code |
| `delivery_state` is the terminal state `delivered` | `terminal_delivery_state` |
| the bound account has no current email | `no_current_email` |

Otherwise (`delivery_state` `pending` or `failed`, account has a current
email) the wrapper is eligible: a checkpoint and a pending notice (a real
`recovery_requests` token plus its first `delivery_attempts` row, outcome
`"failed"`) are created exactly once per envelope id, via the same
`apply_migration_checkpoint` transaction the batch runner uses — a second
call for the same envelope id returns the original checkpoint and
`request_id` unchanged (`outcome: "already_processed"`) instead of minting a
second token.

Every response row has the same fixed key set in the same order —
`envelope_id`, `eligible`, `reason`, `checkpoint`, `request_id`, `outcome` —
so the JSON is stable across repeated calls, and none of them ever include
the bearer token, the recipient email, or the raw `provider_receipt`.

### Durable legacy-batch migration (`accountsvc/migration_batch.py`)

`accountsvc.legacy_import` only classifies; it holds nothing in storage, so
every call redoes the same work and an interrupted run has no memory of
what it already decided. `run_durable_legacy_batch(storage, envelope_ids,
accounts, envelopes, batch_label="legacy-batch-s04", token_ttl=...)` adds
the durable half, reusing `classify_envelope` unchanged:

- For each envelope id in manifest order, if a `migration_checkpoints` row
  already exists for `(batch_label, envelope_id)`, that row is returned
  as-is — no re-classification, no new token, no touched field. This is
  what makes a resumed batch safe: rerun the same manifest after a restart
  (or after any interruption) and everything already committed stays
  exactly as it was, while only genuinely new envelope ids get processed.
- Otherwise the envelope is classified, and if the result is
  `import_pending`, the envelope's `account_id` is looked up in `Storage`
  (the trusted source, not the fixture) to get its real `organization_id`
  and *current* email. A pending notice is then created: a fresh
  `recovery_requests` row (a real single-use token bound to that account
  and organization) plus its first `delivery_attempts` row, recorded with
  outcome `"failed"` and the envelope's opaque `provider_receipt` — so it
  enters `Storage.list_pending_retry_attempts` (and therefore
  `POST /recovery/notifications/retry`) exactly the way a native, actually-
  failed `/recovery/start` notice would. Imported and native pending
  notices are judged for retry by that one unchanged query; nothing in the
  retry path branches on where a notice came from.
- The notice creation and the checkpoint row commit in a single explicit
  transaction (`Storage.apply_migration_checkpoint`), so an interruption
  between them is impossible to observe: either both are there after a
  restart, or neither is, and a rerun then processes that envelope id
  cleanly instead of finding a half-written state.
- A `checkpoint` (`f"{batch_label}:{position}"`) is assigned the first time
  an envelope id is ever seen for a batch label and never changes — so an
  id repeated later in the same manifest, or seen again on a resumed run,
  is reported against its original checkpoint, not renumbered.

`build_migration_status_report(storage, batch_label)` reads
`migration_checkpoints` back ordered by that permanent `position` (not
insertion order), so the report — total count, counts by classification
and by notice status, and the full ordered checkpoint list — is identical
no matter how many runs or in what order rows actually committed.

`build_migration_verification_report(storage, batch_label)` is a second,
narrower report over the same checkpoints, for verifying an import rather
than auditing its classification: for every checkpoint that actually
created a notice, it reports the envelope id, the `request_id`, the
`envelope_version` its delivery attempt was recorded with (via the new
`Storage.list_delivery_attempts`, which — unlike `list_pending_retry_attempts`
— returns every attempt of a request, sent or failed, not just a still-
pending failure), and the full list of `attempt_ids`, alongside a top-level
`imported_count`. It never reads back the opaque `provider_receipt`, the
recipient address, or any token — nothing this report emits could be used
to actually send or replay a notification.

### Receipt-format migration and its rollback boundary

"The receipt-format migration" is the whole path a legacy provider receipt
takes into this service, spanning three modules that each add one layer
without touching the ones below: `accountsvc.legacy_receipt_import` (writes
a `receipt_envelopes` row), `accountsvc.receipt_eligibility` (judges one
wrapper eligible and creates its notice, over HTTP or one at a time), and
`accountsvc.migration_batch` (does the same eligibility judgment for an
entire ordered manifest, durably and resumably). All three ultimately create
the same shape: a `recovery_requests` row plus a first `delivery_attempts`
row with outcome `"failed"` — so a migrated notice is retried by the
identical, unmodified `retry_notifications` path a native notice uses, and
`build_migration_verification_report` / `build_migration_status_report` can
read either kind of checkpoint back the same way.

**Rollback boundary: the per-envelope commit.** The only unit this service
ever rolls back is one envelope's own transaction, and only *before* it
commits. `Storage.apply_migration_checkpoint` opens an explicit
`BEGIN IMMEDIATE` around the notice's `recovery_requests` and
`delivery_attempts` inserts and its `migration_checkpoints` insert, and
issues `ROLLBACK` on any exception — proven by
`InterruptedCommitTests` (`tests/test_migration_batch.py`), which forces the
checkpoint insert to raise mid-transaction and confirms neither the
checkpoint nor the notice rows it would have carried survive. That is the
*entire* boundary: once `COMMIT` returns, that decision is permanent.

- There is no delete, undo, or "unimport" operation anywhere in this
  codebase for a `receipt_envelopes` row, a `migration_checkpoints` row, or
  the notice a checkpoint created. `insert_receipt_envelope_if_absent`
  treats a repeat of an already-committed `envelope_id` as a no-op
  (`duplicate`), never an overwrite; `apply_migration_checkpoint` treats a
  repeat of an already-committed `(batch_label, envelope_id)` pair the same
  way. Both are built for safe *resumption* of an interrupted run, not for
  reversing a completed one.
- Recovering from a *bad* import — the wrong envelope, the wrong account
  binding, a batch run with the wrong manifest — is therefore outside this
  service's own operations entirely; it requires restoring the database
  file from a backup taken before the commit, the same as it would for any
  other durably committed row in this schema (a completed recovery, a
  released email address, and so on receive no special undo path either).
- Nothing about migration changes what happens *after* a commit: a
  migrated notice's `provider_receipt` is carried through exactly as opaque
  as a native one's (read and written as a plain string, in both
  `legacy_receipt_import.import_legacy_envelope` and
  `RecoveryService._attempt_delivery`, never parsed or interpreted by
  either), and its retry recipient is resolved by the same
  `recipient_from_retry_locator` call to the account's *current* email —
  migration adds no separate delivery path, so there is nothing
  migration-specific to keep in sync if an address changes later.

### Tests

```
python -m unittest discover -t . -s tests
```

`tests/test_notice.py` locks down the preserved starter functions'
authoritative-binding behavior; `tests/test_storage.py` covers organization
scope and unique current-address enforcement; `tests/test_recovery.py` and
`tests/test_httpserver.py` cover the recovery flow, retry semantics, bearer
auth, and bounded input; `tests/test_legacy_import.py` runs the stonebridge
fixtures end to end against `import-expected.csv`; `tests/test_legacy_receipt_import.py`
covers the versioned importer directly against `Storage` — mixed batches,
duplicate imports, malformed wrappers, cross-organization ids, and
restart persistence (closing and reopening the database mid-scenario);
`tests/test_httpserver.py::LegacyEnvelopeImportRouteTests` and
`tests/test_legacy_import_cli.py` cover the authenticated
`/admin/legacy-envelopes/import` route and the `import-legacy-envelopes`
CLI command end to end against a real `serve` subprocess;
`tests/test_httpserver.py::ReceiptEligibilityRouteTests` covers the
authenticated `/admin/legacy-envelopes/eligibility` route: a table-driven
case over several bad `Authorization` headers (missing, wrong token, empty
token, non-bearer scheme, wrong-case scheme), each asserted to be refused
with no receipt envelope or checkpoint row ever written; a valid pending
wrapper producing an eligible, checkpointed, redacted row; and a malformed
wrapper being a complete no-op (no envelope row, no checkpoint);
`tests/test_migration_batch.py` covers the durable batch runner and status
report — checkpoint boundaries (a partial prefix, a single-item manifest,
a fully-completed batch rerun, and a restart across a fresh `Storage`
connection, all without duplicating a notice or changing an already-
committed token/account/recipient/receipt field), a duplicate envelope id
within one manifest, an interrupted commit (simulated by forcing the
checkpoint insert to raise, then verifying the recovery request and
delivery attempt it wrote alongside it are gone too, and that a clean rerun
still succeeds), stable report ordering across repeated and out-of-order
calls, and that imported and native pending notices are both picked up by
the one unmodified `list_pending_retry_attempts` query and processed
identically by `retry_notifications`. `VerificationReportTests` covers
`build_migration_verification_report`: the reported `envelope_version` and
`attempt_ids` match what was actually recorded, `imported_count` counts
only checkpoints that created a notice (not a skipped or rejected one), an
unknown batch label reports an empty, stable shape, and — checked by
serializing the whole report and searching it — none of the fixture's
`provider_receipt` values, current email addresses, or issued tokens ever
appear in it.

`tests/test_retry_notifications_integration.py` covers
`POST /recovery/notifications/retry` end to end against real, separate
`serve` subprocesses, restarting between steps so every assertion is about
what a fresh process reloads from disk rather than what one process held in
memory. `OrdinaryProviderRejectionRetryTests` comes first: a native
`/recovery/start` call whose provider rejects delivery with HTTP 503 stays
retryable after a full restart using nothing but the persisted failed
notice and the service bearer token — no legacy-envelope import, no
eligibility call, and no migration checkpoint are ever created or
consulted — and the 503 response body is preserved unchanged as the opaque
`provider_receipt`, distinct from the `recipient` column it is stored
alongside. `ImportedLegacyEnvelopeRetryTests` follows: a legacy envelope
made eligible through `/admin/legacy-envelopes/eligibility` and a native
notice are retried together by one unfiltered, authenticated call after a
restart, after first asserting each notice's persisted `retry_locator` —
read back by that field's own name through the public
`Storage.list_pending_retry_attempts`, not a raw query — matches the
account it was created for; the same test then names and exercises
`AccountService.retry_notifications` directly (the class the route itself
calls, under the name integration callers use for it) against the same
persisted database, confirming it is idempotent once nothing is left
pending. The remaining tests cover: a retry resolves to the same address
when it has not changed; a second retry call after a successful delivery is
a no-op against a third, independently started process; an expired request
is excluded from retry and never attempted; and the route rejects a missing
or wrong bearer token before ever attempting a send.

`tests/test_migration_smoke.py` is one public, black-box smoke path over
the whole pipeline, driven only through the CLI and the loopback HTTP
surface: import a failed legacy notice through the authenticated
eligibility route, stop the service, restart it, retry the notice through
the authenticated retry route, and export the `verify-migration` report —
then check both invariants migration must never disturb: the wrapper's
`provider_receipt` reaches storage unparsed and unchanged, distinct from
the `recipient` it sits beside, and every attempt (the import-time failure
and the post-restart send) resolves to the same current email; the
exported report is also checked to contain neither.
