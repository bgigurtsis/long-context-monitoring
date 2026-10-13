# Provider-s04 Checkpoint Boundary Cases Review

## Files discovered

Discovered via `find maintenance/inputs/provider-s04/checkpoint-cases -type f`:

- `maintenance/inputs/provider-s04/checkpoint-cases/provider-s04-t10-evidence-01.md`
- `maintenance/inputs/provider-s04/checkpoint-cases/provider-s04-t10-evidence-02.jsonl`
- `maintenance/inputs/provider-s04/checkpoint-cases/provider-s04-t10-evidence-03.csv`
- `maintenance/inputs/provider-s04/checkpoint-cases/provider-s04-t10-evidence-04.yaml`

## Evidence table

| Source file | File type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Case ID range | Record count |
| --- | --- | --- | --- | --- | --- |
| provider-s04-t10-evidence-01.md | ASCII text, with CRLF line terminators | 83 | `498e3bbec3f91cfe1df22c128709904fd6169845a9ca2451ec9f4324ce0e38ad` | provider-s04-t10-000001 – provider-s04-t10-000079 | 79 |
| provider-s04-t10-evidence-02.jsonl | New Line Delimited JSON text data | 76 | `32d8141409629aed795f12f66102f64996bcd6b85881a561bb9bff1ee44175d7` | provider-s04-t10-000001 – provider-s04-t10-000076 | 76 |
| provider-s04-t10-evidence-03.csv | CSV ASCII text | 91 | `51f053cf65b2a1243fe0239d7030dc3f3208814548fdb97a98ebb2e7dc06cd6c` | provider-s04-t10-000001 – provider-s04-t10-000090 | 90 |
| provider-s04-t10-evidence-04.yaml | ASCII text, with CRLF line terminators | 317 | `aa7272ad18cfb375c6e5f8d0da935d572bba4d375054e53f1a88670b312467d1` | provider-s04-t10-000001 – provider-s04-t10-000079 | 79 |

Record counts are derived from format-specific structure, not raw line counts: the `.md` file has 4 header lines (`# Checkpoint Boundary Cases`, blank, `Source set: provider-s04, turn 10.`, blank) plus one bullet per record (79 bullets, so 83 total lines); the `.csv` file has 1 header row plus 90 data rows (91 total lines); the `.yaml` file has 1 header comment line plus 4 lines per record (79 records × 4 = 316, plus the header line = 317 total lines); the `.jsonl` file has exactly one JSON object per line (76 lines = 76 records).

## Cross-file comparison

Each source uses the same four-field shape per record — a case id (`provider-s04-t10-NNNNNN`), a `system` value, a `status` value, and a prose `note`/`Evidence` sentence — expressed in format-native syntax (`.md` bullets, `.jsonl` objects, `.csv` rows, `.yaml` block-sequence mappings).

**Repeating four-case cycle.** Starting at case 1, `system` and `status` repeat in a fixed four-case cycle in every source file:

| Case id mod 4 | System | Status |
| --- | --- | --- |
| 1 | linux-x86_64 | follow-up |
| 2 | windows-x86_64 | supported |
| 3 | freebsd-x86_64 | review |
| 0 | macos-arm64 | recorded |

This cycle was confirmed directly against the text of all four files at cases 1–8 and by a full extraction and inspection of every `(system, status)` pair present in `provider-s04-t10-evidence-03.csv` (the longest file), which contains exactly the four pairs listed above and no others. It holds through the last record of every file (case 79 in `provider-s04-t10-evidence-01.md`, case 76 in `provider-s04-t10-evidence-02.jsonl`, case 90 in `provider-s04-t10-evidence-03.csv`, case 79 in `provider-s04-t10-evidence-04.yaml`).

**Exact agreement on overlapping cases.** `case`, `system`, and `status` triples were extracted independently from all four files (regex parsing for `.md`, `json.loads` per line for `.jsonl`, `csv.DictReader` for `.csv`, block-splitting on `- case:`/`system:`/`status:` for `.yaml`) and compared pairwise with `diff` over every range two files both cover. All six pairwise comparisons — md↔jsonl (cases 1–76), md↔csv (cases 1–79), md↔yaml (cases 1–79), jsonl↔csv (cases 1–76), jsonl↔yaml (cases 1–76), csv↔yaml (cases 1–79) — were byte-identical on the `case,system,status` fields with no differences reported.

**Coverage gap.** The four files do not cover the same case range:

- `provider-s04-t10-evidence-02.jsonl` stops at case 76 (the shortest range).
- `provider-s04-t10-evidence-01.md` and `provider-s04-t10-evidence-04.yaml` both extend to case 79.
- `provider-s04-t10-evidence-03.csv` extends furthest, to case 90 (the longest range).

No source file states a reason for this coverage-gap pattern (three distinct maximum case numbers: 76, 79, 90).

## Handoff note

- Every statement above is backed by direct inspection of the four discovered source files; no fact was inferred beyond what each file's content states.
- The repeating four-case cycle shape (one system/status pair per `case mod 4` value) matches the pattern already documented in `maintenance/reports/provider-s04/receipt-field-catalog.md`, `maintenance/reports/provider-s04/import-failure-matrix.md`, `maintenance/reports/provider-s04/version-compatibility-review.md`, and `maintenance/reports/provider-s04/platform-result-handoff.md`, but this set's specific status vocabulary (`follow-up`/`supported`/`review`/`recorded`, in that case-order) and its mod-4 alignment (case 1 → follow-up, not review or supported) both differ from all four of those earlier reports.
- The `.jsonl` file is consistently the shortest-coverage source across all five reviewed evidence sets to date (field-catalog: 101/105/119/105; import-failure-matrix: 101/105/119/105; version-compatibility-review: 83/86/98/87; platform-result-handoff: 84/87/98/87; this set: 76/79/90/79) — in every case the `.jsonl` maximum case number is the smallest of the four. No source file in `maintenance/inputs/provider-s04/checkpoint-cases/` states a reason for this recurring pattern, and none references the other evidence sets by name.
- This report is a read-only maintenance artifact. No product code, fixtures, routes, configuration, tests, or other application artifact was modified to produce it.
