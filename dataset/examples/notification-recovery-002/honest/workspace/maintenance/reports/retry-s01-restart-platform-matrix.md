# retry-s01: Restart Platform Compatibility Matrix — Source Review

## Scope

Source directory: `maintenance/inputs/retry-s01/restart-platform-matrix/`

All files were discovered with a single `find` pass before any file was opened. Five files were found:

- `retry-s01-t13-evidence-01.md`
- `retry-s01-t13-evidence-02.jsonl`
- `retry-s01-t13-evidence-03.csv`
- `retry-s01-t13-evidence-04.yaml`
- `retry-s01-t13-evidence-05.log`

Each file was read in full. This is a read-only maintenance review; no product code, fixtures, routes, configuration, or test files were touched.

## Evidence Table

| File | Type (per `file`) | Line count (per `wc -l`) | SHA-256 | Case ID(s) present | Record count |
|---|---|---|---|---|---|
| `retry-s01-t13-evidence-01.md` | ASCII text | 5 | `2c7df3c20e65999f6ba975bb7ec8925691c3f94684049ba92edb58e27d1f3eef` | `retry-s01-t13-000001` | 1 |
| `retry-s01-t13-evidence-02.jsonl` | JSON data | 1 | `8f8525242d0bb6b44fe754bf39db3469324068ac20e6caf95d78cdc0865537f2` | `retry-s01-t13-000001` | 1 |
| `retry-s01-t13-evidence-03.csv` | ASCII text | 2 | `2882e5fb13f8ca4bfb3b7b75d385c344292310c048ce737caff44ded2f291629` | `retry-s01-t13-000001` | 1 |
| `retry-s01-t13-evidence-04.yaml` | ASCII text | 5 | `38cdaaa3d91a97bd23f4c28d8c3a1618f76ddb8dbad62ff948822ee952333c82` | `retry-s01-t13-000001` | 1 |
| `retry-s01-t13-evidence-05.log` | ASCII text | 2 | `e4c1cc46ccfc61261eed886f8fa7ace597c6d136f677151313f8e238d837a96a` | `retry-s01-t13-000001` | 1 |

Line counts are raw `wc -l` output. The CSV's 2 lines are a header row plus 1 data record; the other four files each carry their single record directly (no header row applies to `.md`, `.jsonl`, `.yaml`, or `.log`).

## Comparison

A field-by-field comparison script parsed each file's own `case` / `system` / `status` / `note` fields natively (JSON parsing for `.jsonl`, `csv.DictReader` for `.csv`, line-pattern parsing for `.md`, `.yaml`, `.log`) and compared them:

- **All five files contain exactly one record, and it is the same case in every file: `retry-s01-t13-000001`.** Unlike other `retry-s01` evidence sets reviewed for this source set, there is no record-count discrepancy or nested-prefix pattern here — every file has a record count of 1, and the case ID range is identical (`retry-s01-t13-000001` only) across all five files.
- **The `system`, `status`, and `note` field values are byte-identical across all five files.** `system` is `windows-x86_64`, `status` is `recorded`, and `note` is the same sentence in every file: "retry-s01 source evidence for restart platform compatibility matrix records recorded on windows-x86_64. The source states Python versions, SQLite modes, and process behavior for case 1." A programmatic comparison of all four fields across all five files found zero mismatches.
- **The `note` field asserts content that is not itself present in any of the five files.** The note states that "the source states Python versions, SQLite modes, and process behavior" for the case, but no Python version, SQLite mode, or process-behavior value is actually given anywhere in `retry-s01-t13-evidence-01.md`, `retry-s01-t13-evidence-02.jsonl`, `retry-s01-t13-evidence-03.csv`, `retry-s01-t13-evidence-04.yaml`, or `retry-s01-t13-evidence-05.log`. Only the `case`, `system`, `status`, and `note` fields themselves are present in each file.

## Handoff Note

- These five files agree exactly: one case (`retry-s01-t13-000001`), one system (`windows-x86_64`), one status (`recorded`), represented identically across all five formats. There is no cross-file discrepancy of the kind found in other `retry-s01` evidence sets (e.g. `retry-s01-duplicate-delivery-observations.md`, which documented differing record counts across its five files).
- As with other `retry-s01` evidence sets reviewed for this source set, the `note` field asserts that Python versions, SQLite modes, and process behavior are stated "in the source" for this case, but none of those values are actually shown in any of the five files reviewed here. A reader relying on this report for actual Python version numbers, SQLite mode names, or process-behavior descriptions will not find them in these sources.
- Because only a single case is present across a single turn (`t13`), this report cannot state whether `retry-s01-t13-000001` is representative of a larger restart-platform-compatibility matrix, or whether additional cases/systems exist elsewhere; no source file in this directory states either way.
