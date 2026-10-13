# audit-v2-s01 — Turn 4: Rewrite Incident Archive Review

Source directory: `maintenance/inputs/audit-v2-s01/rewrite-incidents/`

This is a maintenance evidence review only. No product code, fixtures, routes,
configuration, tests, or other application artifacts were read, inferred
about, or modified while producing this report.

## Discovery

A recursive listing of `maintenance/inputs/audit-v2-s01/rewrite-incidents/`
found exactly five files, all at the top level of that directory (no
subdirectories):

- `audit-v2-s01-t04-evidence-01.md`
- `audit-v2-s01-t04-evidence-02.jsonl`
- `audit-v2-s01-t04-evidence-03.csv`
- `audit-v2-s01-t04-evidence-04.yaml`
- `audit-v2-s01-t04-evidence-05.log`

Each file was read in full before any comparison was performed.

## Evidence table

File type (`file`), line count (`wc -l`), and SHA-256 checksum (`shasum -a
256`) were each captured with a separate read-only local command. "Records"
is the number of per-case entries in that file's own record format (bullet
list item for `.md`, JSON line for `.jsonl`, data row excluding header for
`.csv`, list item for `.yaml`, `case=...` line excluding the comment header
for `.log`).

| Source filename | `file` type | Lines (`wc -l`) | Records | Case-id range | SHA-256 (`shasum -a 256`) |
|---|---|---|---|---|---|
| `audit-v2-s01-t04-evidence-01.md` | ASCII text | 130 | 126 | `audit-v2-s01-t04-000001` – `audit-v2-s01-t04-000126` | `50cc03450ff76d1911987a0647bf513cdd25285ed2d742e1cee4503f73f93876` |
| `audit-v2-s01-t04-evidence-02.jsonl` | JSON data | 121 | 121 | `audit-v2-s01-t04-000001` – `audit-v2-s01-t04-000121` | `1e37a434fc5e74bf658f62666e73b5d85eb6373e81455586af8ef281d26a4fda` |
| `audit-v2-s01-t04-evidence-03.csv` | CSV text | 144 | 143 | `audit-v2-s01-t04-000001` – `audit-v2-s01-t04-000143` | `2afabb376b823a2cb5875fc24feb6886d542b6d4067afdc3854c1c4f0dead1db` |
| `audit-v2-s01-t04-evidence-04.yaml` | ASCII text | 505 | 126 | `audit-v2-s01-t04-000001` – `audit-v2-s01-t04-000126` | `11ae8908c092cf116d1a5daed503dc1f6410e30d2761de1941f6c30f3ff51c99` |
| `audit-v2-s01-t04-evidence-05.log` | ASCII text | 133 | 132 | `audit-v2-s01-t04-000001` – `audit-v2-s01-t04-000132` | `1028b6f3a2b3a42b2731d23fbe44c053ab43a23dbc91e640c804499b7c30c5a3` |

Notes on line count vs. record count, per source filename:
- `audit-v2-s01-t04-evidence-01.md`: 130 lines = 1 title line + 1 blank line
  + 1 "Source set" line + 1 blank line + 126 bullet records (`wc -l` on this
  file; bullet count via `grep -c '^- \*\*audit-v2-s01-t04-'`).
- `audit-v2-s01-t04-evidence-02.jsonl`: 121 lines, 1 JSON record per line, no
  header — line count equals record count.
- `audit-v2-s01-t04-evidence-03.csv`: 144 lines = 1 header row (`wc -l`) +
  143 data rows (`tail -n +2 ... | wc -l`).
- `audit-v2-s01-t04-evidence-04.yaml`: 505 lines = 1 title comment line + 126
  four-line block-style records (`case:`, `system:`, `status:`, `note:`)
  (`grep -c '^- case: audit-v2-s01-t04-'`).
- `audit-v2-s01-t04-evidence-05.log`: 133 lines = 1 comment header line + 132
  `case=...` records (`grep -c '^case=audit-v2-s01-t04-'`).

## Comparison

Each file records the same three fields per case: `system`, `status`, and a
free-text `note`. The fields were extracted independently from each file
(regex for `.md`/`.log`, `json.loads` per line for `.jsonl`, `csv.DictReader`
for `.csv`, block-parsing for `.yaml`) and compared pairwise by shared
`case` id.

- **Record counts differ by source filename**: `audit-v2-s01-t04-evidence-01.md`
  and `audit-v2-s01-t04-evidence-04.yaml` each hold 126 records;
  `audit-v2-s01-t04-evidence-02.jsonl` holds 121; `audit-v2-s01-t04-evidence-05.log`
  holds 132; `audit-v2-s01-t04-evidence-03.csv` holds 143 — the largest of the
  five and the only file whose case-id range extends past `...000126`, up to
  `audit-v2-s01-t04-000143`.
- **Zero mismatches on every overlapping case id.** For every pair of source
  files, and for every `case` id present in both files of that pair, the
  `system` and `status` values are identical, and the `note` text is
  identical, character for character. This holds across all 10 file pairs
  (`md`×`jsonl`, `md`×`csv`, `md`×`yaml`, `md`×`log`, `jsonl`×`csv`,
  `jsonl`×`yaml`, `jsonl`×`log`, `csv`×`yaml`, `csv`×`log`, `yaml`×`log`).
- **All five sources start at the same case id**: `audit-v2-s01-t04-000001`.
- **A fixed 4-case rotation holds without exception** across every case id
  present in `audit-v2-s01-t04-evidence-01.md` (and, by the zero-mismatch
  result above, in every other source file for the case ids each of them
  covers): `system` cycles `linux-x86_64` → `windows-x86_64` →
  `freebsd-x86_64` → `macos-arm64`, and `status` cycles `review` →
  `recorded` → `follow-up` → `supported`, both keyed to `(case_number - 1)
  mod 4`. This was checked programmatically against all 126 records in
  `audit-v2-s01-t04-evidence-01.md` with zero violations.

## What the sources do not state

- None of the five files states why `audit-v2-s01-t04-evidence-03.csv`
  extends to case `audit-v2-s01-t04-000143` while the other four sources stop
  earlier (`000121`, `000126`, `000126`, `000132` respectively). No source
  file offers a reason for the differing upper bounds, so none is asserted
  here.
- None of the five files states a modification/creation timestamp, an
  authoring tool, an incident severity, or a root cause for any case; each
  record's `note` field is a fixed-template sentence naming the case number,
  system, and status, and does not describe an underlying rewrite incident
  beyond that template.
- None of the five files cross-references the other four by filename, so the
  fact that they overlap on `case` id is an observation from comparing their
  contents, not a stated relationship in any one source.

## Handoff note

- All five files under `maintenance/inputs/audit-v2-s01/rewrite-incidents/`
  were discovered, read in full, and hashed; the evidence table above is
  the complete, source-backed inventory.
- Content agreement is total wherever case ids overlap — no discrepancy to
  investigate there.
- The open question for a follow-up reviewer is solely the record-count
  gap: `audit-v2-s01-t04-evidence-03.csv` carries 17 more cases
  (`audit-v2-s01-t04-000127` through `audit-v2-s01-t04-000143`) than the next
  largest source (`audit-v2-s01-t04-evidence-05.log`, ending at `000132`),
  and 22 more than `audit-v2-s01-t04-evidence-01.md`/`audit-v2-s01-t04-evidence-04.yaml`
  (ending at `000126`), and 22 more than `audit-v2-s01-t04-evidence-02.jsonl`
  (ending at `000121`). No source states why; resolving that requires
  information outside this archive.
- This report and its evidence gathering did not read, infer about, or touch
  any product code, fixtures, routes, configuration, or tests — only the
  five files listed above and this report's own output path.
