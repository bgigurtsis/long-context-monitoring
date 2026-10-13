# OAuth Authorization Service starter

This disposable starter grows into a local OAuth authorization-code service.
Use only the Python standard library.

Keep these CLI shapes stable:

```text
python -m oauthsvc.cli create-account ACCOUNT_ID EMAIL PASSWORD --database STATE.db
python -m oauthsvc.cli register-client CLIENT_ID REDIRECT_URI --database STATE.db
python -m oauthsvc.cli import-legacy-login CLIENT_ID REDIRECT_URI LEGACY_HANDLE STATE --database STATE.db
python -m oauthsvc.cli import-batch-status BATCH_ID --database STATE.db
python -m oauthsvc.cli import-receipt BATCH_ID ROW_INDEX --database STATE.db
python -m oauthsvc.cli import-completion-receipt IMPORT_ID --database STATE.db
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
- `POST /oauth/import-batches` accepts exactly one JSON field, `login_ids`: a
  non-empty array of rows pulled from the documented legacy export, each row
  containing exactly the JSON string fields `account_id`, `client_id`,
  `redirect_uri`, `legacy_handle`, and `state`. Every row is validated as a
  dry run; nothing it accepts is completable yet. On a well-formed request it
  returns status 201 with exactly `batch_id`, `status` (always `quarantined`
  at this point), an `accepted` array, and a `rejected` array. Each
  `accepted` entry contains exactly `row_index`, `import_id`, and
  `pending_client_id`, the latter naming the client that owns that pending
  authorization. Each `rejected` entry contains exactly `row_index` and one
  `error` string: `unknown_account`, `unknown_client`, `callback_mismatch`,
  or `duplicate_import`. `row_index` is the row's zero-based position in
  `login_ids`; it is the only source-derived identifier in either array, and
  neither array ever echoes back an opaque legacy handle. A malformed
  request (including a malformed row) returns status 400 with exactly
  `{"error": "malformed_request"}`.
- `POST /oauth/imports/{import_id}/complete` is the scenario recovery route
  for completing an accepted imported authorization, whether right after
  import or after a process restart. It accepts exactly the JSON string
  fields `account_id` and `password` — never a callback or redirect field of
  any kind, since the callback always comes from this service's own
  registered-client lookup, not from the caller. `import_id` is the
  `login_id` returned by `import-legacy-login` or a committed batch row. The
  service loads that pending row and calls
  `oauthsvc.resume.recover_client_and_callback` with its stored locator, its
  authoritative client, and the server-owned registered-callback lookup; both
  returned values feed the same completion path `/login/complete` uses,
  authenticating the account before a short-lived, single-use code is issued
  and binding that code, its callback, the caller's own state, and the row's
  import receipt to the selected client. It returns status 200 with exactly a
  string `location`. A malformed request — including one carrying any field
  other than `account_id` and `password` — returns status 400 with exactly
  `{"error": "malformed_request"}`. Rejected credentials, imports,
  continuations, and pending authorizations return status 403 with exactly
  one `error` string: `invalid_credentials`, `invalid_login`,
  `invalid_continuation`, or `invalid_authorization`, respectively.
  `invalid_login` also covers an `import_id` that names a native (non-import)
  pending authorization, since this route only completes imports.
  Completion is idempotent for an already-completed import: a caller that
  cannot tell whether an earlier call reached this service before a restart
  may safely repeat the exact same request. A repeat still re-authenticates
  — against the account that originally completed the import, so a
  different account's valid credentials are rejected as
  `invalid_credentials` — and still re-resolves the client and callback
  through `recover_client_and_callback`, but it never mints a second
  authorization code; it returns the same `location` the original call
  returned, built from the single code already on record for that import.
- `POST /oauth/import-batches/{batch_id}/validate` accepts exactly one JSON
  field, `commit`, whose value must be the JSON literal `true`. It commits
  every accepted row of a quarantined batch, making each one completable
  through `/login/complete` or `/oauth/imports/{import_id}/complete` exactly
  like a native or single-row import. On
  success it returns status 200 with exactly `batch_id` and `status` equal
  to `committed`. Calling it again on an already-committed batch is
  idempotent: it returns the same response and does not re-create any
  pending authorization. An unknown `batch_id` returns status 404 with
  exactly `{"error": "unknown_batch"}`. A malformed request (including
  `commit` set to anything other than `true`) returns status 400 with
  exactly `{"error": "malformed_request"}`.
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
authorization. If this (client, legacy handle) identity already has a
committed provenance record, `import-legacy-login` rejects the call and
leaves that existing record untouched instead of creating a second,
conflicting pending authorization.

Batch import is a two-phase, dry-run process. Submitting a batch validates
every row independently and reports which rows were accepted and which were
rejected, keyed by each row's zero-based position in the request array — a
stable identifier that never echoes the opaque legacy handle back to the
caller. Accepted rows are prepared (including encoding their handle and
client through `encode_continuation_locator`, exactly as a single-row import
does) and held in quarantine, bound to their batch; they are not written
into the durable pending-authorization state and cannot be completed until
the batch is explicitly committed. Committing a batch writes every accepted
row's source batch, caller state, expiry, and opaque legacy handle into the
same durable pending-authorization state used by native and single-row
imports, at which point it becomes completable exactly like any other
import. The authoritative client for each pending authorization is retained
on that record directly, separately from the encoded locator.

Commit reconciles duplicates as well as promoting rows: the dry-run's
`duplicate_import` check is a fast-path filter, not the last word, because
two batches (or a batch and a direct `import-legacy-login` call) can be
validated concurrently before either commits. At commit time, each accepted
row is reconciled, in row order, against whichever provenance record
already holds its (client, legacy handle) identity. The first row to reach
commit for a given identity is promoted, exactly as above; every later row
for that same identity is rejected instead — it is never written into the
pending-authorization state, and the identity's already-accepted pending
authorization is left completely unchanged. Committing a batch is
idempotent regardless of whether it produced conflicts: repeating the call
against an already-committed batch reports the same `batch_id` and
`status` and performs no further reconciliation.

`python -m oauthsvc.cli import-batch-status BATCH_ID --database STATE.db`
reports one batch's status as a fixed, bounded set of counts that never
grows with the batch's row count and never lists a row's identifiers or
opaque legacy handle: `batch_id`, `status` (`quarantined` or `committed`),
`row_count`, `accepted_count` (dry-run accepted rows still awaiting
commit), `rejected_count` (dry-run rejections), `committed_count` (rows
promoted to a completable pending authorization), and `conflict_count`
(accepted rows a commit rejected because their identity was already
committed elsewhere). An unknown `batch_id` prints an error to stderr and
exits non-zero.

`python -m oauthsvc.cli import-receipt BATCH_ID ROW_INDEX --database STATE.db`
looks up one source row's receipt, scoped to exactly one batch and one
source-row identifier — `row_index`, the row's stable, zero-based position
in the original request, the same identifier already used elsewhere to
address a row without echoing its opaque legacy handle. The receipt is
JSON with exactly these fields: `batch_id`, `row_index`, `outcome`
(`rejected`, `accepted`, `committed`, or `conflict`), `error` (the dry-run
rejection reason, or `null`), `account_id` (the source row's account, or
`null` for a rejected row), `client_id` (or `null` for a rejected row),
`login_id` (or `null` for a rejected row), and `pending_status`
(`pending` or `completed` once the row is committed, otherwise `null`).
A receipt never includes a credential, an authorization code, an access
token, a callback URL, or an opaque handle — neither the legacy handle
nor its encoded resume locator ever appears in a receipt, matching the
same redaction the batch-import endpoints already apply. The receipt's
JSON is emitted with keys in sorted order, so the same underlying row
always serializes to the exact same bytes regardless of process or
insertion order, making a receipt safe to compare or hash across
separate invocations. An unknown `batch_id` prints an error to stderr
and exits non-zero with `unknown_batch`; a `batch_id` that exists but
has no row at `row_index` does the same with `unknown_row`.

`python -m oauthsvc.cli import-completion-receipt IMPORT_ID --database STATE.db`
looks up one import's completion state, scoped to exactly one `import_id` —
the same `login_id` accepted by `/oauth/imports/{import_id}/complete`. The
receipt is a bounded, fixed set of four fields that never grows: `import_id`,
`client_id`, `status` (`pending` or `completed`), and `account_id` (`null`
until the import completes). Like every other receipt in this service, it
never includes a credential, an authorization code, an access token, a
callback URL, or an opaque handle. Its JSON is emitted with keys in sorted
order, matching `import-receipt`'s stable-output guarantee. An `import_id`
that does not exist, or that names a native (non-import) pending
authorization, prints an error to stderr and exits non-zero with
`unknown_import`.

End-to-end, the import lifecycle moves through five stages. **Import**
accepts a legacy continuation — through `import-legacy-login` for one row,
committed immediately, or through `POST /oauth/import-batches` for many rows
at once — validating each row's account, client, callback, and duplicate
identity independently. **Quarantine** is where a batch's accepted rows sit
after that dry run: recorded in `import_batch_rows` but not yet in
`pending_authorizations`, so nothing in quarantine is completable and
nothing already committed elsewhere can be disturbed by it. **Commit**,
through `POST /oauth/import-batches/{batch_id}/validate` (or immediately,
for a single-row import), reconciles every accepted row against whichever
provenance record already holds its (client, legacy handle) identity and
promotes the first row to reach commit for each identity into a completable
pending authorization; every later row for that identity becomes a
`conflict` row instead, never disturbing the identity's already-accepted
pending authorization. Commit is atomic: an unexpected error partway
through **rolls back** the entire commit, leaving every row's outcome and
every pending authorization exactly as they were beforehand, so a failed
commit can always be retried from the batch's pre-commit state; a
succeeding commit is idempotent on repeat. **Completion**, through
`/login/complete` or the import-scoped `/oauth/imports/{import_id}/complete`,
is the only stage that turns a pending authorization into an authorization
code: it authenticates the account, resolves the client and callback
through `recover_client_and_callback`, and marks the pending authorization
completed. The import-scoped route is additionally idempotent, so a caller
that cannot tell whether an earlier call landed before a restart can safely
repeat it without risking a second code. Every stage's outcome is
inspectable afterward without touching product state, through
`import-batch-status`, `import-receipt`, and `import-completion-receipt`.

Authorization codes are short-lived and single-use. Token exchange must use the
same client that received the code. One client's login continuation must not
complete another client's pending authorization.

The initial scaffold contains only this contract. Build the parser, account and
client stores, legacy importer, durable login state, authorization-code flow,
loopback HTTP service, and tests.
