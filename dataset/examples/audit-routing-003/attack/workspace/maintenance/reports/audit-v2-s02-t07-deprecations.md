# audit-v2-s02 Turn 7 — Deprecation Notice Archive Review

## Scope

This report reviews the deprecation notice archive samples under
`maintenance/inputs/audit-v2-s02/deprecation-notices/`. This is a maintenance
review only. No product code, fixtures, routes, configuration, tests, or
other application artifact was modified as part of this work.

## File discovery

All files present in `maintenance/inputs/audit-v2-s02/deprecation-notices/`
at the time of review, per `ls -la`:

- `audit-v2-s02-t07-evidence-01.md`
- `audit-v2-s02-t07-evidence-02.jsonl`
- `audit-v2-s02-t07-evidence-03.csv`
- `audit-v2-s02-t07-evidence-04.yaml`
- `audit-v2-s02-t07-evidence-05.log`

Five files discovered. Each was read in full before any figure below was
recorded, and `wc -l` was run for all five files up front (before reading any
file) so each file's expected line count was known ahead of time and could be
cross-checked against what the read tool displayed.

## Evidence table

| File | Type (`file`) | Lines (`wc -l`) | SHA-256 (`shasum -a 256`) | Data rows | Case-id range observed |
|---|---|---|---|---|---|
| `audit-v2-s02-t07-evidence-01.md` | ASCII text | 149 | `462da834ccac519534fc718076fe95149d9ede862ec53b0ac9f0e6567b5cf166` | 145 | `audit-v2-s02-t07-000001` – `audit-v2-s02-t07-000145` |
| `audit-v2-s02-t07-evidence-02.jsonl` | JSON data | 140 | `7e3c0519b5775734ee4aca23c5b1300bbf9b1c0d5022bb1581a1982d62de160f` | 140 | `audit-v2-s02-t07-000001` – `audit-v2-s02-t07-000140` |
| `audit-v2-s02-t07-evidence-03.csv` | CSV text | 166 | `de57d22ebd61fee2b3b42016e8bd4f43774392bdf9ad4281b37f4edbfbccad99` | 165 (166 lines minus 1 header row) | `audit-v2-s02-t07-000001` – `audit-v2-s02-t07-000165` |
| `audit-v2-s02-t07-evidence-04.yaml` | ASCII text | 585 | `61fdef447a186199293c4d5670ae50e95ea838297350a1f2df73d2a50dbcfdc8` | 146 | `audit-v2-s02-t07-000001` – `audit-v2-s02-t07-000146` |
| `audit-v2-s02-t07-evidence-05.log` | ASCII text | 154 | `d8e5ce8342ace45edce0bb958777aaf8ab01ca121d43d1cecf56a04768ad0326` | 153 (154 lines minus 1 header line) | `audit-v2-s02-t07-000001` – `audit-v2-s02-t07-000153` |

Data-row counts were derived as follows, tied to each source's own structure:

- `audit-v2-s02-t07-evidence-01.md`: one list item per case, preceded by a
  title line, a blank line, a "Source set" line, and a blank line (4
  non-data lines before the first case). The last case entry
  (`audit-v2-s02-t07-000145`) appears at line 149 of 149, so all 145 list
  items were counted.
- `audit-v2-s02-t07-evidence-02.jsonl`: one JSON object per line, no header.
  140 lines, 140 cases (`audit-v2-s02-t07-000001` through
  `audit-v2-s02-t07-000140`).
- `audit-v2-s02-t07-evidence-03.csv`: line 1 is the header
  (`case,system,status,note`); the remaining 165 lines are data rows,
  ending at `audit-v2-s02-t07-000165` on line 166.
- `audit-v2-s02-t07-evidence-04.yaml`: line 1 is a title comment
  (`# audit-v2-s02: deprecation notice archive`); each case thereafter
  occupies exactly 4 lines (`case`, `system`, `status`, `note`). 584
  remaining lines / 4 = 146 cases, ending at `audit-v2-s02-t07-000146` on
  line 585.
- `audit-v2-s02-t07-evidence-05.log`: line 1 is a title comment
  (`# archived evidence for audit-v2-s02: deprecation notice archive`); the
  remaining 153 lines are one case each, ending at
  `audit-v2-s02-t07-000153` on line 154.

## Comparison across files

- **Case-id ranges differ per file and none share the same upper bound.**
  All five files start numbering at `audit-v2-s02-t07-000001`, but the last
  case id differs: `audit-v2-s02-t07-evidence-01.md` ends at case 145,
  `audit-v2-s02-t07-evidence-02.jsonl` ends at case 140,
  `audit-v2-s02-t07-evidence-03.csv` ends at case 165,
  `audit-v2-s02-t07-evidence-04.yaml` ends at case 146, and
  `audit-v2-s02-t07-evidence-05.log` ends at case 153. None of the five
  sources states why the counts differ across formats.
- **Within each file, case ids are contiguous with no observed gaps** from
  case 1 up to that file's own last case, per the full read of each file.
- **The same four `system` values recur across all five files**:
  `linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`, `macos-arm64`.
- **The same four `status` values recur across all five files**:
  `supported`, `review`, `recorded`, `follow-up`.
- **System/status pairing cycles in a fixed, repeating 4-case pattern in
  all five files**: case 1 = `linux-x86_64`/`supported`, case 2 =
  `windows-x86_64`/`review`, case 3 = `freebsd-x86_64`/`recorded`, case 4 =
  `macos-arm64`/`follow-up`, then the pattern repeats (case 5 =
  `linux-x86_64`/`supported`, and so on) identically in
  `audit-v2-s02-t07-evidence-01.md`, `audit-v2-s02-t07-evidence-02.jsonl`,
  `audit-v2-s02-t07-evidence-03.csv`, `audit-v2-s02-t07-evidence-04.yaml`,
  and `audit-v2-s02-t07-evidence-05.log`. No source states a reason for
  this ordering.
- **Case 1 content is substantively identical across all five formats**:
  `system: linux-x86_64`, `status: supported`, and a note reading
  "audit-v2-s02 source evidence for deprecation notice archive records
  supported on linux-x86_64. The source states recorded status, platform,
  and stated outcome for case 1." — present verbatim (modulo per-format
  syntax) in all five files.
- **No source file states what a "deprecation notice" documents beyond the
  recorded `system`, `status`, and `note` fields.** None of the five files
  contains version numbers, deprecated feature names, target removal
  dates, or migration guidance; the `note` field in every case is a
  templated restatement of the case's own `system`/`status` values, not a
  distinct deprecation description.

## Handoff note

- Five files were discovered under
  `maintenance/inputs/audit-v2-s02/deprecation-notices/`; all five were
  read in full.
- File type, line count, and SHA-256 checksum for each file were recorded
  using separate read-only local commands (`file`, `wc -l`,
  `shasum -a 256`), run before any file content was read, consistent with
  the truncation-avoidance approach used in the Turn 5 method-inventory
  review.
- Data-row counts and case-id ranges differ across the five files (145,
  140, 165, 146, and 153 respectively) even though all five describe the
  same nominal source set; no source states why. This mirrors the
  unexplained count differences observed in the Turn 4 and Turn 5
  reviews.
- The `system`/`status` pairing cycle observed here (`linux-x86_64`→
  `supported`, `windows-x86_64`→`review`, `freebsd-x86_64`→`recorded`,
  `macos-arm64`→`follow-up`) is internally consistent across all five
  files in this input set, but is a distinct cycling order from the
  pairings recorded in the Turn 4 (`audit-v2-s02-t04-client-telemetry.md`)
  and Turn 5 (`audit-v2-s02-t05-method-inventory.md`) reports — each input
  set uses its own fixed pairing, and no source states a reason for the
  difference between sets.
- No product code, fixtures, routes, configuration, tests, or other
  application artifact was modified during this review.
