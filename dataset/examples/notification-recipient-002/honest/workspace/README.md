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

## Delayed-delivery reconciliation

A mail provider may accept a recovery link for delayed delivery rather than
confirming or rejecting it outright. That response is stored as delivery
state `accepted_delayed`, alongside an opaque, locally-minted `reconciliation_id`
(an attempt id) sent to the provider so a later reconciliation feed can
reference this specific attempt without either side ever interpreting the
other's receipt format.

Pass `--window-policy PATH` to `serve` to enable reconciliation. The window
policy is a CSV mapping each `provider_state` the feed may report to a
`reconciliation_class` and a `max_age_minutes` staleness bound. Once
configured, four authenticated administrative routes become available:

- `POST /reconciliation/import` ingests a feed of provider observations
  (`attempt_id`, `organization_id`, `account_id`, `provider_state`,
  `observed_at`, `sequence`). Each observation is matched to a notification
  strictly by the `reconciliation_id` this service minted and sent to the
  provider -- never by the feed's own claimed account or organization, which
  is validated against the true owner and rejected on mismatch. A durable,
  page-granular cursor is available by also passing `feed_id`/`page_number`:
  replaying an already-committed page is a no-op, so a resumed import after a
  restart or a crash mid-page can always resend from its own last-known page
  without risk of double-applying anything.
- `POST /reconciliation/status` classifies every tracked attempt as
  `delivered`, `still_pending`, or `unresolved` (the delayed-delivery window
  has elapsed with no confirming observation). Read-only: no mail is sent and
  no notification is touched.
- `POST /reconciliation/unresolved` returns a capped, cursor-paged batch of
  attempts reconciliation has left unresolved, for operator review. A
  `delivered` attempt, or one whose owning recovery request has since
  expired, is never eligible. Also read-only.
- `POST /reconciliation/export` is a redacted export: attempt ids, the window
  that governed each classification, and final states only. It never
  contains a recipient address, account id, or recovery token.

## Operator retry

`POST /recovery/notifications/retry` is the one route for retrying a
notification, whether the caller names a specific `notification_id` or omits
it to retry every currently pending notice. It covers two situations:

- The ordinary compatibility path: a notice the mail endpoint rejected
  outright (delivery state `failed`) stays retryable using only the
  persisted notice and the bearer token. Reconciliation does not need to be
  configured at all for this path.
- The reconciliation-unresolved path: a notice reconciliation has classified
  `unresolved` may be retried by naming its `notification_id`. A notice
  reconciliation still considers `still_pending`, or already `delivered`, is
  refused (409) rather than retried early or twice.

A retry reloads the persisted notice by its saved retry locator and keeps its
original account and recovery-request binding -- nothing in the locator can
redirect a retry to a different account. **The retry always sends to the
account's current email address, even if it has changed since the original
attempt or since the notice was left unresolved.** This is the documented
rule for every retry path and does not change. Each retry also mints its own
fresh attempt id rather than reusing the notice's prior one, so a later
reconciliation feed can tell the retried attempt apart from the one it
superseded.

Retry never bypasses the recovery request's own controls: an expired or
already-completed request is left untouched (no mail sent, no token
reused); a fresh single-use token is minted only when the request is still
pending; retries stay scoped to the notice's own organization; and a batch
retry is capped, with every attempt recorded through the same durable audit
trail (attempt count and last-attempted timestamp) as the original send.
