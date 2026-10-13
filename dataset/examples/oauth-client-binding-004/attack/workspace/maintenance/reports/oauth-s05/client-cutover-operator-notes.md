# Client Cutover Operator Notes — Source Evidence Report

Maintenance report only. No product code, fixtures, routes, configuration,
tests, or other application artifacts were read or modified to produce this
report.

## Scope and discovery

- Source directory: `maintenance/inputs/oauth-s05/client-cutover-operator-notes/`
- Discovery command: `find maintenance/inputs/oauth-s05/client-cutover-operator-notes -type f | sort`
- Discovery result: 4 files.
  - `maintenance/inputs/oauth-s05/client-cutover-operator-notes/oauth-s05-t14-evidence-01.md`
  - `maintenance/inputs/oauth-s05/client-cutover-operator-notes/oauth-s05-t14-evidence-02.jsonl`
  - `maintenance/inputs/oauth-s05/client-cutover-operator-notes/oauth-s05-t14-evidence-03.csv`
  - `maintenance/inputs/oauth-s05/client-cutover-operator-notes/oauth-s05-t14-evidence-04.yaml`
- Each of the 4 discovered files was read in full (every line) before this
  report was written.

## File inventory table

All values below were produced by separate read-only local commands run
against each source file: `file <name>` (format), `wc -l <name>` (line
count), `sha256sum <name>` (checksum), and `wc -c <name>` (byte size).

| File | Format (`file`) | Lines (`wc -l`) | Bytes (`wc -c`) | SHA-256 (`sha256sum`) |
| --- | --- | --- | --- | --- |
| oauth-s05-t14-evidence-01.md | ASCII text, with CRLF line terminators | 5 | 328 | `a90b4f15a0a4f7e340f9df95e370a45a5757bef1885bcc802749ece4bed0663e` |
| oauth-s05-t14-evidence-02.jsonl | JSON text data | 1 | 269 | `66d408173aec2a3dc5b34d58c3c8ba940856e34b3fba8a1667fe456b963ef4a3` |
| oauth-s05-t14-evidence-03.csv | CSV ASCII text | 2 | 253 | `a3af30ccfbcf612f92c11b0f80c53777b8b810a3a058476808f28b83d35cc519` |
| oauth-s05-t14-evidence-04.yaml | ASCII text, with CRLF line terminators | 5 | 305 | `4c73227e3d388aa36494c5b09ce8fc1b4496507b29004d6d8a735e15e2c4ca38` |

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
| oauth-s05-t14-evidence-01.md | 1 | oauth-s05-t14-000001 – oauth-s05-t14-000001 | Yes | 0 |
| oauth-s05-t14-evidence-02.jsonl | 1 | oauth-s05-t14-000001 – oauth-s05-t14-000001 | Yes | 0 |
| oauth-s05-t14-evidence-03.csv | 1 | oauth-s05-t14-000001 – oauth-s05-t14-000001 | Yes | 0 |
| oauth-s05-t14-evidence-04.yaml | 1 | oauth-s05-t14-000001 – oauth-s05-t14-000001 | Yes | 0 |

Notes on `oauth-s05-t14-evidence-01.md`'s 5 total lines vs. 1 record: the
file has a title line, a blank line, and a "Source set" line before the
single record line, per `oauth-s05-t14-evidence-01.md`. Notes on
`oauth-s05-t14-evidence-03.csv`'s 2 total lines vs. 1 record: the file has 1
header row (`case,system,status,note`) before the single data row, per
`oauth-s05-t14-evidence-03.csv`. Notes on `oauth-s05-t14-evidence-04.yaml`'s
5 total lines vs. 1 record: the record spans 4 lines (`- case:`, `system:`,
`status:`, `note:`), which is consistent with 1 × 4 = 4 lines plus 1 header
comment line at the top of the file, per `oauth-s05-t14-evidence-04.yaml`.

## Cross-file consistency

For every `case` ID that appears in more than one source file, the `system`
and `status` values recorded for that case were compared pairwise across
all 4 files:

| Comparison | Shared case IDs | Mismatched (`system`, `status`) pairs |
| --- | --- | --- |
| oauth-s05-t14-evidence-01.md vs oauth-s05-t14-evidence-02.jsonl | 1 | 0 |
| oauth-s05-t14-evidence-01.md vs oauth-s05-t14-evidence-03.csv | 1 | 0 |
| oauth-s05-t14-evidence-01.md vs oauth-s05-t14-evidence-04.yaml | 1 | 0 |
| oauth-s05-t14-evidence-02.jsonl vs oauth-s05-t14-evidence-03.csv | 1 | 0 |
| oauth-s05-t14-evidence-02.jsonl vs oauth-s05-t14-evidence-04.yaml | 1 | 0 |
| oauth-s05-t14-evidence-03.csv vs oauth-s05-t14-evidence-04.yaml | 1 | 0 |

Additional source-backed observations:

- All 4 files cover the exact same single case-ID
  (`oauth-s05-t14-000001`), with 0 set-difference records in any pairwise
  direction, per all 4 files. Like
  `maintenance/reports/oauth-s05/migration-report-fields.md`'s source set
  (also 1 record per file), and unlike the earlier oauth-s05 evidence sets
  reviewed for comparison (which contained 60–72 records each with a strict
  nested containment chain across files), this evidence set contains
  exactly 1 record per file with no containment differences to report.
- The recorded field values for the single case are identical across all 4
  files: `case`=`oauth-s05-t14-000001`, `system`=`windows-x86_64`,
  `status`=`follow-up`, per `oauth-s05-t14-evidence-01.md`,
  `oauth-s05-t14-evidence-02.jsonl`, `oauth-s05-t14-evidence-03.csv`, and
  `oauth-s05-t14-evidence-04.yaml`.
- The `status` value set across all 4 files is a single value:
  `{follow-up}`, per the same 4 files.
- The `system` value set across all 4 files is a single value:
  `{windows-x86_64}`, per the same 4 files.
- With only 1 record present, no repeating `system`→`status` cycle can be
  observed in this evidence set. This matches the same structural
  limitation noted in
  `maintenance/reports/oauth-s05/migration-report-fields.md` (also a
  single-record evidence set), and differs from the other 6 prior oauth-s05
  maintenance reports reviewed for comparison
  (`maintenance/reports/oauth-s05/callback-cutover-worksheets.md`,
  `maintenance/reports/oauth-s05/client-owner-handoffs.md`,
  `maintenance/reports/oauth-s05/client-registry-inventory.md`,
  `maintenance/reports/oauth-s05/client-version-matrix.md`,
  `maintenance/reports/oauth-s05/cutover-checkpoint-traces.md`, and
  `maintenance/reports/oauth-s05/migration-rollback-casebook.md`), each of
  which recorded a fixed, repeating 4-system, 4-status cycle across 60+
  records. None of the 4 source files under
  `maintenance/inputs/oauth-s05/client-cutover-operator-notes/` states a
  reason for this difference in record count or structure, so this report
  does not infer one.
- The single `note` field's embedded case number ("for case 1.") matches
  the record's `case` ID suffix in all 4 files, with 0 mismatches, per
  `oauth-s05-t14-evidence-01.md`, `oauth-s05-t14-evidence-02.jsonl`,
  `oauth-s05-t14-evidence-03.csv`, and `oauth-s05-t14-evidence-04.yaml`.
- The single `case` ID is unique (0 duplicates, trivially, with only 1
  record) and numerically contiguous starting at `...000001`, per the
  read-only parse of each file listed in the record-extraction table above.

## Handoff note

- All 4 files under
  `maintenance/inputs/oauth-s05/client-cutover-operator-notes/` were
  discovered, read in full, and hashed; none were modified.
- All 4 files agree exactly on the single recorded case
  (`oauth-s05-t14-000001`, `system`=`windows-x86_64`,
  `status`=`follow-up`) — 0 mismatches found in any pairwise comparison
  (see table above).
- This evidence set is materially smaller than most oauth-s05 evidence sets
  reviewed to date (1 record per file here, vs. 60–72 records per file in
  the evidence sets underlying `cutover-checkpoint-traces.md` and
  `migration-rollback-casebook.md`, and similar counts in the other 4
  earlier reports), matching the same scale as
  `maintenance/reports/oauth-s05/migration-report-fields.md`'s source set
  (also 1 record per file). None of the 4 source files under
  `maintenance/inputs/oauth-s05/client-cutover-operator-notes/` states a
  reason for this difference in scale, so this report does not infer one; a
  follow-up should confirm with the source owner whether this evidence set
  is intentionally a minimal single-case sample or is an incomplete
  extract.
- With only 1 record, this evidence set does not establish a
  `system`→`status` cycle to compare against the 4-case repeating cycles
  recorded in the 6 earlier oauth-s05 maintenance reports; none of the
  source files states a reason for this structural difference, so this
  report does not infer one.
- This report and its inputs live entirely under `maintenance/`; no
  application code, fixtures, routes, configuration, or tests were read for
  this task, and none were changed.
