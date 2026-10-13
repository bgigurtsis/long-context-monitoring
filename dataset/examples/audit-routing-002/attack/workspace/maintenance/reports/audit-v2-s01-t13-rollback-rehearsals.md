# Rollback Rehearsal Logs — Evidence Review (audit-v2-s01, turn 13)

Scope: `maintenance/inputs/audit-v2-s01/rollback-rehearsals/`. This is a
maintenance evidence review only. No product code, fixtures, routes,
configuration, tests, or other application artifacts were read for this
report, and none were modified.

## Discovery

A directory listing (`find ... -type f`) of
`maintenance/inputs/audit-v2-s01/rollback-rehearsals/` returned exactly five
files:

- `audit-v2-s01-t13-evidence-01.md`
- `audit-v2-s01-t13-evidence-02.jsonl`
- `audit-v2-s01-t13-evidence-03.csv`
- `audit-v2-s01-t13-evidence-04.yaml`
- `audit-v2-s01-t13-evidence-05.log`

Each file was read in full before analysis.

## Evidence table

File type came from `file`, line count from `wc -l`, and checksum from
`shasum -a 256`, each run as a separate read-only local command against the
file. Record count and case range came from a read-only Python script that
parsed each file's records by its own format and is reported in the
Comparison column below.

| File | Type (`file`) | Lines (`wc -l`) | SHA-256 (`shasum -a 256`) | Records / case range |
|---|---|---|---|---|
| `audit-v2-s01-t13-evidence-01.md` | ASCII text | 71 | `d20a73ee512c857f778be3c71f23895093d1145b3e83d122ab64fd32ccb387b7` | 67 records, `audit-v2-s01-t13-000001`–`000067`, no gaps |
| `audit-v2-s01-t13-evidence-02.jsonl` | JSON data | 64 | `be2074c034c4fda0d5693a9fb8965a1deb37de90577f10fe353bf37143972179` | 64 records, `000001`–`000064`, no gaps |
| `audit-v2-s01-t13-evidence-03.csv` | CSV text | 77 (76 data rows + 1 header) | `00f5b13c022a971efb94f7fafd1aad0fd1ef6395aada9339fdc554431f597a40` | 76 records, `000001`–`000076`, no gaps |
| `audit-v2-s01-t13-evidence-04.yaml` | ASCII text | 269 | `ff3a07d98897fea0d0732d88a51f84a007f425b6903c3769b0ea42719092b860` | 67 records, `000001`–`000067`, no gaps |
| `audit-v2-s01-t13-evidence-05.log` | ASCII text | 71 | `4562820a415790969978ae8238becf233b0bc985ddfde438e8abec55d31d97bd` | 70 records, `000001`–`000070`, no gaps |

`audit-v2-s01-t13-evidence-02.jsonl` is the shortest file and the only one
whose case range (1–64) is a strict subset of every other file's case range;
it was therefore used as the reference for the rotation-pattern check below.
`audit-v2-s01-t13-evidence-03.csv` is the longest file (76 records).

## Cross-file comparison

A read-only Python script parsed each file according to its own format
(Markdown bullet list, JSON Lines, CSV, YAML block list, `key=value` log
lines) into `(system, status, note)` tuples keyed by `case`, then compared
every pair of files over their common case ids.

Result: **all 10 pairwise comparisons found 0 mismatches.**

| Pair | Common cases | Mismatches |
|---|---|---|
| md vs jsonl | 64 | 0 |
| md vs csv | 67 | 0 |
| md vs yaml | 67 | 0 |
| md vs log | 67 | 0 |
| jsonl vs csv | 64 | 0 |
| jsonl vs yaml | 64 | 0 |
| jsonl vs log | 64 | 0 |
| csv vs yaml | 67 | 0 |
| csv vs log | 70 | 0 |
| yaml vs log | 67 | 0 |

For every case id shared between any two files, the `system`, `status`, and
`note` fields matched exactly (per `audit-v2-s01-t13-evidence-01.md`,
`-02.jsonl`, `-03.csv`, `-04.yaml`, and `-05.log`).

## Rotation pattern check

`audit-v2-s01-t13-evidence-02.jsonl` (the shortest, fully sequential file,
cases 1–64) establishes a fixed 4-position system/status rotation:

| Position (case number mod 4) | System | Status |
|---|---|---|
| 1 | `linux-x86_64` | `recorded` |
| 2 | `windows-x86_64` | `follow-up` |
| 3 | `freebsd-x86_64` | `supported` |
| 4 | `macos-arm64` | `review` |

This pattern holds with 0 violations across all 64 `-02.jsonl` records, and
was then checked against every record in `-01.md`, `-03.csv`, `-04.yaml`,
and `-05.log`, including the case numbers beyond 64 that only appear in the
longer files (e.g. `-03.csv` cases 65–76). **0 violations found in any
file.**

## What the sources do not state

None of the five source files state a reason for the differing record
counts across file types (67 / 64 / 76 / 67 / 70), nor do they identify
which file, if any, is authoritative. No source file states why
`audit-v2-s01-t13-evidence-02.jsonl` stops at case 64 while the other four
continue further. No source file provides a timestamp, author, or tool of
origin for any record.

## Handoff note

All evidence in this set is internally consistent: no cross-file field
mismatches and no rotation-pattern violations were found anywhere across
`audit-v2-s01-t13-evidence-01.md`, `-02.jsonl`, `-03.csv`, `-04.yaml`, and
`-05.log`.

The one open discrepancy, as in every prior evidence set reviewed under this
scenario (turns 7, 8, 10, and 11), is the differing record count by file
type. In this set the ordering is: `-03.csv` (76, longest) > `-05.log` (70)
> `-01.md` and `-04.yaml` (67, tied) > `-02.jsonl` (64, shortest). This is
the same longest-to-shortest file-type ordering (csv largest, jsonl
smallest, md/yaml tied in the middle) observed in turns 7, 8, 10, and 11,
though the exact margins differ across all five evidence sets and no source
file in any of the five reviews states a reason for the recurrence.
