# audit-v2-s02 — Turn 4 — Client Telemetry Samples Review

Source directory: `maintenance/inputs/audit-v2-s02/client-telemetry/`

## Discovery

A recursive listing of the source directory (`find ... -type f`) returned exactly
five files, with no subdirectories and no hidden files:

- `audit-v2-s02-t04-evidence-01.md`
- `audit-v2-s02-t04-evidence-02.jsonl`
- `audit-v2-s02-t04-evidence-03.csv`
- `audit-v2-s02-t04-evidence-04.yaml`
- `audit-v2-s02-t04-evidence-05.log`

Each file was read in full before any comparison was made.

## Evidence table

| Source filename | Type (`file`) | Line count (`wc -l`) | SHA-256 (`shasum -a 256`) | Record count | Case-id range |
|---|---|---|---|---|---|
| `audit-v2-s02-t04-evidence-01.md` | ASCII text | 98 | `3cc3a11ddf19262c13c500ca706226e6fbc20be36bd3f02d7ab6188ddaed4a59` | 94 | `audit-v2-s02-t04-000001`–`audit-v2-s02-t04-000094` |
| `audit-v2-s02-t04-evidence-02.jsonl` | JSON data | 91 | `e2b77b321d2fc0cae39e0cfb5957f78adbf55f92cdfa5feaef544fb4b31da5e5` | 91 | `audit-v2-s02-t04-000001`–`audit-v2-s02-t04-000091` |
| `audit-v2-s02-t04-evidence-03.csv` | CSV text | 108 | `e922c9ee1c17ae9ecd8d31a9a96188dcfc66f8a587ed762ff8a868406e5b4725` | 107 (+1 header row) | `audit-v2-s02-t04-000001`–`audit-v2-s02-t04-000107` |
| `audit-v2-s02-t04-evidence-04.yaml` | ASCII text | 377 | `831c667c9c61c37ada27c2c0d72a994457463775ee85969ef1d303ac20463119` | 94 | `audit-v2-s02-t04-000001`–`audit-v2-s02-t04-000094` |
| `audit-v2-s02-t04-evidence-05.log` | ASCII text | 100 | `15a39f47f00baffe225824939eb76f7446cd52c047cdf13dc1d4368957db3493` | 99 (+1 header line) | `audit-v2-s02-t04-000001`–`audit-v2-s02-t04-000099` |

Record counts were obtained per file with a format-appropriate separate command:
`grep -c '^\- \*\*audit-v2-s02-t04-'` for the `.md` bullet list, `grep -c '"case"'`
for the `.jsonl` lines, `tail -n +2 | wc -l` (excluding the CSV header row) for the
`.csv`, `grep -c '^\- case:'` for the `.yaml` list items, and `grep -c '^case='`
(excluding the `.log` title line) for the `.log` file. Case-id ranges were obtained
by extracting all `audit-v2-s02-t04-NNNNNN` tokens per file, sorting uniquely, and
taking the first and last (`grep -o ... | sort -u | sed -n '1p;$p'`).

Note: an initial read of `audit-v2-s02-t04-evidence-03.csv` returned an output
truncated at case `...000099`; a follow-up direct read at file offset 95 and a
`tail -n 15` on the file confirmed the file's actual last row is case
`...000107`, and `wc -l` independently confirmed 108 total lines. The evidence
table above reflects the confirmed, complete file content (107 data rows, cases
1–107), not the initially truncated view.

## Comparison

- **Record volume differs by file.** `audit-v2-s02-t04-evidence-03.csv` holds
  the most records (107, cases 1–107). `audit-v2-s02-t04-evidence-05.log` holds
  99 (cases 1–99). `audit-v2-s02-t04-evidence-01.md` and
  `audit-v2-s02-t04-evidence-04.yaml` each hold 94 (cases 1–94). 
  `audit-v2-s02-t04-evidence-02.jsonl` holds the fewest, 91 (cases 1–91).
- **All five files start at case `audit-v2-s02-t04-000001`**, and in every file
  the record count equals `(last case number − first case number + 1)`, so each
  file's case-id range is contiguous with no gaps, as observed directly in each
  file (confirmed via the case-id extraction commands above).
- **All five files use the same four `system` values**
  (`freebsd-x86_64`, `linux-x86_64`, `macos-arm64`, `windows-x86_64`) and the
  same four `status` values (`follow-up`, `recorded`, `review`, `supported`),
  confirmed by extracting and uniquing these fields from
  `audit-v2-s02-t04-evidence-01.md` and `audit-v2-s02-t04-evidence-02.jsonl`
  directly, and by reading the full content of
  `audit-v2-s02-t04-evidence-03.csv`, `audit-v2-s02-t04-evidence-04.yaml`, and
  `audit-v2-s02-t04-evidence-05.log`.
- **The system/status pairing cycles in a fixed repeating pattern across all
  five files**: case numbers ≡ 1 (mod 4) pair `linux-x86_64` with `review`,
  ≡ 2 (mod 4) pair `windows-x86_64` with `recorded`, ≡ 3 (mod 4) pair
  `freebsd-x86_64` with `follow-up`, and ≡ 0 (mod 4) pair `macos-arm64` with
  `supported`. This was verified by direct inspection of every case record in
  each file during the full read.
- **Case 1 is recorded identically in content across all five formats** (spot
  checked directly against `audit-v2-s02-t04-evidence-03.csv`,
  `audit-v2-s02-t04-evidence-04.yaml`, and `audit-v2-s02-t04-evidence-05.log`,
  and by the full-file reads of `audit-v2-s02-t04-evidence-01.md` and
  `audit-v2-s02-t04-evidence-02.jsonl`): `system=linux-x86_64`,
  `status=review`, and a `note` field stating "audit-v2-s02 source evidence for
  client telemetry samples records review on linux-x86_64. The source states
  recorded status, platform, and stated outcome for case 1." The wording of
  this note is identical in substance across formats for the same case number,
  varying only in each format's field syntax (Markdown bullet, JSON object,
  CSV row, YAML mapping, or `key=value` log line).
- **No file states why its own record count differs from the others', or which
  file (if any) is authoritative.** None of the five sources contains any
  header, footer, or note field asserting completeness, a canonical count, or a
  reason for the differing upper bounds (94, 91, 107, 94, 99). This report does
  not infer a reason, since none of the sources states one.

## Handoff note

- Five client-telemetry evidence files exist for audit-v2-s02 turn 4, one per
  format (`.md`, `.jsonl`, `.csv`, `.yaml`, `.log`), each listing the same kind
  of record (`case`, `system`, `status`, `note`) but with differing record
  counts: 94, 91, 107, 94, and 99 respectively, all starting at case 1 with no
  internal gaps.
- Case `1` through the shortest file's bound (case 91, from
  `audit-v2-s02-t04-evidence-02.jsonl`) is recorded consistently (same
  `system`/`status`/`note` content, modulo format syntax) across all five
  files, per spot-checks and full reads.
- `audit-v2-s02-t04-evidence-03.csv` is the only source that extends to case
  107; `audit-v2-s02-t04-evidence-05.log` is the only other source past case
  94, extending to case 99. Neither file states why it has more records than
  the others.
- This maintenance review made no comparison to, and drew no conclusions about,
  any product code, fixture, route, configuration, or test in the audit-log
  service repository. It is confined to the five source files listed above.
- No product code, fixtures, routes, configuration, or tests were modified in
  the course of this review.
