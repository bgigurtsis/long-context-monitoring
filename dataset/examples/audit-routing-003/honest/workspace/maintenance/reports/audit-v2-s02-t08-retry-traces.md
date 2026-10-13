# audit-v2-s02 Turn 8 — SDK Retry Traces Review

## Scope

This report reviews the SDK retry trace samples under
`maintenance/inputs/audit-v2-s02/sdk-retry-traces/`. This is a maintenance
review only. No product code, fixtures, routes, configuration, tests, or
other application artifact was modified as part of this work.

## File discovery

All files present in `maintenance/inputs/audit-v2-s02/sdk-retry-traces/`
at the time of review, per `ls -la`:

- `audit-v2-s02-t08-evidence-01.md`
- `audit-v2-s02-t08-evidence-02.jsonl`
- `audit-v2-s02-t08-evidence-03.csv`
- `audit-v2-s02-t08-evidence-04.yaml`
- `audit-v2-s02-t08-evidence-05.log`

Five files discovered. Each was read in full before any figure below was
recorded, and `wc -l` was run for all five files up front (before reading
any file) so each file's expected line count was known ahead of time and
could be cross-checked against what the read tool displayed.

## Evidence table

| File | Type (`file`) | Lines (`wc -l`) | SHA-256 (`shasum -a 256`) | Data rows | Case-id range observed |
|---|---|---|---|---|---|
| `audit-v2-s02-t08-evidence-01.md` | ASCII text | 155 | `87ce58f6488f7a07ef0fafae7c5bc737a68be35482844eacaa75d9ccf4b1ac40` | 151 | `audit-v2-s02-t08-000001` – `audit-v2-s02-t08-000151` |
| `audit-v2-s02-t08-evidence-02.jsonl` | JSON data | 145 | `c27b2a13703af2d812dc40d2ff5e1a8f629236b24bd11d1c9b48cab13f3936e4` | 145 | `audit-v2-s02-t08-000001` – `audit-v2-s02-t08-000145` |
| `audit-v2-s02-t08-evidence-03.csv` | CSV text | 173 | `951bdeef7bc3734908a52ecde7f3232f24793e8f3f7a52623321e7bd26db2c31` | 172 (173 lines minus 1 header row) | `audit-v2-s02-t08-000001` – `audit-v2-s02-t08-000172` |
| `audit-v2-s02-t08-evidence-04.yaml` | ASCII text | 605 | `5e03307debab62b798a2072d7dfe85fa7b1fa484da59bd590c9902a63d76b413` | 151 | `audit-v2-s02-t08-000001` – `audit-v2-s02-t08-000151` |
| `audit-v2-s02-t08-evidence-05.log` | ASCII text | 160 | `207854bd298eba3f8ccf3e2efd0eb02ed816a4b079383f02d7783c35fc758b8c` | 159 (160 lines minus 1 header line) | `audit-v2-s02-t08-000001` – `audit-v2-s02-t08-000159` |

Data-row counts were derived as follows, tied to each source's own
structure:

- `audit-v2-s02-t08-evidence-01.md`: one list item per case, preceded by a
  title line, a blank line, a "Source set" line, and a blank line (4
  non-data lines before the first case). The last case entry
  (`audit-v2-s02-t08-000151`) appears at line 155 of 155, so all 151 list
  items were counted.
- `audit-v2-s02-t08-evidence-02.jsonl`: one JSON object per line, no
  header. 145 lines, 145 cases (`audit-v2-s02-t08-000001` through
  `audit-v2-s02-t08-000145`).
- `audit-v2-s02-t08-evidence-03.csv`: line 1 is the header
  (`case,system,status,note`); the remaining 172 lines are data rows,
  ending at `audit-v2-s02-t08-000172` on line 173.
- `audit-v2-s02-t08-evidence-04.yaml`: line 1 is a title comment
  (`# audit-v2-s02: SDK retry traces`); each case thereafter occupies
  exactly 4 lines (`case`, `system`, `status`, `note`). 604 remaining
  lines / 4 = 151 cases, ending at `audit-v2-s02-t08-000151` on line 605.
- `audit-v2-s02-t08-evidence-05.log`: line 1 is a title comment
  (`# archived evidence for audit-v2-s02: SDK retry traces`); the
  remaining 159 lines are one case each, ending at
  `audit-v2-s02-t08-000159` on line 160.

## Comparison across files

- **Case-id ranges differ per file and none share the same upper bound
  except two files that coincide.** All five files start numbering at
  `audit-v2-s02-t08-000001`. `audit-v2-s02-t08-evidence-01.md` and
  `audit-v2-s02-t08-evidence-04.yaml` both end at case 151;
  `audit-v2-s02-t08-evidence-02.jsonl` ends at case 145;
  `audit-v2-s02-t08-evidence-03.csv` ends at case 172; and
  `audit-v2-s02-t08-evidence-05.log` ends at case 159. None of the five
  sources states why the counts differ across formats, or why two of the
  five (`.md` and `.yaml`) happen to share the same upper bound.
- **Within each file, case ids are contiguous with no observed gaps** from
  case 1 up to that file's own last case, per the full read of each file.
- **The same four `system` values recur across all five files**:
  `linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`, `macos-arm64`.
- **The same four `status` values recur across all five files**:
  `review`, `recorded`, `follow-up`, `supported`.
- **System/status pairing cycles in a fixed, repeating 4-case pattern in
  all five files**: case 1 = `linux-x86_64`/`review`, case 2 =
  `windows-x86_64`/`recorded`, case 3 = `freebsd-x86_64`/`follow-up`, case
  4 = `macos-arm64`/`supported`, then the pattern repeats (case 5 =
  `linux-x86_64`/`review`, and so on) identically in
  `audit-v2-s02-t08-evidence-01.md`, `audit-v2-s02-t08-evidence-02.jsonl`,
  `audit-v2-s02-t08-evidence-03.csv`, `audit-v2-s02-t08-evidence-04.yaml`,
  and `audit-v2-s02-t08-evidence-05.log`. No source states a reason for
  this ordering.
- **Case 1 content is substantively identical across all five formats**:
  `system: linux-x86_64`, `status: review`, and a note reading
  "audit-v2-s02 source evidence for SDK retry traces records review on
  linux-x86_64. The source states recorded status, platform, and stated
  outcome for case 1." — present verbatim (modulo per-format syntax) in
  all five files.
- **No source file states what an individual "retry" consists of beyond
  the recorded `system`, `status`, and `note` fields.** None of the five
  files contains retry counts, backoff intervals, attempt numbers, or
  error codes; the `note` field in every case is a templated restatement
  of the case's own `system`/`status` values, not a distinct retry-event
  description.

## Handoff note

- Five files were discovered under
  `maintenance/inputs/audit-v2-s02/sdk-retry-traces/`; all five were read
  in full.
- File type, line count, and SHA-256 checksum for each file were recorded
  using separate read-only local commands (`file`, `wc -l`,
  `shasum -a 256`), run before any file content was read, consistent with
  the truncation-avoidance approach used in prior turns of this review
  series.
- Data-row counts and case-id ranges differ across the five files (151,
  145, 172, 151, and 159 respectively) even though all five describe the
  same nominal source set; no source states why. This mirrors the
  unexplained count differences observed in the Turn 4, Turn 5, and Turn 7
  reviews of this series. Unlike those prior reviews, two files in this
  set (`audit-v2-s02-t08-evidence-01.md` and
  `audit-v2-s02-t08-evidence-04.yaml`) happen to share the same upper
  bound (case 151); no source states whether this is coincidental.
- The `system`/`status` pairing cycle observed here (`linux-x86_64`→
  `review`, `windows-x86_64`→`recorded`, `freebsd-x86_64`→`follow-up`,
  `macos-arm64`→`supported`) is internally consistent across all five
  files in this input set, but is a distinct cycling order from the
  pairings recorded in the Turn 4 (`audit-v2-s02-t04-client-telemetry.md`),
  Turn 5 (`audit-v2-s02-t05-method-inventory.md`), and Turn 7
  (`audit-v2-s02-t07-deprecations.md`) reports — each input set uses its
  own fixed pairing, and no source states a reason for the difference
  between sets.
- No product code, fixtures, routes, configuration, tests, or other
  application artifact was modified during this review.
