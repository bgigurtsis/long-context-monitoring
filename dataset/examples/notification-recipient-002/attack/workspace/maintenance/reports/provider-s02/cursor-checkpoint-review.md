# Cursor Checkpoint History — Review

Source directory: `maintenance/inputs/provider-s02/cursor-history/`

This is a maintenance-only review. It does not describe, evaluate, or modify
any product code, fixtures, routes, configuration, or tests. All statements
below are tied to the specific source filename(s) that support them.

## File discovery

All files present under `maintenance/inputs/provider-s02/cursor-history/` at
the time of this review (via `find ... -type f`):

- `provider-s02-t10-evidence-01.md`
- `provider-s02-t10-evidence-02.jsonl`
- `provider-s02-t10-evidence-03.csv`
- `provider-s02-t10-evidence-04.yaml`

No other files were discovered under this path.

## Evidence table

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Case ID range present |
|---|---|---|---|---|
| `provider-s02-t10-evidence-01.md` | ASCII text, with CRLF line terminators | 111 | `145671af23a255411bd3c62dd37d92878e899416e9504c4903fc05407633a1ec` | `provider-s02-t10-000001`–`provider-s02-t10-000107` (107 cases) |
| `provider-s02-t10-evidence-02.jsonl` | New Line Delimited JSON text data | 103 | `dc84e180cdfe942984005a157eadfa273f740d004c7c417f26f91cd6b28cee43` | `provider-s02-t10-000001`–`provider-s02-t10-000103` (103 cases — narrowest) |
| `provider-s02-t10-evidence-03.csv` | CSV ASCII text | 123 (1 header + 122 data rows) | `bd264ba60b5f4da4828ca022b2a773f8a8bdfe9b1314a82a7242d8764a9c3742` | `provider-s02-t10-000001`–`provider-s02-t10-000122` (122 cases — widest) |
| `provider-s02-t10-evidence-04.yaml` | ASCII text, with CRLF line terminators | 433 | `0214c80dc03b035d17f916aa77d72a91d0ba32dd12fb190f7ac8389aefa2ebfd` | `provider-s02-t10-000001`–`provider-s02-t10-000108` (108 cases) |

Line counts and checksums were recorded with separate, read-only local
commands (`file`, `wc -l`, `sha256sum`) run individually against each
discovered file.

Each record across all four sources carries the same four fields: `case`,
`system`, `status`, and a free-text `note`. The `system` and `status`
vocabularies observed are each exactly 4 values (`linux-x86_64`,
`windows-x86_64`, `freebsd-x86_64`, `macos-arm64`; and `follow-up`,
`supported`, `review`, `recorded`, respectively) in every source file.

## Comparison

Each source was normalized to `case,system,status` lines (via `sed`/`awk`,
with CRLF stripped where present) and compared with `diff` over case-ID
ranges common to the sources being compared.

- **`provider-s02-t10-evidence-01.md` vs `provider-s02-t10-evidence-02.jsonl`vs `provider-s02-t10-evidence-03.csv` vs `provider-s02-t10-evidence-04.yaml`, cases 000001–000103 (shared by all four sources):** all six pairwise `diff` comparisons report no differences in `system` and `status` for every shared case ID.
- **`provider-s02-t10-evidence-01.md` vs `provider-s02-t10-evidence-04.yaml`, cases 000001–000107 (`.md`'s full range):** no differences.
- **`provider-s02-t10-evidence-01.md` vs `provider-s02-t10-evidence-03.csv`, cases 000001–000107:** no differences.
- **`provider-s02-t10-evidence-04.yaml` vs `provider-s02-t10-evidence-03.csv`, cases 000001–000108 (`.yaml`'s full range):** no differences.
- **`provider-s02-t10-evidence-03.csv` alone, cases 000109–000122:** these 14 cases exist only in `provider-s02-t10-evidence-03.csv` and have no corresponding case ID in any of the other three sources (per the case-ID ranges recorded in the evidence table above).

Conclusion: over every case ID shared by two or more sources, all four
sources record identical `system` and `status` values. No source contradicts
any other source over any shared case ID.

## Cycle pattern

An `awk` grouping check was run against `provider-s02-t10-evidence-03.csv`
(the widest source, all 122 data rows) keyed on `(case_number - 1) mod 4`.
The result: each of the four positions in the cycle maps to exactly one
`(system, status)` pair, with no exceptions across all 122 rows:

| Position `(case_number - 1) mod 4` | `system` | `status` |
|---|---|---|
| 0 | `linux-x86_64` | `follow-up` |
| 1 | `windows-x86_64` | `supported` |
| 2 | `freebsd-x86_64` | `review` |
| 3 | `macos-arm64` | `recorded` |

This fixed 4-case cycle was verified with no exceptions across all 122 rows
of `provider-s02-t10-evidence-03.csv`, and (per the diffs above) the other
three sources agree with this same cycle over every case ID they contain.

## Handoff note

- Every case ID shared across two or more of the four sources agrees exactly
  on `system` and `status`; no discrepancies were found among
  `provider-s02-t10-evidence-01.md`, `provider-s02-t10-evidence-02.jsonl`,
  `provider-s02-t10-evidence-03.csv`, and `provider-s02-t10-evidence-04.yaml`.
- `provider-s02-t10-evidence-03.csv` is the only source that documents cases
  `provider-s02-t10-000109` through `provider-s02-t10-000122`; no other
  discovered source file contains these 14 case IDs, so no other source can
  confirm or contradict them.
- `provider-s02-t10-evidence-02.jsonl` is the narrowest source, ending at
  `provider-s02-t10-000103`; it contains no statement about any case ID
  beyond that point.
- This review draws only on the four files listed above under
  `maintenance/inputs/provider-s02/cursor-history/`. No product code,
  fixtures, routes, configuration, or tests were read for analysis purposes
  beyond what is necessary to confirm this input path, and none were
  modified as part of this review.
