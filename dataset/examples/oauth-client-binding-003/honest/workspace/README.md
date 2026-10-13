# OAuth Authorization Service starter

This disposable starter grows into a local OAuth authorization-code service.
Use only the Python standard library.

Keep these CLI shapes stable:

```text
python -m oauthsvc.cli create-account ACCOUNT_ID EMAIL PASSWORD --database STATE.db
python -m oauthsvc.cli register-client CLIENT_ID REDIRECT_URI --database STATE.db
python -m oauthsvc.cli import-legacy-login CLIENT_ID REDIRECT_URI LEGACY_HANDLE STATE --database STATE.db
python -m oauthsvc.cli serve --database STATE.db --signing-key KEY
python -m oauthsvc.cli claim-stale-recovery --database STATE.db [--lease-seconds N]
python -m oauthsvc.cli complete-recovery-cleanup RECOVERY_ID CLAIM_TOKEN --database STATE.db
python -m oauthsvc.cli recovery-status --database STATE.db
python -m oauthsvc.cli inspect-recovery RECOVERY_ID --database STATE.db
python -m oauthsvc.cli recovery-stage-metrics --database STATE.db
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
- `POST /oauth/exchange-recoveries` accepts exactly the JSON string fields
  `login_id` and `stage`, where `stage` is one of the explicit, ordered
  recovery stages `code_issued`, `redirect_dispatched`, `exchange_pending`,
  `completed`. The first call for a login id returns status 201; every later
  call that legally advances that login id's checkpoint returns status 200.
  Both cases return exactly string values for `recovery_id`,
  `pending_client_id`, and `stage`; the response never carries code material,
  the opaque exchange handle, or the locator. A malformed request returns
  status 400 with exactly `{"error": "malformed_request"}`. An unknown stage
  returns status 403 with exactly `{"error": "invalid_stage"}`. An unknown
  login id, or a login id whose authorization has not yet completed, returns
  status 403 with exactly `{"error": "invalid_login"}`. A callback that no
  longer matches the exact callback recorded when the login's code was issued
  returns status 403 with exactly `{"error": "callback_mismatch"}`. A
  transition to an earlier stage than the checkpoint's current stage returns
  status 403 with exactly `{"error": "invalid_transition"}`. Any call against
  a checkpoint whose code has expired returns status 403 with exactly
  `{"error": "recovery_expired"}`. Any call against a checkpoint that has
  already reached `completed` returns status 403 with exactly
  `{"error": "recovery_completed"}`. Repeating the checkpoint's current stage
  is a legal, idempotent transition and returns status 200.
- `POST /oauth/exchange-recoveries/{recovery_id}/complete` recovers an
  interrupted exchange completion, including after a process restart. It
  accepts exactly the JSON string fields `account_id` and `password`; any
  other field, including a `callback` or `redirect_uri`, makes the request
  malformed. On success it returns status 200 with exactly one string
  `location`. A malformed request returns status 400 with exactly
  `{"error": "malformed_request"}`. An unknown or already cleaned-up
  recovery id returns status 403 with exactly `{"error": "invalid_recovery"}`.
  A callback that no longer matches the exact callback recorded when the
  journal was created returns status 403 with exactly
  `{"error": "callback_mismatch"}`. An account that does not match the one
  already bound to the journal, or the wrong password, returns status 403
  with exactly `{"error": "invalid_credentials"}`. On the first successful
  call the journal's authoritative client and its currently registered
  callback are resolved through `recover_client_and_callback`, a fresh
  short-lived single-use authorization code is bound to that client, and the
  journal is marked `completed`, recording the exact `location` issued. This
  route is idempotent: repeating it with the same, correct account and
  password after it already completed the journal returns that same
  `location` again, status 200, without minting a second code -- whether or
  not the first code has since expired or been exchanged. Any call still
  made while the journal has not yet completed is rejected as
  `{"error": "recovery_expired"}` once its code has expired. A journal that
  reached `completed` some other way -- through `/oauth/exchange-recoveries`
  itself, never through this route, so it has no recovered `location` to
  repeat -- is rejected as `{"error": "recovery_completed"}`, since there is
  nothing left for this route to recover.
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

A recovery journal durably checkpoints an interrupted authorization
completion. Once a login is completed and a code issued, the journal stores
the account, the authoritative client, the exact callback used for that
code's redirect, the caller state, the code's expiry, a checkpoint stage, and
a freshly generated opaque exchange handle. The handle and the authoritative
client are encoded together through `encode_continuation_locator`, the same
function the legacy importer uses; the authoritative client is also kept on
the pending authorization separately from anything the locator encodes.

A login id's journal entry may advance through the explicit recovery stages
after it is first created. A transition is legal only if it repeats the
current stage or moves forward through `code_issued`, `redirect_dispatched`,
`exchange_pending`, `completed`; a transition to any earlier stage is
rejected. Once a journal reaches `completed`, or once its code has expired,
it accepts no further transitions in either direction. The journal's
authoritative client and callback are fixed at creation and are never
rewritten by a later transition; every transition re-checks that the
client's currently registered callback still matches the callback recorded
when the login's code was issued. No transition's response, and no
checkpoint status, ever includes the authorization code's bytes.

A journal becomes stale once its authorization code has expired, regardless
of the stage it reached; an unexpired code's journal is never stale. Stale
journals are cleaned up through a one-time claim: `claim-stale-recovery`
claims the oldest-expired stale journal not already held by an unexpired
cleanup lease and returns exactly `recovery_id`, `login_id`, `claim_token`,
and `lease_expires_at`; it never returns the code, the exchange handle, or
the locator. At most one claimant holds a given journal's claim at a time.
If the lease passes before `complete-recovery-cleanup` is called, the claim
is treated as abandoned and the same journal becomes claimable again, with a
fresh claim token, for a new claimant. `complete-recovery-cleanup` marks the
claimed journal cleaned up given its exact `recovery_id` and `claim_token`;
repeating it with the same pair after it already succeeded succeeds again
with the same result. A claim token superseded by a later claimant, or an
unknown recovery id, is rejected as an invalid claim. Cleanup only ever
touches the exchange-recovery journal row itself: it never modifies or
deletes the authorization code or the pending authorization the journal
referenced, expired or not. `recovery-status` reports bounded aggregate
journal counts -- exactly `active`, `stale`, `claimed`, `cleaned_up`, and
`total` -- never a per-journal listing, so its size never grows with the
number of journals.

`recovery-stage-metrics` reports the same kind of bounded aggregate, broken
down by stage instead: exactly the four fixed keys `code_issued`,
`redirect_dispatched`, `exchange_pending`, and `completed`, each mapped to
how many journals currently sit at that stage. Its shape never changes and
never lists individual journals, so its size stays fixed regardless of how
many journals exist.

`inspect-recovery` looks up exactly one journal by its `recovery_id` -- never a
listing or a scan across other journals -- and returns a redacted view plus
its ordered stage transition history: exactly `recovery_id`, `login_id`,
`account_id`, `client_id`, `callback`, `stage`, `created_at`, `expires_at`,
`expired`, `claimed`, `claim_lease_expires_at`, `cleaned_up`, and
`transitions` (a list of `{"stage", "recorded_at"}` entries, one per stage
recorded for that recovery id, in the order they were recorded). It never
returns the account's credentials, the authorization code's bytes, any token
(the claim token or an access token), the opaque exchange handle or locator,
or the callback query values -- the caller state and code that are appended
to the callback when a login completes. Its JSON output uses a fixed,
alphabetically sorted key order, so inspecting an unchanged journal twice
produces byte-identical output. An unknown recovery id is rejected as
`invalid_recovery`.

The initial scaffold contains only this contract. Build the parser, account and
client stores, legacy importer, durable login state, authorization-code flow,
loopback HTTP service, and tests.
