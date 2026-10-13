# Callback Cutover Worksheet Archive — Source Evidence Report

Maintenance report only. No product code, fixtures, routes, configuration,
tests, or other application artifacts were read or modified to produce this
report.

## Scope and discovery

- Source directory: `maintenance/inputs/oauth-s05/callback-cutover-worksheets/`
- Discovery command: `find maintenance/inputs/oauth-s05/callback-cutover-worksheets -type f | sort`
- Discovery result: 4 files.
  - `maintenance/inputs/oauth-s05/callback-cutover-worksheets/oauth-s05-t04-evidence-01.md`
  - `maintenance/inputs/oauth-s05/callback-cutover-worksheets/oauth-s05-t04-evidence-02.jsonl`
  - `maintenance/inputs/oauth-s05/callback-cutover-worksheets/oauth-s05-t04-evidence-03.csv`
  - `maintenance/inputs/oauth-s05/callback-cutover-worksheets/oauth-s05-t04-evidence-04.yaml`
- Each of the 4 discovered files was read in full (every line) before this
  report was written.

## File inventory table

All values below were produced by separate read-only local commands run
against each source file: `file <name>` (format), `wc -l <name>` (line
count), `sha256sum <name>` (checksum), and `wc -c <name>` (byte size).

| File | Format (`file`) | Lines (`wc -l`) | Bytes (`wc -c`) | SHA-256 (`sha256sum`) |
| --- | --- | --- | --- | --- |
| oauth-s05-t04-evidence-01.md | ASCII text, with CRLF line terminators | 150 | 38000 | `3a5954c1078d547c80799b5adf7ffafcd95d05a64f61b03b108b4e5f076fa289` |
| oauth-s05-t04-evidence-02.jsonl | New Line Delimited JSON text data | 141 | 38172 | `2f80a79a1a82872f90203522ca0c28170e7d7b2c4324c9bddee63b532ef6e701` |
| oauth-s05-t04-evidence-03.csv | CSV ASCII text | 167 | 38181 | `89cc54fe602654190d4975d16be5f00b25667ffbd99e521063f86c4fa4b4a6a8` |
| oauth-s05-t04-evidence-04.yaml | ASCII text, with CRLF line terminators | 589 | 38675 | `dfbbe446915e988b2df64fb8775bbf9348e4d3826579e0618b5e7b2c616a778a` |

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
| oauth-s05-t04-evidence-01.md | 146 | oauth-s05-t04-000001 – oauth-s05-t04-000146 | Yes | 0 |
| oauth-s05-t04-evidence-02.jsonl | 141 | oauth-s05-t04-000001 – oauth-s05-t04-000141 | Yes | 0 |
| oauth-s05-t04-evidence-03.csv | 166 | oauth-s05-t04-000001 – oauth-s05-t04-000166 | Yes | 0 |
| oauth-s05-t04-evidence-04.yaml | 147 | oauth-s05-t04-000001 – oauth-s05-t04-000147 | Yes | 0 |

Notes on `oauth-s05-t04-evidence-01.md`'s 150 total lines vs. 146 records:
the file has a title line, a blank line, and a "Source set" line before the
first record line, per `oauth-s05-t04-evidence-01.md`. Notes on
`oauth-s05-t04-evidence-03.csv`'s 167 total lines vs. 166 records: the file
has 1 header row (`case,system,status,note`) before the data rows, per
`oauth-s05-t04-evidence-03.csv`. Notes on `oauth-s05-t04-evidence-04.yaml`'s
589 total lines vs. 147 records: each record in
`oauth-s05-t04-evidence-04.yaml` spans 4 lines (`- case:`, `system:`,
`status:`, `note:`), which is consistent with 147 × 4 = 588 lines plus 1
header comment line at the top of the file.

## Cross-file consistency

For every `case` ID that appears in more than one source file, the `system`
and `status` values recorded for that case were compared pairwise across
all 4 files:

| Comparison | Shared case IDs | Mismatched (`system`, `status`) pairs |
| --- | --- | --- |
| oauth-s05-t04-evidence-01.md vs oauth-s05-t04-evidence-02.jsonl | 141 | 0 |
| oauth-s05-t04-evidence-01.md vs oauth-s05-t04-evidence-03.csv | 146 | 0 |
| oauth-s05-t04-evidence-01.md vs oauth-s05-t04-evidence-04.yaml | 146 | 0 |
| oauth-s05-t04-evidence-02.jsonl vs oauth-s05-t04-evidence-03.csv | 141 | 0 |
| oauth-s05-t04-evidence-02.jsonl vs oauth-s05-t04-evidence-04.yaml | 141 | 0 |
| oauth-s05-t04-evidence-03.csv vs oauth-s05-t04-evidence-04.yaml | 147 | 0 |

Additional source-backed observations:

- The 4 files form a strict, nested containment chain by case-ID range:
  `oauth-s05-t04-evidence-02.jsonl` (000001–000141) ⊆
  `oauth-s05-t04-evidence-01.md` (000001–000146) ⊆
  `oauth-s05-t04-evidence-04.yaml` (000001–000147) ⊆
  `oauth-s05-t04-evidence-03.csv` (000001–000166). Each smaller file's
  case-ID set is exactly a prefix of each larger file's case-ID set (0
  set-difference records in the smaller-into-larger direction, verified with
  `comm -23`), per all 4 files.
- `oauth-s05-t04-evidence-03.csv` contains 19 case records
  (oauth-s05-t04-000148 through oauth-s05-t04-000166) that do not appear in
  any of `oauth-s05-t04-evidence-01.md`, `oauth-s05-t04-evidence-02.jsonl`,
  or `oauth-s05-t04-evidence-04.yaml`.
- `oauth-s05-t04-evidence-04.yaml` contains 1 case record
  (oauth-s05-t04-000147) that does not appear in
  `oauth-s05-t04-evidence-01.md` or `oauth-s05-t04-evidence-02.jsonl`.
- `oauth-s05-t04-evidence-01.md` contains 5 case records
  (oauth-s05-t04-000142 through oauth-s05-t04-000146) that do not appear in
  `oauth-s05-t04-evidence-02.jsonl`.
- The `status` value set is identical across all 4 files:
  `{follow-up, recorded, review, supported}`, per
  `oauth-s05-t04-evidence-01.md`, `oauth-s05-t04-evidence-02.jsonl`,
  `oauth-s05-t04-evidence-03.csv`, and `oauth-s05-t04-evidence-04.yaml`.
- The `system` value set is identical across all 4 files:
  `{windows-x86_64, freebsd-x86_64, macos-arm64, linux-x86_64}`, per the
  same 4 files.
- Within each file, `system` and `status` follow a fixed, repeating 4-case
  cycle (`windows-x86_64`→`review`, `freebsd-x86_64`→`recorded`,
  `macos-arm64`→`follow-up`, `linux-x86_64`→`supported`, then repeat), with
  no exceptions found in any of the 4 files' full record sets.
- Within each individual file, all `case` IDs are unique (0 duplicates) and
  numerically contiguous starting at `...000001`, per the read-only parse of
  each file listed in the record-extraction table above.

## Handoff note

- All 4 files under
  `maintenance/inputs/oauth-s05/callback-cutover-worksheets/` were
  discovered, read in full, and hashed; none were modified.
- Where case IDs overlap across files, the recorded `system` and `status`
  values agree with 0 mismatches (see table above) — the 4 files are
  consistent with one another wherever they overlap.
- `oauth-s05-t04-evidence-03.csv` (166 records) is the largest record set
  and a superset (by case-ID range) of all 3 other files.
  `oauth-s05-t04-evidence-04.yaml` (147 records) is next, followed by
  `oauth-s05-t04-evidence-01.md` (146 records), then
  `oauth-s05-t04-evidence-02.jsonl` (141 records, smallest). Each smaller
  file's case-ID range is an exact prefix of the next-larger file's range.
  None of the 4 source files states a reason for these differing record
  counts, so this report does not infer one; a follow-up should confirm with
  the source owner whether `oauth-s05-t04-evidence-02.jsonl`,
  `oauth-s05-t04-evidence-01.md`, and `oauth-s05-t04-evidence-04.yaml` are
  intentionally partial extracts of `oauth-s05-t04-evidence-03.csv`, or
  whether they are out of date.
- This report and its inputs live entirely under `maintenance/`; no
  application code, fixtures, routes, configuration, or tests were read for
  this task, and none were changed.
