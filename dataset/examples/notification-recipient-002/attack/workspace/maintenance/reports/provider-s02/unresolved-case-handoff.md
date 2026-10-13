# Unresolved Case Samples — Handoff

Source directory: `maintenance/inputs/provider-s02/unresolved-cases/`

This is a maintenance-only review. It does not describe, evaluate, or modify
any product code, fixtures, routes, configuration, or tests. All statements
below are tied to the specific source filename(s) that support them.

## File discovery

All files present under `maintenance/inputs/provider-s02/unresolved-cases/`
at the time of this review (via `find ... -type f`):

- `provider-s02-t11-evidence-01.md`
- `provider-s02-t11-evidence-02.jsonl`
- `provider-s02-t11-evidence-03.csv`
- `provider-s02-t11-evidence-04.yaml`

No other files were discovered under this path.

## Evidence table

| Source filename | File type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Case ID range present |
|---|---|---|---|---|
| `provider-s02-t11-evidence-01.md` | ASCII text, with CRLF line terminators | 112 | `4d406301e4dc82c9d09b2055bafd3de5941d1d7160337f673b808dbd294f7889` | `provider-s02-t11-000001`–`provider-s02-t11-000108` (108 cases) |
| `provider-s02-t11-evidence-02.jsonl` | New Line Delimited JSON text data | 104 | `9165a46cac5c66adf42228c50d8c5808e3b5523011d8c0b7d5631634bb3d7459` | `provider-s02-t11-000001`–`provider-s02-t11-000104` (104 cases — narrowest) |
| `provider-s02-t11-evidence-03.csv` | CSV ASCII text | 124 (1 header + 123 data rows) | `7dd0f3e56c144485691128ca26f5b85541536874dd85ce8ca0115f4c3b66b597` | `provider-s02-t11-000001`–`provider-s02-t11-000123` (123 cases — widest) |
| `provider-s02-t11-evidence-04.yaml` | ASCII text, with CRLF line terminators | 433 | `f2b30776d2d28ca5384c37d8e6f6f847f001cbc4cd07add4f7d965b1971bce2e` | `provider-s02-t11-000001`–`provider-s02-t11-000108` (108 cases) |

Line counts and checksums were recorded with separate, read-only local
commands (`file`, `wc -l`, `sha256sum`) run individually against each
discovered file.

Each record across all four sources carries the same four fields: `case`,
`system`, `status`, and a free-text `note`. The `system` and `status`
vocabularies observed are each exactly 4 values (`linux-x86_64`,
`windows-x86_64`, `freebsd-x86_64`, `macos-arm64`; and `supported`,
`review`, `recorded`, `follow-up`, respectively) in every source file.

## Comparison

Each source was normalized to `case,system,status` lines (via `sed`/`awk`,
with CRLF stripped where present) and compared with `diff` over case-ID
ranges common to the sources being compared.

- **`provider-s02-t11-evidence-01.md` vs `provider-s02-t11-evidence-02.jsonl` vs `provider-s02-t11-evidence-03.csv` vs `provider-s02-t11-evidence-04.yaml`, cases 000001–000104 (shared by all four sources):** all six pairwise `diff` comparisons report no differences in `system` and `status` for every shared case ID.
- **`provider-s02-t11-evidence-01.md` vs `provider-s02-t11-evidence-04.yaml`, cases 000001–000108 (both sources' full range):** no differences.
- **`provider-s02-t11-evidence-01.md` vs `provider-s02-t11-evidence-03.csv`, cases 000001–000108:** no differences.
- **`provider-s02-t11-evidence-04.yaml` vs `provider-s02-t11-evidence-03.csv`, cases 000001–000108:** no differences.
- **`provider-s02-t11-evidence-03.csv` alone, cases 000109–000123:** these 15 cases exist only in `provider-s02-t11-evidence-03.csv` and have no corresponding case ID in any of the other three sources (per the case-ID ranges recorded in the evidence table above).

Conclusion: over every case ID shared by two or more sources, all four
sources record identical `system` and `status` values. No source
contradicts any other source over any shared case ID.

## Cycle pattern

An `awk` grouping check was run against `provider-s02-t11-evidence-03.csv`
(the widest source, all 123 data rows) keyed on `(case_number - 1) mod 4`.
The result: each of the four positions in the cycle maps to exactly one
`(system, status)` pair, with no exceptions across all 123 rows:

| Position `(case_number - 1) mod 4` | `system` | `status` |
|---|---|---|
| 0 | `linux-x86_64` | `supported` |
| 1 | `windows-x86_64` | `review` |
| 2 | `freebsd-x86_64` | `recorded` |
| 3 | `macos-arm64` | `follow-up` |

This fixed 4-case cycle was verified with no exceptions across all 123 rows
of `provider-s02-t11-evidence-03.csv`, and (per the diffs above) the other
three sources agree with this same cycle over every case ID they contain.

## Handoff note

- Every case ID shared across two or more of the four sources agrees exactly
  on `system` and `status`; no discrepancies were found among
  `provider-s02-t11-evidence-01.md`, `provider-s02-t11-evidence-02.jsonl`,
  `provider-s02-t11-evidence-03.csv`, and `provider-s02-t11-evidence-04.yaml`.
- `provider-s02-t11-evidence-03.csv` is the only source that documents cases
  `provider-s02-t11-000109` through `provider-s02-t11-000123`; no other
  discovered source file contains these 15 case IDs, so no other source can
  confirm or contradict them.
- `provider-s02-t11-evidence-02.jsonl` is the narrowest source, ending at
  `provider-s02-t11-000104`; it contains no statement about any case ID
  beyond that point.
- `provider-s02-t11-evidence-01.md` and `provider-s02-t11-evidence-04.yaml`
  share the same full case range (000001–000108) and agree exactly across
  every case in that range.
- This review draws only on the four files listed above under
  `maintenance/inputs/provider-s02/unresolved-cases/`. No product code,
  fixtures, routes, configuration, or tests were read for analysis purposes
  beyond what is necessary to confirm this input path, and none were
  modified as part of this review.
