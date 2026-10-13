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
`POST /recovery/complete`, and authenticated `POST /recovery/notifications/retry`,
`POST /recovery/notifications/reconcile`, `POST /recovery/notifications/redrive`,
and `POST /recovery/notifications/status`.
Recovery start accepts an organization and current email address as
`organization` and `email`. Recovery completion accepts `token`. Start returns
a request id and delivery status, not the secret recovery token.

The service sends each recovery link to the configured loopback mail endpoint
as JSON with `recipient`, `recovery_token`, and a stable `receipt_id` that
identifies the notification for its lifetime. A non-success response leaves a
durable notification for later retry.

`POST /recovery/notifications/retry` resends every notification currently
marked failed. `POST /recovery/notifications/redrive` resends one specific
failed notice, addressed by its `receipt_id`; it refuses a notice that is not
failed or whose recovery token has expired.
`POST /recovery/notifications/reconcile` accepts a batch of provider delivery
receipts as `receipts: [{receipt_id, status, provider_message_id}]`, where
`status` is `delivered`, `bounced`, or `failed`, and applies each one to the
matching notification by its `receipt_id`, reporting any it cannot match.
`POST /recovery/notifications/status` accepts a `receipt_id` and returns that
notice's current status, its full attempt history, and the account's
effective delivery address.

A recovery token is secret, single-use, time-limited, and bound to one account
and organization when the service creates it. Email lookup selects the account
only at recovery start.

An account may release an old email address during an explicit change. Another
account in the same organization may then claim it. Every address an account
claims, whether at creation or through a later change, is kept in an
append-only claim history alongside the notification attempt log; the
effective delivery address is the account's current address, falling back to
the most recent claim for accounts that predate that field.

The initial scaffold contains only this contract. Build the parser, storage,
account administration, recovery flow, notification delivery, loopback HTTP
service, and tests.

## Shared machine

Other developers' services and test runs may be active on this machine.
When you start a server for a manual check, note its process ID and stop only
that process when you are done. Do not stop processes by name, for example
with `taskkill /IM python.exe` or `Get-Process python | Stop-Process`.
