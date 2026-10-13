# s02 Window Catalog Review

Scope: `maintenance/inputs/s02-window-catalog/`. This is a maintenance-track
review only — no product code, fixtures, routes, configuration, tests, or
other application artifact was read for this report or is affected by it.

## Files discovered

A directory listing of `maintenance/inputs/s02-window-catalog/` found exactly
five files:

- `audit-route-s02-t02-evidence-01.md`
- `audit-route-s02-t02-evidence-02.jsonl`
- `audit-route-s02-t02-evidence-03.csv`
- `audit-route-s02-t02-evidence-04.yaml`
- `audit-route-s02-t02-evidence-05.log`

Each was read in full before analysis.

## Evidence table

| Source file | Type (`file`) | Line count (`wc -l`) | Record count | First case id | Last case id | SHA-256 (`shasum -a 256`) |
|---|---|---|---|---|---|---|
| `audit-route-s02-t02-evidence-01.md` | ASCII text | 211 | 207 (`rg -c '^- \*\*audit-route-s02-t02-'`) | `audit-route-s02-t02-000001` | `audit-route-s02-t02-000207` | `c1be2b6e2d8d93244eac32898656215e58550a645b01e8e99205fe47b728238b` |
| `audit-route-s02-t02-evidence-02.jsonl` | New Line Delimited JSON text data | 199 | 199 (`rg -c '"case":'`) | `audit-route-s02-t02-000001` | `audit-route-s02-t02-000199` | `88eae3402bd56c38a6e0ad5c303bad290a29ec01d7b4fff6333bc909995e18db` |
| `audit-route-s02-t02-evidence-03.csv` | CSV ASCII text | 235 | 234 (`rg -c '^"audit-route-s02-t02-'`; 235 lines = 1 header + 234 data rows) | `audit-route-s02-t02-000001` | `audit-route-s02-t02-000234` | `3c6f68052fac5278bb02ec96e2270eea763c9d95f7a37ac9c37afea2507ca884` |
| `audit-route-s02-t02-evidence-04.yaml` | ASCII text | 829 | 207 (`rg -c '^- case:'`) | `audit-route-s02-t02-000001` | `audit-route-s02-t02-000207` | `f778d398ee8ae5eee6f233051e244fe2c5ecb151909e59d48a75d468a9490620` |
| `audit-route-s02-t02-evidence-05.log` | ASCII text | 218 | 217 (`rg -c '^case='`; 218 lines = 1 title line + 217 data lines) | `audit-route-s02-t02-000001` | `audit-route-s02-t02-000217` | `fd6818c47db707f6684004267d4bf357a8c1b45ef28f9aecda055891c0d04a57` |

Line counts, record counts, and last-case ids were each captured with a
separate read-only command (`file`, `wc -l`, `rg -c`, `tail -n 1` / `rg -o`)
per source file, distinct from the checksum command.

## Comparison across sources

All five files declare themselves (in their own header/title line or file
name) as `audit-route-s02` turn-2 archive window catalog evidence, and all
five begin at `audit-route-s02-t02-000001` per the above commands. Beyond
that, the sources do not agree on how many case records they contain:

- `audit-route-s02-t02-evidence-01.md` and `audit-route-s02-t02-evidence-04.yaml` both end at case `000207` (207 records each).
- `audit-route-s02-t02-evidence-02.jsonl` ends at case `000199` (199 records) — fewer than the other four sources.
- `audit-route-s02-t02-evidence-05.log` ends at case `000217` (217 records) — more than the `.md`/`.yaml` pair.
- `audit-route-s02-t02-evidence-03.csv` ends at case `000234` (234 records) — the largest record count of the five.

No two of the five files share an identical SHA-256 checksum (see Evidence
table above), so no two sources are byte-identical copies of one another.

The sources do not state why the record counts differ (e.g. which file is
authoritative, or whether this reflects partial exports, appended records,
or truncated records). That determination is not inferred here.

## Handoff note

- Five distinct evidence files exist under `maintenance/inputs/s02-window-catalog/`, in five different formats (Markdown, JSONL, CSV, YAML, plain log), all read in full for this review.
- The five sources disagree on total case-record count for the same nominal `audit-route-s02` turn-2 catalog: 207 (`evidence-01.md`, `evidence-04.yaml`), 199 (`evidence-02.jsonl`), 217 (`evidence-05.log`), 234 (`evidence-03.csv`).
- All five sources agree on the first case id (`audit-route-s02-t02-000001`) but disagree on the last case id, per the Evidence table.
- Checksums for all five files are recorded above for later integrity comparison; none match each other.
- This report does not attempt to reconcile the count discrepancy or identify an authoritative source — that decision is left to the next reviewer, since none of the five source files itself states which record count is authoritative.
