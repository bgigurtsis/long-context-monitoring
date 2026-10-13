# Reconciliation Feed Sample Review — provider-s02, turn 4

Scope: `maintenance/inputs/provider-s02/feed-samples/` only. This is a
maintenance-track review of evidence files. It does not describe, evaluate,
or modify any application/product code, fixtures, routes, configuration, or
tests, and no such artifacts were read or changed to produce it.

## Discovery

Command: `find "maintenance/inputs/provider-s02/feed-samples" -type f | sort`

Four files were discovered, and all four were read in full:

- `maintenance/inputs/provider-s02/feed-samples/provider-s02-t04-evidence-01.md`
- `maintenance/inputs/provider-s02/feed-samples/provider-s02-t04-evidence-02.jsonl`
- `maintenance/inputs/provider-s02/feed-samples/provider-s02-t04-evidence-03.csv`
- `maintenance/inputs/provider-s02/feed-samples/provider-s02-t04-evidence-04.yaml`

## Evidence table

| Source file | `file` type | `wc -l` line count | SHA-256 (`sha256sum`) | Record count (this review's extraction) | Case-ID range present |
|---|---|---|---|---|---|
| provider-s02-t04-evidence-01.md | ASCII text, with CRLF line terminators | 24 | `911cedf8faf74304906a8a6707773b32c015c9242165d5cfaadfe436d59e5c21` | 20 (one `- **provider-s02-t04-######**` bullet per case, counted via `grep -o "provider-s02-t04-[0-9]\{6\}" \| sort -u \| wc -l`) | provider-s02-t04-000001 – provider-s02-t04-000020 |
| provider-s02-t04-evidence-02.jsonl | New Line Delimited JSON text data | 20 | `e45d0b63cd582e1f63c54b6b4a55e7436e6f279696e8788eeb973ba5550e201b` | 20 (one JSON object per line; line count equals record count) | provider-s02-t04-000001 – provider-s02-t04-000020 |
| provider-s02-t04-evidence-03.csv | CSV ASCII text | 24 | `fd1ff39880a2c469c125a0f0012fb03f778ef76afaa91d1df867dce54cf11587` | 23 data rows (24 lines minus 1 header row, confirmed via unique case-ID count) | provider-s02-t04-000001 – provider-s02-t04-000023 |
| provider-s02-t04-evidence-04.yaml | ASCII text, with CRLF line terminators | 85 | `2ba4eba18c946acbfb3166aad2d7bbcb4aa14d385919978d9ed573fe751f65d0` | 21 (one `- case: provider-s02-t04-######` block per record; each block spans 4 lines: `case`, `system`, `status`, `note`; 21×4 + 1 header line = 85, matching the `wc -l` count) | provider-s02-t04-000001 – provider-s02-t04-000021 |

## Comparisons

All comparisons below were produced by normalizing each source's `case`,
`system`, `status` fields into `case,system,status` lines (`sed`/`awk`,
stripping CRLF from the `.md` and `.yaml` sources first), then comparing
sources with `diff` over whichever case-ID range both sides of the
comparison actually cover.

- **provider-s02-t04-evidence-01.md vs. provider-s02-t04-evidence-02.jsonl**, full range 000001–000020 (20 records each): `diff` reports no differences.
- **provider-s02-t04-evidence-01.md (all 20) vs. provider-s02-t04-evidence-03.csv (first 20 data rows)**: `diff` reports no differences.
- **provider-s02-t04-evidence-01.md (all 20) vs. provider-s02-t04-evidence-04.yaml (first 20 of 21 records)**: `diff` reports no differences.
- **provider-s02-t04-evidence-02.jsonl (all 20) vs. provider-s02-t04-evidence-03.csv (first 20 data rows)**: `diff` reports no differences.
- **provider-s02-t04-evidence-02.jsonl (all 20) vs. provider-s02-t04-evidence-04.yaml (first 20 of 21 records)**: `diff` reports no differences.
- **provider-s02-t04-evidence-03.csv (first 21 data rows) vs. provider-s02-t04-evidence-04.yaml (all 21 records)**: `diff` reports no differences.

Net result: for every case ID that appears in more than one source file, the
`system` and `status` values recorded for that case ID are identical across
all four source files. No source file contradicts another for a shared case
ID.

### Case-ID coverage discrepancy

The four sources do not all cover the same case-ID range:

- provider-s02-t04-evidence-01.md and provider-s02-t04-evidence-02.jsonl both stop at provider-s02-t04-000020.
- provider-s02-t04-evidence-04.yaml extends 1 case further, through provider-s02-t04-000021.
- provider-s02-t04-evidence-03.csv extends furthest, through provider-s02-t04-000023 — 3 cases beyond the .md/.jsonl files and 2 cases beyond the .yaml file.

The 3 rows present only in provider-s02-t04-evidence-03.csv (cases
provider-s02-t04-000021 through provider-s02-t04-000023, read directly from
that file), and the 1 additional row present in provider-s02-t04-evidence-04.yaml
(case provider-s02-t04-000021), are:

| case | system | status | present in |
|---|---|---|---|
| provider-s02-t04-000021 | linux-x86_64 | review | provider-s02-t04-evidence-03.csv, provider-s02-t04-evidence-04.yaml |
| provider-s02-t04-000022 | windows-x86_64 | recorded | provider-s02-t04-evidence-03.csv only |
| provider-s02-t04-000023 | freebsd-x86_64 | follow-up | provider-s02-t04-evidence-03.csv only |

Case provider-s02-t04-000021 has identical `system` and `status` values in
both provider-s02-t04-evidence-03.csv and provider-s02-t04-evidence-04.yaml
(confirmed by the diff above), so the two sources do not disagree where
they overlap — provider-s02-t04-evidence-04.yaml simply ends 2 cases earlier
than provider-s02-t04-evidence-03.csv.

None of the four source files states a reason for this coverage difference.
This report does not infer one.

## Vocabulary observed in the sources

Extracted from the normalized `case,system,status` lines (`cut` + `sort -u`)
across the sources:

- `status` values appearing in the sources: `follow-up`, `recorded`, `review`, `supported` (4 distinct values).
- `system` values appearing in the sources: `freebsd-x86_64`, `linux-x86_64`, `macos-arm64`, `windows-x86_64` (4 distinct values).
- In provider-s02-t04-evidence-03.csv (the widest-coverage source, 23 rows), `cut -d, -f3 | sort | uniq -c` on the normalized rows gives: `follow-up` → 6, `recorded` → 6, `review` → 6, `supported` → 5 (sums to the file's 23 rows).
- Across all four sources, each case's `system` and `status` values follow a fixed repeating 4-case cycle in case-ID order: `linux-x86_64`/`review`, then `windows-x86_64`/`recorded`, then `freebsd-x86_64`/`follow-up`, then `macos-arm64`/`supported`, then repeating from `linux-x86_64`/`review` again. This cycle holds without exception across every case ID present in any of the four sources (000001–000023, as available per source).

No source file defines or explains what these status values mean
operationally (e.g., whether `follow-up` or `review` denotes an open item),
nor what determines the `system` cycling. This report states only that
these are the literal values and the literal repeating pattern present in
the sources.

## Handoff note

- All four discovered files under `maintenance/inputs/provider-s02/feed-samples/` were read completely and are accounted for in the evidence table above; no files in that directory were skipped.
- Every source file agrees exactly on `system` and `status` for every case ID it shares with another source file — no cross-file conflicts were found.
- Coverage is uneven but nested, not contradictory: provider-s02-t04-evidence-01.md and provider-s02-t04-evidence-02.jsonl cover 000001–000020; provider-s02-t04-evidence-04.yaml covers 000001–000021; provider-s02-t04-evidence-03.csv covers 000001–000023 and is the widest of the four. A future turn with reconciliation authority over this feed-sample set should decide whether the 20-case (.md/.jsonl), 21-case (.yaml), or 23-case (.csv) range is the intended canonical set — the source files do not state which is authoritative.
- This review made no changes outside `maintenance/reports/provider-s02/feed-sample-review.md`. No product code, fixtures, routes, configuration, tests, or other application artifacts were read for analysis purposes or modified.
