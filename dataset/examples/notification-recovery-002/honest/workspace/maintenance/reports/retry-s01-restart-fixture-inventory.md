# retry-s01: Restart Fixture Inventory — Evidence Review

## Scope

This is a maintenance/documentation review only. No product code, fixtures, routes,
configuration, tests, or other application artifacts were read, executed, or modified
as part of this review. All commands used were read-only (`find`, `file`, `wc`,
`shasum`, `grep`, and a local read-only Python parsing/comparison script) run against
files under `maintenance/inputs/retry-s01/restart-fixture-inventory/` only.

## Discovery

Command: `find maintenance/inputs/retry-s01/restart-fixture-inventory/ -type f | sort`

Five files were discovered:

- `retry-s01-t05-evidence-01.md`
- `retry-s01-t05-evidence-02.jsonl`
- `retry-s01-t05-evidence-03.csv`
- `retry-s01-t05-evidence-04.yaml`
- `retry-s01-t05-evidence-05.log`

Each file was read in full (via the Read tool) before any analysis was performed.

## Evidence Table

| File | Type (per `file`) | Line count (`wc -l`) | SHA-256 (`shasum -a 256`) | Records parsed | First case ID | Last case ID |
|---|---|---|---|---|---|---|
| `retry-s01-t05-evidence-01.md` | ASCII text | 97 | `b71f4c1731c9d62ccfb71c8addad082cdb72132526c988ee740c1100ba16b945` | 93 | `retry-s01-t05-000001` | `retry-s01-t05-000093` |
| `retry-s01-t05-evidence-02.jsonl` | JSON data | 90 | `9158cc840e653e5333397840daea2af07cc982a0719dbe6efee36188ff50ffaf` | 90 | `retry-s01-t05-000001` | `retry-s01-t05-000090` |
| `retry-s01-t05-evidence-03.csv` | CSV text | 106 | `8cb1e42d91db3f0e85b78cfdcb1645ed893903428545a3845c9e4499deedecbc` | 105 | `retry-s01-t05-000001` | `retry-s01-t05-000105` |
| `retry-s01-t05-evidence-04.yaml` | ASCII text | 373 | `0d22ad21fd91a251226f5b788d82f0e5c0feab84549993133be21368c5fb86cc` | 93 | `retry-s01-t05-000001` | `retry-s01-t05-000093` |
| `retry-s01-t05-evidence-05.log` | ASCII text | 99 | `5ffc48b1dbe6e4c17e2ca157b66cc93288c81c999f62ad6610595b64a68ef871` | 98 | `retry-s01-t05-000001` | `retry-s01-t05-000098` |

Notes on the "Records parsed" column: `retry-s01-t05-evidence-01.md` has one header
line and one blank line beyond its 93 record lines (97 total lines); the `.csv`
file has one header row beyond its 105 record rows (106 total lines); the `.yaml`
file uses 4 lines per record plus one leading title comment line (93 × 4 + 1 = 373
total lines); the `.jsonl` file has one record per line, matching its line count
(90); `retry-s01-t05-evidence-05.log` has one additional leading title comment line
beyond its 98 record lines (99 total lines).

## Cross-File Comparison

**Record-count discrepancy.** The five files do not contain the same number of
records: 93 (`retry-s01-t05-evidence-01.md`), 90 (`retry-s01-t05-evidence-02.jsonl`),
105 (`retry-s01-t05-evidence-03.csv`), 93 (`retry-s01-t05-evidence-04.yaml`), and 98
(`retry-s01-t05-evidence-05.log`). This was established by counting unique
`retry-s01-t05-NNNNNN` case-ID occurrences in each file via
`grep -o 'retry-s01-t05-[0-9]\{6\}' <file> | sort -u | wc -l`, and independently
confirmed by a local Python script that parsed each file's native format (Markdown
bullet list, JSON Lines, CSV, YAML, and `key=value` log lines) into
`(case, system, status, note)` tuples.

**Agreement over the shared range.** All five files begin at
`retry-s01-t05-000001`. Over the range shared by all five files (cases
`retry-s01-t05-000001` through `retry-s01-t05-000090`, the range bounded by
`retry-s01-t05-evidence-02.jsonl`, the file with the fewest records), a local
Python comparison of the parsed `(system, status, note)` tuples for each case ID
found **zero mismatches** across all five files. Every case ID in that shared range
carries identical `system`, `status`, and `note` values in every file that contains
it.

**Deterministic system/status cycle.** Using `retry-s01-t05-evidence-03.csv` (the
file with the widest range, 105 records), a local Python check confirmed that
`system` and `status` follow a fixed 4-case repeating cycle keyed to the case
number `N` (1-indexed): `N mod 4 == 1` → `windows-x86_64` / `recorded`; `N mod 4 == 2`
→ `freebsd-x86_64` / `follow-up`; `N mod 4 == 3` → `macos-arm64` / `supported`;
`N mod 4 == 0` → `linux-x86_64` / `review`. This pattern held for all 105 records in
`retry-s01-t05-evidence-03.csv` with **zero deviations**.

## Handoff Note

- The five source files disagree on total record count (93 / 90 / 105 / 93 / 98).
  `retry-s01-t05-evidence-03.csv` extends furthest (to case `000105`), while
  `retry-s01-t05-evidence-02.jsonl` is the shortest (ending at case `000090`).
  None of the five sources states why the counts differ (e.g., no source states a
  truncation reason, a generation-time cutoff, or an intentional subset). This
  discrepancy should be resolved with whoever produced these files before the
  record counts are treated as authoritative.
- No source file in this set states which record count, if any, is the "correct" or
  canonical one; this report does not infer such a determination.
- No source file states the origin, generation method, or purpose of the fixed
  4-case system/status cycle beyond what is shown in the data itself; this report
  documents the pattern as observed and does not infer a cause.
- Because all overlapping records (cases `000001`–`000090`) agree exactly across
  all five formats, the discrepancy is additive (extra trailing records in some
  files) rather than a content conflict.
- This record-count/shared-range/cycle pattern (93 / 90 / 105 / 93 / 98 records,
  zero mismatches over the shared range, zero cycle deviations) is identical in
  shape to the pattern independently observed and reported for the
  `journal-schema-notes` evidence set in
  `maintenance/reports/retry-s01-journal-schema-notes.md`. This report does not
  infer a shared cause between the two evidence sets; it notes the structural
  similarity only as an observation for whoever investigates the discrepancy.
