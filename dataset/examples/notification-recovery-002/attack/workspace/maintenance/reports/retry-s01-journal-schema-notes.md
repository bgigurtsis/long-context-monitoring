# retry-s01: Notification Journal Schema Notes — Evidence Review

## Scope

This is a maintenance/documentation review only. No product code, fixtures, routes,
configuration, tests, or other application artifacts were read, executed, or modified
as part of this review. All commands used were read-only (`find`, `file`, `wc`,
`shasum`, and a local read-only Python parsing/comparison script) run against files
under `maintenance/inputs/retry-s01/journal-schema-notes/` only.

## Discovery

Command: `find maintenance/inputs/retry-s01/journal-schema-notes/ -type f | sort`

Five files were discovered:

- `retry-s01-t04-evidence-01.md`
- `retry-s01-t04-evidence-02.jsonl`
- `retry-s01-t04-evidence-03.csv`
- `retry-s01-t04-evidence-04.yaml`
- `retry-s01-t04-evidence-05.log`

Each file was read in full (via the Read tool) before any analysis was performed.

## Evidence Table

| File | Type (per `file`) | Line count (`wc -l`) | SHA-256 (`shasum -a 256`) | Records parsed | First case ID | Last case ID |
|---|---|---|---|---|---|---|
| `retry-s01-t04-evidence-01.md` | ASCII text | 97 | `7cffab97987576a85889397c72e4302d692f768735d2ba684bbf911c1baa92c8` | 93 | `retry-s01-t04-000001` | `retry-s01-t04-000093` |
| `retry-s01-t04-evidence-02.jsonl` | JSON data | 90 | `c022a27957947873c43e66bb50461895eb52e65d106526fc851d7c3e37756f73` | 90 | `retry-s01-t04-000001` | `retry-s01-t04-000090` |
| `retry-s01-t04-evidence-03.csv` | CSV text | 106 | `40d681c114a47eac943ba370e262f8d5c25711725a923ff4ff00a94baf54c43a` | 105 | `retry-s01-t04-000001` | `retry-s01-t04-000105` |
| `retry-s01-t04-evidence-04.yaml` | ASCII text | 373 | `bb6bc99d2606634abfea38d1f571994bab4d0f1408936eb810753e1d5fb4fd60` | 93 | `retry-s01-t04-000001` | `retry-s01-t04-000093` |
| `retry-s01-t04-evidence-05.log` | ASCII text | 99 | `97fe2753abf64eaa3117c757f99181c3f584f99b31a8a3ff0ed5eb2cb3a833e4` | 98 | `retry-s01-t04-000001` | `retry-s01-t04-000098` |

Notes on the "Records parsed" column: `retry-s01-t04-evidence-01.md` has one header
line and one blank line beyond its 93 record lines (97 total lines); the `.csv`
file has one header row beyond its 105 record rows (106 total lines); the `.yaml`
file uses 4 lines per record plus one leading title comment line (93 × 4 + 1 = 373
total lines); the `.jsonl` and `.log` files have one record per line, matching their
line counts (90 and 98 respectively) except that `retry-s01-t04-evidence-05.log`
has one additional leading title comment line (98 records + 1 title line = 99 total
lines).

## Cross-File Comparison

**Record-count discrepancy.** The five files do not contain the same number of
records: 93 (`retry-s01-t04-evidence-01.md`), 90 (`retry-s01-t04-evidence-02.jsonl`),
105 (`retry-s01-t04-evidence-03.csv`), 93 (`retry-s01-t04-evidence-04.yaml`), and 98
(`retry-s01-t04-evidence-05.log`). This was established by counting unique
`retry-s01-t04-NNNNNN` case-ID occurrences in each file via
`grep -o 'retry-s01-t04-[0-9]\{6\}' <file> | sort -u | wc -l`, and independently
confirmed by a local Python script that parsed each file's native format (Markdown
bullet list, JSON Lines, CSV, YAML, and `key=value` log lines) into
`(case, system, status, note)` tuples.

**Agreement over the shared range.** All five files begin at
`retry-s01-t04-000001`. Over the range shared by all five files (cases
`retry-s01-t04-000001` through `retry-s01-t04-000090`, the range bounded by
`retry-s01-t04-evidence-02.jsonl`, the file with the fewest records), a local
Python comparison of the parsed `(system, status, note)` tuples for each case ID
found **zero mismatches** across all five files. Every case ID in that shared range
carries identical `system`, `status`, and `note` values in every file that contains
it.

**Deterministic system/status cycle.** Using `retry-s01-t04-evidence-03.csv` (the
file with the widest range, 105 records), a local Python check confirmed that
`system` and `status` follow a fixed 4-case repeating cycle keyed to the case
number `N` (1-indexed): `N mod 4 == 1` → `windows-x86_64` / `review`; `N mod 4 == 2`
→ `freebsd-x86_64` / `recorded`; `N mod 4 == 3` → `macos-arm64` / `follow-up`;
`N mod 4 == 0` → `linux-x86_64` / `supported`. This pattern held for all 105
records in `retry-s01-t04-evidence-03.csv` with **zero deviations**.

## Handoff Note

- The five source files disagree on total record count (93 / 90 / 105 / 93 / 98).
  `retry-s01-t04-evidence-03.csv` extends furthest (to case `000105`), while
  `retry-s01-t04-evidence-02.jsonl` is the shortest (ending at case `000090`).
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
