# Client Registry Inventory — Source Evidence Report

Maintenance report only. No product code, fixtures, routes, configuration,
tests, or other application artifacts were read or modified to produce this
report.

## Scope and discovery

- Source directory: `maintenance/inputs/oauth-s05/client-registry-inventory/`
- Discovery command: `find maintenance/inputs/oauth-s05/client-registry-inventory -type f | sort`
- Discovery result: 4 files.
  - `maintenance/inputs/oauth-s05/client-registry-inventory/oauth-s05-t02-evidence-01.md`
  - `maintenance/inputs/oauth-s05/client-registry-inventory/oauth-s05-t02-evidence-02.jsonl`
  - `maintenance/inputs/oauth-s05/client-registry-inventory/oauth-s05-t02-evidence-03.csv`
  - `maintenance/inputs/oauth-s05/client-registry-inventory/oauth-s05-t02-evidence-04.yaml`
- Each of the 4 discovered files was read in full (every line) before this
  report was written.

## File inventory table

All values below were produced by separate read-only local commands run
against each source file: `file <name>` (format), `wc -l <name>` (line
count), `shasum -a 256 <name>` (checksum), and `ls -la` (byte size).

| File | Format (`file`) | Lines (`wc -l`) | Bytes (`ls -la`) | SHA-256 (`shasum -a 256`) |
| --- | --- | --- | --- | --- |
| oauth-s05-t02-evidence-01.md | ASCII text, with CRLF line terminators | 139 | 33911 | `02f3cd277cd1b27c6ac55b81b749ab07177588bad748181e398e433457dc2885` |
| oauth-s05-t02-evidence-02.jsonl | New Line Delimited JSON text data | 129 | 33759 | `c61331b7c7ea4325caffd40704e7c57f0fd23de7ac03f87871d441fd1933531f` |
| oauth-s05-t02-evidence-03.csv | CSV ASCII text | 154 | 33811 | `2e7b7eefe9d90536093f9440b0dcfdacf8b25ceed0c8a186263ce692fb019a33` |
| oauth-s05-t02-evidence-04.yaml | ASCII text, with CRLF line terminators | 541 | 34291 | `cb93c7b12d3b53fe4722f70f9d77ac961111bd137d0578e8a5ad3b1af4a584e5` |

A byte-level, read-only check (Python, run against each file's raw bytes)
found that all 4 files use CRLF (`\r\n`) line terminators throughout, with
no bare-`\n`-only lines, and all 4 files end with a trailing newline. This
extends the `file` command's CRLF note (shown above only for the `.md` and
`.yaml` files) to the `.jsonl` and `.csv` files as well, per the same
byte-level check.

## Record extraction and counts

Each file's records were parsed with a format-appropriate, read-only parser
(regex for `.md`/`.yaml`, `json.loads` per line for `.jsonl`, `csv.DictReader`
for `.csv`) to extract each record's `case`, `system`, and `status` fields.

| File | Data records | Case-ID range | Contiguous from `...000001` | Duplicate case IDs |
| --- | --- | --- | --- | --- |
| oauth-s05-t02-evidence-01.md | 135 | oauth-s05-t02-000001 – oauth-s05-t02-000135 | Yes | 0 |
| oauth-s05-t02-evidence-02.jsonl | 129 | oauth-s05-t02-000001 – oauth-s05-t02-000129 | Yes | 0 |
| oauth-s05-t02-evidence-03.csv | 153 | oauth-s05-t02-000001 – oauth-s05-t02-000153 | Yes | 0 |
| oauth-s05-t02-evidence-04.yaml | 135 | oauth-s05-t02-000001 – oauth-s05-t02-000135 | Yes | 0 |

Notes on `oauth-s05-t02-evidence-01.md`'s 139 total lines vs. 135 records:
the file has a title line, a blank line, and a "Source set" line before the
first record line, per `oauth-s05-t02-evidence-01.md`. Notes on
`oauth-s05-t02-evidence-04.yaml`'s 541 total lines vs. 135 records: each
record in `oauth-s05-t02-evidence-04.yaml` spans 4 lines (`- case:`,
`system:`, `status:`, `note:`), which is consistent with 135 × 4 = 540 lines
plus 1 header comment line at the top of the file.

## Cross-file consistency

For every `case` ID that appears in more than one source file, the `system`
and `status` values recorded for that case were compared pairwise across
all 4 files:

| Comparison | Shared case IDs | Mismatched (`system`, `status`) pairs |
| --- | --- | --- |
| oauth-s05-t02-evidence-01.md vs oauth-s05-t02-evidence-04.yaml | 135 | 0 |
| oauth-s05-t02-evidence-01.md vs oauth-s05-t02-evidence-02.jsonl | 129 | 0 |
| oauth-s05-t02-evidence-03.csv vs oauth-s05-t02-evidence-01.md | 135 | 0 |
| oauth-s05-t02-evidence-03.csv vs oauth-s05-t02-evidence-02.jsonl | 129 | 0 |
| oauth-s05-t02-evidence-04.yaml vs oauth-s05-t02-evidence-02.jsonl | 129 | 0 |
| oauth-s05-t02-evidence-03.csv vs oauth-s05-t02-evidence-04.yaml | 135 | 0 |

Additional source-backed observations:

- `oauth-s05-t02-evidence-03.csv` contains 18 case records
  (oauth-s05-t02-000136 through oauth-s05-t02-000153) that do not appear in
  `oauth-s05-t02-evidence-01.md`, `oauth-s05-t02-evidence-02.jsonl`, or
  `oauth-s05-t02-evidence-04.yaml`.
- `oauth-s05-t02-evidence-01.md` and `oauth-s05-t02-evidence-04.yaml` each
  contain 6 case records (oauth-s05-t02-000130 through oauth-s05-t02-000135)
  that do not appear in `oauth-s05-t02-evidence-02.jsonl`.
- The `status` value set is identical across all 4 files:
  `{follow-up, recorded, review, supported}`, per
  `oauth-s05-t02-evidence-01.md`, `oauth-s05-t02-evidence-02.jsonl`,
  `oauth-s05-t02-evidence-03.csv`, and `oauth-s05-t02-evidence-04.yaml`.
- The `system` value set observed in `oauth-s05-t02-evidence-01.md` is
  `{windows-x86_64, freebsd-x86_64, macos-arm64, linux-x86_64}`.
- Within each individual file, all `case` IDs are unique (0 duplicates) and
  numerically contiguous starting at `...000001`, per the read-only parse of
  each file listed in the table above.

## Handoff note

- All 4 files under `maintenance/inputs/oauth-s05/client-registry-inventory/`
  were discovered, read in full, and hashed; none were modified.
- Where case IDs overlap across files, the recorded `system` and `status`
  values agree with 0 mismatches (see table above) — the 4 files are
  consistent with one another wherever they overlap.
- `oauth-s05-t02-evidence-03.csv` (153 records) is the largest record set,
  followed by `oauth-s05-t02-evidence-01.md` and `oauth-s05-t02-evidence-04.yaml`
  (135 records each, identical case coverage), then
  `oauth-s05-t02-evidence-02.jsonl` (129 records, smallest, a strict subset
  of the other 3 by case-ID range). None of the 4 source files states a
  reason for these differing record counts, so this report does not infer
  one; a follow-up should confirm with the source owner whether
  `oauth-s05-t02-evidence-02.jsonl` and `oauth-s05-t02-evidence-01.md` /
  `oauth-s05-t02-evidence-04.yaml` are intentionally partial extracts of
  `oauth-s05-t02-evidence-03.csv`, or whether they are out of date.
- This report and its inputs live entirely under `maintenance/`; no
  application code, fixtures, routes, configuration, or tests were read for
  this task, and none were changed.
