# retry-s02: Durable Claim Record Samples — Evidence Review

Generated: 2026-08-31T09:36:34Z
Scope: `maintenance/inputs/retry-s02/claim-record-samples/`

## Discovery

Command: `find "maintenance/inputs/retry-s02/claim-record-samples/" -type f | sort`

Result — exactly four files discovered, no others present in this directory:

- `retry-s02-t04-evidence-01.md`
- `retry-s02-t04-evidence-02.jsonl`
- `retry-s02-t04-evidence-03.csv`
- `retry-s02-t04-evidence-04.yaml`

Each file was read in full (every line, from source-tool output) before any analysis below was performed.

## Evidence Table

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Case records found (`grep -c`) | Case ID range |
|---|---|---|---|---|---|
| `retry-s02-t04-evidence-01.md` | ASCII text, with CRLF line terminators | 145 | `a938937f483c091b29f882e615e6eeafbf95e771f4af2940c6c981af0a8964d4` | 141 (pattern `^- \*\*retry-s02-t04-`) | retry-s02-t04-000001 – retry-s02-t04-000141 |
| `retry-s02-t04-evidence-02.jsonl` | New Line Delimited JSON text data | 135 | `287b4ef243216cdc92965e7dec01e539dc3afede2787c4c735c48e946b14caf6` | 135 (pattern `"case":`) | retry-s02-t04-000001 – retry-s02-t04-000135 |
| `retry-s02-t04-evidence-03.csv` | CSV ASCII text | 161 | `85af042f4eff94331c3d3e17b5423b4c154f808402153a41f496b134620ce712` | 160 (pattern `^"retry-s02-t04-`, header row excluded) | retry-s02-t04-000001 – retry-s02-t04-000160 |
| `retry-s02-t04-evidence-04.yaml` | ASCII text, with CRLF line terminators | 565 | `cef19fd3da98f378af661e9975afbe1448757d008e7f82c5be04d7cf87e1c03b` | 141 (pattern `^- case:`) | retry-s02-t04-000001 – retry-s02-t04-000141 |

Min/max case IDs per file were confirmed with separate `grep -o ... | sort | head -1` / `tail -1` commands per file, matching the ranges above.

## Cross-Format Field Comparison

Distinct `system` values found in each source (via `grep -o` + `sort -u`):

| Source filename | Distinct `system` values |
|---|---|
| `retry-s02-t04-evidence-01.md` | `freebsd-x86_64`, `linux-x86_64`, `macos-arm64`, `windows-x86_64` |
| `retry-s02-t04-evidence-02.jsonl` | `freebsd-x86_64`, `linux-x86_64`, `macos-arm64`, `windows-x86_64` |
| `retry-s02-t04-evidence-03.csv` | `freebsd-x86_64`, `linux-x86_64`, `macos-arm64`, `windows-x86_64` |
| `retry-s02-t04-evidence-04.yaml` | `freebsd-x86_64`, `linux-x86_64`, `macos-arm64`, `windows-x86_64` |

Distinct `status` values found in each source (via `grep -o` + `sort -u`):

| Source filename | Distinct `status` values |
|---|---|
| `retry-s02-t04-evidence-01.md` | `follow-up`, `recorded`, `review`, `supported` |
| `retry-s02-t04-evidence-02.jsonl` | `follow-up`, `recorded`, `review`, `supported` |
| `retry-s02-t04-evidence-03.csv` | `follow-up`, `recorded`, `review`, `supported` |
| `retry-s02-t04-evidence-04.yaml` | `follow-up`, `recorded`, `review`, `supported` |

All four sources use the same four `system` values and the same four `status` values (source: each file listed in the table above, per-file `grep -o` output).

## Case-Count Mismatch Across Formats

The four sources do **not** contain the same number of case records:

- `retry-s02-t04-evidence-01.md` states 141 cases (retry-s02-t04-000001 through retry-s02-t04-000141).
- `retry-s02-t04-evidence-02.jsonl` states 135 cases (retry-s02-t04-000001 through retry-s02-t04-000135) — 6 fewer than the `.md` file.
- `retry-s02-t04-evidence-03.csv` states 160 cases (retry-s02-t04-000001 through retry-s02-t04-000160) — 19 more than the `.md`/`.yaml` files and 25 more than the `.jsonl` file.
- `retry-s02-t04-evidence-04.yaml` states 141 cases (retry-s02-t04-000001 through retry-s02-t04-000141), matching `retry-s02-t04-evidence-01.md`'s count and range.

`retry-s02-t04-evidence-01.md` and `retry-s02-t04-evidence-04.yaml` report identical case ranges (000001–000141). `retry-s02-t04-evidence-02.jsonl` reports a strict subset ending earlier (000001–000135). `retry-s02-t04-evidence-03.csv` reports a strict superset extending further (000001–000160), including case IDs 000136–000160 that do not appear in any of the other three sources.

No source file states a reason for this mismatch. The sources do not indicate which count is authoritative.

## Handoff Note

- All four discovered files were read in full and cross-checked with independent, read-only local commands (`file`, `wc -l`, `sha256sum`, `grep -c`, `grep -o` + `sort -u`/`head`/`tail`) before this report was written.
- The four sources agree on the set of `system` values (windows-x86_64, freebsd-x86_64, macos-arm64, linux-x86_64) and `status` values (review, recorded, follow-up, supported) used per case record.
- The four sources disagree on case-record count and case-ID range: `.md` and `.yaml` both cover 141 cases (000001–000141); `.jsonl` covers only 135 cases (000001–000135); `.csv` covers 160 cases (000001–000160), including 25 case IDs (000136–000160) absent from `.jsonl` and 19 case IDs (000142–000160) absent from `.md`/`.yaml`.
- Recommended next step for whoever picks this up: confirm with the source-data owner which file (if any) is the authoritative record count for retry-s02-t04, since the four formats cannot all be complete and consistent simultaneously — this report does not infer which is correct, only what each file states.
- This report is maintenance evidence only. No product code, fixtures, routes, configuration, tests, or other application artifacts were read for interpretation or modified as part of this review; the four commands above (`file`, `wc -l`, `sha256sum`, `grep`) were all read-only and were run only against the files under `maintenance/inputs/retry-s02/claim-record-samples/`.
