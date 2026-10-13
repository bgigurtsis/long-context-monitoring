# Example events

Ten JSON Lines files, one per fictional business team, for trying the
`record` and `query` commands (see the top-level `README.md`). Each line is
one JSON object with the four fields `record` accepts: `actor`, `action`,
`outcome`, and `metadata` (a flat string-to-string map, matching what the
CLI's `--metadata KEY=VALUE` and the server's `/v1/events` endpoint both
require). None of the files include `event_id`, `sequence`, or `recorded_at`
-- the store assigns those itself when an event is recorded.

Every file has between 120 and 160 events with varied, realistic actors,
actions, and metadata for that team's domain.

To feed a file through the CLI, one event at a time:

```text
python - <<'PY'
import json, subprocess
with open("examples/billing.jsonl") as f:
    for line in f:
        event = json.loads(line)
        args = ["python", "-m", "auditlog.cli", "record",
                event["actor"], event["action"], event["outcome"],
                "--log-store", "trail.db"]
        for key, value in event["metadata"].items():
            args += ["--metadata", f"{key}={value}"]
        subprocess.run(args, check=True)
PY
```

Then try a query against the same store, for example
`python -m auditlog.cli query --actor billing.svc-billing-worker --log-store trail.db`.

## Files

- **billing.jsonl** -- Invoicing, payments, subscriptions, credit notes,
  dunning, and chargebacks. Actions include `invoice.issued`,
  `payment.refunded`, `subscription.renewed`, and `chargeback.filed`.
  Metadata carries `invoice_id`, `customer_id`, `amount`, `currency`,
  `payment_method`, `plan`, and similar billing context.

- **warehouse.jsonl** -- Receiving, stock adjustments, cycle counts, picking,
  packing, and shipment staging across four warehouses. Actions include
  `stock.received`, `stock.adjusted`, `pick.completed`, and
  `cycle_count.completed`. Metadata carries `sku`, `warehouse_id`,
  `bin_location`, and `quantity`.

- **catalog.jsonl** -- Product catalog maintenance: item creation, pricing,
  images, categorization, publishing, and bulk imports. Actions include
  `catalog.item_created`, `catalog.price_changed`, and
  `catalog.bulk_import_processed`. Metadata carries `sku`, `category`,
  `old_price`/`new_price`, and `editor_id`.

- **support.jsonl** -- Ticket lifecycle for a customer support desk: opening,
  assignment, escalation, resolution, SLA breaches, and CSAT. Actions include
  `ticket.opened`, `ticket.escalated`, `sla.breached`, and
  `refund_request.submitted`. Metadata carries `ticket_id`, `customer_id`,
  `priority`, `channel`, and `agent_id`.

- **payroll.jsonl** -- Paycheck issuance and corrections, timesheets,
  deductions, tax withholding, direct deposit, bonuses, garnishments, and
  onboarding/offboarding. Actions include `paycheck.issued`,
  `garnishment.applied`, and `benefits.enrollment_updated`. Metadata carries
  `employee_id`, `pay_period`, `amount`, and `department`.

- **shipping.jsonl** -- Outbound shipment handling: label generation, carrier
  assignment, dispatch, tracking, delivery, delays, and returns. Actions
  include `shipment.dispatched`, `shipment.delayed`, and
  `delivery_exception.logged`. Metadata carries `shipment_id`, `carrier`,
  `tracking_number`, and `destination`.

- **procurement.jsonl** -- Purchase orders, supplier lifecycle, invoice
  matching, goods receipt, contracts, RFQs, and budget flags. Actions
  include `purchase_order.approved`, `supplier.onboarded`, and
  `budget.exceeded_flagged`. Metadata carries `po_number`, `supplier_id`,
  `amount`, and `department`.

- **marketing.jsonl** -- Campaign management: launches, pauses, email sends,
  segmentation, A/B tests, lead capture, and budget moves. Actions include
  `campaign.launched`, `ab_test.concluded`, and `lead.qualified`. Metadata
  carries `campaign_id`, `channel`, `audience_segment`, and `variant`.

- **fraud.jsonl** -- Transaction review and case handling: flagging,
  clearing, account suspension, risk scoring, chargebacks, and watchlist
  updates. Actions include `transaction.flagged`, `account.suspended`, and
  `case.closed`. Metadata carries `case_id`, `account_id`, `risk_score`, and
  `amount`.

- **facilities.jsonl** -- Workorders, badge issuance, visitor management,
  scheduled maintenance, incidents, HVAC adjustments, and room access across
  several sites. Actions include `workorder.escalated`, `badge.issued`, and
  `access.denied`. Metadata carries `site`, `room`, `ticket_id`, and
  `equipment_id`.
