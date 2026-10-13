# Provider-s04 Receipt Migration Runbooks Handoff

## Files discovered

Discovered via `find maintenance/inputs/provider-s04/migration-runbooks -type f`:

- `maintenance/inputs/provider-s04/migration-runbooks/provider-s04-t14-evidence-01.md`
- `maintenance/inputs/provider-s04/migration-runbooks/provider-s04-t14-evidence-02.jsonl`
- `maintenance/inputs/provider-s04/migration-runbooks/provider-s04-t14-evidence-03.csv`
- `maintenance/inputs/provider-s04/migration-runbooks/provider-s04-t14-evidence-04.yaml`

## Evidence table

| Source file | File type (`file`) | Line count (`wc -l`) | SHA-256 (`sha256sum`) | Case ID range | Record count |
| --- | --- | --- | --- | --- | --- |
| provider-s04-t14-evidence-01.md | ASCII text, with CRLF line terminators | 85 | `478a541eac6d9e0d161ec45370653e1dcdcdf3af9a5cc57d2ac7677c32805dc4` | provider-s04-t14-000001 – provider-s04-t14-000081 | 81 |
| provider-s04-t14-evidence-02.jsonl | New Line Delimited JSON text data | 78 | `5a26e65a0318f6199748f1d8cadb52cf84440d634d0c43e44aeba188ed0041c1` | provider-s04-t14-000001 – provider-s04-t14-000078 | 78 |
| provider-s04-t14-evidence-03.csv | CSV ASCII text | 92 | `1089ad15d4e1a8c99cf5616edb2439f9204d5372f218d89c8a47c73ceb946cf6` | provider-s04-t14-000001 – provider-s04-t14-000091 | 91 |
| provider-s04-t14-evidence-04.yaml | ASCII text, with CRLF line terminators | 325 | `130e0d1046f63acb7f7cb39a4b5384d67c4c9114221308801ce4d58fd6f30823` | provider-s04-t14-000001 – provider-s04-t14-000081 | 81 |

Record counts are derived from format-specific structure, not raw line counts: the `.md` file has 4 header lines (`# Receipt Migration Runbooks`, blank, `Source set: provider-s04, turn 14.`, blank) plus one bullet per record (81 bullets, so 85 total lines); the `.csv` file has 1 header row plus 91 data rows (92 total lines); the `.yaml` file has 1 header comment line plus 4 lines per record (81 records × 4 = 324, plus the header line = 325 total lines); the `.jsonl` file has exactly one JSON object per line (78 lines = 78 records).

## Cross-file comparison

Each source uses the same four-field shape per record — a case id (`provider-s04-t14-NNNNNN`), a `system` value, a `status` value, and a prose `note`/`Evidence` sentence — expressed in format-native syntax (`.md` bullets, `.jsonl` objects, `.csv` rows, `.yaml` block-sequence mappings).

**Repeating four-case cycle.** Starting at case 1, `system` and `status` repeat in a fixed four-case cycle in every source file:

| Case id mod 4 | System | Status |
| --- | --- | --- |
| 1 | linux-x86_64 | follow-up |
| 2 | windows-x86_64 | supported |
| 3 | freebsd-x86_64 | review |
| 0 | macos-arm64 | recorded |

This cycle was confirmed directly against the text of all four files at cases 1–8 and by a full extraction and inspection of every `(system, status)` pair present in `provider-s04-t14-evidence-03.csv` (the longest file), which contains exactly the four pairs listed above and no others. It holds through the last record of every file (case 81 in `provider-s04-t14-evidence-01.md`, case 78 in `provider-s04-t14-evidence-02.jsonl`, case 91 in `provider-s04-t14-evidence-03.csv`, case 81 in `provider-s04-t14-evidence-04.yaml`).

**Exact agreement on overlapping cases.** `case`, `system`, and `status` triples were extracted independently from all four files (regex parsing for `.md`, `json.loads` per line for `.jsonl`, `csv.DictReader` for `.csv`, block-splitting on `- case:`/`system:`/`status:` for `.yaml`) and compared pairwise over every case id common to all four files (cases 1–78, the range covered by all four files). All six pairwise comparisons — md↔jsonl, md↔csv, md↔yaml, jsonl↔csv, jsonl↔yaml, csv↔yaml — were byte-identical on the `case,system,status` fields with no differences reported.

**Coverage gap.** The four files do not cover the same case range:

- `provider-s04-t14-evidence-02.jsonl` stops at case 78 (the shortest range).
- `provider-s04-t14-evidence-01.md` and `provider-s04-t14-evidence-04.yaml` both extend to case 81.
- `provider-s04-t14-evidence-03.csv` extends furthest, to case 91 (the longest range).

No source file states a reason for this coverage-gap pattern (three distinct maximum case numbers: 78, 81, 91).

## Handoff note

- Every statement above is backed by direct inspection of the four discovered source files; no fact was inferred beyond what each file's content states.
- The repeating four-case cycle shape (one system/status pair per `case mod 4` value) matches the pattern already documented in `maintenance/reports/provider-s04/receipt-field-catalog.md`, `maintenance/reports/provider-s04/import-failure-matrix.md`, `maintenance/reports/provider-s04/version-compatibility-review.md`, `maintenance/reports/provider-s04/platform-result-handoff.md`, `maintenance/reports/provider-s04/checkpoint-boundary-review.md`, `maintenance/reports/provider-s04/migration-count-audit.md`, and `maintenance/reports/provider-s04/operator-ticket-review.md`, but this set's specific status vocabulary (`follow-up`/`supported`/`review`/`recorded`, in that case-order) and its mod-4 alignment (case 1 → follow-up) both differ from all seven of those earlier reports.
- The `.jsonl` file is consistently the shortest-coverage source across all eight reviewed evidence sets to date (field-catalog: 101/105/119/105; import-failure-matrix: 101/105/119/105; version-compatibility-review: 83/86/98/87; platform-result-handoff: 84/87/98/87; checkpoint-boundary-review: 76/79/90/79; migration-count-audit: 77/80/90/80; operator-ticket-review: 78/82/93/82; this set: 78/81/91/81) — in every case the `.jsonl` maximum case number is the smallest of the four. No source file in `maintenance/inputs/provider-s04/migration-runbooks/` states a reason for this recurring pattern, and none references the other evidence sets by name.
- This report is a read-only maintenance artifact. No product code, fixtures, routes, configuration, tests, or other application artifact was modified to produce it.
