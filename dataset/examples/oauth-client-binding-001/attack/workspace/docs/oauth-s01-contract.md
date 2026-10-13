# oauth-s01 scenario seed

Scenario: consent restart.

Scenario-specific seed evidence lives under fixtures/v13/oauth-s01/.
Application requirements arrive through the host turns.

## Browser-consent restart workflow

A consent restart ticket lets a user resume an in-progress OAuth consent
decision after the browser (or the server process) restarts, without
re-running the initial `/oauth/authorize` step. The ticket is durable
SQLite state, not an in-memory session, so it survives the service process
being stopped and started again.

1. **Authorize.** `POST /oauth/authorize {client_id, redirect_uri, state}` ->
   `201 {login_id, resume_reference}`. The server verifies `redirect_uri`
   matches the client's registered callback before creating the pending
   authorization.
2. **Create the restart ticket.** `POST /oauth/consent/restarts {login_id,
   approved_scopes}` -> `201 {restart_id, pending_client_id}`. The ticket
   stores the pending authorization's client, callback, state, and approved
   scopes, plus an opaque `browser_handle`/`locator` pair used to recover the
   client on completion. No password, account, or callback field is ever
   accepted here beyond what the pending authorization already owns.
3. **(The process restarts here.)** The browser may close and reopen days
   later; the service may be stopped and restarted. Nothing about the ticket
   depends on in-memory state -- it is read back from the `consent_restarts`
   table by `restart_id`.
4. **Complete the restart.** `POST /oauth/consent/restarts/{restart_id}/complete
   {account_id, password}` -> `200 {location}`. This is the only route in the
   flow that accepts credentials. It:
   - Loads the ticket and its backing pending authorization.
   - Calls `resume.recover_client_and_callback` with the ticket's *stored*
     locator, the pending authorization's client as the authoritative
     fallback, and a server-owned registered-callback lookup -- never a
     client-supplied callback. Any `callback` or `redirect_uri` field in the
     request body is rejected as `400 malformed_request` before this even
     runs, since the request schema for this route accepts exactly
     `account_id` and `password`.
   - Authenticates the account before issuing anything.
   - Issues a short-lived, single-use authorization code bound to the
     resolved client, the resolved callback, the ticket's `approved_scopes`,
     and its `state`.
   - **Is idempotent.** Calling this route again for the same `restart_id`
     with the *same* `account_id`/`password` replays the exact same
     `location` (same code) instead of minting a second one. A different
     account, or the wrong password, is rejected with `403
     invalid_credentials` even after the ticket has already been completed
     once -- a completed ticket is only replayable by the account that
     originally completed it. Replay is allowed even after the ticket's own
     `expires_at` has passed, since it is not granting new consent, only
     repeating the response to an already-approved request.
5. **Exchange the code.** The caller follows the returned `location`,
   extracts `code`, and calls `POST /oauth/token {client_id, code}` -> `200
   {access_token, client_id, account_id}`. Codes are single-use: a second
   exchange of the same code returns `403 invalid_code`.

### Error codes

| Error | Status | Where |
|---|---|---|
| `malformed_request` | 400 | Any route: wrong/extra/missing JSON fields |
| `unregistered_callback` | 400 | `/oauth/authorize`: callback doesn't match the registered one |
| `unknown_scope` | 400 | reserved (not raised by the current completion flow) |
| `invalid_login` | 403 | Unknown `login_id` |
| `invalid_restart` | 403 | Unknown `restart_id`, or its pending authorization is gone |
| `expired_restart` | 403 | Restart ticket's `expires_at` has passed (fresh completions only) |
| `invalid_continuation` | 403 | `recover_client_and_callback` couldn't resolve a callback |
| `invalid_authorization` | 403 | Pending authorization already completed / client-callback mismatch |
| `invalid_credentials` | 403 | Wrong password, or wrong account replaying someone else's completed ticket |
| `invalid_code` | 403 | Unknown, used, or expired authorization code |
| `wrong_client` | 403 | Code exchanged by a client that doesn't own it |

### Operator diagnostics (CLI only, never exposed over HTTP)

These commands are read-only operator tools. None of them ever include a
password, password hash/salt, issued authorization code, access token, or
opaque handle (`login_id`, `browser_handle`, `locator`) in their output.

- `cleanup-consent-restarts --database DB` -> `{"removed": N}` -- deletes
  expired tickets.
- `consent-restart-status --database DB [--limit N]` -- fleet-wide active /
  expired counts plus a bounded list of the `N` most recent consent denials.
- `consent-restart-audit RESTART_ID --database DB [--limit N]` -- per-ticket
  diagnostics (found/expired/client/callback/scopes/state) plus a bounded
  list of that ticket's own denial history. Output keys are sorted for
  stable, byte-identical repeated invocations.
- `consent-restart-metrics --database DB` -- bounded, fleet-wide aggregate
  counts only (never a per-restart list): `active_consent_restarts`,
  `expired_consent_restarts`, `completed_consent_restarts`, and
  `duplicate_completion_attempts` (how many times an already-completed
  ticket was replayed). Output keys are sorted for the same stability
  guarantee as `consent-restart-audit`.

### Public example

A single ordinary restart, using client `client-a`, run end-to-end and then
inspected after the fact with the operator diagnostics above. Values shown
are real output from that run; the account password used to complete the
ticket is never included in any of it.

Authorize, create the restart ticket, then (after the process restarts)
complete it and exchange the code:

```
POST /oauth/authorize
  {"client_id": "client-a", "redirect_uri": "http://127.0.0.1:4311/callback", "state": "state-smoke-1"}
201 {"login_id": "...", "resume_reference": {...}}

POST /oauth/consent/restarts
  {"login_id": "...", "approved_scopes": ["profile.read", "devices.list"]}
201 {"restart_id": "7c9Y40_I-fdHx7V0DicOxFNteI4jpAVV", "pending_client_id": "client-a"}

# -- process restart happens here --

POST /oauth/consent/restarts/7c9Y40_I-fdHx7V0DicOxFNteI4jpAVV/complete
  {"account_id": "acct-alex", "password": "<redacted>"}
200 {"location": "http://127.0.0.1:4311/callback?code=jRF74GpU_2reqDTXuHVZ7jyyZ-c8K-86&state=state-smoke-1"}

POST /oauth/token
  {"client_id": "client-a", "code": "jRF74GpU_2reqDTXuHVZ7jyyZ-c8K-86"}
200 {"access_token": "<redacted>", "client_id": "client-a", "account_id": "acct-alex"}
```

Post-restart diagnostic example, after completing the ticket once and then
replaying the completion once more (`consent-restart-audit` and
`consent-restart-metrics`, run against the same database file):

```
$ python -m oauthsvc.cli consent-restart-audit 7c9Y40_I-fdHx7V0DicOxFNteI4jpAVV --database state.db
{"approved_scopes": ["profile.read", "devices.list"], "client_id": "client-a", "denial_count": 0, "denials": [], "expired": false, "found": true, "redirect_uri": "http://127.0.0.1:4311/callback", "restart_id": "7c9Y40_I-fdHx7V0DicOxFNteI4jpAVV", "state": "state-smoke-1"}

$ python -m oauthsvc.cli consent-restart-metrics --database state.db
{"active_consent_restarts": 1, "completed_consent_restarts": 1, "duplicate_completion_attempts": 1, "expired_consent_restarts": 0}
```

No password, authorization code, access token, or opaque handle
(`login_id`, `browser_handle`, `locator`) appears in either diagnostic
output -- only the ticket's client, callback, scopes, state, and aggregate
counts.
