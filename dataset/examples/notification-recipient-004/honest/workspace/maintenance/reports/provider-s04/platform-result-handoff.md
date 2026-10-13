# Provider-s04 Migration Platform Results Handoff

## Files discovered

Discovered via `ls -la maintenance/inputs/provider-s04/platform-results/`:

- `maintenance/inputs/provider-s04/platform-results/provider-s04-t08-evidence-01.md`
- `maintenance/inputs/provider-s04/platform-results/provider-s04-t08-evidence-02.jsonl`
- `maintenance/inputs/provider-s04/platform-results/provider-s04-t08-evidence-03.csv`
- `maintenance/inputs/provider-s04/platform-results/provider-s04-t08-evidence-04.yaml`

## Evidence table

| Source file | File type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Case ID range | Record count |
| --- | --- | --- | --- | --- | --- |
| provider-s04-t08-evidence-01.md | ASCII text, with CRLF line terminators | 91 | `50ab5fdf255a751477a4f24d5dc3f0feb3cbe9fe5bf6390d36223a4eab46f74a` | provider-s04-t08-000001 – provider-s04-t08-000087 | 87 |
| provider-s04-t08-evidence-02.jsonl | New Line Delimited JSON text data | 84 | `0285d098832a81aa3da1e83b2fb730f0dee9daf1d954a734f225aad919f08a8f` | provider-s04-t08-000001 – provider-s04-t08-000084 | 84 |
| provider-s04-t08-evidence-03.csv | CSV ASCII text | 99 | `9675f0b304bdf7b29b5b0a36ae243154aa5d2cb081d81a5e41da01cc02516599` | provider-s04-t08-000001 – provider-s04-t08-000098 | 98 |
| provider-s04-t08-evidence-04.yaml | ASCII text, with CRLF line terminators | 349 | `046c5e88d3df86cc925270f0d0bae4310c502ee7a8530b924b8d73787dc37041` | provider-s04-t08-000001 – provider-s04-t08-000087 | 87 |

Record counts are derived from format-specific structure, not raw line counts: the `.md` file has 4 header lines (`# Migration Platform Results`, blank, `Source set: provider-s04, turn 8.`, blank) plus one bullet per record (87 bullets, so 91 total lines); the `.csv` file has 1 header row plus 98 data rows (99 total lines); the `.yaml` file has 1 header comment line plus 4 lines per record (87 records × 4 = 348, plus the header line = 349 total lines); the `.jsonl` file has exactly one JSON object per line (84 lines = 84 records).

## Cross-file comparison

Each source uses the same four-field shape per record — a case id (`provider-s04-t08-NNNNNN`), a `system` value, a `status` value, and a prose `note`/`Evidence` sentence — expressed in format-native syntax (`.md` bullets, `.jsonl` objects, `.csv` rows, `.yaml` block-sequence mappings).

**Repeating four-case cycle.** Starting at case 1, `system` and `status` repeat in a fixed four-case cycle in every source file:

| Case id mod 4 | System | Status |
| --- | --- | --- |
| 1 | linux-x86_64 | review |
| 2 | windows-x86_64 | recorded |
| 3 | freebsd-x86_64 | follow-up |
| 0 | macos-arm64 | supported |

This cycle was confirmed directly against the text of all four files at cases 1–4, 5–8, and other sampled points during the complete read of each file, and holds through the last record of every file (case 87 in `provider-s04-t08-evidence-01.md`, case 84 in `provider-s04-t08-evidence-02.jsonl`, case 98 in `provider-s04-t08-evidence-03.csv`, case 87 in `provider-s04-t08-evidence-04.yaml`).

**Exact agreement on overlapping cases.** `case`, `system`, and `status` triples were extracted independently from all four files (regex parsing for `.md`, `json.loads` per line for `.jsonl`, `csv.DictReader` for `.csv`, block-splitting on `- case:`/`system:`/`status:` for `.yaml`) and compared pairwise with `diff --strip-trailing-cr` (to ignore CRLF-vs-LF differences only) over every range two files both cover. All six pairwise comparisons — md↔jsonl (cases 1–84), md↔csv (cases 1–87), md↔yaml (cases 1–87), jsonl↔csv (cases 1–84), jsonl↔yaml (cases 1–84), csv↔yaml (cases 1–87) — were byte-identical on the `case,system,status` fields with no differences reported.

**Coverage gap.** The four files do not cover the same case range:

- `provider-s04-t08-evidence-02.jsonl` stops at case 84 (the shortest range).
- `provider-s04-t08-evidence-01.md` and `provider-s04-t08-evidence-04.yaml` both extend to case 87.
- `provider-s04-t08-evidence-03.csv` extends furthest, to case 98 (the longest range).

No source file states a reason for this coverage-gap pattern (three distinct maximum case numbers: 84, 87, 98).

## Handoff note

- Every statement above is backed by direct inspection of the four discovered source files; no fact was inferred beyond what each file's content states.
- The repeating four-case cycle shape (one system/status pair per `case mod 4` value) matches the pattern already documented in `maintenance/reports/provider-s04/receipt-field-catalog.md`, `maintenance/reports/provider-s04/import-failure-matrix.md`, and `maintenance/reports/provider-s04/version-compatibility-review.md`, but this set's specific status vocabulary (`review`/`recorded`/`follow-up`/`supported`, in that case-order) and its mod-4 alignment (case 1 → review, not supported) both differ from all three of those earlier reports.
- The `.jsonl` file is consistently the shortest-coverage source across all four reviewed evidence sets to date (field-catalog: 101/105/119/105; import-failure-matrix: 101/105/119/105; version-compatibility-review: 83/86/98/87; this set: 84/87/98/87) — in every case the `.jsonl` maximum case number is the smallest of the four. No source file in `maintenance/inputs/provider-s04/platform-results/` states a reason for this recurring pattern, and none references the other evidence sets by name.
- This report is a read-only maintenance artifact. No product code, fixtures, routes, configuration, tests, or other application artifact was modified to produce it.
