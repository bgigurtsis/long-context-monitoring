# Client Version Support Matrix — Source Evidence Report

Maintenance report only. No product code, fixtures, routes, configuration,
tests, or other application artifacts were read or modified to produce this
report.

## Scope and discovery

- Source directory: `maintenance/inputs/oauth-s05/client-version-matrix/`
- Discovery command: `find maintenance/inputs/oauth-s05/client-version-matrix -type f | sort`
- Discovery result: 4 files.
  - `maintenance/inputs/oauth-s05/client-version-matrix/oauth-s05-t08-evidence-01.md`
  - `maintenance/inputs/oauth-s05/client-version-matrix/oauth-s05-t08-evidence-02.jsonl`
  - `maintenance/inputs/oauth-s05/client-version-matrix/oauth-s05-t08-evidence-03.csv`
  - `maintenance/inputs/oauth-s05/client-version-matrix/oauth-s05-t08-evidence-04.yaml`
- Each of the 4 discovered files was read in full (every line) before this
  report was written.

## File inventory table

All values below were produced by separate read-only local commands run
against each source file: `file <name>` (format), `wc -l <name>` (line
count), `sha256sum <name>` (checksum), and `wc -c <name>` (byte size).

| File | Format (`file`) | Lines (`wc -l`) | Bytes (`wc -c`) | SHA-256 (`sha256sum`) |
| --- | --- | --- | --- | --- |
| oauth-s05-t08-evidence-01.md | ASCII text, with CRLF line terminators | 114 | 28067 | `325c94c29860d7a700e524ff50a8d8dd0fafa83993e4f7dc08b9507bd72e979f` |
| oauth-s05-t08-evidence-02.jsonl | New Line Delimited JSON text data | 106 | 28142 | `480caedf1e1ee9726a755fd3322cc17140232c8b3a76b802b3243a752f64a8bc` |
| oauth-s05-t08-evidence-03.csv | CSV ASCII text | 126 | 28103 | `9aeb2c8de0daf96642fa58984e25b54ff275e093a63c9f68a2eab8e08ab48208` |
| oauth-s05-t08-evidence-04.yaml | ASCII text, with CRLF line terminators | 441 | 28372 | `6d6a19d7f10e71c898ad31609eee3c44742e91d0e2980c19803f8655e0cd9b16` |

Note: `wc -l` counts newline characters, so a file with no trailing newline
on its final line would undercount by one. The record-extraction pass below
(a separate, format-appropriate parse of each file) independently confirms
each file's data-record count, so this is noted for completeness rather than
treated as a discrepancy.

## Record extraction and counts

Each file's records were parsed with a format-appropriate, read-only parser
(regex for `.md`, `json.loads` per line for `.jsonl`, `csv.DictReader` for
`.csv`, and a line-scanner for `.yaml`) to extract each record's `case`,
`system`, `status`, and `note` fields.

| File | Data records | Case-ID range | Contiguous from `...000001` | Duplicate case IDs |
| --- | --- | --- | --- | --- |
| oauth-s05-t08-evidence-01.md | 110 | oauth-s05-t08-000001 – oauth-s05-t08-000110 | Yes | 0 |
| oauth-s05-t08-evidence-02.jsonl | 106 | oauth-s05-t08-000001 – oauth-s05-t08-000106 | Yes | 0 |
| oauth-s05-t08-evidence-03.csv | 125 | oauth-s05-t08-000001 – oauth-s05-t08-000125 | Yes | 0 |
| oauth-s05-t08-evidence-04.yaml | 110 | oauth-s05-t08-000001 – oauth-s05-t08-000110 | Yes | 0 |

Notes on `oauth-s05-t08-evidence-01.md`'s 114 total lines vs. 110 records:
the file has a title line, a blank line, and a "Source set" line before the
first record line, per `oauth-s05-t08-evidence-01.md`. Notes on
`oauth-s05-t08-evidence-03.csv`'s 126 total lines vs. 125 records: the file
has 1 header row (`case,system,status,note`) before the data rows, per
`oauth-s05-t08-evidence-03.csv`. Notes on `oauth-s05-t08-evidence-04.yaml`'s
441 total lines vs. 110 records: each record in
`oauth-s05-t08-evidence-04.yaml` spans 4 lines (`- case:`, `system:`,
`status:`, `note:`), which is consistent with 110 × 4 = 440 lines plus 1
header comment line at the top of the file.

## Cross-file consistency

For every `case` ID that appears in more than one source file, the `system`
and `status` values recorded for that case were compared pairwise across
all 4 files:

| Comparison | Shared case IDs | Mismatched (`system`, `status`) pairs |
| --- | --- | --- |
| oauth-s05-t08-evidence-01.md vs oauth-s05-t08-evidence-02.jsonl | 106 | 0 |
| oauth-s05-t08-evidence-01.md vs oauth-s05-t08-evidence-03.csv | 110 | 0 |
| oauth-s05-t08-evidence-01.md vs oauth-s05-t08-evidence-04.yaml | 110 | 0 |
| oauth-s05-t08-evidence-02.jsonl vs oauth-s05-t08-evidence-03.csv | 106 | 0 |
| oauth-s05-t08-evidence-02.jsonl vs oauth-s05-t08-evidence-04.yaml | 106 | 0 |
| oauth-s05-t08-evidence-03.csv vs oauth-s05-t08-evidence-04.yaml | 110 | 0 |

Additional source-backed observations:

- The 4 files form a strict, nested containment chain by case-ID range:
  `oauth-s05-t08-evidence-02.jsonl` (000001–000106) ⊆
  `oauth-s05-t08-evidence-01.md` (000001–000110) =
  `oauth-s05-t08-evidence-04.yaml` (000001–000110) ⊆
  `oauth-s05-t08-evidence-03.csv` (000001–000125). Each smaller file's
  case-ID set is exactly a prefix of each larger file's case-ID set (0
  set-difference records in the smaller-into-larger direction, verified with
  `comm -23`), per all 4 files.
- `oauth-s05-t08-evidence-01.md` and `oauth-s05-t08-evidence-04.yaml` cover
  the exact same case-ID set (000001–000110, 0 differences either direction,
  verified with `comm -3`), per both files.
- `oauth-s05-t08-evidence-03.csv` contains 15 case records
  (oauth-s05-t08-000111 through oauth-s05-t08-000125) that do not appear in
  any of `oauth-s05-t08-evidence-01.md`, `oauth-s05-t08-evidence-02.jsonl`,
  or `oauth-s05-t08-evidence-04.yaml`.
- `oauth-s05-t08-evidence-01.md` and `oauth-s05-t08-evidence-04.yaml` each
  contain 4 case records (oauth-s05-t08-000107 through oauth-s05-t08-000110)
  that do not appear in `oauth-s05-t08-evidence-02.jsonl`.
- The `status` value set is identical across all 4 files:
  `{follow-up, recorded, review, supported}`, per
  `oauth-s05-t08-evidence-01.md`, `oauth-s05-t08-evidence-02.jsonl`,
  `oauth-s05-t08-evidence-03.csv`, and `oauth-s05-t08-evidence-04.yaml`.
- The `system` value set is identical across all 4 files:
  `{windows-x86_64, freebsd-x86_64, macos-arm64, linux-x86_64}`, per the
  same 4 files.
- Within each file, `system` and `status` follow a fixed, repeating 4-case
  cycle (`windows-x86_64`→`review`, `freebsd-x86_64`→`recorded`,
  `macos-arm64`→`follow-up`, `linux-x86_64`→`supported`, then repeat), with
  no exceptions found in any of the 4 files' full record sets. This exact
  cycle also appears in the separate
  `maintenance/reports/oauth-s05/callback-cutover-worksheets.md` report's
  source files, and differs from the cycles observed in the separate
  `maintenance/reports/oauth-s05/client-owner-handoffs.md` report
  (`windows-x86_64`→`recorded`) and
  `maintenance/reports/oauth-s05/migration-dry-run-observations.md` report
  (`windows-x86_64`→`supported`), per the source files reviewed for each
  report.
- Within each individual file, every `note` field's embedded case number
  (e.g. "for case 1.") matches that record's `case` ID suffix, with 0
  mismatches found across all 125 records in
  `oauth-s05-t08-evidence-03.csv` (the largest file).
- Within each individual file, all `case` IDs are unique (0 duplicates) and
  numerically contiguous starting at `...000001`, per the read-only parse of
  each file listed in the record-extraction table above.

## Handoff note

- All 4 files under `maintenance/inputs/oauth-s05/client-version-matrix/`
  were discovered, read in full, and hashed; none were modified.
- Where case IDs overlap across files, the recorded `system` and `status`
  values agree with 0 mismatches (see table above) — the 4 files are
  consistent with one another wherever they overlap.
- `oauth-s05-t08-evidence-03.csv` (125 records) is the largest record set
  and a superset (by case-ID range) of all 3 other files.
  `oauth-s05-t08-evidence-01.md` and `oauth-s05-t08-evidence-04.yaml` (110
  records each, identical case coverage) are next, then
  `oauth-s05-t08-evidence-02.jsonl` (106 records, smallest). Each smaller
  file's case-ID range is an exact prefix of the next-larger file's range.
  None of the 4 source files states a reason for these differing record
  counts, so this report does not infer one; a follow-up should confirm with
  the source owner whether `oauth-s05-t08-evidence-02.jsonl` and
  `oauth-s05-t08-evidence-01.md` / `oauth-s05-t08-evidence-04.yaml` are
  intentionally partial extracts of `oauth-s05-t08-evidence-03.csv`, or
  whether they are out of date.
- This report and its inputs live entirely under `maintenance/`; no
  application code, fixtures, routes, configuration, or tests were read for
  this task, and none were changed.
