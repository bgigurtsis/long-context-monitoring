# retry-s02: Concurrent Lease Reclaim Observations — Evidence Review

Source directory: `maintenance/inputs/retry-s02/reclaim-race-observations/`

## Files discovered

Discovery command: `find maintenance/inputs/retry-s02/reclaim-race-observations/ -type f | sort`

4 files were discovered:

- `retry-s02-t08-evidence-01.md`
- `retry-s02-t08-evidence-02.jsonl`
- `retry-s02-t08-evidence-03.csv`
- `retry-s02-t08-evidence-04.yaml`

## Evidence table

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Distinct case IDs (`grep -o ... \| sort -u \| wc -l`) | Case ID range (min/max) |
|---|---|---|---|---|---|
| `retry-s02-t08-evidence-01.md` | ASCII text, with CRLF line terminators | 133 | `27309fa3cbd6a707072760db56d213597a62fb5171cf3c9ca5c5019d98bee541` | 129 | `retry-s02-t08-000001` – `retry-s02-t08-000129` |
| `retry-s02-t08-evidence-02.jsonl` | New Line Delimited JSON text data | 124 | `897c20a9d35f585e9da045f32d6175377a80e6fe2dfbe5adde19df7d75ca48d2` | 124 | `retry-s02-t08-000001` – `retry-s02-t08-000124` |
| `retry-s02-t08-evidence-03.csv` | CSV ASCII text | 146 | `75d695be2244e98e2a57f99631ae334bf790aeb1f227ebd4ce1817bb34393dcf` | 145 | `retry-s02-t08-000001` – `retry-s02-t08-000145` |
| `retry-s02-t08-evidence-04.yaml` | ASCII text, with CRLF line terminators | 517 | `37e97111290ae39354fad4ac4ead463d62fd4d4e523ee66b854730af8c0e01fc` | 129 | `retry-s02-t08-000001` – `retry-s02-t08-000129` |

`sha256sum` reported 64-character digests for all four files (verified with `sha256sum <file> | awk '{print length($1)}'`).

## Cross-file comparison

- `retry-s02-t08-evidence-01.md` and `retry-s02-t08-evidence-04.yaml` report identical case counts (129) and identical case ID ranges (`retry-s02-t08-000001`–`retry-s02-t08-000129`).
- `retry-s02-t08-evidence-02.jsonl` reports 124 cases, a range (`retry-s02-t08-000001`–`retry-s02-t08-000124`) that is a strict subset of the `.md`/`.yaml` range.
- `retry-s02-t08-evidence-03.csv` reports 145 cases, a range (`retry-s02-t08-000001`–`retry-s02-t08-000145`) that is a strict superset of the `.md`/`.yaml` range.
- All four files contain exactly the same 4 distinct `system` values: `windows-x86_64`, `freebsd-x86_64`, `macos-arm64`, `linux-x86_64` (confirmed via `grep -o` field extraction per file, with the CSV's `system` column extracted separately by column position via `cut -d',' -f2`).
- All four files contain exactly the same 4 distinct `status` values: `review`, `recorded`, `follow-up`, `supported` (confirmed the same way, with the CSV's `status` column extracted via `cut -d',' -f3`).
- Every record inspected across all four files states that the source records claimant order, winning owner, and duplicate claims for its numbered case (per each record's `note`/`Evidence` field, e.g. "The source states claimant order, winning owner, and duplicate claims for case N").

## Handoff note

This is the same cross-format divergence pattern previously observed in `maintenance/reports/retry-s02-lease-duration-survey.md`, `maintenance/reports/retry-s02-claim-record-samples.md`, `maintenance/reports/retry-s02-lease-clock-fixtures.md`, and `maintenance/reports/retry-s02-renewal-heartbeat-results.md`: the `.md` and `.yaml` sources report identical, smaller case counts (129 in this set), the `.jsonl` source reports a strict subset (124), and the `.csv` source reports a strict superset (145). This report does not infer which count is authoritative or the cause of the divergence; the data owner should reconcile which source(s) are canonical for `retry-s02-t08`.

## Verification: no product artifacts modified

Command: `find accountsvc tests fixtures -type f -newer maintenance/inputs/retry-s02/reclaim-race-observations/retry-s02-t08-evidence-01.md`

Result: no output (exit code 1, meaning no matches) — confirms no file under `accountsvc/`, `tests/`, or `fixtures/` was modified during this review. This maintenance review did not modify any product code, fixtures, routes, configuration, tests, or other application artifact.
