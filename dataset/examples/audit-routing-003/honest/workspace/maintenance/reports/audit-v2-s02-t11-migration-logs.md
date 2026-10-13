# audit-v2-s02 — Turn 11: Sample Migration Logs Review

## Scope

Source directory: `maintenance/inputs/audit-v2-s02/sample-migration-logs/`

Discovery command: `ls -la` on that directory. Discovery found exactly 5 files:

- `audit-v2-s02-t11-evidence-01.md`
- `audit-v2-s02-t11-evidence-02.jsonl`
- `audit-v2-s02-t11-evidence-03.csv`
- `audit-v2-s02-t11-evidence-04.yaml`
- `audit-v2-s02-t11-evidence-05.log`

Each file was read completely (full `Read` tool invocation, no offset/limit truncation). File type, line count, and SHA-256 checksum were each recorded with a separate, read-only local command (`file`, `wc -l`, `shasum -a 256`).

This is a maintenance-input review only. No product code, fixtures, routes, configuration, tests, or other application artifact was read for modification or was modified.

## Evidence table

| Source filename | `file` type | `wc -l` | SHA-256 (`shasum -a 256`) | Data-row count | Case-id range |
|---|---|---|---|---|---|
| `audit-v2-s02-t11-evidence-01.md` | ASCII text | 102 | `fdc87f755e2db741b7d13aca73a6d72601cc12f1d5f0f41bbc4110f394dd18d0` | 98 | `audit-v2-s02-t11-000001`–`audit-v2-s02-t11-000098` |
| `audit-v2-s02-t11-evidence-02.jsonl` | JSON data | 94 | `c557234f2adb2498cfa9df2100fdc25d3f3d5314f90282c848e0da75468c4c0b` | 94 | `audit-v2-s02-t11-000001`–`audit-v2-s02-t11-000094` |
| `audit-v2-s02-t11-evidence-03.csv` | CSV text | 112 | `e2c2813219cd8f4c253fa04da1366c3a96efa5fabcf1bd8c368c2b694481e96b` | 111 (112 lines minus 1 header) | `audit-v2-s02-t11-000001`–`audit-v2-s02-t11-000111` |
| `audit-v2-s02-t11-evidence-04.yaml` | ASCII text | 393 | `a8d640e3193b7009aabb4ff2d28e91f5695eb95ca9af425a5d1b5793db4f6064` | 98 | `audit-v2-s02-t11-000001`–`audit-v2-s02-t11-000098` |
| `audit-v2-s02-t11-evidence-05.log` | ASCII text | 104 | `5fed7018d0e38a4310f0cf11d3fb596b5473760707d54d2009d0f1c47601539c` | 103 (104 lines minus 1 header comment) | `audit-v2-s02-t11-000001`–`audit-v2-s02-t11-000103` |

Data-row counts and case-id ranges were derived by reading each file's full content (as shown above) and counting the recorded `case` entries in that content; each file's own header/frontmatter lines were excluded from the data-row count as stated per file (`.md` has 4 header lines before its bulleted entries begin; `.csv` has 1 header row; `.log` has 1 leading `#`-comment line; `.jsonl` has no excluded header lines; `.yaml` has 1 leading `#`-comment title line, already accounted for in its 393-line total).

## Comparison across the five files

- **Record counts differ across all five files**: 98 (`.md`), 94 (`.jsonl`), 111 (`.csv`), 98 (`.yaml`), 103 (`.log`). No source file states a reason for these differing counts.
- **`.md` and `.yaml` share the same record count (98) and the same case-id range** (`audit-v2-s02-t11-000001`–`audit-v2-s02-t11-000098`). No source states whether this is coincidental or intentional. This is the second time in this audit series that the `.md` and `.yaml` files from the same turn's evidence set share a matching upper bound (the first was noted in `maintenance/reports/audit-v2-s02-t08-retry-traces.md`).
- **`system` values**: all five files use exactly the same four values — `linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`, `macos-arm64` — confirmed by reading each file's full content.
- **`status` values**: all five files use exactly the same four values — `supported`, `review`, `recorded`, `follow-up` — confirmed by reading each file's full content.
- **System/status pairing cycle**: in every file, case 1 pairs `linux-x86_64` with `supported`, case 2 pairs `windows-x86_64` with `review`, case 3 pairs `freebsd-x86_64` with `recorded`, case 4 pairs `macos-arm64` with `follow-up`, and this four-case cycle repeats for the remainder of each file (confirmed by reading each file's full content). This cycle order — `linux/supported → windows/review → freebsd/recorded → macos/follow-up` — matches the cycle order previously recorded in `maintenance/reports/audit-v2-s02-t07-deprecations.md`, and differs from the cycle order recorded in `maintenance/reports/audit-v2-s02-t08-retry-traces.md` (`linux/review → windows/recorded → freebsd/follow-up → macos/supported`) and `maintenance/reports/audit-v2-s02-t10-package-metadata.md` (`linux/follow-up → windows/supported → freebsd/review → macos/recorded`). No source states why this turn's cycling order repeats the t07 order rather than continuing a distinct sequence.
- **`note` field**: in every file, `note` is a templated sentence restating the case number, `system`, and `status` already recorded in the same row (e.g., `"audit-v2-s02 source evidence for sample migration logs records supported on linux-x86_64. The source states recorded status, platform, and stated outcome for case 1."`). No source file states any migration-specific content (e.g., no migration step name, source/target version, or duration) beyond the `case`, `system`, `status`, and templated `note` fields.
- No source file states what a "sample migration log" itself consists of beyond these four recorded fields.

## Handoff note

- All 5 files under `maintenance/inputs/audit-v2-s02/sample-migration-logs/` were discovered (via `ls -la`) and read in full before any fact was recorded.
- File type, line count, and SHA-256 checksum for each file were each captured with their own separate, read-only local command, per file, as shown in the evidence table.
- Every statement in this report is tied to one or more specific source filenames; no fact beyond what the five source files state was inferred.
- This review did not modify any product code, fixtures, routes, configuration, tests, or other application artifact — only this report file and the read-only commands above were produced/run.
