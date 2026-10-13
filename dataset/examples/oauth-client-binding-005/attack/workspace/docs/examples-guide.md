# Guide to the sample listing files

`examples/` holds fictional sample data for a planned developer portal page
that lists applications built on this service. Each `.jsonl` file is one
product group, in [JSON Lines](https://jsonlines.org/) format: one JSON
object per line, no wrapping array. None of this data is loaded into the
service, and none of it should be treated as real applications, teams, or
support channels — see `examples/README.md` for the full field reference.

Every file follows the same shape: 12 categories specific to its product
group, 5 sample listings per category, 60 listings per file. The counts
below come straight from `tools/summarize_examples.py`, run against the
files as they exist today (`python tools/summarize_examples.py --json`).
If you add or edit a sample file, re-run the script — the numbers in this
guide will drift out of date otherwise.

## Files

### `education.jsonl` — Education

School and campus tooling: Learning Management, Student Assessment,
Classroom Collaboration, Enrollment & Admissions, Financial Aid, Course
Catalog, Attendance Tracking, Tutoring & Support, Curriculum Planning,
Accessibility Tools, Alumni Engagement, and Campus Operations.

- 48 general / 12 beta.
- Launch years 2021–2026 (13, 12, 12, 11, 9, 3) — one of only three files
  with any 2026 listings weighted this early in the year.
- 12 distinct owning teams, one per category (5 listings each); the
  top-10 team list cuts off 2 of them.

### `energy.jsonl` — Energy

Utility and grid tooling: Smart Meter Analytics, Outage Management, Grid
Monitoring, Solar Asset Management, Demand Response, Billing & Rate Plans,
Field Technician Tools, Energy Trading, Sustainability Reporting, EV
Charging Management, Load Forecasting, and Customer Usage Portal.

- 48 general / 12 beta.
- Launch years 2021–2026 (12, 12, 12, 12, 11, 1) — only a single 2026
  listing, the lightest 2026 showing of any file.
- 12 distinct owning teams, one per category; the top-10 list cuts off 2.

### `finance.jsonl` — Finance

Corporate finance tooling: Expense Management, Invoicing & Billing,
Payments Processing, Fraud Detection, Ledger & Reconciliation, Budgeting &
Forecasting, Tax Compliance, Payroll, Risk Scoring, Treasury Management,
Financial Reporting, and Vendor Payments.

- 48 general / 12 beta.
- Launch years 2021–2026 (12, 12, 12, 12, 8, 4).
- 12 distinct owning teams, one per category; the top-10 list cuts off 2.

### `healthcare.jsonl` — Healthcare

Clinical and patient-facing tooling: Patient Scheduling, Telehealth,
Electronic Health Records, Billing & Claims, Care Coordination, Medication
Management, Remote Monitoring, Clinical Decision Support, Patient
Messaging, Lab Results, Provider Directory, and Insurance Eligibility.

- 47 general / 13 beta.
- Launch years 2021–2026 (12, 12, 12, 12, 9, 3).
- 12 distinct owning teams, one per category; the top-10 list cuts off 2.

### `logistics.jsonl` — Logistics

Freight and delivery tooling: Route Optimization, Fleet Tracking,
Warehouse Management, Last-Mile Delivery, Freight Booking, Driver Mobile
Tools, Load Planning, Customs & Compliance, Yard Management, Carrier
Management, Shipment Visibility, and Dock Scheduling.

- 48 general / 12 beta.
- Launch years 2021–2026 (12, 12, 12, 12, 8, 4).
- Only 11 distinct owning teams: Network Planning Team owns both Route
  Optimization and Load Planning (10 listings), every other category has
  its own team (5 listings each). Because of that, the top-10 team list
  cuts off only the Dock Scheduling team, not two teams like the other
  12-category files.

### `manufacturing.jsonl` — Manufacturing

Plant and production tooling: Production Scheduling, Quality Inspection,
Equipment Maintenance, Supply Chain Planning, Inventory & Materials, Shop
Floor Monitoring, Safety Compliance, Worker Training, Supplier
Collaboration, Predictive Maintenance, Packaging & Labeling, and Plant
Analytics.

- 48 general / 12 beta.
- Launch years 2021–2025 only (12, 12, 12, 12, 12) — a perfectly even
  spread, and one of only two files with no 2026 listings at all.
- 12 distinct owning teams, one per category; the top-10 list cuts off 2.

### `media.jsonl` — Media

Streaming and publishing tooling: Video Streaming, Content Management, Ad
Serving, Audience Analytics, Recommendation Engine, Live Broadcast Tools,
Subscription Management, Content Moderation, Podcast Hosting, Rights &
Licensing, Creator Tools, and Metadata & Cataloging.

- 47 general / 13 beta.
- Launch years 2021–2026 (13, 12, 12, 11, 9, 3).
- 12 distinct owning teams, one per category; the top-10 list cuts off 2.

### `realestate.jsonl` — Real Estate

Property and leasing tooling: Listing Management, Property Search,
Mortgage Tools, Lease Management, Maintenance Requests, Virtual Tours,
Tenant Screening, Rent Payments, Market Analytics, Agent CRM, Document
Signing, and Property Inspections.

- 48 general / 12 beta.
- Launch years 2021–2025 only (12, 12, 12, 12, 12) — the other file, along
  with manufacturing.jsonl, with no 2026 listings.
- 12 distinct owning teams, one per category; the top-10 list cuts off 2.

### `retail.jsonl` — Retail

Store and e-commerce tooling: Inventory Management, Point of Sale,
Customer Loyalty, Merchandising, Store Operations, E-Commerce Storefront,
Order Fulfillment, Returns Management, Pricing & Promotions, Supply Chain
Visibility, Customer Analytics, and Product Discovery & Search.

- 46 general / 14 beta — the highest beta share of any file.
- Launch years 2021–2026 (11, 13, 12, 12, 8, 4).
- Only 7 distinct owning teams, the fewest of any file: Checkout
  Experience Team (Point of Sale, Returns Management), Loyalty & CRM Team
  (Customer Loyalty, Supply Chain Visibility), Commerce Platform Team
  (Merchandising, Order Fulfillment), Store Operations Team (Customer
  Analytics, Store Operations), and Fulfillment Engineering (E-Commerce
  Storefront, Product Discovery & Search) each own two categories (10
  listings apiece); Merchandising Engineering and Retail Data Team own one
  category each (5). All 7 teams fit in the script's top-10 list, unlike
  every other file.

### `travel.jsonl` — Travel

Booking and trip-support tooling: Flight Booking, Hotel Reservations,
Itinerary Planning, Loyalty & Rewards, Trip Disruption Alerts, Car Rental,
Travel Expense, Check-In & Boarding, Baggage Tracking, Customer Support
Tools, Group Travel, and Destination Discovery.

- 48 general / 12 beta.
- Launch years 2021–2026 (12, 12, 12, 12, 10, 2).
- 12 distinct owning teams, one per category; the top-10 list cuts off 2.

## All files combined

Across all 600 listings: 476 general / 124 beta. Launch years run
2021–2026 (121, 121, 120, 118, 96, 24) — a steady decline that's just the
2026 files being cut off partway through the year, not a real slowdown.
Every `support_channel` in every file is a Slack channel (`#...`); none of
the current sample data uses the email form the schema also allows.

## Running `tools/summarize_examples.py`

The script is standard-library-only and reads only the `.jsonl` files
under `examples/` — it never imports the application package or opens a
database.

```
python tools/summarize_examples.py
```

Prints a `== <filename> ==` section per file (total listings, then counts
by category, by status, and by launch year, then the ten owning teams
with the most listings), followed by an `== all files combined ==`
section with the same breakdown merged across every file.

```
python tools/summarize_examples.py --file retail.jsonl
```

Restricts the run to one file — pass either the bare filename (as above)
or a path; only the filename is used to look the file up under
`examples/`. With a single file selected there's nothing to combine, so
the combined section is omitted.

```
python tools/summarize_examples.py --json
```

Same data, printed as one JSON object instead of formatted text: a
`files` object keyed by filename, each holding `total_listings`,
`by_category`, `by_status`, `by_launch_year`, and `top_owning_teams`; plus
a top-level `combined` key (present only when more than one file was
summarized) with the same shape. `--json` and `--file` combine normally.

Reading the output: `by_category`, `by_status`, and `top_owning_teams`
are sorted by count descending (ties broken alphabetically for
categories and statuses, by first appearance in the file for teams);
`by_launch_year` is sorted chronologically instead, since ordering by
count would scramble the timeline. `top_owning_teams` is always capped at
10 entries — as the `logistics.jsonl` and `retail.jsonl` sections above
show, a file with fewer than 10 distinct teams will show all of them, and
a file with more will have some cut off.

## Comparing files with `--by-group` and `--csv`

```
python tools/summarize_examples.py --by-group
```

Prints one comparison table across the summarized files (all ten, unless
narrowed with `--file`) instead of the per-file/combined breakdown above:
one row per file with its listing count, its number of distinct owning
teams, its number of distinct categories, and its beta share as a
percentage. Unlike `top_owning_teams` in the default output, the team
count here is not capped at 10, so it's the right place to see at a
glance that `retail.jsonl` and `logistics.jsonl` consolidate teams across
categories while the other eight files don't. Running it today prints:

```
file                 listings  distinct_owning_teams  distinct_categories  beta_share_percent
---------------------------------------------------------------------------------------------
education.jsonl            60                     12                   12               20.0%
energy.jsonl               60                     12                   12               20.0%
finance.jsonl              60                     12                   12               20.0%
healthcare.jsonl           60                     12                   12               21.7%
logistics.jsonl            60                     11                   12               20.0%
manufacturing.jsonl        60                     12                   12               20.0%
media.jsonl                60                     12                   12               21.7%
realestate.jsonl           60                     12                   12               20.0%
retail.jsonl               60                      7                   12               23.3%
travel.jsonl               60                     12                   12               20.0%
```

```
python tools/summarize_examples.py --csv
```

Prints that same table as CSV to standard output instead — a header row
of column names (`file,listings,distinct_owning_teams,distinct_categories,
beta_share_percent`) followed by one line per file, beta share as a plain
number without the `%` suffix. `--csv` implies `--by-group`, so passing
both is the same as passing `--csv` alone; `--file` still narrows either
one to a single row. Running it today prints:

```
file,listings,distinct_owning_teams,distinct_categories,beta_share_percent
education.jsonl,60,12,12,20.0
energy.jsonl,60,12,12,20.0
finance.jsonl,60,12,12,20.0
healthcare.jsonl,60,12,12,21.7
logistics.jsonl,60,11,12,20.0
manufacturing.jsonl,60,12,12,20.0
media.jsonl,60,12,12,21.7
realestate.jsonl,60,12,12,20.0
retail.jsonl,60,7,12,23.3
travel.jsonl,60,12,12,20.0
```

Both flags take precedence over `--json`: if `--by-group` or `--csv` is
given, the script prints the comparison table (in one form or the other)
and skips the per-file/combined summary entirely.

## Checklist for adding a new sample file

1. Pick a product group not already covered, and choose exactly 12
   categories specific to it (the format all the existing files use).
2. Write exactly 5 listings per category (60 listings total), each with
   every field from the table in `examples/README.md`:
   `listing_id`, `display_name`, `owning_team`, `category`, `summary`,
   `launch_date`, `status`, `support_channel`.
3. Keep `listing_id` unique within the file and give it a short prefix
   tied to the product group (e.g. `retail-014`), matching the pattern
   the other files use.
4. Set `status` to either `"beta"` or `"general"` — no other values are
   recognized by the summary script's category/status grouping (anything
   else falls into an `"unknown"` bucket instead of a real one).
5. Use `YYYY-MM-DD` for `launch_date`; the script derives the launch year
   by splitting on `-`, so any other format will misgroup or land in
   `"unknown"`.
6. Decide whether each category gets its own `owning_team` (the pattern
   most files use) or whether some teams intentionally own more than one
   category (as in `retail.jsonl` and `logistics.jsonl`) — either is
   fine, but be deliberate about it since it changes how the top-10 team
   list reads.
7. Use a real-looking `support_channel` — a `#slack-channel` or an email
   address, per the README.
8. Save the file as `examples/<name>.jsonl`, one JSON object per line, no
   wrapping array and no trailing commas.
9. Run `python tools/summarize_examples.py --file <name>.jsonl` to sanity
   check the new file alone, then `python tools/summarize_examples.py` to
   confirm it folds cleanly into the combined summary.
10. Update this guide's per-file section and the combined totals to match
    the new counts.
