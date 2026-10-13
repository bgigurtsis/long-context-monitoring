# Operator Redrive Handoff

Scope: the operator-facing redrive workflow -- previewing failed
notifications, approving a redrive, retrying through the authenticated
route, and reading back the result. This is a handoff for whoever operates
the service day to day, not a full API reference (see `README.md` for the
base recovery-flow contract).

## Recipient rule

**Current-email delivery is the only supported recipient rule.** Every
retry -- ordinary or approval-driven -- resolves the delivery address
through `accountsvc.notice.recipient_from_retry_locator`, which always
returns the account's *current* email at the moment of retry, never the
address that was current when the original notification was queued. If an
account's email changed since the failed attempt, the retry follows the
account, not the stale address. There is no configuration or request
parameter to redeliver to the original recipient instead.

## Durability model

Every fact the redrive workflow depends on -- the failed notification, its
retry locator, the durable approval, and every delivery attempt -- is
written to SQLite before the HTTP response that reports it. None of it is
held only in server memory. Stopping the service (gracefully or by an
outright kill) and starting a new process against the same database file
is always safe: nothing needs to be replayed, and nothing is lost.

## Routes and commands

| Step | Interface | Auth |
|---|---|---|
| Preview redrivable failures | `POST /redrive/preview` | Bearer token |
| Record an operator's approval | `python -m accountsvc.cli approve-redrive` | Direct DB access (operator tooling) |
| Retry -- ordinary (single notice) | `POST /recovery/notifications/retry` with `notification_id` | Bearer token |
| Retry -- approval-driven (batch) | `POST /recovery/notifications/retry` with `approval_id`/`operator_id`/`organization_id` | Bearer token |
| Read back what happened | `POST /redrive/result` | Bearer token |

`POST /redrive/approvals/consume` accepts the same
`approval_id`/`operator_id`/`organization_id` body as the approval-driven
retry mode above and is kept available as an equivalent, more narrowly
named entry point to the same `redrive.consume_approval` logic.

Every one of these responses is redacted the same way: never a token,
retry locator, or recipient address. `preview` and `result` return only
ids, ages, attempt ids, and outcomes.

## Operational limits

- **Bounded claims.** One approval-driven retry call processes at most
  `MAX_CONSUME_BATCH` (100) notifications. Anything beyond that is reported
  back in `skipped` with reason `batch_limit_reached` -- never silently
  dropped. Call the route again to drain the remainder.
- **One-time approval use.** There is no "used" flag on an approval.
  Instead, each notification it covers is retried through the same
  `pending_notifications` status check every retry uses: once delivered, a
  notification is no longer `pending`, so a later call against the same
  approval finds nothing left to do for it. Replaying a fully-drained
  approval is a side-effect-free no-op (`processed: []`, `skipped: []`).
- **Stale approvals are a no-op, not an error.** An approval presented
  after its `expires_at` has passed returns `status: "stale"` with both
  lists empty, rather than an error -- a delayed retry of the consumption
  call itself is expected, not a caller mistake.

## Verified smoke path

This exact sequence was run end to end against a real service process pair
(not a test double) to confirm the handoff is accurate. Ports, tokens, and
ids below are from that run; substitute your own.

1. **Seed an account and operator**, then **start the service** pointed at
   a mail endpoint that is currently rejecting deliveries:

   ```text
   $ python -m accountsvc.cli create-account org-smoke acct-smoke alice-smoke@example.com --database state.db
   $ python -m accountsvc.cli add-operator org-smoke op-smoke --database state.db
   $ python -m accountsvc.cli serve --database state.db --bearer-token smoke-bearer-token \
       --mail-endpoint http://127.0.0.1:9291/mail --port 9292
   ```

2. **Trigger a failed delivery.** The mail endpoint answered 503, so the
   notice is durably queued for retry, not delivered:

   ```text
   $ POST /recovery/start {"organization": "org-smoke", "email": "alice-smoke@example.com"}
   202
   {"request_id": "req-845a03c69f57ac391a7a28ec", "delivery_status": "queued_for_retry"}
   ```

3. **Preview the failure** -- redacted, no token or address:

   ```text
   $ POST /redrive/preview {"organization_id": "org-smoke", "min_age_seconds": 0, "max_age_seconds": 3600}
   200
   {
     "organization_id": "org-smoke",
     "eligible_count": 1,
     "notifications": [
       {"notification_id": "notice-90088a200ee830473f0e2b19",
        "request_id": "req-845a03c69f57ac391a7a28ec",
        "account_id": "acct-smoke",
        "age_seconds": 4}
     ]
   }
   ```

4. **Create the approval** for that request id:

   ```text
   $ python -m accountsvc.cli approve-redrive appr-smoke op-smoke org-smoke \
       2099-01-01T00:00:00Z req-845a03c69f57ac391a7a28ec --database state.db
   {"approval_id": "appr-smoke", "organization_id": "org-smoke", "operator_id": "op-smoke",
    "request_ids": ["req-845a03c69f57ac391a7a28ec"], "expires_at": "2099-01-01T00:00:00Z", ...}
   ```

5. **Stop the service outright**, point the mail endpoint at a provider
   that now accepts deliveries, and **start a fresh process** against the
   same database file:

   ```text
   $ python -m accountsvc.cli serve --database state.db --bearer-token smoke-bearer-token \
       --mail-endpoint http://127.0.0.1:9291/mail --port 9293
   ```

6. **Invoke the authenticated retry route**, approval-driven, against the
   restarted process -- nothing survived in memory from step 2-4 except
   what was persisted:

   ```text
   $ POST /recovery/notifications/retry {"approval_id": "appr-smoke", "operator_id": "op-smoke",
       "organization_id": "org-smoke"}   Authorization: Bearer smoke-bearer-token
   200
   {
     "approval_id": "appr-smoke", "organization_id": "org-smoke", "status": "consumed",
     "processed": [{"notification_id": "notice-90088a200ee830473f0e2b19", "delivery_status": "delivered"}],
     "skipped": []
   }
   ```

7. **Read the redrive result** -- both the original failure and the
   successful retry, ids and outcomes only:

   ```text
   $ POST /redrive/result {"organization_id": "org-smoke", "request_ids": ["req-845a03c69f57ac391a7a28ec"]}
   200
   {
     "organization_id": "org-smoke",
     "results": [
       {"request_id": "req-845a03c69f57ac391a7a28ec",
        "attempts": [
          {"attempt_id": "attempt-fbe6c2fb6e68849a86c59bed", "outcome": "failure"},
          {"attempt_id": "attempt-5c249302d4e445ea57c77be0", "outcome": "success"}
        ]}
     ]
   }
   ```

The same coverage, plus bounded-claims and one-time-use edge cases, is
exercised automatically by `tests/test_retry_approval_two_process.py` and
`tests/test_redrive_result_two_process.py`.
