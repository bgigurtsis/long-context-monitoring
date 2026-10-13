# Sample application listings

This folder holds sample data for a planned developer portal page that lists
the applications built on this service. Each file is fictional sample data
for design and prototyping purposes only — nothing here is loaded into the
service, and none of it should be treated as real applications, teams, or
support channels.

## Format

Each `.jsonl` file is JSON Lines: one JSON object per line, no wrapping
array. Every listing has these fields:

| Field             | Description                                                        |
|-------------------|---------------------------------------------------------------------|
| `listing_id`      | Stable identifier, unique within the file (e.g. `retail-014`).      |
| `display_name`    | The application's name as shown on the portal.                      |
| `owning_team`     | The internal team responsible for the application.                  |
| `category`        | A subcategory within the product group (e.g. "Point of Sale").      |
| `summary`         | One or two sentences on what the application does for its users.    |
| `launch_date`     | The date the application launched, as `YYYY-MM-DD`.                 |
| `status`          | Either `beta` or `general`.                                         |
| `support_channel` | Where users can get help (a Slack channel or an email address).     |

## Files

Each file represents a fictional product group and contains 60 sample
listings drawn from 12 categories specific to that group (5 listings per
category).

- **retail.jsonl** — Store and e-commerce tooling: inventory, point of sale,
  loyalty, merchandising, store operations, storefronts, fulfillment,
  returns, pricing and promotions, supply chain visibility, customer
  analytics, and product discovery.
- **logistics.jsonl** — Freight and delivery tooling: route optimization,
  fleet tracking, warehouse management, last-mile delivery, freight
  booking, driver mobile tools, load planning, customs and compliance,
  yard management, carrier management, shipment visibility, and dock
  scheduling.
- **finance.jsonl** — Corporate finance tooling: expense management,
  invoicing and billing, payments processing, fraud detection, ledger and
  reconciliation, budgeting and forecasting, tax compliance, payroll, risk
  scoring, treasury management, financial reporting, and vendor payments.
- **media.jsonl** — Streaming and publishing tooling: video streaming,
  content management, ad serving, audience analytics, recommendations,
  live broadcast tools, subscription management, content moderation,
  podcast hosting, rights and licensing, creator tools, and metadata and
  cataloging.
- **education.jsonl** — School and campus tooling: learning management,
  student assessment, classroom collaboration, enrollment and admissions,
  financial aid, course catalog, attendance tracking, tutoring and
  support, curriculum planning, accessibility tools, alumni engagement,
  and campus operations.
- **healthcare.jsonl** — Clinical and patient-facing tooling: patient
  scheduling, telehealth, electronic health records, billing and claims,
  care coordination, medication management, remote monitoring, clinical
  decision support, patient messaging, lab results, provider directory,
  and insurance eligibility.
- **travel.jsonl** — Booking and trip-support tooling: flight booking,
  hotel reservations, itinerary planning, loyalty and rewards, trip
  disruption alerts, car rental, travel expense, check-in and boarding,
  baggage tracking, customer support tools, group travel, and destination
  discovery.
- **realestate.jsonl** — Property and leasing tooling: listing management,
  property search, mortgage tools, lease management, maintenance
  requests, virtual tours, tenant screening, rent payments, market
  analytics, agent CRM, document signing, and property inspections.
- **energy.jsonl** — Utility and grid tooling: smart meter analytics,
  outage management, grid monitoring, solar asset management, demand
  response, billing and rate plans, field technician tools, energy
  trading, sustainability reporting, EV charging management, load
  forecasting, and customer usage portal.
- **manufacturing.jsonl** — Plant and production tooling: production
  scheduling, quality inspection, equipment maintenance, supply chain
  planning, inventory and materials, shop floor monitoring, safety
  compliance, worker training, supplier collaboration, predictive
  maintenance, packaging and labeling, and plant analytics.
