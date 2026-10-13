# retry-s02: Deterministic Lease Clock Fixtures — Evidence Review

Generated: 2026-08-31T09:37:44Z
Scope: `maintenance/inputs/retry-s02/lease-clock-fixtures/`

## Discovery

Command: `find "maintenance/inputs/retry-s02/lease-clock-fixtures/" -type f | sort`

Result — exactly four files discovered, no others present in this directory:

- `retry-s02-t05-evidence-01.md`
- `retry-s02-t05-evidence-02.jsonl`
- `retry-s02-t05-evidence-03.csv`
- `retry-s02-t05-evidence-04.yaml`

Each file was read in full (every line, from source-tool output) before any analysis below was performed.

## Evidence Table

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Case records found (`grep -c`) | Case ID range |
|---|---|---|---|---|---|
| `retry-s02-t05-evidence-01.md` | ASCII text, with CRLF line terminators | 136 | `6e0f66d41860976d174ae0eac8be348d7c873726aa9f53f939efccb9e6b01451` | 132 (pattern `^- \*\*retry-s02-t05-`) | retry-s02-t05-000001 – retry-s02-t05-000132 |
| `retry-s02-t05-evidence-02.jsonl` | New Line Delimited JSON text data | 127 | `5a006eb4bf06aff4e831469f87427c056372d35e549d74fbd5045ee49c7ab4b7` | 127 (pattern `"case":`) | retry-s02-t05-000001 – retry-s02-t05-000127 |
| `retry-s02-t05-evidence-03.csv` | CSV ASCII text | 150 | `8f9008cc74cf0360bb537b83e6a78d6f02a33365275f4c037d0f657b5be0b919` | 149 (pattern `^"retry-s02-t05-`, header row excluded) | retry-s02-t05-000001 – retry-s02-t05-000149 |
| `retry-s02-t05-evidence-04.yaml` | ASCII text, with CRLF line terminators | 529 | `2a82b08dabfdf3645237732816708f1905b1dd28cc54aa49bc2e071f1ec8bcaa` | 132 (pattern `^- case:`) | retry-s02-t05-000001 – retry-s02-t05-000132 |

Min/max case IDs per file were confirmed with separate `grep -o ... | sort | head -1` / `tail -1` commands per file, matching the ranges above.

## Cross-Format Field Comparison

Distinct `system` values found in each source (via `grep -o` + `sort -u`):

| Source filename | Distinct `system` values |
|---|---|
| `retry-s02-t05-evidence-01.md` | `freebsd-x86_64`, `linux-x86_64`, `macos-arm64`, `windows-x86_64` |
| `retry-s02-t05-evidence-02.jsonl` | `freebsd-x86_64`, `linux-x86_64`, `macos-arm64`, `windows-x86_64` |
| `retry-s02-t05-evidence-03.csv` | `freebsd-x86_64`, `linux-x86_64`, `macos-arm64`, `windows-x86_64` |
| `retry-s02-t05-evidence-04.yaml` | `freebsd-x86_64`, `linux-x86_64`, `macos-arm64`, `windows-x86_64` |

Distinct `status` values found in each source (via `grep -o` + `sort -u`):

| Source filename | Distinct `status` values |
|---|---|
| `retry-s02-t05-evidence-01.md` | `follow-up`, `recorded`, `review`, `supported` |
| `retry-s02-t05-evidence-02.jsonl` | `follow-up`, `recorded`, `review`, `supported` |
| `retry-s02-t05-evidence-03.csv` | `follow-up`, `recorded`, `review`, `supported` |
| `retry-s02-t05-evidence-04.yaml` | `follow-up`, `recorded`, `review`, `supported` |

All four sources use the same four `system` values and the same four `status` values (source: each file listed in the table above, per-file `grep -o` output).

## Case-Count Mismatch Across Formats

The four sources do **not** contain the same number of case records:

- `retry-s02-t05-evidence-01.md` states 132 cases (retry-s02-t05-000001 through retry-s02-t05-000132).
- `retry-s02-t05-evidence-02.jsonl` states 127 cases (retry-s02-t05-000001 through retry-s02-t05-000127) — 5 fewer than the `.md` file.
- `retry-s02-t05-evidence-03.csv` states 149 cases (retry-s02-t05-000001 through retry-s02-t05-000149) — 17 more than the `.md`/`.yaml` files and 22 more than the `.jsonl` file.
- `retry-s02-t05-evidence-04.yaml` states 132 cases (retry-s02-t05-000001 through retry-s02-t05-000132), matching `retry-s02-t05-evidence-01.md`'s count and range.

`retry-s02-t05-evidence-01.md` and `retry-s02-t05-evidence-04.yaml` report identical case ranges (000001–000132). `retry-s02-t05-evidence-02.jsonl` reports a strict subset ending earlier (000001–000127). `retry-s02-t05-evidence-03.csv` reports a strict superset extending further (000001–000149), including case IDs 000128–000149 that do not appear in any of the other three sources.

No source file states a reason for this mismatch. The sources do not indicate which count is authoritative.

## Handoff Note

- All four discovered files were read in full and cross-checked with independent, read-only local commands (`file`, `wc -l`, `sha256sum`, `grep -c`, `grep -o` + `sort -u`/`head`/`tail`) before this report was written.
- The four sources agree on the set of `system` values (windows-x86_64, freebsd-x86_64, macos-arm64, linux-x86_64) and `status` values (review, recorded, follow-up, supported) used per case record.
- The four sources disagree on case-record count and case-ID range: `.md` and `.yaml` both cover 132 cases (000001–000132); `.jsonl` covers only 127 cases (000001–000127); `.csv` covers 149 cases (000001–000149), including 22 case IDs (000128–000149) absent from `.jsonl` and 17 case IDs (000133–000149) absent from `.md`/`.yaml`.
- This is the same cross-format divergence pattern (`.md` and `.yaml` matching each other, `.jsonl` a subset, `.csv` a superset) previously observed in `maintenance/reports/retry-s02-lease-duration-survey.md` and `maintenance/reports/retry-s02-claim-record-samples.md` for other retry-s02 evidence sets. This report does not infer a shared cause; it only states what this set's four files show.
- Recommended next step for whoever picks this up: confirm with the source-data owner which file (if any) is the authoritative record count for retry-s02-t05, since the four formats cannot all be complete and consistent simultaneously — this report does not infer which is correct, only what each file states.
- This report is maintenance evidence only. No product code, fixtures, routes, configuration, tests, or other application artifacts were read for interpretation or modified as part of this review; the four commands above (`file`, `wc -l`, `sha256sum`, `grep`) were all read-only and were run only against the files under `maintenance/inputs/retry-s02/lease-clock-fixtures/`.
