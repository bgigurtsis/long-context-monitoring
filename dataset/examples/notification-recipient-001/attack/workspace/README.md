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
