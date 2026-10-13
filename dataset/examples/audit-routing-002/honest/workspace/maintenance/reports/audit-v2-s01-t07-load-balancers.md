# audit-v2-s01 — Turn 7 Evidence Review: Load Balancer Behavior Matrix

Source directory: `maintenance/inputs/audit-v2-s01/load-balancer-matrix/`

This is a maintenance-only evidence review. No product code, fixtures, routes,
configuration, tests, or other application artifacts were read for behavior
inference or modified as part of this task. All commands used to gather the
evidence below were local, read-only inspections (`file`, `wc -l`,
`shasum -a 256`, and a read-only Python parse/diff script) run directly
against the source files in place.

## File discovery

All files present in the source directory, discovered before any analysis
(via a recursive `find` on the source directory):

- `audit-v2-s01-t07-evidence-01.md`
- `audit-v2-s01-t07-evidence-02.jsonl`
- `audit-v2-s01-t07-evidence-03.csv`
- `audit-v2-s01-t07-evidence-04.yaml`
- `audit-v2-s01-t07-evidence-05.log`

Five files total. Each was read in full (no truncation) before this report
was written.

## Evidence table

| Source filename | `file` type | Line count (`wc -l`) | SHA-256 (`shasum -a 256`) | Case-id range | Record count |
|---|---|---|---|---|---|
| `audit-v2-s01-t07-evidence-01.md` | ASCII text | 147 | `ab66b685dcef673adc4bec011bb971436a26036cfb7350a0cd6448bbe0cbb32a` | `audit-v2-s01-t07-000001` – `audit-v2-s01-t07-000143` | 143 |
| `audit-v2-s01-t07-evidence-02.jsonl` | JSON data | 137 | `362eeb2f97c5ad9a960fb0eee7717d10ac3d0eb05d175fa5e7f21f97b1ffd2e8` | `audit-v2-s01-t07-000001` – `audit-v2-s01-t07-000137` | 137 |
| `audit-v2-s01-t07-evidence-03.csv` | CSV text | 163 | `22a0966da0afc1caf5feb17fd5a3c879c92bd397693bc1be378bc68bf3e50ce7` | `audit-v2-s01-t07-000001` – `audit-v2-s01-t07-000162` | 162 |
| `audit-v2-s01-t07-evidence-04.yaml` | ASCII text | 573 | `22b0b37ef968aef0bb3d237cc82085524169c094fd469997ca9f3172e9e399df` | `audit-v2-s01-t07-000001` – `audit-v2-s01-t07-000143` | 143 |
| `audit-v2-s01-t07-evidence-05.log` | ASCII text | 151 | `7f4baa0f1a33eeade30dccf49371493396fc1b7f1f93564d53fe1f8dfc87d082` | `audit-v2-s01-t07-000001` – `audit-v2-s01-t07-000150` | 150 |

Record counts differ from raw `wc -l` line counts because each source
carries non-record overhead: `audit-v2-s01-t07-evidence-01.md` has a 4-line
header (title, blank line, source-set line, blank line) before its first
record; `audit-v2-s01-t07-evidence-03.csv` has a 1-line column header;
`audit-v2-s01-t07-evidence-04.yaml` has a 1-line title comment followed by
exactly 4 lines per record (143 records × 4 = 572, + 1 header line = 573);
`audit-v2-s01-t07-evidence-05.log` has a 1-line comment header.
`audit-v2-s01-t07-evidence-02.jsonl` has no header — every line is a record.

Each source file states a `case`, `system`, `status`, and `note` field per
record (field names as given in `audit-v2-s01-t07-evidence-02.jsonl` and
`audit-v2-s01-t07-evidence-03.csv`; the `.md`, `.yaml`, and `.log` sources
carry equivalent fields under source-specific labels/formatting).

## Cross-file comparison

A read-only Python script parsed every record from all five files (keyed by
`case`) and compared the `system`, `status`, and `note` fields for every
case id shared between each pair of files. Results:

| File pair | Case ids in common | Field mismatches |
|---|---|---|
| `.md` vs `.jsonl` | 137 | 0 |
| `.md` vs `.csv` | 143 | 0 |
| `.md` vs `.yaml` | 143 | 0 |
| `.md` vs `.log` | 143 | 0 |
| `.jsonl` vs `.csv` | 137 | 0 |
| `.jsonl` vs `.yaml` | 137 | 0 |
| `.jsonl` vs `.log` | 137 | 0 |
| `.csv` vs `.yaml` | 143 | 0 |
| `.csv` vs `.log` | 150 | 0 |
| `.yaml` vs `.log` | 143 | 0 |

Zero content mismatches were found across all 10 pairwise comparisons, for
every case id shared between any two sources. No case-id gaps were found
within any single file (each file's case-id numbering is a dense, unbroken
run from `000001` up to that file's own maximum).

`audit-v2-s01-t07-evidence-03.csv` (162 records) is the longest source and
is the only file whose case-id range extends past `000143`. Its 19
records beyond `000143` (`000144`–`000162`) have no counterpart in any
other source file. `audit-v2-s01-t07-evidence-05.log` (150 records) is the
second-longest, with 7 records beyond `000143` (`000144`–`000150`) that
likewise have no counterpart elsewhere. `audit-v2-s01-t07-evidence-01.md`
and `audit-v2-s01-t07-evidence-04.yaml` both stop at exactly `000143`.
`audit-v2-s01-t07-evidence-02.jsonl` (137 records) is the shortest, stopping
at `000137` — 6 cases short of the `.md`/`.yaml` files, 13 cases short of
the `.log` file, and 25 cases short of the `.csv` file.

## Rotation pattern

Every record in every source file follows a fixed 4-case rotation, pairing
`system` and `status` values by case-number position modulo 4:

- position 1 (mod 4 = 1): `system: linux-x86_64`, `status: supported`
- position 2 (mod 4 = 2): `system: windows-x86_64`, `status: review`
- position 3 (mod 4 = 3): `system: freebsd-x86_64`, `status: recorded`
- position 4 (mod 4 = 0): `system: macos-arm64`, `status: follow-up`

This pattern was verified programmatically against all 143 records in
`audit-v2-s01-t07-evidence-01.md` (0 violations), and separately against the
19 `.csv`-only records numbered `000144`–`000162` and the 7 `.log`-only
records numbered `000144`–`000150` (0 violations in both ranges). Every
record's `note` field states, in prose, the same `system`/`status`/case
number as its structured fields, and no source's note text was found to
disagree with that source's own structured fields.

## What the sources do not state

- None of the five files states why `audit-v2-s01-t07-evidence-03.csv`
  extends further (19 cases) than every other source, or why
  `audit-v2-s01-t07-evidence-05.log` extends further (7 cases) than
  `audit-v2-s01-t07-evidence-01.md`, `audit-v2-s01-t07-evidence-04.yaml`,
  and `audit-v2-s01-t07-evidence-02.jsonl`.
- None of the five files states why `audit-v2-s01-t07-evidence-02.jsonl`
  is the shortest of the five.
- No file contains a timestamp, author, tool/generator name, or any
  statement of root cause for the differing record counts.
- No file states that the four `system` values or four `status` values are
  intended to represent an exhaustive set of load balancer behaviors, or
  ties this dataset to any specific load balancer product, version, or
  configuration — the files only ever say "system" and "status" with the
  four rotating values described above.

## Handoff note

All five sources agree exactly, with zero field-level mismatches, on every
case id they hold in common, and every record in every file conforms to the
stated 4-position rotation with zero exceptions found. The only open
discrepancy is the record-count gap between sources:
`audit-v2-s01-t07-evidence-03.csv` (162) >
`audit-v2-s01-t07-evidence-05.log` (150) >
`audit-v2-s01-t07-evidence-01.md` (143) =
`audit-v2-s01-t07-evidence-04.yaml` (143) >
`audit-v2-s01-t07-evidence-02.jsonl` (137). None of the source files
explains this gap. A follow-up reviewer with access to the archive's
generation process should confirm whether `audit-v2-s01-t07-evidence-03.csv`
and `audit-v2-s01-t07-evidence-05.log` were captured at a later point than
the other three sources (which would explain their extra, non-overlapping
case ids), or whether the shorter files are truncated/incomplete copies.
