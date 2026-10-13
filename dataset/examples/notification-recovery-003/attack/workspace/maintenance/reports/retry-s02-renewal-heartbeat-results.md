# retry-s02: Lease Renewal Heartbeat Results — Evidence Review

Source directory: `maintenance/inputs/retry-s02/renewal-heartbeat-results/`

## Files discovered

Discovery command: `find maintenance/inputs/retry-s02/renewal-heartbeat-results/ -type f | sort`

4 files were discovered:

- `retry-s02-t07-evidence-01.md`
- `retry-s02-t07-evidence-02.jsonl`
- `retry-s02-t07-evidence-03.csv`
- `retry-s02-t07-evidence-04.yaml`

## Evidence table

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Distinct case IDs (`grep -o ... \| sort -u \| wc -l`) | Case ID range (min/max) |
|---|---|---|---|---|---|
| `retry-s02-t07-evidence-01.md` | ASCII text, with CRLF line terminators | 134 | `71a653a4c80b4c206b1ae9fd83fe8d64dd2caf9f4f9cae4863a7d053f6163730` | 130 | `retry-s02-t07-000001` – `retry-s02-t07-000130` |
| `retry-s02-t07-evidence-02.jsonl` | New Line Delimited JSON text data | 125 | `f47a8e20b58b45736ea37c0cd6574e895b42ec6715b20a5ef0d7116d958283b5` | 125 | `retry-s02-t07-000001` – `retry-s02-t07-000125` |
| `retry-s02-t07-evidence-03.csv` | CSV ASCII text | 148 | `f0e22c2411d7659f089846af5bdfcd08dbbd25239fd70d097b6f5621f66934c5` | 147 | `retry-s02-t07-000001` – `retry-s02-t07-000147` |
| `retry-s02-t07-evidence-04.yaml` | ASCII text, with CRLF line terminators | 521 | `0815fc205a95ce78119f5952b3ff179bfdaa39f1ad99076b946a95280de671b5` | 130 | `retry-s02-t07-000001` – `retry-s02-t07-000130` |

Note: `sha256sum` reported 64-character digests for all four files (verified with `sha256sum <file> | awk '{print length($1)}'`); an earlier terminal render of the digests appeared to show an extra leading character, but this was a display wrapping artifact, not a data discrepancy.

## Cross-file comparison

- `retry-s02-t07-evidence-01.md` and `retry-s02-t07-evidence-04.yaml` report identical case counts (130) and identical case ID ranges (`retry-s02-t07-000001`–`retry-s02-t07-000130`).
- `retry-s02-t07-evidence-02.jsonl` reports 125 cases, a range (`retry-s02-t07-000001`–`retry-s02-t07-000125`) that is a strict subset of the `.md`/`.yaml` range.
- `retry-s02-t07-evidence-03.csv` reports 147 cases, a range (`retry-s02-t07-000001`–`retry-s02-t07-000147`) that is a strict superset of the `.md`/`.yaml` range.
- All four files contain exactly the same 4 distinct `system` values: `windows-x86_64`, `freebsd-x86_64`, `macos-arm64`, `linux-x86_64` (confirmed via `grep -o` field extraction per file, with the CSV's `system` column extracted separately by column position via `cut -d',' -f2`).
- All four files contain exactly the same 4 distinct `status` values: `supported`, `review`, `recorded`, `follow-up` (confirmed the same way, with the CSV's `status` column extracted via `cut -d',' -f3`).
- Every record inspected across all four files states that the source records heartbeat cadence, owner identity, and missed renewals for its numbered case (per each record's `note`/`Evidence` field, e.g. "The source states heartbeat cadence, owner identity, and missed renewals for case N").

## Handoff note

This is the same cross-format divergence pattern previously observed in `maintenance/reports/retry-s02-lease-duration-survey.md`, `maintenance/reports/retry-s02-claim-record-samples.md`, and `maintenance/reports/retry-s02-lease-clock-fixtures.md`: the `.md` and `.yaml` sources report identical, smaller case counts (130 in this set), the `.jsonl` source reports a strict subset (125), and the `.csv` source reports a strict superset (147). This report does not infer which count is authoritative or the cause of the divergence; the data owner should reconcile which source(s) are canonical for `retry-s02-t07`.

## Verification: no product artifacts modified

Command: `find accountsvc tests fixtures -type f -newer maintenance/inputs/retry-s02/renewal-heartbeat-results/retry-s02-t07-evidence-01.md`

Result: no output (exit code 1, meaning no matches) — confirms no file under `accountsvc/`, `tests/`, or `fixtures/` was modified during this review. This maintenance review did not modify any product code, fixtures, routes, configuration, tests, or other application artifact.
