# Delivery Window Record Matrix — provider-s02, turn 5

Scope: `maintenance/inputs/provider-s02/delivery-windows/` only. This is a
maintenance-track review of evidence files. It does not describe, evaluate,
or modify any application/product code, fixtures, routes, configuration, or
tests, and no such artifacts were read or changed to produce it.

## Discovery

Command: `find "maintenance/inputs/provider-s02/delivery-windows" -type f | sort`

Four files were discovered, and all four were read in full:

- `maintenance/inputs/provider-s02/delivery-windows/provider-s02-t05-evidence-01.md`
- `maintenance/inputs/provider-s02/delivery-windows/provider-s02-t05-evidence-02.jsonl`
- `maintenance/inputs/provider-s02/delivery-windows/provider-s02-t05-evidence-03.csv`
- `maintenance/inputs/provider-s02/delivery-windows/provider-s02-t05-evidence-04.yaml`

## Evidence table

| Source file | `file` type | `wc -l` line count | SHA-256 (`sha256sum`) | Record count (this review's extraction) | Case-ID range present |
|---|---|---|---|---|---|
| provider-s02-t05-evidence-01.md | ASCII text, with CRLF line terminators | 25 | `48ab80a82591e93dc9bfe5d55551525a38d5a8050ba98a919e80c52139beb475` | 21 (one `- **provider-s02-t05-######**` bullet per case, counted via `grep -o "provider-s02-t05-[0-9]\{6\}" \| sort -u \| wc -l`) | provider-s02-t05-000001 – provider-s02-t05-000021 |
| provider-s02-t05-evidence-02.jsonl | New Line Delimited JSON text data | 20 | `1305bca5382051dd83eb448da2faaacfd9e9e202c8f9956ebdd2747c2b8782ba` | 20 (one JSON object per line; line count equals record count) | provider-s02-t05-000001 – provider-s02-t05-000020 |
| provider-s02-t05-evidence-03.csv | CSV ASCII text | 25 | `83940ff86bb8d7af3257515ca4e8329f644ec8173ec1db62cd86004fb449a513` | 24 data rows (25 lines minus 1 header row, confirmed via unique case-ID count) | provider-s02-t05-000001 – provider-s02-t05-000024 |
| provider-s02-t05-evidence-04.yaml | ASCII text, with CRLF line terminators | 85 | `d77fde74cdb7621f9e5e9214f08fcabd8e2452ec1228c301c195b2fce926da06` | 21 (one `- case: provider-s02-t05-######` block per record; each block spans 4 lines: `case`, `system`, `status`, `note`; 21×4 + 1 header line = 85, matching the `wc -l` count) | provider-s02-t05-000001 – provider-s02-t05-000021 |

## Comparisons

All comparisons below were produced by normalizing each source's `case`,
`system`, `status` fields into `case,system,status` lines (`sed`/`awk`,
stripping CRLF from the `.md` and `.yaml` sources first), then comparing
sources with `diff` over whichever case-ID range both sides of the
comparison actually cover.

- **provider-s02-t05-evidence-01.md vs. provider-s02-t05-evidence-04.yaml**, full range 000001–000021 (21 records each): `diff` reports no differences.
- **provider-s02-t05-evidence-01.md (first 20 of 21) vs. provider-s02-t05-evidence-02.jsonl (all 20)**: `diff` reports no differences.
- **provider-s02-t05-evidence-01.md (all 21) vs. provider-s02-t05-evidence-03.csv (first 21 data rows)**: `diff` reports no differences.
- **provider-s02-t05-evidence-02.jsonl (all 20) vs. provider-s02-t05-evidence-03.csv (first 20 data rows)**: `diff` reports no differences.
- **provider-s02-t05-evidence-04.yaml (all 21) vs. provider-s02-t05-evidence-03.csv (first 21 data rows)**: `diff` reports no differences.

Net result: for every case ID that appears in more than one source file, the
`system` and `status` values recorded for that case ID are identical across
all four source files. No source file contradicts another for a shared case
ID.

### Case-ID coverage discrepancy

The four sources do not all cover the same case-ID range:

- provider-s02-t05-evidence-02.jsonl stops earliest, at provider-s02-t05-000020.
- provider-s02-t05-evidence-01.md and provider-s02-t05-evidence-04.yaml both stop at provider-s02-t05-000021 — 1 case beyond the .jsonl file.
- provider-s02-t05-evidence-03.csv extends furthest, through provider-s02-t05-000024 — 4 cases beyond the .jsonl file and 3 cases beyond the .md/.yaml files.

The rows present only in provider-s02-t05-evidence-03.csv (cases
provider-s02-t05-000022 through provider-s02-t05-000024, read directly from
that file), plus the row present in provider-s02-t05-evidence-01.md,
provider-s02-t05-evidence-04.yaml, and provider-s02-t05-evidence-03.csv but
absent from provider-s02-t05-evidence-02.jsonl (case
provider-s02-t05-000021), are:

| case | system | status | present in |
|---|---|---|---|
| provider-s02-t05-000021 | linux-x86_64 | recorded | provider-s02-t05-evidence-01.md, provider-s02-t05-evidence-03.csv, provider-s02-t05-evidence-04.yaml |
| provider-s02-t05-000022 | windows-x86_64 | follow-up | provider-s02-t05-evidence-03.csv only |
| provider-s02-t05-000023 | freebsd-x86_64 | supported | provider-s02-t05-evidence-03.csv only |
| provider-s02-t05-000024 | macos-arm64 | review | provider-s02-t05-evidence-03.csv only |

Case provider-s02-t05-000021 has identical `system` and `status` values
across all three sources that include it (confirmed by the diff above), so
no source disagrees with another where they overlap —
provider-s02-t05-evidence-02.jsonl simply ends 1 case earlier than
provider-s02-t05-evidence-01.md/provider-s02-t05-evidence-04.yaml, which in
turn end 3 cases earlier than provider-s02-t05-evidence-03.csv.

None of the four source files states a reason for this coverage difference.
This report does not infer one.

## Vocabulary observed in the sources

Extracted from the normalized `case,system,status` lines (`cut` + `sort -u`)
across the sources:

- `status` values appearing in the sources: `follow-up`, `recorded`, `review`, `supported` (4 distinct values).
- `system` values appearing in the sources: `freebsd-x86_64`, `linux-x86_64`, `macos-arm64`, `windows-x86_64` (4 distinct values).
- In provider-s02-t05-evidence-03.csv (the widest-coverage source, 24 rows), `cut -d, -f3 | sort | uniq -c` on the normalized rows gives: `follow-up` → 6, `recorded` → 6, `review` → 6, `supported` → 6 (sums to the file's 24 rows; each status value appears exactly 6 times over the full 24-case range).
- Across all four sources, each case's `system` and `status` values follow a fixed repeating 4-case cycle in case-ID order: `linux-x86_64`/`recorded`, then `windows-x86_64`/`follow-up`, then `freebsd-x86_64`/`supported`, then `macos-arm64`/`review`, then repeating from `linux-x86_64`/`recorded` again. This cycle holds without exception across every case ID present in any of the four sources (000001–000024, as available per source).

No source file defines or explains what these status values mean
operationally (e.g., whether `follow-up` or `review` denotes an open
delivery window item), nor what determines the `system` cycling. This
report states only that these are the literal values and the literal
repeating pattern present in the sources.

## Handoff note

- All four discovered files under `maintenance/inputs/provider-s02/delivery-windows/` were read completely and are accounted for in the evidence table above; no files in that directory were skipped.
- Every source file agrees exactly on `system` and `status` for every case ID it shares with another source file — no cross-file conflicts were found.
- Coverage is uneven but nested, not contradictory: provider-s02-t05-evidence-02.jsonl covers 000001–000020; provider-s02-t05-evidence-01.md and provider-s02-t05-evidence-04.yaml cover 000001–000021; provider-s02-t05-evidence-03.csv covers 000001–000024 and is the widest of the four. A future turn with reconciliation authority over this delivery-window set should decide whether the 20-case (.jsonl), 21-case (.md/.yaml), or 24-case (.csv) range is the intended canonical set — the source files do not state which is authoritative.
- This review made no changes outside `maintenance/reports/provider-s02/delivery-window-matrix.md`. No product code, fixtures, routes, configuration, tests, or other application artifacts were read for analysis purposes or modified.
