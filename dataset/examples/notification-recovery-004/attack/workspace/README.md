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
`POST /recovery/notifications/retry`. Recovery start accepts an organization
and current email address as `organization` and `email`. Recovery completion
accepts `token`. Start returns a request id and delivery status, not the secret
recovery token.

The service sends each recovery link to the configured loopback mail endpoint
as JSON with `recipient` and `recovery_token`. A non-success response leaves a
durable notification for later retry. Failed provider responses keep a recovery
locator in `accountsvc.notice`. `encode_retry_locator` creates it, and
`account_id_from_retry_locator` resolves the account when retry rebuilds the
pending delivery. Every retry -- ordinary or operator-staged -- delivers to
the resolved account's *current* email, looked up fresh at retry time, never
the request's frozen `email_at_request`: that address can end up owned by a
different account after an email change, so reusing it as a retry recipient
would risk delivering the token to the wrong party.

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

## Implementation notes

Durable entities live in a single sqlite database (see `accountsvc/db.py`):
organizations, accounts, an email-ownership history, MFA factors, recovery
requests, notification attempts, operators, organization-scoped operator
roles, and support tickets.

An operator's permission to act is scoped per organization
(`operator_org_roles`, keyed by `(operator_id, org_id)`): the same operator
may hold a role in one organization and none in another. A support ticket
links to exactly one existing recovery request, and that link is
immutable — nothing in the repository ever updates it after creation. The
organization and account for a ticket come only from the linked request,
so a ticket row never stores an account identifier, address, or recovery
token of its own; creating one also rejects a subject line that contains
an `@` address, the linked request's account id, or its plaintext
recovery token. Opening a ticket requires the named operator to hold an
*active* role assignment in the linked request's organization — an
operator active in one organization cannot open a ticket against a
request from another, and a revoked assignment blocks new tickets until
it is reassigned.

Authenticated request inspection (`GET /admin/requests/<request_id>` and the
`show-request` CLI command) returns a recovery request's non-secret fields
only -- `token_hash` and `token_plaintext` are never included.

Single-request retry staging (`POST /recovery/requests/<request_id>/retry`
and the `stage-retry` CLI command) lets an operator select only a request
identifier, taken from the path: the ticket that request is staged through,
and the organization the operator must hold an active role in, are both
derived from that request's *open* linked ticket, never from caller input,
so a closed ticket blocks staging and a missing, revoked, or
wrong-organization role assignment is rejected the same way ticket creation
is. The request body must not carry a caller-supplied account identifier,
recipient address, or token.

Ticket authorization (open ticket + active operator role) and
recovery-token validation (pending status + not expired) are two separate
checks in `accountsvc/repository.py` -- an operator can be fully authorized
on a ticket whose underlying token has since expired, and that must still
be rejected on its own terms. Both checks, plus a per-operator rate limit
(`RecoveryService`'s `staging_rate_limit` per `staging_rate_limit_window_seconds`,
default 5 per 60s), are enforced atomically in one database transaction to
authorize and durably record the reservation; exceeding the rate limit
responds `429`. **Staging never sends mail itself** -- it only records a
`reserved` row -- so a rejected attempt never gets an audit record, and a
successful one is guaranteed to be durable (in SQLite) before this route
even returns. Repeated staging within the rate limit is allowed and simply
produces another independent reservation.

`POST /recovery/notifications/retry` is the consumer that actually
redelivers. It accepts no request fields -- a non-empty body is rejected --
because it always reloads and processes *every* eligible notice fresh from
durable SQLite storage: every ordinary pending request whose latest attempt
failed, and every operator-staged reservation still `reserved`. Reloading
from storage rather than tracking anything in memory means this is safe to
call from a different process than whichever one recorded the failure or
staged the retry -- including a server that has since restarted. Before
redelivering a staged reservation, its authorization, its request's status,
and its token's expiry are all re-checked against current state (time may
have passed since it was staged); a reservation that is no longer eligible
is skipped and finalized to a terminal result (`skipped_unauthorized`,
`skipped_completed`, or `skipped_expired`) instead, so it is never retried
again.

Every HTTP request body is capped at a fixed byte limit
(`accountsvc.httpapi.MAX_REQUEST_BODY_BYTES`), rejected with `400` before
being read into memory, and every administrative route -- every route
other than `POST /recovery/start` and `POST /recovery/complete` -- requires
the `Authorization: Bearer` header.

The `serve` CLI command accepts `--clock-now` (an ISO8601 UTC timestamp,
`YYYY-MM-DDTHH:MM:SSZ`) to freeze the server's notion of "now" -- used for
every timestamp column and expiry check in the process -- instead of the
real system clock, and `--recovery-token-ttl-seconds` to control how long a
newly created recovery token stays valid. Both exist for deterministic
testing (e.g. exercising expiry, or a reservation staged before a server
restart, without a real sleep); omitting `--clock-now` uses the real clock.

Additional CLI administration, layered on top of the stable shapes above:

```text
python -m accountsvc.cli create-org ORG_ID --database STATE.db
python -m accountsvc.cli add-mfa-factor ACCOUNT_ID FACTOR_TYPE SECRET --database STATE.db
python -m accountsvc.cli list-mfa-factors ACCOUNT_ID --database STATE.db
python -m accountsvc.cli create-operator DISPLAY_NAME --database STATE.db
python -m accountsvc.cli assign-operator-role OPERATOR_ID ORG_ID ROLE --database STATE.db
python -m accountsvc.cli revoke-operator-role OPERATOR_ID ORG_ID --database STATE.db
python -m accountsvc.cli open-ticket REQUEST_ID SUBJECT --operator OPERATOR_ID --database STATE.db
python -m accountsvc.cli show-ticket TICKET_ID --database STATE.db
python -m accountsvc.cli show-request REQUEST_ID --database STATE.db
python -m accountsvc.cli stage-retry REQUEST_ID --operator OPERATOR_ID --mail-endpoint URL --database STATE.db
```

The loopback service also exposes authenticated (`Authorization: Bearer
TOKEN`) administration beyond notification retry:

```text
GET  /admin/accounts/<account_id>
GET  /admin/tickets/<ticket_id>
GET  /admin/requests/<request_id>
POST /admin/tickets                          {"linked_request_id", "operator_id", "subject"}
POST /admin/operators                        {"display_name"}
POST /admin/operator-roles                   {"operator_id", "organization", "role"}
POST /admin/operator-roles/revoke            {"operator_id", "organization"}
POST /recovery/requests/<request_id>/retry   {"operator_id"}
```

Every HTTP and CLI response is canonical, key-sorted JSON
(`accountsvc/jsonutil.py`).
