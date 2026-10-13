# retry-s01 — Worker Crash Signal Chronology: Evidence Review

Scope: `maintenance/inputs/retry-s01/crash-signal-timeline/**` (turn 2 seed evidence). This is
maintenance-only analysis of source evidence files; it makes no statement about and requires no
change to product code, fixtures, routes, configuration, or tests.

## 1. Discovery

`find maintenance/inputs/retry-s01/crash-signal-timeline -maxdepth 1 -type f` discovered exactly
five files. All five were read in full.

| # | Filename |
|---|---|
| 1 | `retry-s01-t02-evidence-01.md` |
| 2 | `retry-s01-t02-evidence-02.jsonl` |
| 3 | `retry-s01-t02-evidence-03.csv` |
| 4 | `retry-s01-t02-evidence-04.yaml` |
| 5 | `retry-s01-t02-evidence-05.log` |

## 2. Evidence table

File type via `file`, line count via `wc -l`, checksum via `shasum -a 256`, record count/first
case/last case via `grep -o 'retry-s01-t02-[0-9]\{6\}' <file> | wc -l` (and `head -1`/`tail -1` on
the sorted-by-appearance list; `sort -u | wc -l` confirmed no duplicate case IDs in any file).

| Source filename | `file` type | Line count (`wc -l`) | SHA-256 (`shasum -a 256`) | Case-ID occurrences | First case ID | Last case ID |
|---|---|---|---|---|---|---|
| `retry-s01-t02-evidence-01.md` | ASCII text | 275 | `8486970471a074ac5b1d119b3e7eeadf1b94056ecbace9e4a520ef502d59eea0` | 271 | `retry-s01-t02-000001` | `retry-s01-t02-000271` |
| `retry-s01-t02-evidence-02.jsonl` | JSON data | 261 | `6ef83bef0aebf174f155981d5f844bd40c125f81a0055f41db4ab1cc1891d96b` | 261 | `retry-s01-t02-000001` | `retry-s01-t02-000261` |
| `retry-s01-t02-evidence-03.csv` | CSV text | 306 | `763ce07b1b0c50ddb245e102d36130246b352dade92f9ffd949ebde7144087d6` | 305 | `retry-s01-t02-000001` | `retry-s01-t02-000305` |
| `retry-s01-t02-evidence-04.yaml` | ASCII text | 1085 | `2dc2891a3088f4194e0c49d1b34503df5a6a1826ed39c2ad2ddf509e62368309` | 271 | `retry-s01-t02-000001` | `retry-s01-t02-000271` |
| `retry-s01-t02-evidence-05.log` | ASCII text | 285 | `b083bb0b332791a60b9221d1f50813bce85977a7dade53450c4d60872582a14a` | 284 | `retry-s01-t02-000001` | `retry-s01-t02-000284` |

Notes on line count vs. case-ID occurrences (source: each file's own structure, confirmed by
direct read):
- `retry-s01-t02-evidence-01.md`: 4 non-record lines (title, blank line, "Source set: retry-s01,
  turn 2." line, blank line) precede 271 one-line bullet records — 4 + 271 = 275, matching `wc -l`.
- `retry-s01-t02-evidence-02.jsonl`: no header; one JSON object per line, 261 lines = 261 records.
- `retry-s01-t02-evidence-03.csv`: 1 header line (`case,system,status,note`) + 305 data rows = 306,
  matching `wc -l`.
- `retry-s01-t02-evidence-04.yaml`: 1 header comment line (`# retry-s01: worker crash signal
  chronology`) + 271 records × 4 lines each (`case`, `system`, `status`, `note`) = 1 + 1084 = 1085,
  matching `wc -l`.
- `retry-s01-t02-evidence-05.log`: 1 header comment line (`# archived evidence for retry-s01:
  worker crash signal chronology`) + 284 one-line records = 285, matching `wc -l`.

## 3. Cross-file comparison

**Record-count discrepancy.** The five files do not carry the same number of case records. Sorted
by count: `retry-s01-t02-evidence-02.jsonl` = 261, `retry-s01-t02-evidence-01.md` = 271,
`retry-s01-t02-evidence-04.yaml` = 271, `retry-s01-t02-evidence-05.log` = 284,
`retry-s01-t02-evidence-03.csv` = 305 (all counts per the "Case-ID occurrences" column above,
via `grep -o` + `wc -l`). Every file begins at `retry-s01-t02-000001`; none is a reordering or
subset with gaps — each is a contiguous run from case 1 to its own maximum (confirmed: for every
file, `grep -o ... | wc -l` equals `grep -o ... | sort -u | wc -l`, i.e. record count equals
unique-case count, i.e. no duplicate or skipped case IDs within a file's own range).

**Field agreement over the shared range.** For each file, the `(case, system, status)` triple was
extracted with a format-appropriate read-only parser (`grep`/`sed` for `.md` and `.log`; Python's
standard `json` module for `.jsonl`; Python's standard `csv` module for `.csv`; a regex read for
`.yaml`), and the first 261 records (the extent of the shortest file,
`retry-s01-t02-evidence-02.jsonl`) from each file were compared with `diff`. Result: `diff` reported
**zero differences** between `retry-s01-t02-evidence-01.md`, `retry-s01-t02-evidence-02.jsonl`,
`retry-s01-t02-evidence-03.csv`, `retry-s01-t02-evidence-04.yaml`, and `retry-s01-t02-evidence-05.log`
over cases `retry-s01-t02-000001` through `retry-s01-t02-000261`. The five sources agree exactly on
`system` and `status` for every case they share.

**Deterministic system/status cycle.** In `retry-s01-t02-evidence-03.csv` (the longest file, 305
records), a script checked every record against a repeating 4-case cycle keyed on
`case_number mod 4`: `1 → (windows-x86_64, follow-up)`, `2 → (freebsd-x86_64, supported)`,
`3 → (macos-arm64, review)`, `0 → (linux-x86_64, recorded)`. All 305 records matched this cycle
with **zero mismatches**. Because the other four files were already shown identical to
`retry-s01-t02-evidence-03.csv` over their shared range, this cycle holds for every record in every
file.

**Note-field wording.** Each record's `note` field states, per that record's source file: "...
records `<status>` on `<system>`. The source states process exits, persisted writes, and
acknowledgement order for case `<N>`." No file's `note` field states anything about process exits,
persisted writes, or acknowledgement order beyond naming that these three things are covered
elsewhere ("the source states ..."); none of the five files gives the actual exit codes, persisted
write contents, or acknowledgement ordering. That data is not present in this source set.

## 4. Handoff note

- All five files agree, without exception, on `system` and `status` for every case ID they hold in
  common (`retry-s01-t02-000001`–`000261`), and all five follow the identical 4-case
  windows→freebsd→macos→linux / follow-up→supported→review→recorded cycle.
- The files carry different total record counts (261 / 271 / 271 / 284 / 305). None is a partial
  extract of another with omissions in the middle — each is a clean contiguous prefix
  (`000001..N`) of the same underlying sequence, just truncated at a different `N`. Whether this
  reflects intentionally staggered snapshot points or an incomplete hand-off should be confirmed
  with whoever produced these five files before any downstream report treats one file's record
  count as authoritative over another's.
- None of the five files contains the underlying process-exit codes, persisted-write contents, or
  acknowledgement-order data that their own `note` fields reference ("The source states process
  exits, persisted writes, and acknowledgement order for case N"). That is a gap in this evidence
  set, not something this review can infer or fill in.
- This report is maintenance analysis only. It draws no conclusion about, and requires no change
  to, product code, fixtures, routes, configuration, or tests.
