# retry-s01: Crash Recovery Runbook Cases — Source Review

## Scope

Source directory: `maintenance/inputs/retry-s01/crash-runbook-cases/`

All files were discovered with a single `find` pass before any file was opened. Five files were found:

- `retry-s01-t10-evidence-01.md`
- `retry-s01-t10-evidence-02.jsonl`
- `retry-s01-t10-evidence-03.csv`
- `retry-s01-t10-evidence-04.yaml`
- `retry-s01-t10-evidence-05.log`

Each file was read in full. This is a read-only maintenance review; no product code, fixtures, routes, configuration, or test files were touched.

## Evidence Table

| File | Type (per `file`) | Line count (per `wc -l`) | SHA-256 | Case ID range present | Record count |
|---|---|---|---|---|---|
| `retry-s01-t10-evidence-01.md` | ASCII text | 47 | `139f7d31953e1cbf27df58ce4fa200b5b12a2a2cda6eb086f7bfe64a2d9c0351` | `retry-s01-t10-000001` .. `retry-s01-t10-000043` | 43 |
| `retry-s01-t10-evidence-02.jsonl` | JSON data | 42 | `076ccce73c7cb3c94593695a90bc86493a06aff24542b0215b15886f40bdfb5d` | `retry-s01-t10-000001` .. `retry-s01-t10-000042` | 42 |
| `retry-s01-t10-evidence-03.csv` | CSV text | 50 | `3e860a92fe9a7a95e15b3d1b36a1d351017c857a0911930b4889e588871419a6` | `retry-s01-t10-000001` .. `retry-s01-t10-000049` | 49 |
| `retry-s01-t10-evidence-04.yaml` | ASCII text | 177 | `2995d4d3a050160a47df8a02bd1e9d3b87a9bf1c813ec55cdbe35007ff80a962` | `retry-s01-t10-000001` .. `retry-s01-t10-000044` | 44 |
| `retry-s01-t10-evidence-05.log` | ASCII text | 46 | `9e9280c2d46c6b4ca765cb68b09c3f91684b0603b516dc5608c168344efc49c7` | `retry-s01-t10-000001` .. `retry-s01-t10-000045` | 45 |

Line counts are raw `wc -l` output (the CSV's 50 lines include its header row, giving 49 data records; the other four formats have no header row).

## Comparison

A field-by-field comparison script parsed each file's own `case` / `system` / `status` / `note` records natively (JSON parsing for `.jsonl`, `csv.DictReader` for `.csv`, line-pattern parsing for `.md`, `.yaml`, `.log`) and compared them:

- **Record counts differ across the five files**, unlike the corresponding evidence sets reviewed previously for other `retry-s01` inputs (which had matching counts across all formats). Here: `retry-s01-t10-evidence-02.jsonl` has 42 records, `retry-s01-t10-evidence-01.md` has 43, `retry-s01-t10-evidence-04.yaml` has 44, `retry-s01-t10-evidence-05.log` has 45, and `retry-s01-t10-evidence-03.csv` has 49 — the most of any file.
- **The five case-ID ranges form a strict, contiguous nesting.** Every file's case IDs start at `retry-s01-t10-000001` and run without gaps to that file's own maximum. The shorter files' ranges are each an exact prefix of the next-longer file's range: `retry-s01-t10-evidence-02.jsonl` (1–42) is a prefix of `retry-s01-t10-evidence-01.md` (1–43), which is a prefix of `retry-s01-t10-evidence-04.yaml` (1–44), which is a prefix of `retry-s01-t10-evidence-05.log` (1–45), which is a prefix of `retry-s01-t10-evidence-03.csv` (1–49). No file contains a case ID that a shorter file's range skips over.
- **Every case that appears in more than one file has identical `system`, `status`, and `note` field values across all files that contain it.** Zero field-level mismatches were found among the 42 cases common to all five files (case-by-case comparison against `retry-s01-t10-evidence-01.md` as reference, checked against all five sources).
- The `system` values cycle through `windows-x86_64`, `freebsd-x86_64`, `macos-arm64`, `linux-x86_64` in a repeating 4-case pattern, and `status` cycles through `follow-up`, `supported`, `review`, `recorded` in lockstep with the same 4-case pattern, as shown by the values recorded in each source file for cases `000001` through the maximum case number present in that file.
- Each record's `note` field states only that "the source states operator steps, stated preconditions, and observed outcomes" for that case number — no operator steps, preconditions, or outcomes are themselves given in any of the five files. This wording is identical in structure across `retry-s01-t10-evidence-01.md`, `retry-s01-t10-evidence-02.jsonl`, `retry-s01-t10-evidence-03.csv`, `retry-s01-t10-evidence-04.yaml`, and `retry-s01-t10-evidence-05.log`.

## Handoff Note

- These five files do not agree on how many crash-recovery runbook cases exist for `retry-s01`, turn 10. The case count present ranges from 42 (`retry-s01-t10-evidence-02.jsonl`) to 49 (`retry-s01-t10-evidence-03.csv`), with `retry-s01-t10-evidence-01.md` (43), `retry-s01-t10-evidence-04.yaml` (44), and `retry-s01-t10-evidence-05.log` (45) falling in between. Any downstream consumer that needs an authoritative case count or the full set of cases must reconcile this discrepancy against `retry-s01-t10-evidence-03.csv`, the only file that includes cases `retry-s01-t10-000044` through `retry-s01-t10-000049`; these six cases are absent from all four other source files. No source file states which file (if any) is authoritative, so this report does not assume one.
- Because the five sets nest as exact prefixes with no field-level conflicts on overlapping cases, there is no evidence of a data-integrity discrepancy (e.g., disagreement about a given case's contents) — only a difference in how many trailing cases each file happened to capture. This report does not infer a reason for the differing extents, since none of the five source files states one.
- As with the other `retry-s01` evidence sets reviewed for this source set, every `note` field asserts that operator steps, stated preconditions, and observed outcomes exist "in the source" for each case, but no operator steps, preconditions, or outcomes are actually shown in any of the five files reviewed here. A reader relying on this report for actual runbook procedure content will not find it in these sources.
