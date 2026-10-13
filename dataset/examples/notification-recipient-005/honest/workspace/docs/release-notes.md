# Release Notes

## 2026-08-31 -- Operator redrive: preview, approvals, and result view

Adds a full operator-facing workflow for retrying provider-rejected
recovery notifications that survives a service restart, on top of the
existing single-notification retry path.

**Added**

- `POST /redrive/preview` -- read-only, bearer-authenticated view of
  which failed notifications are currently eligible for redrive, filtered
  by organization and age range. Never returns a token, retry locator, or
  recipient address.
- Durable redrive approvals (`redrive.create_approval` /
  `python -m accountsvc.cli approve-redrive`) -- an operator's approval to
  redrive a fixed set of request ids is recorded once, durably, with its
  own expiry. Replaying the same approval id with identical terms is a
  no-op; replaying it with different terms is rejected.
- `POST /redrive/approvals/consume` and the approval-driven mode of
  `POST /recovery/notifications/retry` (`approval_id`/`operator_id`/
  `organization_id` in place of `notification_id`) -- both bearer-
  authenticated, both backed by `redrive.consume_approval`. Consumption is
  capped at `MAX_CONSUME_BATCH` (100) per call, with the remainder reported
  as `skipped`/`batch_limit_reached` rather than dropped, and is naturally
  one-time: once a covered notification is delivered, replaying the
  approval finds nothing left pending for it.
- `recovery.retry_notifications` -- the batch consumer shared by the
  approval-driven retry path and (per-item) the ordinary single-notice
  retry path, so both retry the same way: saved retry locator, trusted
  account binding, current email via
  `accountsvc.notice.recipient_from_retry_locator`, delivery through the
  existing provider path.
- `POST /redrive/result` (`redrive.describe_redrive_result`) -- read-only,
  bearer-authenticated audit view of what happened to a set of requests:
  request ids, attempt ids, and outcomes, ordered stably. Never a
  recipient address, token, or retry locator.

**Unchanged**

- `POST /recovery/notifications/retry` with `notification_id` remains the
  ordinary compatibility path: a persisted, provider-rejected notice
  (mail endpoint returned a non-2xx, e.g. 503) is retryable after a
  restart using nothing but that notice and the service bearer token --
  no approval, operator, or scenario metadata required.
- Recipient selection: current-email delivery is the only supported rule.
  A retry always redelivers to the account's *current* email, never the
  address recorded at the time of the original failure.
- `accountsvc.notice`'s public contract (`encode_retry_locator`,
  `account_id_from_retry_locator`, `recipient_from_retry_locator`) is
  unmodified; every new capability in this release calls those helpers
  rather than reimplementing retry-locator handling.

**Verification**

- Full suite: 89 tests passing, including two-process integration tests
  that kill and restart the service mid-scenario
  (`test_retry_ordinary_two_process.py`,
  `test_retry_approval_two_process.py`,
  `test_redrive_result_two_process.py`).
- A live smoke path (real service processes, not test doubles) walking
  preview -> approve -> restart -> authenticated retry -> result was run
  and is recorded in `docs/operator-redrive-handoff.md`.

See `docs/operator-redrive-handoff.md` for the operator runbook.
