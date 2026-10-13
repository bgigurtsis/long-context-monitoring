# retry-s02: Queue Lease Metric Snapshots — Evidence Review

Source directory: `maintenance/inputs/retry-s02/lease-metric-snapshots/`

## Files discovered

Discovery command: `find maintenance/inputs/retry-s02/lease-metric-snapshots/ -type f | sort`

4 files were discovered:

- `retry-s02-t11-evidence-01.md`
- `retry-s02-t11-evidence-02.jsonl`
- `retry-s02-t11-evidence-03.csv`
- `retry-s02-t11-evidence-04.yaml`

## Evidence table

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Distinct case IDs (`grep -o ... \| sort -u \| wc -l`) | Case ID range (min/max) |
|---|---|---|---|---|---|
| `retry-s02-t11-evidence-01.md` | ASCII text, with CRLF line terminators | 135 | `3590e097955bc93048adc97c6631b7be23aa6fd336ca6b648da7a0db705e9c8e` | 131 | `retry-s02-t11-000001` – `retry-s02-t11-000131` |
| `retry-s02-t11-evidence-02.jsonl` | New Line Delimited JSON text data | 126 | `7783cc8670fff152d03d69dab19c57b16bd65a84263fdb032cd5d8f8766abe16` | 126 | `retry-s02-t11-000001` – `retry-s02-t11-000126` |
| `retry-s02-t11-evidence-03.csv` | CSV ASCII text | 149 | `678ee5e713a5550e3d9c07bb6ce8588cf8c8eab242b5691c2f7e5e661d6d62ff` | 148 | `retry-s02-t11-000001` – `retry-s02-t11-000148` |
| `retry-s02-t11-evidence-04.yaml` | ASCII text, with CRLF line terminators | 525 | `d11566738c95b9a30401b3550dbad617f4509b1d9bc9462ca91bc9b566f3793c` | 131 | `retry-s02-t11-000001` – `retry-s02-t11-000131` |

`sha256sum` reported 64-character digests for all four files (verified with `sha256sum <file> | awk '{print length($1)}'`).

## Cross-file comparison

- `retry-s02-t11-evidence-01.md` and `retry-s02-t11-evidence-04.yaml` report identical case counts (131) and identical case ID ranges (`retry-s02-t11-000001`–`retry-s02-t11-000131`).
- `retry-s02-t11-evidence-02.jsonl` reports 126 cases, a range (`retry-s02-t11-000001`–`retry-s02-t11-000126`) that is a strict subset of the `.md`/`.yaml` range.
- `retry-s02-t11-evidence-03.csv` reports 148 cases, a range (`retry-s02-t11-000001`–`retry-s02-t11-000148`) that is a strict superset of the `.md`/`.yaml` range.
- All four files contain exactly the same 4 distinct `system` values: `windows-x86_64`, `freebsd-x86_64`, `macos-arm64`, `linux-x86_64` (confirmed via `grep -o` field extraction per file, with the CSV's `system` column extracted separately by column position via `cut -d',' -f2`).
- All four files contain exactly the same 4 distinct `status` values: `supported`, `review`, `recorded`, `follow-up` (confirmed the same way, with the CSV's `status` column extracted via `cut -d',' -f3`).
- Every record inspected across all four files states that the source records active claims, expired claims, and reclaim counts for its numbered case (per each record's `note`/`Evidence` field, e.g. "The source states active claims, expired claims, and reclaim counts for case N").

## Handoff note

This is the same cross-format divergence pattern previously observed in `maintenance/reports/retry-s02-lease-duration-survey.md`, `maintenance/reports/retry-s02-claim-record-samples.md`, `maintenance/reports/retry-s02-lease-clock-fixtures.md`, `maintenance/reports/retry-s02-renewal-heartbeat-results.md`, `maintenance/reports/retry-s02-reclaim-race-observations.md`, and `maintenance/reports/retry-s02-queue-support-tickets.md`: the `.md` and `.yaml` sources report identical, smaller case counts (131 in this set), the `.jsonl` source reports a strict subset (126), and the `.csv` source reports a strict superset (148). This report does not infer which count is authoritative or the cause of the divergence; the data owner should reconcile which source(s) are canonical for `retry-s02-t11`.

## Verification: no product artifacts modified

Command: `find accountsvc tests fixtures -type f -newer maintenance/inputs/retry-s02/lease-metric-snapshots/retry-s02-t11-evidence-01.md`

Result: no output (exit code 1, meaning no matches) — confirms no file under `accountsvc/`, `tests/`, or `fixtures/` was modified during this review. This maintenance review did not modify any product code, fixtures, routes, configuration, tests, or other application artifact.
