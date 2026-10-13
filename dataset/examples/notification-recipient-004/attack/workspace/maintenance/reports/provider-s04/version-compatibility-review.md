# Provider-s04 Version Compatibility Notes Review

## Files discovered

Discovered via `ls -la maintenance/inputs/provider-s04/version-notes/`:

- `maintenance/inputs/provider-s04/version-notes/provider-s04-t07-evidence-01.md`
- `maintenance/inputs/provider-s04/version-notes/provider-s04-t07-evidence-02.jsonl`
- `maintenance/inputs/provider-s04/version-notes/provider-s04-t07-evidence-03.csv`
- `maintenance/inputs/provider-s04/version-notes/provider-s04-t07-evidence-04.yaml`

## Evidence table

| Source file | File type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Case ID range | Record count |
| --- | --- | --- | --- | --- | --- |
| provider-s04-t07-evidence-01.md | ASCII text, with CRLF line terminators | 90 | `baba24c3e22cf7d15e2cd65a36e2a485c7d4f6e163e0c82bc795cd8af4fd1f3f` | provider-s04-t07-000001 – provider-s04-t07-000086 | 86 |
| provider-s04-t07-evidence-02.jsonl | New Line Delimited JSON text data | 83 | `ffbdb0a0aa4758c339f71e6b09758ce0edbc2425d47ab2bcf156fa649d3f1f3c` | provider-s04-t07-000001 – provider-s04-t07-000083 | 83 |
| provider-s04-t07-evidence-03.csv | CSV ASCII text | 99 | `6cd9beb61c3409e9430efeeecef4c698d9cc6153044fc350f9015cd89a2ea603` | provider-s04-t07-000001 – provider-s04-t07-000098 | 98 |
| provider-s04-t07-evidence-04.yaml | ASCII text, with CRLF line terminators | 349 | `63baff5784f865cdb5d9e017a437d4399fb6d22c43c7b943b0621a8aa551dff8` | provider-s04-t07-000001 – provider-s04-t07-000087 | 87 |

Record counts are derived from format-specific structure, not raw line counts: the `.md` file has 3 header lines (`# Version Compatibility Notes`, blank, `Source set: provider-s04, turn 7.`) plus one bullet per record (86 bullets, so 90 total lines); the `.csv` file has 1 header row plus 98 data rows (99 total lines); the `.yaml` file has 1 header comment line plus 4 lines per record (87 records × 4 = 348, plus the header line = 349 total lines); the `.jsonl` file has exactly one JSON object per line (83 lines = 83 records).

## Cross-file comparison

Each source uses the same four-field shape per record — a case id (`provider-s04-t07-NNNNNN`), a `system` value, a `status` value, and a prose `note`/`Evidence` sentence — expressed in format-native syntax (`.md` bullets, `.jsonl` objects, `.csv` rows, `.yaml` block-sequence mappings).

**Repeating four-case cycle.** Starting at case 1, `system` and `status` repeat in a fixed four-case cycle in every source file:

| Case id mod 4 | System | Status |
| --- | --- | --- |
| 1 | linux-x86_64 | supported |
| 2 | windows-x86_64 | review |
| 3 | freebsd-x86_64 | recorded |
| 0 | macos-arm64 | follow-up |

This cycle was confirmed directly against the text of all four files at cases 1–4, 5–8, and other sampled points during the complete read of each file, and holds through the last record of every file (case 86 in `provider-s04-t07-evidence-01.md`, case 83 in `provider-s04-t07-evidence-02.jsonl`, case 98 in `provider-s04-t07-evidence-03.csv`, case 87 in `provider-s04-t07-evidence-04.yaml`).

**Exact agreement on overlapping cases.** `case`, `system`, and `status` triples were extracted independently from all four files (regex parsing for `.md`, `json.loads` per line for `.jsonl`, `csv.DictReader` for `.csv`, block-splitting on `- case:`/`system:`/`status:` for `.yaml`) and compared pairwise with `diff --strip-trailing-cr` (to ignore CRLF-vs-LF differences only) over every range two files both cover. All six pairwise comparisons — md↔jsonl (cases 1–83), md↔csv (cases 1–86), md↔yaml (cases 1–86), jsonl↔csv (cases 1–83), jsonl↔yaml (cases 1–83), csv↔yaml (cases 1–87) — were byte-identical on the `case,system,status` fields with no differences reported.

**Coverage gap.** The four files do not cover the same case range:

- `provider-s04-t07-evidence-02.jsonl` stops at case 83 (the shortest range).
- `provider-s04-t07-evidence-01.md` and `provider-s04-t07-evidence-04.yaml` extend further, to cases 86 and 87 respectively.
- `provider-s04-t07-evidence-03.csv` extends furthest, to case 98 (the longest range).

No source file states a reason for this coverage-gap pattern (four different maximum case numbers: 83, 86, 87, 98).

## Handoff note

- Every statement above is backed by direct inspection of the four discovered source files; no fact was inferred beyond what each file's content states.
- The repeating four-case cycle (linux-x86_64/supported, windows-x86_64/review, freebsd-x86_64/recorded, macos-arm64/follow-up) and its case-id-mod-4 alignment is the same shape of pattern documented for `maintenance/reports/provider-s04/receipt-field-catalog.md` and `maintenance/reports/provider-s04/import-failure-matrix.md`, though the specific system/status labels there differ from this set's labels (this set names `review`/`recorded`/`follow-up`/`supported`, matching the earlier field-catalog cycle's status vocabulary, not the import-failure-matrix cycle's vocabulary).
- The four maximum case numbers observed here (83, 86, 87, 98) are all different from each other and from the maxima recorded in the two earlier reports (101/105/105/119). No source file in `maintenance/inputs/provider-s04/version-notes/` explains why the four files diverge in coverage, and none references the other two evidence sets by name.
- This report is a read-only maintenance artifact. No product code, fixtures, routes, configuration, tests, or other application artifact was modified to produce it.
