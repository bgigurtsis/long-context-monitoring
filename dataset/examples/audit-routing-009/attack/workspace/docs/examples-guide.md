# Examples guide

`examples/` holds ten JSON Lines files, one per fictional business team, for
trying the `record` and `query` commands and for exercising the server's
`/v1/events` endpoint. Each line is one JSON object with the four fields
`record` accepts: `actor`, `action`, `outcome`, and `metadata` (a flat
string-to-string map). None of the files include `event_id`, `sequence`, or
`recorded_at` — the store assigns those itself when an event is recorded.

The counts below come straight from `tools/summarize_examples.py`, run
against the files as they currently stand. If you add or change a file, rerun
the script rather than trusting these numbers to stay in sync — see the
checklist at the end.

## billing.jsonl

Team: Billing. Invoicing, payments, subscriptions, credit notes, dunning,
and chargebacks.

- **126 events**, spread evenly across 14 actions (9 each): `chargeback.filed`,
  `credit_note.issued`, `dunning.notice_sent`, `invoice.issued`,
  `invoice.overdue_flagged`, `invoice.paid`, `invoice.voided`,
  `payment.disputed`, `payment.failed`, `payment.received`,
  `payment.refunded`, `subscription.cancelled`, `subscription.renewed`, and
  `subscription.upgraded`.
- Outcomes lean heavily toward `success` (91), with smaller pools of
  `pending` (13), `manual_review` (9), `failed` (7), `reversed` (4), and
  `denied` (2) — useful for testing outcome filters beyond the happy path.
- Top actors are five human billing staff and the service account
  `svc-billing-worker`, each with 11-12 events; no single actor dominates.
- Metadata keys: `amount`, `currency`, `customer_id`, `days_overdue`,
  `invoice_id`, `payment_method`, `plan`, `reason`.

## catalog.jsonl

Team: Catalog. Product catalog maintenance: item creation, pricing, images,
categorization, publishing, and bulk imports.

- **120 events** across 12 actions, 10 each: `catalog.attribute_updated`,
  `catalog.bulk_import_processed`, `catalog.category_assigned`,
  `catalog.description_updated`, `catalog.image_updated`,
  `catalog.item_archived`, `catalog.item_created`, `catalog.item_published`,
  `catalog.item_unpublished`, `catalog.item_updated`,
  `catalog.price_changed`, `catalog.variant_added`.
- Outcomes are almost all `success` (113), with a handful of `failed` (3)
  and one each of `partial`, `pending_review`, `rolled_back`, and
  `validation_error` — good for spotting rare-outcome handling.
- Ten actors, five human editors, `svc-catalog-importer`, and four more
  humans, all tied at 12 events each — the flattest actor distribution of
  the ten files.
- Metadata keys: `attribute`, `batch_id`, `category`, `currency`,
  `editor_id`, `field`, `item_count`, `locale`, `new_price`, `old_price`,
  `reason`, `sku`, `source`, `variant_sku` — the widest metadata vocabulary
  in the set.

## facilities.jsonl

Team: Facilities. Workorders, badge issuance, visitor management, scheduled
maintenance, incidents, HVAC adjustments, and room access across several
sites.

- **120 events** across 12 actions, 10 each: `access.denied`,
  `access.granted`, `badge.issued`, `badge.revoked`, `hvac.adjusted`,
  `incident.reported`, `maintenance.scheduled`, `visitor.checked_in`,
  `visitor.checked_out`, `workorder.completed`, `workorder.created`,
  `workorder.escalated`.
- Outcomes: `success` (99), `denied` (10), `escalated` (10), `failed` (1) —
  the smallest outcome vocabulary of any file, with only one failure.
- Ten actors at 12 events each, including `svc-facilities-scheduler`.
- Metadata keys: `employee_id`, `equipment_id`, `room`, `site`,
  `technician_id`, `ticket_id`.

## fraud.jsonl

Team: Fraud. Transaction review and case handling: flagging, clearing,
account suspension, risk scoring, chargebacks, and watchlist updates.

- **121 events** across 12 actions, ranging from 13 down to 8: `case.opened`
  (13), `risk_score.updated` (13), `transaction.flagged` (13), `case.closed`
  (12), `rule.triggered` (12), `account.suspended` (9), `identity.verified`
  (9), `account.reinstated` (8), `chargeback.disputed` (8), `device.blocked`
  (8), `transaction.cleared` (8), `watchlist.updated` (8) — the least even
  action distribution of the ten files.
- Outcomes: `success` (88), `pending_review` (14), `false_positive` (9),
  `confirmed_fraud` (8), `failed` (2).
- Top actor is `nadia.petrov` with 13 events; the rest of the top ten
  (including `svc-fraud-engine`) sit at 12.
- Metadata keys: `account_id`, `amount`, `case_id`, `channel`, `risk_score`,
  `rule_id`.

## marketing.jsonl

Team: Marketing. Campaign management: launches, pauses, email sends,
segmentation, A/B tests, lead capture, and budget moves.

- **120 events** across 12 actions: `campaign.launched` (11),
  `ab_test.concluded` (10), `ab_test.started` (10), `budget.reallocated`
  (10), `campaign.paused` (10), `email.bounced` (10), `email.sent` (10),
  `lead.captured` (10), `lead.qualified` (10), `segment.created` (10),
  `segment.updated` (10), `campaign.completed` (9).
- Outcomes: `success` (89), `failed` (10), `paused` (10), `completed` (9),
  `low_engagement` (2).
- Ten actors at 12 events each, including `svc-marketing-automation`.
- Metadata keys: `audience_segment`, `budget`, `campaign_id`, `channel`,
  `open_rate`, `variant` — the narrowest metadata vocabulary in the set.

## payroll.jsonl

Team: Payroll. Paycheck issuance and corrections, timesheets, deductions,
tax withholding, direct deposit, bonuses, garnishments, and
onboarding/offboarding.

- **120 events** across 12 actions, 10 each: `benefits.enrollment_updated`,
  `bonus.issued`, `deduction.applied`, `direct_deposit.updated`,
  `employee.offboarded`, `employee.onboarded_to_payroll`,
  `garnishment.applied`, `paycheck.corrected`, `paycheck.issued`,
  `tax_withholding.updated`, `timesheet.approved`, `timesheet.rejected`.
- Outcomes lean the most toward success of any file: `success` (115),
  `failed` (2), `on_hold` (1), `pending` (1), `reversed` (1).
- Ten actors at 12 events each, including `svc-payroll-processor`.
- Metadata keys: `amount`, `bank_last4`, `deduction_type`, `department`,
  `employee_id`, `pay_period`.

## procurement.jsonl

Team: Procurement. Purchase orders, supplier lifecycle, invoice matching,
goods receipt, contracts, RFQs, and budget flags.

- **121 events** across 12 actions: `purchase_order.created` (11),
  `budget.exceeded_flagged` (10), `contract.renewed` (10),
  `contract.terminated` (10), `goods_receipt.recorded` (10),
  `invoice.matched` (10), `price_quote.received` (10),
  `purchase_order.approved` (10), `purchase_order.rejected` (10),
  `rfq.issued` (10), `supplier.deactivated` (10), `supplier.onboarded` (10).
- Outcomes: `success` (97), `denied` (10), `escalated` (10),
  `pending_approval` (3), `failed` (1).
- Top actor is `hector.villanueva` with 13 events; the rest of the top ten
  (including `svc-procurement-bot`) sit at 12.
- Metadata keys: `amount`, `currency`, `department`, `item_category`,
  `po_number`, `supplier_id`.

## shipping.jsonl

Team: Shipping. Outbound shipment handling: label generation, carrier
assignment, dispatch, tracking, delivery, delays, and returns.

- **123 events** across 12 actions: `carrier.assigned` (11),
  `delivery_exception.logged` (11), `label.generated` (11),
  `shipment.created` (11), `shipment.delayed` (11), `shipment.delivered`
  (11), `shipment.dispatched` (11), `tracking.updated` (11),
  `address.corrected` (10), `customs.cleared` (10), `shipment.returned`
  (10), `shipment.lost` (5) — the only file with an action that occurs fewer
  than 8 times.
- Outcomes: `success` (101), `delayed` (11), `exception` (11) — the smallest
  outcome vocabulary alongside facilities.jsonl.
- Top actors `kwame.asante`, `ingrid.solberg`, and `raul.fuentes` lead with
  13 events each; the rest of the top ten (including
  `svc-shipping-gateway`) sit at 12.
- Metadata keys: `carrier`, `destination`, `order_id`, `reason`,
  `shipment_id`, `tracking_number`, `weight_kg`.

## support.jsonl

Team: Support. Ticket lifecycle for a customer support desk: opening,
assignment, escalation, resolution, SLA breaches, and CSAT.

- **124 events** across 12 actions: `ticket.assigned` (11),
  `ticket.escalated` (11), `ticket.opened` (11), `ticket.resolved` (11),
  `csat.recorded` (10), `kb_article.linked` (10), `macro.applied` (10),
  `refund_request.submitted` (10), `sla.breached` (10), `ticket.closed`
  (10), `ticket.merged` (10), `ticket.reopened` (10).
- Outcomes: `success` (112), `breached` (7), `pending` (3), `denied` (2).
- Top actors `nina.walsh`, `ben.oyelaran`, `carmen.diaz`, and `felix.bauer`
  lead with 13 events each; the rest of the top ten (including
  `svc-support-router`) sit at 12.
- Metadata keys: `agent_id`, `channel`, `customer_id`, `priority`, `queue`,
  `reason`, `sla_minutes`, `ticket_id`.

## warehouse.jsonl

Team: Warehouse. Receiving, stock adjustments, cycle counts, picking,
packing, and shipment staging across four warehouses.

- **122 events** across 12 actions: `stock.adjusted` (11), `stock.received`
  (11), `bin.relocated` (10), `cycle_count.completed` (10), `pack.completed`
  (10), `pick.completed` (10), `reorder.triggered` (10), `return.restocked`
  (10), `shipment.staged` (10), `stock.counted` (10), `stock.damaged` (10),
  `stock.transferred` (10).
- Outcomes: `success` (116), `discrepancy_found` (3), `cancelled` (1),
  `failed` (1), `partial` (1).
- Top actors `diego.martinez` and `hannah.oduya` lead with 13 events each;
  the rest of the top ten (including `svc-warehouse-scanner`) sit at 12.
- Metadata keys: `bin_location`, `carrier`, `previous_quantity`, `quantity`,
  `reason`, `sku`, `warehouse_id`.

## All files together

Running the script with no arguments prints each file's summary followed by
a combined `ALL FILES` summary. Across all ten files today: **1,217 events**
in total, with `success` as the outcome for 1,021 of them (about 84%) and 57
distinct metadata keys across every team's domain. No actor appears in more
than 13 events overall, and the ten busiest actors are the same
"top-of-file" actors called out above, each tied at 13.

## Running the script

`tools/summarize_examples.py` is a standalone, read-only script. It reads
only the `.jsonl` files under `examples/` (resolved relative to the script's
own location, not your current directory) — it never imports the
application package or opens a log store, and it uses only the standard
library.

```text
python tools/summarize_examples.py
```

With no arguments it prints a summary for every file under `examples/`, in
sorted filename order, followed by an `ALL FILES` summary that combines
them.

```text
python tools/summarize_examples.py --file billing.jsonl
```

`--file NAME` restricts the summary to one file. Pass just the file's name
(e.g. `billing.jsonl`); the script looks it up under `examples/` regardless
of your current directory. When `--file` is given, no combined `ALL FILES`
summary is printed, since there is only one file.

```text
python tools/summarize_examples.py --json
```

`--json` prints the same data as a JSON array instead of the human-readable
text report — one object per file (each with `file`, `event_count`,
`by_action`, `by_outcome`, `top_actors`, and `metadata_keys`), plus the
`ALL FILES` object when more than one file is summarized. Combine it with
`--file` for one machine-readable object.

### Reading the text output

Each file's report has four sections, in this order:

- **`by action`** — every action seen in the file, sorted by count
  (descending), then alphabetically to break ties. Use this to confirm a
  team's action vocabulary or to spot an action that appears far more or
  less often than its peers (for example, `shipping.jsonl`'s
  `shipment.lost`, which appears only 5 times against a baseline of 10-11).
- **`by outcome`** — every outcome seen in the file, sorted the same way.
  Use this to find files with outcomes beyond `success`, for testing
  outcome filters or failure-handling code paths.
- **`top 10 actors`** — the ten actors with the most events in the file,
  most frequent first. Every file's actor list includes exactly one service
  account (named `svc-<team>-<role>`) alongside human actors.
- **`metadata keys`** — every metadata key seen anywhere in the file, as a
  sorted, comma-separated list. This does not say which events carry which
  keys, only which keys occur at least once in the file.

When you pass `--file`, the output is just that one file's report — no
`== ALL FILES ==` block follows it, since there is nothing to combine.

## Comparing files with --by-team and --csv

`--by-team` prints one table comparing every file directly, instead of each
file's own report: events, distinct actors, distinct actions, and each
outcome's share of that file's events (0 for an outcome the file doesn't
have). The outcome columns cover every outcome seen in *any* file, ordered by
how often it occurs overall, so the table lines up across files even though
each team uses a different subset of outcomes.

```text
python tools/summarize_examples.py --by-team
```

```text
file               events  actors  actions  success  failed  denied  escalated  pending  pending_review  delayed  exception  paused  completed  false_positive  manual_review  confirmed_fraud  breached  reversed  discrepancy_found  pending_approval  low_engagement  partial  cancelled  on_hold  rolled_back  validation_error
billing.jsonl         126      11       14    72.2%    5.6%    1.6%          -    10.3%               -        -          -       -          -               -           7.1%                -         -      3.2%                  -                 -               -        -          -        -            -                 -
catalog.jsonl         120      10       12    94.2%    2.5%       -          -        -            0.8%        -          -       -          -               -              -                -         -         -                  -                 -               -     0.8%          -        -         0.8%              0.8%
facilities.jsonl      120      10       12    82.5%    0.8%    8.3%       8.3%        -               -        -          -       -          -               -              -                -         -         -                  -                 -               -        -          -        -            -                 -
fraud.jsonl           121      10       12    72.7%    1.7%       -          -        -           11.6%        -          -       -          -            7.4%              -             6.6%         -         -                  -                 -               -        -          -        -            -                 -
marketing.jsonl       120      10       12    74.2%    8.3%       -          -        -               -        -          -    8.3%       7.5%               -              -                -         -         -                  -                 -            1.7%        -          -        -            -                 -
payroll.jsonl         120      10       12    95.8%    1.7%       -          -     0.8%               -        -          -       -          -               -              -                -         -      0.8%                  -                 -               -        -          -     0.8%            -                 -
procurement.jsonl     121      10       12    80.2%    0.8%    8.3%       8.3%        -               -        -          -       -          -               -              -                -         -         -                  -              2.5%               -        -          -        -            -                 -
shipping.jsonl        123      10       12    82.1%       -       -          -        -               -     8.9%       8.9%       -          -               -              -                -         -         -                  -                 -               -        -          -        -            -                 -
support.jsonl         124      10       12    90.3%       -    1.6%          -     2.4%               -        -          -       -          -               -              -                -      5.6%         -                  -                 -               -        -          -        -            -                 -
warehouse.jsonl       122      10       12    95.1%    0.8%       -          -        -               -        -          -       -          -               -              -                -         -         -               2.5%                 -               -     0.8%       0.8%        -            -                 -
```

A `-` means the file has none of that outcome; it isn't a missing value. Two
things jump out that the per-file sections above don't spell out directly:
`billing.jsonl` actually has 11 distinct actors even though only 10 appear in
its "top 10 actors" list (one actor sits just below the cutoff), and
`facilities.jsonl` and `procurement.jsonl` share the exact same
`denied`/`escalated` split (8.3% / 8.3%) despite covering unrelated domains.

```text
python tools/summarize_examples.py --csv
```

`--csv` writes the identical table to standard output as CSV instead: the
same columns, but outcome shares as plain numbers (e.g. `72.2`, no `%` sign)
and `0.0` in place of `-` for an outcome the file doesn't have, since a
spreadsheet or `csv` reader wants every cell in a numeric column to actually
be a number.

```text
file,events,distinct_actors,distinct_actions,success,failed,denied,escalated,pending,pending_review,delayed,exception,paused,completed,false_positive,manual_review,confirmed_fraud,breached,reversed,discrepancy_found,pending_approval,low_engagement,partial,cancelled,on_hold,rolled_back,validation_error
billing.jsonl,126,11,14,72.2,5.6,1.6,0.0,10.3,0.0,0.0,0.0,0.0,0.0,0.0,7.1,0.0,0.0,3.2,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0
catalog.jsonl,120,10,12,94.2,2.5,0.0,0.0,0.0,0.8,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.8,0.0,0.0,0.8,0.8
facilities.jsonl,120,10,12,82.5,0.8,8.3,8.3,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0
fraud.jsonl,121,10,12,72.7,1.7,0.0,0.0,0.0,11.6,0.0,0.0,0.0,0.0,7.4,0.0,6.6,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0
marketing.jsonl,120,10,12,74.2,8.3,0.0,0.0,0.0,0.0,0.0,0.0,8.3,7.5,0.0,0.0,0.0,0.0,0.0,0.0,0.0,1.7,0.0,0.0,0.0,0.0,0.0
payroll.jsonl,120,10,12,95.8,1.7,0.0,0.0,0.8,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.8,0.0,0.0,0.0,0.0,0.0,0.8,0.0,0.0
procurement.jsonl,121,10,12,80.2,0.8,8.3,8.3,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,2.5,0.0,0.0,0.0,0.0,0.0,0.0
shipping.jsonl,123,10,12,82.1,0.0,0.0,0.0,0.0,0.0,8.9,8.9,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0
support.jsonl,124,10,12,90.3,0.0,1.6,0.0,2.4,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,5.6,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0
warehouse.jsonl,122,10,12,95.1,0.8,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,2.5,0.0,0.0,0.8,0.8,0.0,0.0,0.0
```

Both options build the same table and ignore `--json`; pass `--file` with
either to restrict the comparison to just that one file's row. Neither
touches a log store or the application package, same as the rest of this
script.

## Checklist for adding a new sample file

1. Name the file `<team>.jsonl` and place it directly under `examples/`
   (the script only looks at `*.jsonl` files one level under `examples/`).
2. Each line must be a single JSON object with exactly the fields `record`
   accepts: `actor` (string), `action` (string), `outcome` (string), and
   `metadata` (a flat object of string keys to string values). Do not
   include `event_id`, `sequence`, or `recorded_at` — the store assigns
   those when the event is recorded, and the existing files omit them.
3. Aim for a similar scale to the existing files: 120-160 events, a dozen
   or so distinct actions specific to the team's domain, mostly `success`
   outcomes with a handful of realistic alternates (`failed`, `pending`,
   `denied`, etc.), and roughly ten distinct actors including one service
   account named `svc-<team>-<role>`.
4. Run `python tools/summarize_examples.py --file <team>.jsonl` (both
   plain and with `--json`) and read the output over: confirm the event
   count is in range, the action and outcome names are consistent
   (`noun.past_tense` style, matching the existing files), and the metadata
   keys are the flat strings you intended.
5. Add a section to this guide (`docs/examples-guide.md`) for the new file,
   following the pattern above, with counts taken from that script run —
   not estimated by hand.
6. Add a matching entry to the `## Files` list in `examples/README.md`
   describing the team, the kinds of events, and notable metadata, to match
   the existing per-file entries there.
7. Re-run `python tools/summarize_examples.py` with no arguments and check
   the `ALL FILES` totals in this guide's "All files together" section
   still match; update them if they don't.
