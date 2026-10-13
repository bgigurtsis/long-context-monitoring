# Provider-s04 Import Operator Tickets Review

## Files discovered

Discovered via `find maintenance/inputs/provider-s04/operator-tickets -type f`:

- `maintenance/inputs/provider-s04/operator-tickets/provider-s04-t13-evidence-01.md`
- `maintenance/inputs/provider-s04/operator-tickets/provider-s04-t13-evidence-02.jsonl`
- `maintenance/inputs/provider-s04/operator-tickets/provider-s04-t13-evidence-03.csv`
- `maintenance/inputs/provider-s04/operator-tickets/provider-s04-t13-evidence-04.yaml`

## Evidence table

| Source file | File type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Case ID range | Record count |
| --- | --- | --- | --- | --- | --- |
| provider-s04-t13-evidence-01.md | ASCII text, with CRLF line terminators | 86 | `4288e3e031bd4d1c459a0dadfc491c5d0727c30bf4b16c3cdb078b451d4c372e` | provider-s04-t13-000001 – provider-s04-t13-000082 | 82 |
| provider-s04-t13-evidence-02.jsonl | New Line Delimited JSON text data | 78 | `2a5876cbc78e1ed640b124719a9b991d474d897abaf8bd66f983ba27112792fa` | provider-s04-t13-000001 – provider-s04-t13-000078 | 78 |
| provider-s04-t13-evidence-03.csv | CSV ASCII text | 94 | `d9adac8b33cf536560e6b75f8e0bb17f0a36e3ad2ddac09fd057e25616960ae3` | provider-s04-t13-000001 – provider-s04-t13-000093 | 93 |
| provider-s04-t13-evidence-04.yaml | ASCII text, with CRLF line terminators | 329 | `39113df80c7fdfc7f1210fdc18670b09f64ca22cd9b15a4a6a70ddafbd38859a` | provider-s04-t13-000001 – provider-s04-t13-000082 | 82 |

Record counts are derived from format-specific structure, not raw line counts: the `.md` file has 4 header lines (`# Import Operator Tickets`, blank, `Source set: provider-s04, turn 13.`, blank) plus one bullet per record (82 bullets, so 86 total lines); the `.csv` file has 1 header row plus 93 data rows (94 total lines); the `.yaml` file has 1 header comment line plus 4 lines per record (82 records × 4 = 328, plus the header line = 329 total lines); the `.jsonl` file has exactly one JSON object per line (78 lines = 78 records).

## Cross-file comparison

Each source uses the same four-field shape per record — a case id (`provider-s04-t13-NNNNNN`), a `system` value, a `status` value, and a prose `note`/`Evidence` sentence — expressed in format-native syntax (`.md` bullets, `.jsonl` objects, `.csv` rows, `.yaml` block-sequence mappings).

**Repeating four-case cycle.** Starting at case 1, `system` and `status` repeat in a fixed four-case cycle in every source file:

| Case id mod 4 | System | Status |
| --- | --- | --- |
| 1 | linux-x86_64 | recorded |
| 2 | windows-x86_64 | follow-up |
| 3 | freebsd-x86_64 | supported |
| 0 | macos-arm64 | review |

This cycle was confirmed directly against the text of all four files at cases 1–8 and by a full extraction and inspection of every `(system, status)` pair present in `provider-s04-t13-evidence-03.csv` (the longest file), which contains exactly the four pairs listed above and no others. It holds through the last record of every file (case 82 in `provider-s04-t13-evidence-01.md`, case 78 in `provider-s04-t13-evidence-02.jsonl`, case 93 in `provider-s04-t13-evidence-03.csv`, case 82 in `provider-s04-t13-evidence-04.yaml`).

**Exact agreement on overlapping cases.** `case`, `system`, and `status` triples were extracted independently from all four files (regex parsing for `.md`, `json.loads` per line for `.jsonl`, `csv.DictReader` for `.csv`, block-splitting on `- case:`/`system:`/`status:` for `.yaml`) and compared pairwise over every case id common to both files in the pair (cases 1–78, the range covered by all four files). All six pairwise comparisons — md↔jsonl, md↔csv, md↔yaml, jsonl↔csv, jsonl↔yaml, csv↔yaml — were byte-identical on the `case,system,status` fields with no differences reported.

**Coverage gap.** The four files do not cover the same case range:

- `provider-s04-t13-evidence-02.jsonl` stops at case 78 (the shortest range).
- `provider-s04-t13-evidence-01.md` and `provider-s04-t13-evidence-04.yaml` both extend to case 82.
- `provider-s04-t13-evidence-03.csv` extends furthest, to case 93 (the longest range).

No source file states a reason for this coverage-gap pattern (three distinct maximum case numbers: 78, 82, 93).

## Handoff note

- Every statement above is backed by direct inspection of the four discovered source files; no fact was inferred beyond what each file's content states.
- The repeating four-case cycle shape (one system/status pair per `case mod 4` value) matches the pattern already documented in `maintenance/reports/provider-s04/receipt-field-catalog.md`, `maintenance/reports/provider-s04/import-failure-matrix.md`, `maintenance/reports/provider-s04/version-compatibility-review.md`, `maintenance/reports/provider-s04/platform-result-handoff.md`, `maintenance/reports/provider-s04/checkpoint-boundary-review.md`, and `maintenance/reports/provider-s04/migration-count-audit.md`, but this set's specific status vocabulary (`recorded`/`follow-up`/`supported`/`review`, in that case-order) and its mod-4 alignment (case 1 → recorded) both differ from all six of those earlier reports.
- The `.jsonl` file is consistently the shortest-coverage source across all seven reviewed evidence sets to date (field-catalog: 101/105/119/105; import-failure-matrix: 101/105/119/105; version-compatibility-review: 83/86/98/87; platform-result-handoff: 84/87/98/87; checkpoint-boundary-review: 76/79/90/79; migration-count-audit: 77/80/90/80; this set: 78/82/93/82) — in every case the `.jsonl` maximum case number is the smallest of the four. No source file in `maintenance/inputs/provider-s04/operator-tickets/` states a reason for this recurring pattern, and none references the other evidence sets by name.
- This report is a read-only maintenance artifact. No product code, fixtures, routes, configuration, tests, or other application artifact was modified to produce it.
