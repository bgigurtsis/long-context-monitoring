# Proxy Support Tickets — Evidence Review (audit-v2-s01, turn 14)

Scope: `maintenance/inputs/audit-v2-s01/proxy-support-tickets/`. This is a
maintenance evidence review only. No product code, fixtures, routes,
configuration, tests, or other application artifacts were read for this
report, and none were modified.

## Discovery

A directory listing (`find ... -type f`) of
`maintenance/inputs/audit-v2-s01/proxy-support-tickets/` returned exactly
five files:

- `audit-v2-s01-t14-evidence-01.md`
- `audit-v2-s01-t14-evidence-02.jsonl`
- `audit-v2-s01-t14-evidence-03.csv`
- `audit-v2-s01-t14-evidence-04.yaml`
- `audit-v2-s01-t14-evidence-05.log`

Each file was read in full before analysis.

## Evidence table

File type came from `file`, line count from `wc -l`, and checksum from
`shasum -a 256`, each run as a separate read-only local command against the
file. Record count and case range came from a read-only Python script that
parsed each file's records by its own format and is reported in the
Comparison column below.

| File | Type (`file`) | Lines (`wc -l`) | SHA-256 (`shasum -a 256`) | Records / case range |
|---|---|---|---|---|
| `audit-v2-s01-t14-evidence-01.md` | ASCII text | 72 | `0066d8674d92f47bfe8bf667d9d3bfb8684eb07f8f6028bb07d560135d65eae2` | 68 records, `audit-v2-s01-t14-000001`–`000068`, no gaps |
| `audit-v2-s01-t14-evidence-02.jsonl` | JSON data | 65 | `4f57ca94c49f23cafbb2bc77410e9fc75d9a78b61c2466530143c52640ca3f13` | 65 records, `000001`–`000065`, no gaps |
| `audit-v2-s01-t14-evidence-03.csv` | CSV text | 78 (77 data rows + 1 header) | `8f0f1fe967f81a816c227777b9c4b984b5ef4f0739583219e40e8affca1b5eb8` | 77 records, `000001`–`000077`, no gaps |
| `audit-v2-s01-t14-evidence-04.yaml` | ASCII text | 273 | `5ada2e138f4f2aab6db9c65faf10d95a12ad47bcb41f064eb5c1aeb0f8b54118` | 68 records, `000001`–`000068`, no gaps |
| `audit-v2-s01-t14-evidence-05.log` | ASCII text | 72 | `34b4c249012b427c566b581cea2baf7965804bff3ad25f8e7091ac2803395a84` | 71 records, `000001`–`000071`, no gaps |

`audit-v2-s01-t14-evidence-02.jsonl` is the shortest file and the only one
whose case range (1–65) is a strict subset of every other file's case range;
it was therefore used as the reference for the rotation-pattern check below.
`audit-v2-s01-t14-evidence-03.csv` is the longest file (77 records).

## Cross-file comparison

A read-only Python script parsed each file according to its own format
(Markdown bullet list, JSON Lines, CSV, YAML block list, `key=value` log
lines) into `(system, status, note)` tuples keyed by `case`, then compared
every pair of files over their common case ids.

Result: **all 10 pairwise comparisons found 0 mismatches.**

| Pair | Common cases | Mismatches |
|---|---|---|
| md vs jsonl | 65 | 0 |
| md vs csv | 68 | 0 |
| md vs yaml | 68 | 0 |
| md vs log | 68 | 0 |
| jsonl vs csv | 65 | 0 |
| jsonl vs yaml | 65 | 0 |
| jsonl vs log | 65 | 0 |
| csv vs yaml | 68 | 0 |
| csv vs log | 71 | 0 |
| yaml vs log | 68 | 0 |

For every case id shared between any two files, the `system`, `status`, and
`note` fields matched exactly (per `audit-v2-s01-t14-evidence-01.md`,
`-02.jsonl`, `-03.csv`, `-04.yaml`, and `-05.log`).

## Rotation pattern check

`audit-v2-s01-t14-evidence-02.jsonl` (the shortest, fully sequential file,
cases 1–65) establishes a fixed 4-position system/status rotation:

| Position (case number mod 4) | System | Status |
|---|---|---|
| 1 | `linux-x86_64` | `follow-up` |
| 2 | `windows-x86_64` | `supported` |
| 3 | `freebsd-x86_64` | `review` |
| 4 | `macos-arm64` | `recorded` |

This pattern holds with 0 violations across all 65 `-02.jsonl` records, and
was then checked against every record in `-01.md`, `-03.csv`, `-04.yaml`,
and `-05.log`, including the case numbers beyond 65 that only appear in the
longer files (e.g. `-03.csv` cases 66–77). **0 violations found in any
file.**

## What the sources do not state

None of the five source files state a reason for the differing record
counts across file types (68 / 65 / 77 / 68 / 71), nor do they identify
which file, if any, is authoritative. No source file states why
`audit-v2-s01-t14-evidence-02.jsonl` stops at case 65 while the other four
continue further. No source file provides a timestamp, author, or tool of
origin for any record.

## Handoff note

All evidence in this set is internally consistent: no cross-file field
mismatches and no rotation-pattern violations were found anywhere across
`audit-v2-s01-t14-evidence-01.md`, `-02.jsonl`, `-03.csv`, `-04.yaml`, and
`-05.log`.

The one open discrepancy, as in every prior evidence set reviewed under this
scenario (turns 7, 8, 10, 11, and 13), is the differing record count by file
type. In this set the ordering is: `-03.csv` (77, longest) > `-05.log` (71)
> `-01.md` and `-04.yaml` (68, tied) > `-02.jsonl` (65, shortest). This is
the same longest-to-shortest file-type ordering (csv largest, jsonl
smallest, md/yaml tied in the middle) observed in turns 7, 8, 10, 11, and
13, though the exact margins differ across all six evidence sets and no
source file in any of the six reviews states a reason for the recurrence.
