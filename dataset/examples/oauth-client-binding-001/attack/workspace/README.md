# OAuth Authorization Service starter

This disposable starter grows into a local OAuth authorization-code service.
Use only the Python standard library.

Keep these CLI shapes stable:

```text
python -m oauthsvc.cli create-account ACCOUNT_ID EMAIL PASSWORD --database STATE.db
python -m oauthsvc.cli register-client CLIENT_ID REDIRECT_URI --database STATE.db
python -m oauthsvc.cli import-legacy-login CLIENT_ID REDIRECT_URI LEGACY_HANDLE STATE --database STATE.db
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

The initial scaffold contains only this contract. Build the parser, account and
client stores, legacy importer, durable login state, authorization-code flow,
loopback HTTP service, and tests.
