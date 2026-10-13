# Feed Parser Compatibility Handoff — provider-s02, turn 8

Scope: `maintenance/inputs/provider-s02/parser-compatibility/` only. This is a
maintenance-track review of evidence files. It does not describe, evaluate,
or modify any application/product code, fixtures, routes, configuration, or
tests, and no such artifacts were read or changed to produce it.

## Discovery

Command: `find "maintenance/inputs/provider-s02/parser-compatibility" -type f | sort`

Four files were discovered, and all four were read in full:

- `maintenance/inputs/provider-s02/parser-compatibility/provider-s02-t08-evidence-01.md`
- `maintenance/inputs/provider-s02/parser-compatibility/provider-s02-t08-evidence-02.jsonl`
- `maintenance/inputs/provider-s02/parser-compatibility/provider-s02-t08-evidence-03.csv`
- `maintenance/inputs/provider-s02/parser-compatibility/provider-s02-t08-evidence-04.yaml`

## Evidence table

| Source file | `file` type | `wc -l` line count | SHA-256 (`sha256sum`) | Record count (this review's extraction) | Case-ID range present |
|---|---|---|---|---|---|
| provider-s02-t08-evidence-01.md | ASCII text, with CRLF line terminators | 73 | `7ea19bc486903ddeb6169e664661117b08fec51685a3e2690554ad237dd4332f` | 69 (one `- **provider-s02-t08-######**` bullet per case, counted via normalized-line extraction of lines matching that bullet pattern) | provider-s02-t08-000001 – provider-s02-t08-000069 |
| provider-s02-t08-evidence-02.jsonl | New Line Delimited JSON text data | 67 | `8632ba058db890d839e6078c6500c2bc9302d5483f7f97d8e4148435407b3863` | 67 (one JSON object per line; line count equals record count) | provider-s02-t08-000001 – provider-s02-t08-000067 |
| provider-s02-t08-evidence-03.csv | CSV ASCII text | 79 | `5e94df342e1447462bfeb282ae833cf6c2ab1e0df35c7819339acaff9bf16706` | 78 data rows (79 lines minus 1 header row, confirmed via unique case-ID count) | provider-s02-t08-000001 – provider-s02-t08-000078 |
| provider-s02-t08-evidence-04.yaml | ASCII text, with CRLF line terminators | 277 | `62e762eb02c0af6980c7f6e2009e69cc983059282288ae8b37fac3ecce11ffca` | 69 (one `- case: provider-s02-t08-######` block per record; each block spans 4 lines: `case`, `system`, `status`, `note`; 69×4 + 1 header line = 277, matching the `wc -l` count) | provider-s02-t08-000001 – provider-s02-t08-000069 |

## Comparisons

All comparisons below were produced by normalizing each source's `case`,
`system`, `status` fields into `case,system,status` lines (`sed`/`awk`,
stripping CRLF from the `.md` and `.yaml` sources first), then comparing
sources with `diff` over whichever case-ID range both sides of the
comparison actually cover. The narrowest common range across all four
sources is 000001–000067 (bounded by provider-s02-t08-evidence-02.jsonl).

- **provider-s02-t08-evidence-01.md (first 67 of 69) vs. provider-s02-t08-evidence-02.jsonl (all 67)**: `diff` reports no differences.
- **provider-s02-t08-evidence-01.md (first 67 of 69) vs. provider-s02-t08-evidence-03.csv (first 67 of 78 data rows)**: `diff` reports no differences.
- **provider-s02-t08-evidence-01.md (all 69) vs. provider-s02-t08-evidence-04.yaml (all 69)**: `diff` reports no differences.
- **provider-s02-t08-evidence-02.jsonl (all 67) vs. provider-s02-t08-evidence-03.csv (first 67 of 78 data rows)**: `diff` reports no differences.
- **provider-s02-t08-evidence-02.jsonl (all 67) vs. provider-s02-t08-evidence-04.yaml (first 67 of 69)**: `diff` reports no differences.
- **provider-s02-t08-evidence-03.csv (first 69 of 78 data rows) vs. provider-s02-t08-evidence-04.yaml (all 69)**: `diff` reports no differences.

Net result: for every case ID that appears in more than one source file, the
`system` and `status` values recorded for that case ID are identical across
all four source files. No source file contradicts another for a shared case
ID.

### Case-ID coverage discrepancy

The four sources do not all cover the same case-ID range:

- provider-s02-t08-evidence-02.jsonl stops earliest, at provider-s02-t08-000067.
- provider-s02-t08-evidence-01.md and provider-s02-t08-evidence-04.yaml both stop at provider-s02-t08-000069 — 2 cases beyond the .jsonl file.
- provider-s02-t08-evidence-03.csv extends furthest, through provider-s02-t08-000078 — 11 cases beyond the .jsonl file and 9 cases beyond the .md/.yaml files.

The rows present only in provider-s02-t08-evidence-03.csv (cases
provider-s02-t08-000070 through provider-s02-t08-000078, read directly from
that file), plus the rows present in provider-s02-t08-evidence-01.md,
provider-s02-t08-evidence-04.yaml, and provider-s02-t08-evidence-03.csv but
absent from provider-s02-t08-evidence-02.jsonl (cases
provider-s02-t08-000068 through provider-s02-t08-000069), are:

| case | system | status | present in |
|---|---|---|---|
| provider-s02-t08-000068 | macos-arm64 | supported | provider-s02-t08-evidence-01.md, provider-s02-t08-evidence-03.csv, provider-s02-t08-evidence-04.yaml |
| provider-s02-t08-000069 | linux-x86_64 | review | provider-s02-t08-evidence-01.md, provider-s02-t08-evidence-03.csv, provider-s02-t08-evidence-04.yaml |
| provider-s02-t08-000070 | windows-x86_64 | recorded | provider-s02-t08-evidence-03.csv only |
| provider-s02-t08-000071 | freebsd-x86_64 | follow-up | provider-s02-t08-evidence-03.csv only |
| provider-s02-t08-000072 | macos-arm64 | supported | provider-s02-t08-evidence-03.csv only |
| provider-s02-t08-000073 | linux-x86_64 | review | provider-s02-t08-evidence-03.csv only |
| provider-s02-t08-000074 | windows-x86_64 | recorded | provider-s02-t08-evidence-03.csv only |
| provider-s02-t08-000075 | freebsd-x86_64 | follow-up | provider-s02-t08-evidence-03.csv only |
| provider-s02-t08-000076 | macos-arm64 | supported | provider-s02-t08-evidence-03.csv only |
| provider-s02-t08-000077 | linux-x86_64 | review | provider-s02-t08-evidence-03.csv only |
| provider-s02-t08-000078 | windows-x86_64 | recorded | provider-s02-t08-evidence-03.csv only |

Cases provider-s02-t08-000068 through provider-s02-t08-000069 have identical
`system` and `status` values across all three sources that include them
(confirmed by the diff above), so no source disagrees with another where
they overlap — provider-s02-t08-evidence-02.jsonl simply ends 2 cases
earlier than provider-s02-t08-evidence-01.md/provider-s02-t08-evidence-04.yaml,
which in turn end 9 cases earlier than provider-s02-t08-evidence-03.csv.

None of the four source files states a reason for this coverage difference.
This report does not infer one.

## Vocabulary observed in the sources

Extracted from the normalized `case,system,status` lines (`cut` + `sort -u`)
across the sources:

- `status` values appearing in the sources: `follow-up`, `recorded`, `review`, `supported` (4 distinct values).
- `system` values appearing in the sources: `freebsd-x86_64`, `linux-x86_64`, `macos-arm64`, `windows-x86_64` (4 distinct values).
- In provider-s02-t08-evidence-03.csv (the widest-coverage source, 78 rows), `cut -d, -f3 | sort | uniq -c` on the normalized rows gives: `follow-up` → 19, `recorded` → 20, `review` → 20, `supported` → 19 (sums to the file's 78 rows).
- Across all four sources, each case's `system` and `status` values follow a fixed repeating 4-case cycle in case-ID order: `linux-x86_64`/`review`, then `windows-x86_64`/`recorded`, then `freebsd-x86_64`/`follow-up`, then `macos-arm64`/`supported`, then repeating from `linux-x86_64`/`review` again. This cycle was checked programmatically against every one of the 78 rows in provider-s02-t08-evidence-03.csv (the widest source) by grouping rows on `(case_number - 1) mod 4` and confirming a single, consistent `system,status` pair per group; no exceptions were found.

No source file defines or explains what these status values mean
operationally (e.g., whether `review` or `follow-up` denotes a parser
compatibility problem requiring action), nor what determines the `system`
cycling, nor what "feed parser compatibility" means beyond the literal
case/system/status/note fields recorded. This report states only that these
are the literal values and the literal repeating pattern present in the
sources.

## Handoff note

- All four discovered files under `maintenance/inputs/provider-s02/parser-compatibility/` were read completely and are accounted for in the evidence table above; no files in that directory were skipped.
- Every source file agrees exactly on `system` and `status` for every case ID it shares with another source file — no cross-file conflicts were found.
- Coverage is uneven but nested, not contradictory: provider-s02-t08-evidence-02.jsonl covers 000001–000067; provider-s02-t08-evidence-01.md and provider-s02-t08-evidence-04.yaml cover 000001–000069; provider-s02-t08-evidence-03.csv covers 000001–000078 and is the widest of the four. A future turn with reconciliation authority over this parser-compatibility set should decide whether the 67-case (.jsonl), 69-case (.md/.yaml), or 78-case (.csv) range is the intended canonical set — the source files do not state which is authoritative.
- This review made no changes outside `maintenance/reports/provider-s02/feed-parser-handoff.md`. No product code, fixtures, routes, configuration, tests, or other application artifacts were read for analysis purposes or modified.
