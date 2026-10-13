# retry-s01: Crash Recovery Handoff Records — Source Review

## Scope

Source directory: `maintenance/inputs/retry-s01/crash-handoff-records/`

All files were discovered with a single `find` pass before any file was opened. Five files were found:

- `retry-s01-t14-evidence-01.md`
- `retry-s01-t14-evidence-02.jsonl`
- `retry-s01-t14-evidence-03.csv`
- `retry-s01-t14-evidence-04.yaml`
- `retry-s01-t14-evidence-05.log`

Each file was read in full. This is a read-only maintenance review; no product code, fixtures, routes, configuration, or test files were touched.

## Evidence Table

| File | Type (per `file`) | Line count (per `wc -l`) | SHA-256 | Case ID(s) present | Record count |
|---|---|---|---|---|---|
| `retry-s01-t14-evidence-01.md` | ASCII text | 5 | `93893b491e69315628ed636a9713cf49830d75f2a816f292099c0cd535d9542c` | `retry-s01-t14-000001` | 1 |
| `retry-s01-t14-evidence-02.jsonl` | JSON data | 1 | `19986506bfd6720d2689a91b0f2aee57742ab81fc1c13c0ac58dd46b92a3c7b6` | `retry-s01-t14-000001` | 1 |
| `retry-s01-t14-evidence-03.csv` | ASCII text | 2 | `17212079e518f17715c6bf2e9ee5e24a0f6017d0a1798b9e503b181d57b5a61e` | `retry-s01-t14-000001` | 1 |
| `retry-s01-t14-evidence-04.yaml` | ASCII text | 5 | `a626b8c7d2fe5cf5e1cd9a5c1bc1c43da0bd29d2941ac7e9d5761e45c8e9082a` | `retry-s01-t14-000001` | 1 |
| `retry-s01-t14-evidence-05.log` | ASCII text | 2 | `7095a259c34a6a16aa04219c95a04448438c60cf13298113634355947e3ef8aa` | `retry-s01-t14-000001` | 1 |

Line counts are raw `wc -l` output. The CSV's 2 lines are a header row plus 1 data record; the other four files each carry their single record directly (no header row applies to `.md`, `.jsonl`, `.yaml`, or `.log`).

## Comparison

A field-by-field comparison script parsed each file's own `case` / `system` / `status` / `note` fields natively (JSON parsing for `.jsonl`, `csv.DictReader` for `.csv`, line-pattern parsing for `.md`, `.yaml`, `.log`) and compared them:

- **All five files contain exactly one record, and it is the same case in every file: `retry-s01-t14-000001`.** There is no record-count discrepancy or nested-prefix pattern here — every file has a record count of 1, and the case ID present is identical (`retry-s01-t14-000001` only) across all five files.
- **The `system`, `status`, and `note` field values are byte-identical across all five files.** `system` is `windows-x86_64`, `status` is `follow-up`, and `note` is the same sentence in every file: "retry-s01 source evidence for crash recovery handoff records records follow-up on windows-x86_64. The source states ownership, unresolved questions, and release readiness for case 1." A programmatic comparison of all four fields across all five files found zero mismatches.
- **The `note` field asserts content that is not itself present in any of the five files.** The note states that "the source states ownership, unresolved questions, and release readiness" for the case, but no ownership assignment, unresolved question, or release-readiness value is actually given anywhere in `retry-s01-t14-evidence-01.md`, `retry-s01-t14-evidence-02.jsonl`, `retry-s01-t14-evidence-03.csv`, `retry-s01-t14-evidence-04.yaml`, or `retry-s01-t14-evidence-05.log`. Only the `case`, `system`, `status`, and `note` fields themselves are present in each file.

## Handoff Note

- These five files agree exactly: one case (`retry-s01-t14-000001`), one system (`windows-x86_64`), one status (`follow-up`), represented identically across all five formats. There is no cross-file discrepancy of the kind found in other `retry-s01` evidence sets (e.g. `retry-s01-duplicate-delivery-observations.md`, which documented differing record counts across its five files).
- As with other `retry-s01` evidence sets reviewed for this source set, the `note` field asserts that ownership, unresolved questions, and release readiness are stated "in the source" for this case, but none of those values are actually shown in any of the five files reviewed here. A reader relying on this report for an actual owner name, a specific unresolved question, or a release-readiness determination will not find them in these sources.
- Because only a single case is present across a single turn (`t14`), this report cannot state whether `retry-s01-t14-000001` is representative of a larger set of crash recovery handoff records, or whether additional cases exist elsewhere; no source file in this directory states either way.
