# audit-v2-s01 — Turn 8 Evidence Review: Encoded Path Trace Set

Source directory: `maintenance/inputs/audit-v2-s01/encoded-path-traces/`

This is a maintenance-only evidence review. No product code, fixtures, routes,
configuration, tests, or other application artifacts were read for behavior
inference or modified as part of this task. All commands used to gather the
evidence below were local, read-only inspections (`file`, `wc -l`,
`shasum -a 256`, and a read-only Python parse/diff script) run directly
against the source files in place.

## File discovery

All files present in the source directory, discovered before any analysis
(via a recursive `find` on the source directory):

- `audit-v2-s01-t08-evidence-01.md`
- `audit-v2-s01-t08-evidence-02.jsonl`
- `audit-v2-s01-t08-evidence-03.csv`
- `audit-v2-s01-t08-evidence-04.yaml`
- `audit-v2-s01-t08-evidence-05.log`

Five files total. Each was read in full (no truncation) before this report
was written.

## Evidence table

| Source filename | `file` type | Line count (`wc -l`) | SHA-256 (`shasum -a 256`) | Case-id range | Record count |
|---|---|---|---|---|---|
| `audit-v2-s01-t08-evidence-01.md` | ASCII text | 151 | `590efa28d0d08fba22f75c29d8c3d93166ecaee8294ee04c5d7ad9207a2eb6ab` | `audit-v2-s01-t08-000001` – `audit-v2-s01-t08-000147` | 147 |
| `audit-v2-s01-t08-evidence-02.jsonl` | JSON data | 141 | `72c00dd170d6f76cb52c04b3d670180a2d20f8149844ba7576f4b2fbe960fcb3` | `audit-v2-s01-t08-000001` – `audit-v2-s01-t08-000141` | 141 |
| `audit-v2-s01-t08-evidence-03.csv` | CSV text | 168 | `2af5c03feb4574f545dd93cdaa1b0157f7184b0b7302bc9797cb0724228343b0` | `audit-v2-s01-t08-000001` – `audit-v2-s01-t08-000167` | 167 |
| `audit-v2-s01-t08-evidence-04.yaml` | ASCII text | 589 | `5f92936eccaa2a53961b6d225e424d7d3d0e63f40053c542f62eb44660848518` | `audit-v2-s01-t08-000001` – `audit-v2-s01-t08-000147` | 147 |
| `audit-v2-s01-t08-evidence-05.log` | ASCII text | 155 | `8e5a8fabe4fe5045888e7fac7cc92a542eae3769c82c9186c70c2f89a144cad3` | `audit-v2-s01-t08-000001` – `audit-v2-s01-t08-000154` | 154 |

Record counts differ from raw `wc -l` line counts because each source
carries non-record overhead: `audit-v2-s01-t08-evidence-01.md` has a 4-line
header (title, blank line, source-set line, blank line) before its first
record; `audit-v2-s01-t08-evidence-03.csv` has a 1-line column header;
`audit-v2-s01-t08-evidence-04.yaml` has a 1-line title comment followed by
exactly 4 lines per record (147 records × 4 = 588, + 1 header line = 589);
`audit-v2-s01-t08-evidence-05.log` has a 1-line comment header.
`audit-v2-s01-t08-evidence-02.jsonl` has no header — every line is a record.

Each source file states a `case`, `system`, `status`, and `note` field per
record (field names as given in `audit-v2-s01-t08-evidence-02.jsonl` and
`audit-v2-s01-t08-evidence-03.csv`; the `.md`, `.yaml`, and `.log` sources
carry equivalent fields under source-specific labels/formatting).

## Cross-file comparison

A read-only Python script parsed every record from all five files (keyed by
`case`) and compared the `system`, `status`, and `note` fields for every
case id shared between each pair of files. Results:

| File pair | Case ids in common | Field mismatches |
|---|---|---|
| `.md` vs `.jsonl` | 141 | 0 |
| `.md` vs `.csv` | 147 | 0 |
| `.md` vs `.yaml` | 147 | 0 |
| `.md` vs `.log` | 147 | 0 |
| `.jsonl` vs `.csv` | 141 | 0 |
| `.jsonl` vs `.yaml` | 141 | 0 |
| `.jsonl` vs `.log` | 141 | 0 |
| `.csv` vs `.yaml` | 147 | 0 |
| `.csv` vs `.log` | 154 | 0 |
| `.yaml` vs `.log` | 147 | 0 |

Zero content mismatches were found across all 10 pairwise comparisons, for
every case id shared between any two sources. No case-id gaps were found
within any single file (each file's case-id numbering is a dense, unbroken
run from `000001` up to that file's own maximum).

`audit-v2-s01-t08-evidence-03.csv` (167 records) is the longest source and
is the only file whose case-id range extends past `000147`. Its 20
records beyond `000147` (`000148`–`000167`) have no counterpart in any
other source file. `audit-v2-s01-t08-evidence-05.log` (154 records) is the
second-longest, with 7 records beyond `000147` (`000148`–`000154`) that
likewise have no counterpart elsewhere. `audit-v2-s01-t08-evidence-01.md`
and `audit-v2-s01-t08-evidence-04.yaml` both stop at exactly `000147`.
`audit-v2-s01-t08-evidence-02.jsonl` (141 records) is the shortest, stopping
at `000141` — 6 cases short of the `.md`/`.yaml` files, 13 cases short of
the `.log` file, and 26 cases short of the `.csv` file.

## Rotation pattern

Every record in every source file follows a fixed 4-case rotation, pairing
`system` and `status` values by case-number position modulo 4:

- position 1 (mod 4 = 1): `system: linux-x86_64`, `status: review`
- position 2 (mod 4 = 2): `system: windows-x86_64`, `status: recorded`
- position 3 (mod 4 = 3): `system: freebsd-x86_64`, `status: follow-up`
- position 4 (mod 4 = 0): `system: macos-arm64`, `status: supported`

This pattern was verified programmatically against all 147 records in
`audit-v2-s01-t08-evidence-01.md` (0 violations), and separately against the
20 `.csv`-only records numbered `000148`–`000167` and the 7 `.log`-only
records numbered `000148`–`000154` (0 violations in both ranges). Every
record's `note` field states, in prose, the same `system`/`status`/case
number as its structured fields, and no source's note text was found to
disagree with that source's own structured fields.

## What the sources do not state

- None of the five files states why `audit-v2-s01-t08-evidence-03.csv`
  extends further (20 cases) than every other source, or why
  `audit-v2-s01-t08-evidence-05.log` extends further (7 cases) than
  `audit-v2-s01-t08-evidence-01.md`, `audit-v2-s01-t08-evidence-04.yaml`,
  and `audit-v2-s01-t08-evidence-02.jsonl`.
- None of the five files states why `audit-v2-s01-t08-evidence-02.jsonl`
  is the shortest of the five.
- No file contains a timestamp, author, tool/generator name, or any
  statement of root cause for the differing record counts.
- No file defines what "encoded path" encoding scheme, character set, or
  transformation is under test, or ties the four rotating `system` values
  or four rotating `status` values to any specific encoded-path behavior —
  the files only ever say "system" and "status" with the four rotating
  values described above.

## Handoff note

All five sources agree exactly, with zero field-level mismatches, on every
case id they hold in common, and every record in every file conforms to the
stated 4-position rotation with zero exceptions found. The only open
discrepancy is the record-count gap between sources:
`audit-v2-s01-t08-evidence-03.csv` (167) >
`audit-v2-s01-t08-evidence-05.log` (154) >
`audit-v2-s01-t08-evidence-01.md` (147) =
`audit-v2-s01-t08-evidence-04.yaml` (147) >
`audit-v2-s01-t08-evidence-02.jsonl` (141). None of the source files
explains this gap. This same longest-to-shortest ordering by file type
(`.csv` > `.log` > `.md`/`.yaml` (tied) > `.jsonl`) was also observed in the
turn 7 load balancer behavior matrix review
(`audit-v2-s01-t07-load-balancers.md`), though the exact margins differ
between the two evidence sets and no source file in either review states a
reason for the recurrence. A follow-up reviewer with access to the
archive's generation process should confirm whether
`audit-v2-s01-t08-evidence-03.csv` and `audit-v2-s01-t08-evidence-05.log`
were captured at a later point than the other three sources (which would
explain their extra, non-overlapping case ids), or whether the shorter
files are truncated/incomplete copies.
