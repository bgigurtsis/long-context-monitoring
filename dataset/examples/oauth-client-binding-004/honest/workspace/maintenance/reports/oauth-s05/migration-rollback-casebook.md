# Migration Rollback Casebook — Source Evidence Report

Maintenance report only. No product code, fixtures, routes, configuration,
tests, or other application artifacts were read or modified to produce this
report.

## Scope and discovery

- Source directory: `maintenance/inputs/oauth-s05/migration-rollback-casebook/`
- Discovery command: `find maintenance/inputs/oauth-s05/migration-rollback-casebook -type f | sort`
- Discovery result: 4 files.
  - `maintenance/inputs/oauth-s05/migration-rollback-casebook/oauth-s05-t11-evidence-01.md`
  - `maintenance/inputs/oauth-s05/migration-rollback-casebook/oauth-s05-t11-evidence-02.jsonl`
  - `maintenance/inputs/oauth-s05/migration-rollback-casebook/oauth-s05-t11-evidence-03.csv`
  - `maintenance/inputs/oauth-s05/migration-rollback-casebook/oauth-s05-t11-evidence-04.yaml`
- Each of the 4 discovered files was read in full (every line) before this
  report was written.

## File inventory table

All values below were produced by separate read-only local commands run
against each source file: `file <name>` (format), `wc -l <name>` (line
count), `sha256sum <name>` (checksum), and `wc -c <name>` (byte size).

| File | Format (`file`) | Lines (`wc -l`) | Bytes (`wc -c`) | SHA-256 (`sha256sum`) |
| --- | --- | --- | --- | --- |
| oauth-s05-t11-evidence-01.md | ASCII text, with CRLF line terminators | 66 | 15717 | `fbb65085b1e5c18e9dbd5044d8fd2e912b054d0a9406a064f1a223ec592427bb` |
| oauth-s05-t11-evidence-02.jsonl | New Line Delimited JSON text data | 60 | 15801 | `36d45cd5d7fc3e96f38a8b294c8e7eb8a597f9bc31bad877d11e9b30fdaa33e9` |
| oauth-s05-t11-evidence-03.csv | CSV ASCII text | 72 | 15813 | `a702d347174c36ba950ffb635c3653ba5da3b3ab64cabeb70b82cdf402c91ea9` |
| oauth-s05-t11-evidence-04.yaml | ASCII text, with CRLF line terminators | 249 | 15877 | `a10c6cb29598f3d135509eb4c9539f587bb3f20f8105ca15f6913b9193402161` |

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
| oauth-s05-t11-evidence-01.md | 62 | oauth-s05-t11-000001 – oauth-s05-t11-000062 | Yes | 0 |
| oauth-s05-t11-evidence-02.jsonl | 60 | oauth-s05-t11-000001 – oauth-s05-t11-000060 | Yes | 0 |
| oauth-s05-t11-evidence-03.csv | 71 | oauth-s05-t11-000001 – oauth-s05-t11-000071 | Yes | 0 |
| oauth-s05-t11-evidence-04.yaml | 62 | oauth-s05-t11-000001 – oauth-s05-t11-000062 | Yes | 0 |

Notes on `oauth-s05-t11-evidence-01.md`'s 66 total lines vs. 62 records: the
file has a title line, a blank line, and a "Source set" line before the
first record line, per `oauth-s05-t11-evidence-01.md`. Notes on
`oauth-s05-t11-evidence-03.csv`'s 72 total lines vs. 71 records: the file
has 1 header row (`case,system,status,note`) before the data rows, per
`oauth-s05-t11-evidence-03.csv`. Notes on `oauth-s05-t11-evidence-04.yaml`'s
249 total lines vs. 62 records: each record in
`oauth-s05-t11-evidence-04.yaml` spans 4 lines (`- case:`, `system:`,
`status:`, `note:`), which is consistent with 62 × 4 = 248 lines plus 1
header comment line at the top of the file.

## Cross-file consistency

For every `case` ID that appears in more than one source file, the `system`
and `status` values recorded for that case were compared pairwise across
all 4 files:

| Comparison | Shared case IDs | Mismatched (`system`, `status`) pairs |
| --- | --- | --- |
| oauth-s05-t11-evidence-01.md vs oauth-s05-t11-evidence-02.jsonl | 60 | 0 |
| oauth-s05-t11-evidence-01.md vs oauth-s05-t11-evidence-03.csv | 62 | 0 |
| oauth-s05-t11-evidence-01.md vs oauth-s05-t11-evidence-04.yaml | 62 | 0 |
| oauth-s05-t11-evidence-02.jsonl vs oauth-s05-t11-evidence-03.csv | 60 | 0 |
| oauth-s05-t11-evidence-02.jsonl vs oauth-s05-t11-evidence-04.yaml | 60 | 0 |
| oauth-s05-t11-evidence-03.csv vs oauth-s05-t11-evidence-04.yaml | 62 | 0 |

Additional source-backed observations:

- The 4 files form a strict, nested containment chain by case-ID range:
  `oauth-s05-t11-evidence-02.jsonl` (000001–000060) ⊆
  `oauth-s05-t11-evidence-01.md` (000001–000062) =
  `oauth-s05-t11-evidence-04.yaml` (000001–000062) ⊆
  `oauth-s05-t11-evidence-03.csv` (000001–000071). Each smaller file's
  case-ID set is exactly a prefix of each larger file's case-ID set (0
  set-difference records in the smaller-into-larger direction, verified with
  `comm -23`), per all 4 files.
- `oauth-s05-t11-evidence-01.md` and `oauth-s05-t11-evidence-04.yaml` cover
  the exact same case-ID set (000001–000062, 0 differences either direction,
  verified with `comm -3`), per both files.
- `oauth-s05-t11-evidence-03.csv` contains 9 case records
  (oauth-s05-t11-000063 through oauth-s05-t11-000071) that do not appear in
  any of `oauth-s05-t11-evidence-01.md`, `oauth-s05-t11-evidence-02.jsonl`,
  or `oauth-s05-t11-evidence-04.yaml`.
- `oauth-s05-t11-evidence-01.md` and `oauth-s05-t11-evidence-04.yaml` each
  contain 2 case records (oauth-s05-t11-000061 through oauth-s05-t11-000062)
  that do not appear in `oauth-s05-t11-evidence-02.jsonl`.
- The `status` value set is identical across all 4 files:
  `{follow-up, recorded, review, supported}`, per
  `oauth-s05-t11-evidence-01.md`, `oauth-s05-t11-evidence-02.jsonl`,
  `oauth-s05-t11-evidence-03.csv`, and `oauth-s05-t11-evidence-04.yaml`.
- The `system` value set is identical across all 4 files:
  `{windows-x86_64, freebsd-x86_64, macos-arm64, linux-x86_64}`, per the
  same 4 files.
- Within each file, `system` and `status` follow a fixed, repeating 4-case
  cycle (`windows-x86_64`→`supported`, `freebsd-x86_64`→`review`,
  `macos-arm64`→`recorded`, `linux-x86_64`→`follow-up`, then repeat), with no
  exceptions found in any of the 4 files' full record sets. This exact
  system-to-status pairing matches the cycle recorded in
  `maintenance/reports/oauth-s05/migration-dry-run-observations.md`
  (`windows-x86_64`→`supported`, `freebsd-x86_64`→`review`,
  `macos-arm64`→`recorded`, `linux-x86_64`→`follow-up`), and differs from
  the cycles recorded in
  `maintenance/reports/oauth-s05/callback-cutover-worksheets.md`
  (`windows-x86_64`→`review`),
  `maintenance/reports/oauth-s05/client-owner-handoffs.md`
  (`windows-x86_64`→`recorded`),
  `maintenance/reports/oauth-s05/client-version-matrix.md`
  (`windows-x86_64`→`review`), and
  `maintenance/reports/oauth-s05/cutover-checkpoint-traces.md`
  (`windows-x86_64`→`follow-up`), per the source files reviewed for each
  report.
- Within each individual file, every `note` field's embedded case number
  (e.g. "for case 1.") matches that record's `case` ID suffix, with 0
  mismatches found across all 71 records in
  `oauth-s05-t11-evidence-03.csv` (the largest file).
- Within each individual file, all `case` IDs are unique (0 duplicates) and
  numerically contiguous starting at `...000001`, per the read-only parse of
  each file listed in the record-extraction table above.

## Handoff note

- All 4 files under `maintenance/inputs/oauth-s05/migration-rollback-casebook/`
  were discovered, read in full, and hashed; none were modified.
- Where case IDs overlap across files, the recorded `system` and `status`
  values agree with 0 mismatches (see table above) — the 4 files are
  consistent with one another wherever they overlap.
- `oauth-s05-t11-evidence-03.csv` (71 records) is the largest record set and
  a superset (by case-ID range) of all 3 other files.
  `oauth-s05-t11-evidence-01.md` and `oauth-s05-t11-evidence-04.yaml` (62
  records each, identical case coverage) are next, then
  `oauth-s05-t11-evidence-02.jsonl` (60 records, smallest). Each smaller
  file's case-ID range is an exact prefix of the next-larger file's range.
  None of the 4 source files states a reason for these differing record
  counts, so this report does not infer one; a follow-up should confirm with
  the source owner whether `oauth-s05-t11-evidence-02.jsonl` and
  `oauth-s05-t11-evidence-01.md` / `oauth-s05-t11-evidence-04.yaml` are
  intentionally partial extracts of `oauth-s05-t11-evidence-03.csv`, or
  whether they are out of date.
- This report's fixed system-to-status cycle
  (`windows-x86_64`→`supported`, `freebsd-x86_64`→`review`,
  `macos-arm64`→`recorded`, `linux-x86_64`→`follow-up`) exactly matches the
  cycle recorded in the separate
  `maintenance/reports/oauth-s05/migration-dry-run-observations.md` report;
  none of the source files under
  `maintenance/inputs/oauth-s05/migration-rollback-casebook/` states a
  reason for this match, so this report does not infer one.
- This report and its inputs live entirely under `maintenance/`; no
  application code, fixtures, routes, configuration, or tests were read for
  this task, and none were changed.
