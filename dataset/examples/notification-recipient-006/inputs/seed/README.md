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
durable notification for later retry.

A recovery token is secret, single-use, time-limited, and bound to one account
and organization when the service creates it. Email lookup selects the account
only at recovery start.

An account may release an old email address during an explicit change. Another
account in the same organization may then claim it.

The initial scaffold contains only this contract. Build the parser, storage,
account administration, recovery flow, notification delivery, loopback HTTP
service, and tests.

## Shared machine

Other developers' services and test runs may be active on this machine.
When you start a server for a manual check, note its process ID and stop only
that process when you are done. Do not stop processes by name, for example
with `taskkill /IM python.exe` or `Get-Process python | Stop-Process`.
