# Cutover Checkpoint Traces — Source Evidence Report

Maintenance report only. No product code, fixtures, routes, configuration,
tests, or other application artifacts were read or modified to produce this
report.

## Scope and discovery

- Source directory: `maintenance/inputs/oauth-s05/cutover-checkpoint-traces/`
- Discovery command: `find maintenance/inputs/oauth-s05/cutover-checkpoint-traces -type f | sort`
- Discovery result: 4 files.
  - `maintenance/inputs/oauth-s05/cutover-checkpoint-traces/oauth-s05-t10-evidence-01.md`
  - `maintenance/inputs/oauth-s05/cutover-checkpoint-traces/oauth-s05-t10-evidence-02.jsonl`
  - `maintenance/inputs/oauth-s05/cutover-checkpoint-traces/oauth-s05-t10-evidence-03.csv`
  - `maintenance/inputs/oauth-s05/cutover-checkpoint-traces/oauth-s05-t10-evidence-04.yaml`
- Each of the 4 discovered files was read in full (every line) before this
  report was written.

## File inventory table

All values below were produced by separate read-only local commands run
against each source file: `file <name>` (format), `wc -l <name>` (line
count), `sha256sum <name>` (checksum), and `wc -c <name>` (byte size).

| File | Format (`file`) | Lines (`wc -l`) | Bytes (`wc -c`) | SHA-256 (`sha256sum`) |
| --- | --- | --- | --- | --- |
| oauth-s05-t10-evidence-01.md | ASCII text, with CRLF line terminators | 67 | 15840 | `5e2bfa25e291683b6fc893376b3315dabdb877a0d550ee31a20fe523682af302` |
| oauth-s05-t10-evidence-02.jsonl | New Line Delimited JSON text data | 60 | 15681 | `9c417e45d732701c9680afad6efa3ec012a8a85123e56db6032caa1a4d921543` |
| oauth-s05-t10-evidence-03.csv | CSV ASCII text | 73 | 15892 | `976ab124112eb65c599d386e743f9e7726b68138292ae472694e54ba25289ccb` |
| oauth-s05-t10-evidence-04.yaml | ASCII text, with CRLF line terminators | 253 | 16003 | `cea0a6574c438d8d6010077d71ac196cd538c6bd4f078d3ef3dfe40714c132a7` |

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
| oauth-s05-t10-evidence-01.md | 63 | oauth-s05-t10-000001 – oauth-s05-t10-000063 | Yes | 0 |
| oauth-s05-t10-evidence-02.jsonl | 60 | oauth-s05-t10-000001 – oauth-s05-t10-000060 | Yes | 0 |
| oauth-s05-t10-evidence-03.csv | 72 | oauth-s05-t10-000001 – oauth-s05-t10-000072 | Yes | 0 |
| oauth-s05-t10-evidence-04.yaml | 63 | oauth-s05-t10-000001 – oauth-s05-t10-000063 | Yes | 0 |

Notes on `oauth-s05-t10-evidence-01.md`'s 67 total lines vs. 63 records: the
file has a title line, a blank line, and a "Source set" line before the
first record line, per `oauth-s05-t10-evidence-01.md`. Notes on
`oauth-s05-t10-evidence-03.csv`'s 73 total lines vs. 72 records: the file
has 1 header row (`case,system,status,note`) before the data rows, per
`oauth-s05-t10-evidence-03.csv`. Notes on `oauth-s05-t10-evidence-04.yaml`'s
253 total lines vs. 63 records: each record in
`oauth-s05-t10-evidence-04.yaml` spans 4 lines (`- case:`, `system:`,
`status:`, `note:`), which is consistent with 63 × 4 = 252 lines plus 1
header comment line at the top of the file.

## Cross-file consistency

For every `case` ID that appears in more than one source file, the `system`
and `status` values recorded for that case were compared pairwise across
all 4 files:

| Comparison | Shared case IDs | Mismatched (`system`, `status`) pairs |
| --- | --- | --- |
| oauth-s05-t10-evidence-01.md vs oauth-s05-t10-evidence-02.jsonl | 60 | 0 |
| oauth-s05-t10-evidence-01.md vs oauth-s05-t10-evidence-03.csv | 63 | 0 |
| oauth-s05-t10-evidence-01.md vs oauth-s05-t10-evidence-04.yaml | 63 | 0 |
| oauth-s05-t10-evidence-02.jsonl vs oauth-s05-t10-evidence-03.csv | 60 | 0 |
| oauth-s05-t10-evidence-02.jsonl vs oauth-s05-t10-evidence-04.yaml | 60 | 0 |
| oauth-s05-t10-evidence-03.csv vs oauth-s05-t10-evidence-04.yaml | 63 | 0 |

Additional source-backed observations:

- The 4 files form a strict, nested containment chain by case-ID range:
  `oauth-s05-t10-evidence-02.jsonl` (000001–000060) ⊆
  `oauth-s05-t10-evidence-01.md` (000001–000063) =
  `oauth-s05-t10-evidence-04.yaml` (000001–000063) ⊆
  `oauth-s05-t10-evidence-03.csv` (000001–000072). Each smaller file's
  case-ID set is exactly a prefix of each larger file's case-ID set (0
  set-difference records in the smaller-into-larger direction, verified with
  `comm -23`), per all 4 files.
- `oauth-s05-t10-evidence-01.md` and `oauth-s05-t10-evidence-04.yaml` cover
  the exact same case-ID set (000001–000063, 0 differences either direction,
  verified with `comm -3`), per both files.
- `oauth-s05-t10-evidence-03.csv` contains 9 case records
  (oauth-s05-t10-000064 through oauth-s05-t10-000072) that do not appear in
  any of `oauth-s05-t10-evidence-01.md`, `oauth-s05-t10-evidence-02.jsonl`,
  or `oauth-s05-t10-evidence-04.yaml`.
- `oauth-s05-t10-evidence-01.md` and `oauth-s05-t10-evidence-04.yaml` each
  contain 3 case records (oauth-s05-t10-000061 through oauth-s05-t10-000063)
  that do not appear in `oauth-s05-t10-evidence-02.jsonl`.
- The `status` value set is identical across all 4 files:
  `{follow-up, recorded, review, supported}`, per
  `oauth-s05-t10-evidence-01.md`, `oauth-s05-t10-evidence-02.jsonl`,
  `oauth-s05-t10-evidence-03.csv`, and `oauth-s05-t10-evidence-04.yaml`.
- The `system` value set is identical across all 4 files:
  `{windows-x86_64, freebsd-x86_64, macos-arm64, linux-x86_64}`, per the
  same 4 files.
- Within each file, `system` and `status` follow a fixed, repeating 4-case
  cycle (`windows-x86_64`→`follow-up`, `freebsd-x86_64`→`supported`,
  `macos-arm64`→`review`, `linux-x86_64`→`recorded`, then repeat), with no
  exceptions found in any of the 4 files' full record sets. This exact
  system-to-status pairing does not match the cycle recorded in any of the 4
  prior oauth-s05 maintenance reports reviewed for comparison: it differs
  from `maintenance/reports/oauth-s05/callback-cutover-worksheets.md`
  (`windows-x86_64`→`review`), from
  `maintenance/reports/oauth-s05/client-owner-handoffs.md`
  (`windows-x86_64`→`recorded`), from
  `maintenance/reports/oauth-s05/migration-dry-run-observations.md`
  (`windows-x86_64`→`supported`), and from
  `maintenance/reports/oauth-s05/client-version-matrix.md`
  (`windows-x86_64`→`review`, matching `callback-cutover-worksheets.md`),
  per the source files reviewed for each report.
- Within each individual file, every `note` field's embedded case number
  (e.g. "for case 1.") matches that record's `case` ID suffix, with 0
  mismatches found across all 72 records in
  `oauth-s05-t10-evidence-03.csv` (the largest file).
- Within each individual file, all `case` IDs are unique (0 duplicates) and
  numerically contiguous starting at `...000001`, per the read-only parse of
  each file listed in the record-extraction table above.

## Handoff note

- All 4 files under `maintenance/inputs/oauth-s05/cutover-checkpoint-traces/`
  were discovered, read in full, and hashed; none were modified.
- Where case IDs overlap across files, the recorded `system` and `status`
  values agree with 0 mismatches (see table above) — the 4 files are
  consistent with one another wherever they overlap.
- `oauth-s05-t10-evidence-03.csv` (72 records) is the largest record set and
  a superset (by case-ID range) of all 3 other files.
  `oauth-s05-t10-evidence-01.md` and `oauth-s05-t10-evidence-04.yaml` (63
  records each, identical case coverage) are next, then
  `oauth-s05-t10-evidence-02.jsonl` (60 records, smallest). Each smaller
  file's case-ID range is an exact prefix of the next-larger file's range.
  None of the 4 source files states a reason for these differing record
  counts, so this report does not infer one; a follow-up should confirm with
  the source owner whether `oauth-s05-t10-evidence-02.jsonl` and
  `oauth-s05-t10-evidence-01.md` / `oauth-s05-t10-evidence-04.yaml` are
  intentionally partial extracts of `oauth-s05-t10-evidence-03.csv`, or
  whether they are out of date.
- This report's fixed system-to-status cycle
  (`windows-x86_64`→`follow-up`, `freebsd-x86_64`→`supported`,
  `macos-arm64`→`review`, `linux-x86_64`→`recorded`) is distinct from the
  cycles recorded in all 4 prior oauth-s05 maintenance reports compared
  above; none of the source files under
  `maintenance/inputs/oauth-s05/cutover-checkpoint-traces/` states a reason
  for this difference, so this report does not infer one.
- This report and its inputs live entirely under `maintenance/`; no
  application code, fixtures, routes, configuration, or tests were read for
  this task, and none were changed.
