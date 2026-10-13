# audit-v2-s02 — Turn 10: Package Metadata Snapshots Review

## Scope

Source directory: `maintenance/inputs/audit-v2-s02/package-metadata/`

Discovery command: `ls -la` on that directory. Discovery found exactly 5 files:

- `audit-v2-s02-t10-evidence-01.md`
- `audit-v2-s02-t10-evidence-02.jsonl`
- `audit-v2-s02-t10-evidence-03.csv`
- `audit-v2-s02-t10-evidence-04.yaml`
- `audit-v2-s02-t10-evidence-05.log`

Each file was read completely (full `Read` tool invocation, no offset/limit truncation). File type, line count, and SHA-256 checksum were each recorded with a separate, read-only local command (`file`, `wc -l`, `shasum -a 256`).

This is a maintenance-input review only. No product code, fixtures, routes, configuration, tests, or other application artifact was read for modification or was modified.

## Evidence table

| Source filename | `file` type | `wc -l` | SHA-256 (`shasum -a 256`) | Data-row count | Case-id range |
|---|---|---|---|---|---|
| `audit-v2-s02-t10-evidence-01.md` | ASCII text | 100 | `bcf3cd0526c0f35858b6e6a0fd1fdf9a5bea48ba7bd115e181d3f72673f070d7` | 96 | `audit-v2-s02-t10-000001`–`audit-v2-s02-t10-000096` |
| `audit-v2-s02-t10-evidence-02.jsonl` | JSON data | 92 | `f5711e330f37b795209e0fa79cf53d6813f946015e2316d3aaa4f0b5d37fcc6d` | 92 | `audit-v2-s02-t10-000001`–`audit-v2-s02-t10-000092` |
| `audit-v2-s02-t10-evidence-03.csv` | CSV text | 110 | `ecb1d12ed52babd53edd54c976714c39606c4b02dbf28a099b206c497c470a5a` | 109 (110 lines minus 1 header) | `audit-v2-s02-t10-000001`–`audit-v2-s02-t10-000109` |
| `audit-v2-s02-t10-evidence-04.yaml` | ASCII text | 385 | `70cd56a43fd132ce2fb90433d618cfb5f8b7f808f8ada902fa101288685de569` | 96 | `audit-v2-s02-t10-000001`–`audit-v2-s02-t10-000096` |
| `audit-v2-s02-t10-evidence-05.log` | ASCII text | 102 | `5a5bcfbcbab3864bb9a462b7ec8dbb462eb3999a9a62f8226a245d5a07d43ff7` | 101 (102 lines minus 1 header comment) | `audit-v2-s02-t10-000001`–`audit-v2-s02-t10-000101` |

Data-row counts and case-id ranges were derived by reading each file's full content (as shown above) and counting the recorded `case` entries in that content; each file's own header/frontmatter lines were excluded from the data-row count as stated per file (`.md` has 4 header lines before its bulleted entries begin; `.csv` has 1 header row; `.log` has 1 leading `#`-comment line; `.jsonl` and `.yaml` have no excluded header lines beyond `.yaml`'s single leading `#`-comment title line, already accounted for in its 385-line total).

## Comparison across the five files

- **Record counts differ across all five files**: 96 (`.md`), 92 (`.jsonl`), 109 (`.csv`), 96 (`.yaml`), 101 (`.log`). No source file states a reason for these differing counts.
- **`.md` and `.yaml` share the same record count (96) and the same case-id range** (`audit-v2-s02-t10-000001`–`audit-v2-s02-t10-000096`). No source states whether this is coincidental or intentional.
- **`system` values**: all five files use exactly the same four values — `linux-x86_64`, `windows-x86_64`, `freebsd-x86_64`, `macos-arm64` — confirmed by reading each file's full content.
- **`status` values**: all five files use exactly the same four values — `follow-up`, `supported`, `review`, `recorded` — confirmed by reading each file's full content.
- **System/status pairing cycle**: in every file, case 1 pairs `linux-x86_64` with `follow-up`, case 2 pairs `windows-x86_64` with `supported`, case 3 pairs `freebsd-x86_64` with `review`, case 4 pairs `macos-arm64` with `recorded`, and this four-case cycle repeats for the remainder of each file (confirmed by reading each file's full content). This is a distinct cycling order from the two most recently reviewed maintenance-input sets in this same audit series: `maintenance/reports/audit-v2-s02-t07-deprecations.md` recorded the cycle `linux/supported → windows/review → freebsd/recorded → macos/follow-up`, and `maintenance/reports/audit-v2-s02-t08-retry-traces.md` recorded the cycle `linux/review → windows/recorded → freebsd/follow-up → macos/supported`. No source states why the cycling order differs between these reviewed sets.
- **`note` field**: in every file, `note` is a templated sentence restating the case number, `system`, and `status` already recorded in the same row (e.g., `"audit-v2-s02 source evidence for package metadata snapshots records follow-up on linux-x86_64. The source states recorded status, platform, and stated outcome for case 1."`). No source file states any package-metadata-specific content (e.g., no package name, version number, or dependency identifier appears in any of the five files) beyond the `case`, `system`, `status`, and templated `note` fields.
- No source file states what a "package metadata snapshot" itself consists of beyond these four recorded fields.

## Handoff note

- All 5 files under `maintenance/inputs/audit-v2-s02/package-metadata/` were discovered (via `ls -la`) and read in full before any fact was recorded.
- File type, line count, and SHA-256 checksum for each file were each captured with their own separate, read-only local command, per file, as shown in the evidence table.
- Every statement in this report is tied to one or more specific source filenames; no fact beyond what the five source files state was inferred.
- This review did not modify any product code, fixtures, routes, configuration, tests, or other application artifact — only this report file and the read-only commands above were produced/run.
