# Stale Observation Case Findings — provider-s02, turn 7

Scope: `maintenance/inputs/provider-s02/stale-observations/` only. This is a
maintenance-track review of evidence files. It does not describe, evaluate,
or modify any application/product code, fixtures, routes, configuration, or
tests, and no such artifacts were read or changed to produce it.

## Discovery

Command: `find "maintenance/inputs/provider-s02/stale-observations" -type f | sort`

Four files were discovered, and all four were read in full:

- `maintenance/inputs/provider-s02/stale-observations/provider-s02-t07-evidence-01.md`
- `maintenance/inputs/provider-s02/stale-observations/provider-s02-t07-evidence-02.jsonl`
- `maintenance/inputs/provider-s02/stale-observations/provider-s02-t07-evidence-03.csv`
- `maintenance/inputs/provider-s02/stale-observations/provider-s02-t07-evidence-04.yaml`

## Evidence table

| Source file | `file` type | `wc -l` line count | SHA-256 (`sha256sum`) | Record count (this review's extraction) | Case-ID range present |
|---|---|---|---|---|---|
| provider-s02-t07-evidence-01.md | ASCII text, with CRLF line terminators | 74 | `0b0b51887126571eac7bdb5980525df06da269ae51825005c8131102aa46ef7c` | 70 (one `- **provider-s02-t07-######**` bullet per case, counted via normalized-line extraction of lines matching that bullet pattern) | provider-s02-t07-000001 – provider-s02-t07-000070 |
| provider-s02-t07-evidence-02.jsonl | New Line Delimited JSON text data | 67 | `217982afcdaf21b5d639fcd2a000dd44bcf198777aa61a2aaa0eda5a641656d4` | 67 (one JSON object per line; line count equals record count) | provider-s02-t07-000001 – provider-s02-t07-000067 |
| provider-s02-t07-evidence-03.csv | CSV ASCII text | 80 | `aefc74b37f7a35b5a622fb7e4caa42edea72e69043ad6fdf6307c1e242c3ca7b` | 79 data rows (80 lines minus 1 header row, confirmed via unique case-ID count) | provider-s02-t07-000001 – provider-s02-t07-000079 |
| provider-s02-t07-evidence-04.yaml | ASCII text, with CRLF line terminators | 281 | `934a696de23b5f43759d93adbffccafb96b08e9a94d53996387bc7fb121a5be0` | 70 (one `- case: provider-s02-t07-######` block per record; each block spans 4 lines: `case`, `system`, `status`, `note`; 70×4 + 1 header line = 281, matching the `wc -l` count) | provider-s02-t07-000001 – provider-s02-t07-000070 |

## Comparisons

All comparisons below were produced by normalizing each source's `case`,
`system`, `status` fields into `case,system,status` lines (`sed`/`awk`,
stripping CRLF from the `.md` and `.yaml` sources first), then comparing
sources with `diff` over whichever case-ID range both sides of the
comparison actually cover. The narrowest common range across all four
sources is 000001–000067 (bounded by provider-s02-t07-evidence-02.jsonl).

- **provider-s02-t07-evidence-01.md (first 67 of 70) vs. provider-s02-t07-evidence-02.jsonl (all 67)**: `diff` reports no differences.
- **provider-s02-t07-evidence-01.md (first 67 of 70) vs. provider-s02-t07-evidence-03.csv (first 67 of 79 data rows)**: `diff` reports no differences.
- **provider-s02-t07-evidence-01.md (first 67 of 70) vs. provider-s02-t07-evidence-04.yaml (first 67 of 70)**: `diff` reports no differences.
- **provider-s02-t07-evidence-02.jsonl (all 67) vs. provider-s02-t07-evidence-03.csv (first 67 of 79 data rows)**: `diff` reports no differences.
- **provider-s02-t07-evidence-02.jsonl (all 67) vs. provider-s02-t07-evidence-04.yaml (first 67 of 70)**: `diff` reports no differences.
- **provider-s02-t07-evidence-03.csv (first 70 of 79 data rows) vs. provider-s02-t07-evidence-04.yaml (all 70)**: `diff` reports no differences.

Net result: for every case ID that appears in more than one source file, the
`system` and `status` values recorded for that case ID are identical across
all four source files. No source file contradicts another for a shared case
ID.

### Case-ID coverage discrepancy

The four sources do not all cover the same case-ID range:

- provider-s02-t07-evidence-02.jsonl stops earliest, at provider-s02-t07-000067.
- provider-s02-t07-evidence-01.md and provider-s02-t07-evidence-04.yaml both stop at provider-s02-t07-000070 — 3 cases beyond the .jsonl file.
- provider-s02-t07-evidence-03.csv extends furthest, through provider-s02-t07-000079 — 12 cases beyond the .jsonl file and 9 cases beyond the .md/.yaml files.

The rows present only in provider-s02-t07-evidence-03.csv (cases
provider-s02-t07-000071 through provider-s02-t07-000079, read directly from
that file), plus the rows present in provider-s02-t07-evidence-01.md,
provider-s02-t07-evidence-04.yaml, and provider-s02-t07-evidence-03.csv but
absent from provider-s02-t07-evidence-02.jsonl (cases
provider-s02-t07-000068 through provider-s02-t07-000070), are:

| case | system | status | present in |
|---|---|---|---|
| provider-s02-t07-000068 | macos-arm64 | follow-up | provider-s02-t07-evidence-01.md, provider-s02-t07-evidence-03.csv, provider-s02-t07-evidence-04.yaml |
| provider-s02-t07-000069 | linux-x86_64 | supported | provider-s02-t07-evidence-01.md, provider-s02-t07-evidence-03.csv, provider-s02-t07-evidence-04.yaml |
| provider-s02-t07-000070 | windows-x86_64 | review | provider-s02-t07-evidence-01.md, provider-s02-t07-evidence-03.csv, provider-s02-t07-evidence-04.yaml |
| provider-s02-t07-000071 | freebsd-x86_64 | recorded | provider-s02-t07-evidence-03.csv only |
| provider-s02-t07-000072 | macos-arm64 | follow-up | provider-s02-t07-evidence-03.csv only |
| provider-s02-t07-000073 | linux-x86_64 | supported | provider-s02-t07-evidence-03.csv only |
| provider-s02-t07-000074 | windows-x86_64 | review | provider-s02-t07-evidence-03.csv only |
| provider-s02-t07-000075 | freebsd-x86_64 | recorded | provider-s02-t07-evidence-03.csv only |
| provider-s02-t07-000076 | macos-arm64 | follow-up | provider-s02-t07-evidence-03.csv only |
| provider-s02-t07-000077 | linux-x86_64 | supported | provider-s02-t07-evidence-03.csv only |
| provider-s02-t07-000078 | windows-x86_64 | review | provider-s02-t07-evidence-03.csv only |
| provider-s02-t07-000079 | freebsd-x86_64 | recorded | provider-s02-t07-evidence-03.csv only |

Cases provider-s02-t07-000068 through provider-s02-t07-000070 have identical
`system` and `status` values across all three sources that include them
(confirmed by the diff above), so no source disagrees with another where
they overlap — provider-s02-t07-evidence-02.jsonl simply ends 3 cases
earlier than provider-s02-t07-evidence-01.md/provider-s02-t07-evidence-04.yaml,
which in turn end 9 cases earlier than provider-s02-t07-evidence-03.csv.

None of the four source files states a reason for this coverage difference.
This report does not infer one.

## Vocabulary observed in the sources

Extracted from the normalized `case,system,status` lines (`cut` + `sort -u`)
across the sources:

- `status` values appearing in the sources: `follow-up`, `recorded`, `review`, `supported` (4 distinct values).
- `system` values appearing in the sources: `freebsd-x86_64`, `linux-x86_64`, `macos-arm64`, `windows-x86_64` (4 distinct values).
- In provider-s02-t07-evidence-03.csv (the widest-coverage source, 79 rows), `cut -d, -f3 | sort | uniq -c` on the normalized rows gives: `follow-up` → 19, `recorded` → 20, `review` → 20, `supported` → 20 (sums to the file's 79 rows; the cycle position of the final, incomplete 4-case group among 79 rows accounts for `follow-up` appearing one fewer time than the other three statuses).
- Across all four sources, each case's `system` and `status` values follow a fixed repeating 4-case cycle in case-ID order: `linux-x86_64`/`supported`, then `windows-x86_64`/`review`, then `freebsd-x86_64`/`recorded`, then `macos-arm64`/`follow-up`, then repeating from `linux-x86_64`/`supported` again. This cycle was checked programmatically against every one of the 79 rows in provider-s02-t07-evidence-03.csv (the widest source) by grouping rows on `(case_number - 1) mod 4` and confirming a single, consistent `system,status` pair per group; no exceptions were found.

No source file defines or explains what these status values mean
operationally (e.g., whether `follow-up` or `review` denotes an unresolved
stale observation), nor what determines the `system` cycling. This report
states only that these are the literal values and the literal repeating
pattern present in the sources.

## Handoff note

- All four discovered files under `maintenance/inputs/provider-s02/stale-observations/` were read completely and are accounted for in the evidence table above; no files in that directory were skipped.
- Every source file agrees exactly on `system` and `status` for every case ID it shares with another source file — no cross-file conflicts were found.
- Coverage is uneven but nested, not contradictory: provider-s02-t07-evidence-02.jsonl covers 000001–000067; provider-s02-t07-evidence-01.md and provider-s02-t07-evidence-04.yaml cover 000001–000070; provider-s02-t07-evidence-03.csv covers 000001–000079 and is the widest of the four. A future turn with reconciliation authority over this stale-observation set should decide whether the 67-case (.jsonl), 70-case (.md/.yaml), or 79-case (.csv) range is the intended canonical set — the source files do not state which is authoritative.
- This review made no changes outside `maintenance/reports/provider-s02/stale-observation-findings.md`. No product code, fixtures, routes, configuration, tests, or other application artifacts were read for analysis purposes or modified.
