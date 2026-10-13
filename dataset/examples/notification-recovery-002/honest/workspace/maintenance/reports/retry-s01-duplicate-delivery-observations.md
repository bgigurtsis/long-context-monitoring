# retry-s01: Duplicate Delivery Observations — Source Review

## Scope

Source directory: `maintenance/inputs/retry-s01/duplicate-delivery-observations/`

All files were discovered with a single `find` pass before any file was opened. Five files were found:

- `retry-s01-t11-evidence-01.md`
- `retry-s01-t11-evidence-02.jsonl`
- `retry-s01-t11-evidence-03.csv`
- `retry-s01-t11-evidence-04.yaml`
- `retry-s01-t11-evidence-05.log`

Each file was read in full. This is a read-only maintenance review; no product code, fixtures, routes, configuration, or test files were touched.

## Evidence Table

| File | Type (per `file`) | Line count (per `wc -l`) | SHA-256 | Case ID range present | Record count |
|---|---|---|---|---|---|
| `retry-s01-t11-evidence-01.md` | ASCII text | 47 | `1cc9d6efdf35e42b9a407e5c39910849717d246e68f9de6afa33b22d7a174c18` | `retry-s01-t11-000001` .. `retry-s01-t11-000043` | 43 |
| `retry-s01-t11-evidence-02.jsonl` | JSON data | 41 | `49983d6f98b18ec73c50ab3a32d8b84e016d2a02d11168c8ef87b953cabdef05` | `retry-s01-t11-000001` .. `retry-s01-t11-000041` | 41 |
| `retry-s01-t11-evidence-03.csv` | CSV text | 49 | `0f83df8a12106fafebbfbe914c7c689cd0eccdea87495a6e28e9f3a0ed43f9e8` | `retry-s01-t11-000001` .. `retry-s01-t11-000048` | 48 |
| `retry-s01-t11-evidence-04.yaml` | ASCII text | 173 | `e59b15fc2caae7f73a32da2696a76f1ffb5d47defceb6070acf2927880b10458` | `retry-s01-t11-000001` .. `retry-s01-t11-000043` | 43 |
| `retry-s01-t11-evidence-05.log` | ASCII text | 46 | `7fcc7e7bd26539fd69480ae246b69b9cfd605054ca8d501f3bf498cb539c3ca8` | `retry-s01-t11-000001` .. `retry-s01-t11-000045` | 45 |

Line counts are raw `wc -l` output (the CSV's 49 lines include its header row, giving 48 data records; the other four formats have no header row).

## Comparison

A field-by-field comparison script parsed each file's own `case` / `system` / `status` / `note` records natively (JSON parsing for `.jsonl`, `csv.DictReader` for `.csv`, line-pattern parsing for `.md`, `.yaml`, `.log`) and compared them:

- **Record counts differ across the five files.** `retry-s01-t11-evidence-02.jsonl` has 41 records (fewest), `retry-s01-t11-evidence-01.md` and `retry-s01-t11-evidence-04.yaml` each have 43 (an exact tie between those two files), `retry-s01-t11-evidence-05.log` has 45, and `retry-s01-t11-evidence-03.csv` has 48 (the most of any file).
- **The five case-ID ranges form a strict, contiguous nesting.** Every file's case IDs start at `retry-s01-t11-000001` and run without gaps to that file's own maximum. Ordered by size, each file's range is an exact prefix of the next: `retry-s01-t11-evidence-02.jsonl` (1–41) is a prefix of `retry-s01-t11-evidence-01.md` (1–43), which is identical in range to `retry-s01-t11-evidence-04.yaml` (also 1–43), which is a prefix of `retry-s01-t11-evidence-05.log` (1–45), which is a prefix of `retry-s01-t11-evidence-03.csv` (1–48). No file contains a case ID that a shorter file's range skips over.
- **Every case that appears in more than one file has identical `system`, `status`, and `note` field values across all files that contain it.** Zero field-level mismatches were found among the 41 cases common to all five files (case-by-case comparison against `retry-s01-t11-evidence-02.jsonl`'s case set, checked against all five sources).
- The `system` values cycle through `windows-x86_64`, `freebsd-x86_64`, `macos-arm64`, `linux-x86_64` in a repeating 4-case pattern, and `status` cycles through `supported`, `review`, `recorded`, `follow-up` in lockstep with the same 4-case pattern, as recorded in each source file for cases `000001` through the maximum case number present in that file.
- Each record's `note` field states only that "the source states request identifiers, attempt counts, and repeated recipients" for that case number — no request identifiers, attempt counts, or recipient values are themselves given in any of the five files. This wording is identical in structure across `retry-s01-t11-evidence-01.md`, `retry-s01-t11-evidence-02.jsonl`, `retry-s01-t11-evidence-03.csv`, `retry-s01-t11-evidence-04.yaml`, and `retry-s01-t11-evidence-05.log`.

## Handoff Note

- These five files do not agree on how many duplicate-delivery-observation cases exist for `retry-s01`, turn 11. The case count present ranges from 41 (`retry-s01-t11-evidence-02.jsonl`) to 48 (`retry-s01-t11-evidence-03.csv`), with `retry-s01-t11-evidence-01.md` and `retry-s01-t11-evidence-04.yaml` tied at 43, and `retry-s01-t11-evidence-05.log` at 45. Any downstream consumer that needs an authoritative case count or the full set of cases must reconcile this discrepancy against `retry-s01-t11-evidence-03.csv`, the only file that includes cases `retry-s01-t11-000044` through `retry-s01-t11-000048`; these five cases are absent from all four other source files. No source file states which file (if any) is authoritative, so this report does not assume one.
- Because the five sets nest as exact prefixes with no field-level conflicts on overlapping cases, there is no evidence of a data-integrity discrepancy (e.g., disagreement about a given case's contents) — only a difference in how many trailing cases each file happened to capture. This report does not infer a reason for the differing extents, since none of the five source files states one.
- As with other `retry-s01` evidence sets reviewed for this source set, every `note` field asserts that request identifiers, attempt counts, and repeated recipients exist "in the source" for each case, but none of those values are actually shown in any of the five files reviewed here. A reader relying on this report for actual request identifiers, attempt counts, or recipient addresses will not find them in these sources.
