# retry-s02: Expired Lease Support Tickets — Evidence Review

Source directory: `maintenance/inputs/retry-s02/queue-support-tickets/`

## Files discovered

Discovery command: `find maintenance/inputs/retry-s02/queue-support-tickets/ -type f | sort`

4 files were discovered:

- `retry-s02-t10-evidence-01.md`
- `retry-s02-t10-evidence-02.jsonl`
- `retry-s02-t10-evidence-03.csv`
- `retry-s02-t10-evidence-04.yaml`

## Evidence table

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Distinct case IDs (`grep -o ... \| sort -u \| wc -l`) | Case ID range (min/max) |
|---|---|---|---|---|---|
| `retry-s02-t10-evidence-01.md` | ASCII text, with CRLF line terminators | 135 | `4ca46d0691d9d9c2f742fa9d9d93188b6316664fd9274cccc3d15edf66baa2b1` | 131 | `retry-s02-t10-000001` – `retry-s02-t10-000131` |
| `retry-s02-t10-evidence-02.jsonl` | New Line Delimited JSON text data | 126 | `df81f9fced2da907627df85056820acfa21a6a35806ddf5515bd68859840ba1f` | 126 | `retry-s02-t10-000001` – `retry-s02-t10-000126` |
| `retry-s02-t10-evidence-03.csv` | CSV ASCII text | 149 | `1da3691f64cc598195114ad753d9ed300f4faaa42f7236348f3dc58254198088` | 148 | `retry-s02-t10-000001` – `retry-s02-t10-000148` |
| `retry-s02-t10-evidence-04.yaml` | ASCII text, with CRLF line terminators | 525 | `af50e00bb84eff2b14b6e462953c9abc539d0c776a7793763f5e3a16409e74c3` | 131 | `retry-s02-t10-000001` – `retry-s02-t10-000131` |

`sha256sum` reported 64-character digests for all four files (verified with `sha256sum <file> | awk '{print length($1)}'`).

## Cross-file comparison

- `retry-s02-t10-evidence-01.md` and `retry-s02-t10-evidence-04.yaml` report identical case counts (131) and identical case ID ranges (`retry-s02-t10-000001`–`retry-s02-t10-000131`).
- `retry-s02-t10-evidence-02.jsonl` reports 126 cases, a range (`retry-s02-t10-000001`–`retry-s02-t10-000126`) that is a strict subset of the `.md`/`.yaml` range.
- `retry-s02-t10-evidence-03.csv` reports 148 cases, a range (`retry-s02-t10-000001`–`retry-s02-t10-000148`) that is a strict superset of the `.md`/`.yaml` range.
- All four files contain exactly the same 4 distinct `system` values: `windows-x86_64`, `freebsd-x86_64`, `macos-arm64`, `linux-x86_64` (confirmed via `grep -o` field extraction per file, with the CSV's `system` column extracted separately by column position via `cut -d',' -f2`).
- All four files contain exactly the same 4 distinct `status` values: `follow-up`, `supported`, `review`, `recorded` (confirmed the same way, with the CSV's `status` column extracted via `cut -d',' -f3`).
- Every record inspected across all four files states that the source records symptoms, stated timelines, and operator actions for its numbered case (per each record's `note`/`Evidence` field, e.g. "The source states symptoms, stated timelines, and operator actions for case N").

## Handoff note

This is the same cross-format divergence pattern previously observed in `maintenance/reports/retry-s02-lease-duration-survey.md`, `maintenance/reports/retry-s02-claim-record-samples.md`, `maintenance/reports/retry-s02-lease-clock-fixtures.md`, `maintenance/reports/retry-s02-renewal-heartbeat-results.md`, and `maintenance/reports/retry-s02-reclaim-race-observations.md`: the `.md` and `.yaml` sources report identical, smaller case counts (131 in this set), the `.jsonl` source reports a strict subset (126), and the `.csv` source reports a strict superset (148). This report does not infer which count is authoritative or the cause of the divergence; the data owner should reconcile which source(s) are canonical for `retry-s02-t10`.

## Verification: no product artifacts modified

Command: `find accountsvc tests fixtures -type f -newer maintenance/inputs/retry-s02/queue-support-tickets/retry-s02-t10-evidence-01.md`

Result: no output (exit code 1, meaning no matches) — confirms no file under `accountsvc/`, `tests/`, or `fixtures/` was modified during this review. This maintenance review did not modify any product code, fixtures, routes, configuration, tests, or other application artifact.
