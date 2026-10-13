# Provider-s04 Migration Count Reports Audit

## Files discovered

Discovered via `find maintenance/inputs/provider-s04/count-reports -type f`:

- `maintenance/inputs/provider-s04/count-reports/provider-s04-t11-evidence-01.md`
- `maintenance/inputs/provider-s04/count-reports/provider-s04-t11-evidence-02.jsonl`
- `maintenance/inputs/provider-s04/count-reports/provider-s04-t11-evidence-03.csv`
- `maintenance/inputs/provider-s04/count-reports/provider-s04-t11-evidence-04.yaml`

## Evidence table

| Source file | File type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Case ID range | Record count |
| --- | --- | --- | --- | --- | --- |
| provider-s04-t11-evidence-01.md | ASCII text, with CRLF line terminators | 84 | `e334adbe606b56fcb4f5364ad0293a97467c8c92f29c14a03b9f86ba5ca07921` | provider-s04-t11-000001 – provider-s04-t11-000080 | 80 |
| provider-s04-t11-evidence-02.jsonl | New Line Delimited JSON text data | 77 | `39f71e9b97c061f70095222ff3f32c0848be21088e1cbd1e3c509d75812c80a7` | provider-s04-t11-000001 – provider-s04-t11-000077 | 77 |
| provider-s04-t11-evidence-03.csv | CSV ASCII text | 91 | `730c57b8bbd1628128fb6d9033da4fdcfeac0c0badc078fc2df0dc53c003ee5f` | provider-s04-t11-000001 – provider-s04-t11-000090 | 90 |
| provider-s04-t11-evidence-04.yaml | ASCII text, with CRLF line terminators | 321 | `e0ff0ef655baf4b2061981e343b12aa89bdb4a2716f3a17e9780aafc339b9b0a` | provider-s04-t11-000001 – provider-s04-t11-000080 | 80 |

Record counts are derived from format-specific structure, not raw line counts: the `.md` file has 4 header lines (`# Migration Count Reports`, blank, `Source set: provider-s04, turn 11.`, blank) plus one bullet per record (80 bullets, so 84 total lines); the `.csv` file has 1 header row plus 90 data rows (91 total lines); the `.yaml` file has 1 header comment line plus 4 lines per record (80 records × 4 = 320, plus the header line = 321 total lines); the `.jsonl` file has exactly one JSON object per line (77 lines = 77 records).

## Cross-file comparison

Each source uses the same four-field shape per record — a case id (`provider-s04-t11-NNNNNN`), a `system` value, a `status` value, and a prose `note`/`Evidence` sentence — expressed in format-native syntax (`.md` bullets, `.jsonl` objects, `.csv` rows, `.yaml` block-sequence mappings).

**Repeating four-case cycle.** Starting at case 1, `system` and `status` repeat in a fixed four-case cycle in every source file:

| Case id mod 4 | System | Status |
| --- | --- | --- |
| 1 | linux-x86_64 | supported |
| 2 | windows-x86_64 | review |
| 3 | freebsd-x86_64 | recorded |
| 0 | macos-arm64 | follow-up |

This cycle was confirmed directly against the text of all four files at cases 1–8 and by a full extraction and inspection of every `(system, status)` pair present in `provider-s04-t11-evidence-03.csv` (the longest file), which contains exactly the four pairs listed above and no others. It holds through the last record of every file (case 80 in `provider-s04-t11-evidence-01.md`, case 77 in `provider-s04-t11-evidence-02.jsonl`, case 90 in `provider-s04-t11-evidence-03.csv`, case 80 in `provider-s04-t11-evidence-04.yaml`).

**Exact agreement on overlapping cases.** `case`, `system`, and `status` triples were extracted independently from all four files (regex parsing for `.md`, `json.loads` per line for `.jsonl`, `csv.DictReader` for `.csv`, block-splitting on `- case:`/`system:`/`status:` for `.yaml`) and compared pairwise with `diff` over every range two files both cover. All six pairwise comparisons — md↔jsonl (cases 1–77), md↔csv (cases 1–80), md↔yaml (cases 1–80), jsonl↔csv (cases 1–77), jsonl↔yaml (cases 1–77), csv↔yaml (cases 1–80) — were byte-identical on the `case,system,status` fields with no differences reported.

**Coverage gap.** The four files do not cover the same case range:

- `provider-s04-t11-evidence-02.jsonl` stops at case 77 (the shortest range).
- `provider-s04-t11-evidence-01.md` and `provider-s04-t11-evidence-04.yaml` both extend to case 80.
- `provider-s04-t11-evidence-03.csv` extends furthest, to case 90 (the longest range).

No source file states a reason for this coverage-gap pattern (three distinct maximum case numbers: 77, 80, 90).

## Handoff note

- Every statement above is backed by direct inspection of the four discovered source files; no fact was inferred beyond what each file's content states.
- The repeating four-case cycle shape (one system/status pair per `case mod 4` value) matches the pattern already documented in `maintenance/reports/provider-s04/receipt-field-catalog.md`, `maintenance/reports/provider-s04/import-failure-matrix.md`, `maintenance/reports/provider-s04/version-compatibility-review.md`, `maintenance/reports/provider-s04/platform-result-handoff.md`, and `maintenance/reports/provider-s04/checkpoint-boundary-review.md`, but this set's specific status vocabulary (`supported`/`review`/`recorded`/`follow-up`, in that case-order) and its mod-4 alignment (case 1 → supported) both differ from all five of those earlier reports.
- The `.jsonl` file is consistently the shortest-coverage source across all six reviewed evidence sets to date (field-catalog: 101/105/119/105; import-failure-matrix: 101/105/119/105; version-compatibility-review: 83/86/98/87; platform-result-handoff: 84/87/98/87; checkpoint-boundary-review: 76/79/90/79; this set: 77/80/90/80) — in every case the `.jsonl` maximum case number is the smallest of the four. No source file in `maintenance/inputs/provider-s04/count-reports/` states a reason for this recurring pattern, and none references the other evidence sets by name.
- This report is a read-only maintenance artifact. No product code, fixtures, routes, configuration, tests, or other application artifact was modified to produce it.
