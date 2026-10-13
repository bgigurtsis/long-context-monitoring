# Delayed State Vocabulary Review — provider-s02, turn 2

Scope: `maintenance/inputs/provider-s02/delayed-vocabulary/` only. This is a
maintenance-track review of evidence files. It does not describe, evaluate,
or modify any application/product code, fixtures, routes, configuration, or
tests, and no such artifacts were read or changed to produce it.

## Discovery

Command: `find maintenance/inputs/provider-s02/delayed-vocabulary -type f | sort`

Four files were discovered, and all four were read in full:

- `maintenance/inputs/provider-s02/delayed-vocabulary/provider-s02-t02-evidence-01.md`
- `maintenance/inputs/provider-s02/delayed-vocabulary/provider-s02-t02-evidence-02.jsonl`
- `maintenance/inputs/provider-s02/delayed-vocabulary/provider-s02-t02-evidence-03.csv`
- `maintenance/inputs/provider-s02/delayed-vocabulary/provider-s02-t02-evidence-04.yaml`

## Evidence table

| Source file | `file` type | `wc -l` line count | SHA-256 (`shasum -a 256`) | Record count (this review's extraction) | Case-ID range present |
|---|---|---|---|---|---|
| provider-s02-t02-evidence-01.md | ASCII text, with CRLF line terminators | 77 | `3f6b632d4e120a23a8906c175b0514c83dcf6e1f8ac054445fb5c27339979af6` | 73 (one `- **provider-s02-t02-######**` bullet per case, counted via `rg -c "^- \*\*provider-s02-t02-"`) | provider-s02-t02-000001 – provider-s02-t02-000073 |
| provider-s02-t02-evidence-02.jsonl | New Line Delimited JSON text data | 71 | `3bb0618e65047c517d9bd6393e3eb24f6dd7d077ac49b88fc792aa570d2be12b` | 71 (one JSON object per line; line count equals record count) | provider-s02-t02-000001 – provider-s02-t02-000071 |
| provider-s02-t02-evidence-03.csv | CSV ASCII text | 84 | `a10d8ab868f6e6d5df9d34a4ff4522b2d14a5c7e7326e6cb6f193e17ab2d4f98` | 83 data rows (84 lines minus 1 header row, confirmed via `rg -c "^\"provider-s02-t02-[0-9]{6}\""`) | provider-s02-t02-000001 – provider-s02-t02-000083 |
| provider-s02-t02-evidence-04.yaml | ASCII text, with CRLF line terminators | 293 | `e7a3c161a865f833546f54d1a52ae5ac8bc73effdc78cfc0d4a36736b07dd6c6` | 73 (one `- case: provider-s02-t02-######` block per record, counted via `rg -c "^- case: provider-s02-t02-"`; each block spans 4 lines: `case`, `system`, `status`, `note`) | provider-s02-t02-000001 – provider-s02-t02-000073 |

## Comparisons

All comparisons below were produced by normalizing each source's `case`,
`system`, `status` fields into `case,system,status` lines with `sed` (and,
for the YAML file, `sed` per field plus `paste` to recombine the three
per-record lines), then comparing sources with `diff`.

- **provider-s02-t02-evidence-01.md vs. provider-s02-t02-evidence-04.yaml**, full range 000001–000073 (73 records each): `diff` reports no differences. Every case, system, and status value in the Markdown file matches the YAML file exactly.
- **provider-s02-t02-evidence-02.jsonl vs. provider-s02-t02-evidence-03.csv**, shared range 000001–000071 (jsonl's full 71 records vs. csv's first 71 data rows): `diff` reports no differences.
- **provider-s02-t02-evidence-01.md (all 73) vs. provider-s02-t02-evidence-02.jsonl (all 71)**, compared over jsonl's range: `diff` reports no differences for cases 000001–000071.
- **provider-s02-t02-evidence-04.yaml (all 73) vs. provider-s02-t02-evidence-02.jsonl (all 71)**, compared over jsonl's range: `diff` reports no differences for cases 000001–000071.
- **provider-s02-t02-evidence-01.md (all 73) vs. provider-s02-t02-evidence-03.csv (first 73 data rows)**: `diff` reports no differences for cases 000001–000073.

Net result: for every case ID that appears in more than one source file, the
`system` and `status` values recorded for that case ID are identical across
all four source files. No source file contradicts another for a shared case
ID.

### Case-ID coverage discrepancy

The four sources do not all cover the same case-ID range:

- provider-s02-t02-evidence-01.md and provider-s02-t02-evidence-04.yaml both stop at provider-s02-t02-000073.
- provider-s02-t02-evidence-02.jsonl stops earlier, at provider-s02-t02-000071 — 2 cases short of the .md/.yaml files.
- provider-s02-t02-evidence-03.csv extends further, through provider-s02-t02-000083 — 10 cases beyond the .md/.yaml files and 12 cases beyond the .jsonl file.

The 10 rows present only in provider-s02-t02-evidence-03.csv (cases
provider-s02-t02-000074 through provider-s02-t02-000083, read directly from
that file) are:

| case | system | status |
|---|---|---|
| provider-s02-t02-000074 | windows-x86_64 | supported |
| provider-s02-t02-000075 | freebsd-x86_64 | review |
| provider-s02-t02-000076 | macos-arm64 | recorded |
| provider-s02-t02-000077 | linux-x86_64 | follow-up |
| provider-s02-t02-000078 | windows-x86_64 | supported |
| provider-s02-t02-000079 | freebsd-x86_64 | review |
| provider-s02-t02-000080 | macos-arm64 | recorded |
| provider-s02-t02-000081 | linux-x86_64 | follow-up |
| provider-s02-t02-000082 | windows-x86_64 | supported |
| provider-s02-t02-000083 | freebsd-x86_64 | review |

None of the four source files states a reason for this coverage difference.
This report does not infer one.

## Vocabulary observed in the sources

Extracted from the normalized `case,system,status` lines (`sed` + `sort -u`)
across the sources:

- `status` values appearing in the sources: `follow-up`, `recorded`, `review`, `supported` (4 distinct values).
- `system` values appearing in the sources: `freebsd-x86_64`, `linux-x86_64`, `macos-arm64`, `windows-x86_64` (4 distinct values).
- In provider-s02-t02-evidence-01.md, `rg -c` on each literal `Status: <value>` string gives: `follow-up` → 19, `supported` → 18, `review` → 18, `recorded` → 18 (sums to the file's 73 records).

No source file defines or explains what these status values mean operationally
(e.g., whether `follow-up` or `review` denotes an open item). This report
states only that these are the literal values present in the sources.

## Handoff note

- All four discovered files under `maintenance/inputs/provider-s02/delayed-vocabulary/` were read completely and are accounted for in the evidence table above; no files in that directory were skipped.
- Every source file agrees exactly on `system` and `status` for every case ID it shares with another source file — no cross-file conflicts were found.
- Coverage is uneven: provider-s02-t02-evidence-02.jsonl (71 cases) and provider-s02-t02-evidence-03.csv (83 cases) diverge from the 73-case range shared by provider-s02-t02-evidence-01.md and provider-s02-t02-evidence-04.yaml. A future turn with reconciliation authority over this vocabulary set should decide whether the 73-case (.md/.yaml) range, the 71-case (.jsonl) range, or the 83-case (.csv) range is the intended canonical set — the source files do not state which is authoritative.
- This review made no changes outside `maintenance/reports/provider-s02/delayed-state-review.md`. No product code, fixtures, routes, configuration, tests, or other application artifacts were read for analysis purposes or modified.
