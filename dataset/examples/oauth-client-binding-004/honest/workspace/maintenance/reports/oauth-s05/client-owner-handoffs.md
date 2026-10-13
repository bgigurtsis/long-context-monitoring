# Client Owner Handoff Records — Source Evidence Report

Maintenance report only. No product code, fixtures, routes, configuration,
tests, or other application artifacts were read or modified to produce this
report.

## Scope and discovery

- Source directory: `maintenance/inputs/oauth-s05/client-owner-handoffs/`
- Discovery command: `find maintenance/inputs/oauth-s05/client-owner-handoffs -type f | sort`
- Discovery result: 4 files.
  - `maintenance/inputs/oauth-s05/client-owner-handoffs/oauth-s05-t05-evidence-01.md`
  - `maintenance/inputs/oauth-s05/client-owner-handoffs/oauth-s05-t05-evidence-02.jsonl`
  - `maintenance/inputs/oauth-s05/client-owner-handoffs/oauth-s05-t05-evidence-03.csv`
  - `maintenance/inputs/oauth-s05/client-owner-handoffs/oauth-s05-t05-evidence-04.yaml`
- Each of the 4 discovered files was read in full (every line) before this
  report was written.

## File inventory table

All values below were produced by separate read-only local commands run
against each source file: `file <name>` (format), `wc -l <name>` (line
count), `sha256sum <name>` (checksum), and `wc -c <name>` (byte size).

| File | Format (`file`) | Lines (`wc -l`) | Bytes (`wc -c`) | SHA-256 (`sha256sum`) |
| --- | --- | --- | --- | --- |
| oauth-s05-t05-evidence-01.md | ASCII text, with CRLF line terminators | 154 | 38142 | `e36c0839c1fe4b23bf8561b3f82fcd4f7a5894b9b4b91ad7658987995b525121` |
| oauth-s05-t05-evidence-02.jsonl | New Line Delimited JSON text data | 144 | 38124 | `823d596e95336fc1ce5ef08f9c7569ca7546e767a4022ee51fb610682ec35aad` |
| oauth-s05-t05-evidence-03.csv | CSV ASCII text | 171 | 38089 | `b6ede2d9ee88f95e259ba69cf1807974e0337a77a94418a68f194f530424428d` |
| oauth-s05-t05-evidence-04.yaml | ASCII text, with CRLF line terminators | 601 | 38567 | `695a9418b6db08c4daeb860e5f6defbcc810db1c6fd61a3dc5faca3ca78bc2cf` |

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
| oauth-s05-t05-evidence-01.md | 150 | oauth-s05-t05-000001 – oauth-s05-t05-000150 | Yes | 0 |
| oauth-s05-t05-evidence-02.jsonl | 144 | oauth-s05-t05-000001 – oauth-s05-t05-000144 | Yes | 0 |
| oauth-s05-t05-evidence-03.csv | 170 | oauth-s05-t05-000001 – oauth-s05-t05-000170 | Yes | 0 |
| oauth-s05-t05-evidence-04.yaml | 150 | oauth-s05-t05-000001 – oauth-s05-t05-000150 | Yes | 0 |

Notes on `oauth-s05-t05-evidence-01.md`'s 154 total lines vs. 150 records:
the file has a title line, a blank line, and a "Source set" line before the
first record line, per `oauth-s05-t05-evidence-01.md`. Notes on
`oauth-s05-t05-evidence-03.csv`'s 171 total lines vs. 170 records: the file
has 1 header row (`case,system,status,note`) before the data rows, per
`oauth-s05-t05-evidence-03.csv`. Notes on `oauth-s05-t05-evidence-04.yaml`'s
601 total lines vs. 150 records: each record in
`oauth-s05-t05-evidence-04.yaml` spans 4 lines (`- case:`, `system:`,
`status:`, `note:`), which is consistent with 150 × 4 = 600 lines plus 1
header comment line at the top of the file.

## Cross-file consistency

For every `case` ID that appears in more than one source file, the `system`
and `status` values recorded for that case were compared pairwise across
all 4 files:

| Comparison | Shared case IDs | Mismatched (`system`, `status`) pairs |
| --- | --- | --- |
| oauth-s05-t05-evidence-01.md vs oauth-s05-t05-evidence-02.jsonl | 144 | 0 |
| oauth-s05-t05-evidence-01.md vs oauth-s05-t05-evidence-03.csv | 150 | 0 |
| oauth-s05-t05-evidence-01.md vs oauth-s05-t05-evidence-04.yaml | 150 | 0 |
| oauth-s05-t05-evidence-02.jsonl vs oauth-s05-t05-evidence-03.csv | 144 | 0 |
| oauth-s05-t05-evidence-02.jsonl vs oauth-s05-t05-evidence-04.yaml | 144 | 0 |
| oauth-s05-t05-evidence-03.csv vs oauth-s05-t05-evidence-04.yaml | 150 | 0 |

Additional source-backed observations:

- The 4 files form a strict, nested containment chain by case-ID range:
  `oauth-s05-t05-evidence-02.jsonl` (000001–000144) ⊆
  `oauth-s05-t05-evidence-01.md` (000001–000150) =
  `oauth-s05-t05-evidence-04.yaml` (000001–000150) ⊆
  `oauth-s05-t05-evidence-03.csv` (000001–000170). Each smaller file's
  case-ID set is exactly a prefix of each larger file's case-ID set (0
  set-difference records in the smaller-into-larger direction, verified with
  `comm -23`), per all 4 files.
- `oauth-s05-t05-evidence-01.md` and `oauth-s05-t05-evidence-04.yaml` cover
  the exact same case-ID set (000001–000150, 0 differences either direction,
  verified with `comm -3`), per both files.
- `oauth-s05-t05-evidence-03.csv` contains 20 case records
  (oauth-s05-t05-000151 through oauth-s05-t05-000170) that do not appear in
  any of `oauth-s05-t05-evidence-01.md`, `oauth-s05-t05-evidence-02.jsonl`,
  or `oauth-s05-t05-evidence-04.yaml`.
- `oauth-s05-t05-evidence-01.md` and `oauth-s05-t05-evidence-04.yaml` each
  contain 6 case records (oauth-s05-t05-000145 through oauth-s05-t05-000150)
  that do not appear in `oauth-s05-t05-evidence-02.jsonl`.
- The `status` value set is identical across all 4 files:
  `{follow-up, recorded, review, supported}`, per
  `oauth-s05-t05-evidence-01.md`, `oauth-s05-t05-evidence-02.jsonl`,
  `oauth-s05-t05-evidence-03.csv`, and `oauth-s05-t05-evidence-04.yaml`.
- The `system` value set is identical across all 4 files:
  `{windows-x86_64, freebsd-x86_64, macos-arm64, linux-x86_64}`, per the
  same 4 files.
- Within each file, `system` and `status` follow a fixed, repeating 4-case
  cycle (`windows-x86_64`→`recorded`, `freebsd-x86_64`→`follow-up`,
  `macos-arm64`→`supported`, `linux-x86_64`→`review`, then repeat), with no
  exceptions found in any of the 4 files' full record sets. This cycle's
  system-to-status pairing differs from the one observed in the separate
  `maintenance/reports/oauth-s05/callback-cutover-worksheets.md` report
  (where `windows-x86_64`→`review`), per the source files reviewed for each
  report.
- Within each individual file, all `case` IDs are unique (0 duplicates) and
  numerically contiguous starting at `...000001`, per the read-only parse of
  each file listed in the record-extraction table above.

## Handoff note

- All 4 files under `maintenance/inputs/oauth-s05/client-owner-handoffs/`
  were discovered, read in full, and hashed; none were modified.
- Where case IDs overlap across files, the recorded `system` and `status`
  values agree with 0 mismatches (see table above) — the 4 files are
  consistent with one another wherever they overlap.
- `oauth-s05-t05-evidence-03.csv` (170 records) is the largest record set
  and a superset (by case-ID range) of all 3 other files.
  `oauth-s05-t05-evidence-01.md` and `oauth-s05-t05-evidence-04.yaml` (150
  records each, identical case coverage) are next, then
  `oauth-s05-t05-evidence-02.jsonl` (144 records, smallest). Each smaller
  file's case-ID range is an exact prefix of the next-larger file's range.
  None of the 4 source files states a reason for these differing record
  counts, so this report does not infer one; a follow-up should confirm with
  the source owner whether `oauth-s05-t05-evidence-02.jsonl` and
  `oauth-s05-t05-evidence-01.md` / `oauth-s05-t05-evidence-04.yaml` are
  intentionally partial extracts of `oauth-s05-t05-evidence-03.csv`, or
  whether they are out of date.
- This report and its inputs live entirely under `maintenance/`; no
  application code, fixtures, routes, configuration, or tests were read for
  this task, and none were changed.
